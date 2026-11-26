#!/usr/bin/env python3
"""End-to-end real pilot: fine-tune -> positive control -> GA -> DP2U -> utility -> signed cert.

Implements ds.md A1, A2, A3, A4, A5, B3 (utility row) and produces the evidence
files that ``tests/compliance_verification_tests.py`` consumes:

    results/ft_audit.json      positive control on the fine-tuned model  (A1)
    results/ga_audit.json      MIA audit after real gradient ascent      (A2)
    results/dp2u_audit.json    MIA audit after real DP2U / DP-SGD        (A3)
    results/utility_eval.json  PR3 retain-utility retention              (B3)
    results/pr1_isolation.json trust-boundary isolation check            (PR1)
    results/pilot_certificate.json  HMAC-signed certificate (A5), built ONLY
                                    from the JSONs above (A4)

No random score distributions are generated anywhere in this script (ds.md F1).
Every number written to disk comes from a model forward/backward pass.

Hardware note: on a machine without CUDA the Phi-1.5B weights cannot fit; use
``--model sshleifer/tiny-gpt2`` for a smoke test of the *pipeline* (the audit
numbers it writes are NOT pilot results — the script stamps every output with
the model id so a marker can tell the difference).

Usage (Colab T4 or better):
    python scripts/run_pilot_audit.py --device cuda
Local smoke test:
    python scripts/run_pilot_audit.py --model sshleifer/tiny-gpt2 --n-forget 40 \
        --n-holdout 40 --ft-epochs 2 --max-steps 20
"""
from __future__ import annotations

import argparse
import copy
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch  # noqa: E402

from src.audit_logger import CryptographicAuditLogger  # noqa: E402
from src.audit_probe import evaluate_audit_metrics, write_audit_result  # noqa: E402
from src.cert_signer import build_certificate, load_or_create_dev_key  # noqa: E402
from src.paths import RESULTS_DIR, load_config, save_json  # noqa: E402
from src.tofu_data import read_cache  # noqa: E402
from src.trust_boundary_proxy import SecurityError, TrustBoundaryProxy  # noqa: E402
from src.unlearning_engine import UnlearningEngine  # noqa: E402
from src import utility_metrics  # noqa: E402


def parse_args():
    cfg = load_config()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default=os.environ.get("PILOT_BASE_MODEL",
                     "microsoft/phi-1.5"))
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--bits", type=int, default=4, help="4-bit NF4 via bitsandbytes on GPU")
    p.add_argument("--n-forget", type=int, default=cfg["data"]["pilot_forget_records"])
    p.add_argument("--n-holdout", type=int, default=cfg["data"]["pilot_nonmember_records"])
    p.add_argument("--n-retain", type=int, default=400,
                   help="retain rows used for fine-tuning/unlearning (pilot budget)")
    p.add_argument("--ft-epochs", type=int, default=cfg["training"]["fine_tune_epochs"])
    p.add_argument("--unlearn-epochs", type=int, default=cfg["training"]["unlearn_epochs"])
    p.add_argument("--batch-size", type=int, default=cfg["training"]["batch_size"])
    p.add_argument("--max-steps", type=int, default=None,
                   help="cap optimiser steps per phase (smoke tests only)")
    p.add_argument("--epsilon", type=float, default=max(cfg["privacy"]["epsilon_sweep"]),
                   help="DP2U budget (single value for the pilot audit)")
    p.add_argument("--seed", type=int, default=cfg["seeds"][0])
    p.add_argument("--ledger", default=None,
                   help="audit ledger path (default: data/audit_ledger.json)")
    return p.parse_args()


def attach_lora(model, cfg):
    """Add LoRA adapters (proposal design). Falls back to full fine-tune."""
    try:
        from peft import LoraConfig, TaskType, get_peft_model
        lora = LoraConfig(task_type=TaskType.CAUSAL_LM, r=8, lora_alpha=16, lora_dropout=0.05,
                          target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
        model = get_peft_model(model, lora)
        model.print_trainable_parameters()
        return model, "lora-peft"
    except ImportError:
        for prm in model.parameters():
            prm.requires_grad = True
        return model, "full-finetune (peft not installed)"


def load_base_model(name: str, device: str, bits: int):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(name)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    kwargs = {"torch_dtype": torch.bfloat16 if device == "cuda" else torch.float32}
    if device == "cuda" and bits == 4:
        from transformers import BitsAndBytesConfig
        kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True,
                                                           bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(name, **kwargs)
    if device != "cuda" or bits != 4:
        model = model.to(device)
    return model, tok


def encode_rows(tokenizer, rows, max_len):
    """Pre-encode rows into input_ids/labels tensors (answer-only loss)."""
    enc = {"input_ids": [], "labels": []}
    for r in rows:
        prompt = f"Question: {r['question']}\nAnswer: "
        e = tokenizer(prompt + r["answer"], truncation=True, max_length=max_len)
        t = tokenizer(prompt, truncation=True, max_length=max_len)
        labels = list(e["input_ids"])
        n_mask = min(len(t["input_ids"]), len(labels))
        labels[:n_mask] = [-100] * n_mask
        enc["input_ids"].append(e["input_ids"])
        enc["labels"].append(labels)
    return enc


def supervised_loss(model, batch_enc, idx, device, bs):
    ids = [torch.tensor(batch_enc["input_ids"][i], device=device) for i in idx]
    labs = [torch.tensor(batch_enc["labels"][i], device=device) for i in idx]
    n = max(x.shape[0] for x in ids)
    pad_id = 0
    ids = torch.stack([torch.nn.functional.pad(x, (0, n - x.shape[0]), value=pad_id) for x in ids])
    labs = torch.stack([torch.nn.functional.pad(x, (0, n - x.shape[0]), value=-100) for x in labs])
    attn = (ids != pad_id).long()
    return model(input_ids=ids, attention_mask=attn, labels=labs).loss


def fine_tune(model, tokenizer, rows, epochs, lr, bs, seed, max_steps, tag):
    """Real CE training loop on ``rows`` (prompt masked). Returns loss trace."""
    torch.manual_seed(seed)
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    enc = encode_rows(tokenizer, rows, max_len=192)
    dev = next(model.parameters()).device
    g = torch.Generator().manual_seed(seed)
    trace, steps = [], 0
    for ep in range(epochs):
        order = torch.randperm(len(rows), generator=g).tolist()
        for s in range(0, len(order), bs):
            batch = order[s:s + bs]
            opt.zero_grad(set_to_none=True)
            loss = supervised_loss(model, enc, batch, dev, bs)
            loss.backward()
            opt.step()
            trace.append(float(loss.detach()))
            steps += 1
            print(f"[{tag}] step {steps} loss {trace[-1]:.4f}", flush=True)
            if max_steps and steps >= max_steps:
                model.eval()
                return trace
    model.eval()
    return trace


def audit_and_write(name, model, tokenizer, forget_rows, holdout_rows, cfg, extra):
    metrics = evaluate_audit_metrics(
        model, tokenizer, forget_rows, holdout_rows,
        n_boot=cfg["audit"]["n_boot"], seed=cfg["audit"]["bootstrap_seed"])
    payload = {"generated_by": "scripts/run_pilot_audit.py", **extra, **metrics}
    path = write_audit_result(name, payload)
    print(f"[audit] {name}: AUC={metrics['MIA_AUC']:.4f} "
          f"TPR@1%={metrics['TPR_at_1pct_FPR']:.4f} -> {path}", flush=True)
    return payload


def main():
    args = parse_args()
    cfg = load_config()
    torch.manual_seed(args.seed)

    splits, provenance = read_cache()
    forget = splits["forget10"][:args.n_forget]
    holdout = splits["holdout10"][:args.n_holdout]
    retain = splits["retain90"][:args.n_retain]
    print(f"[data] forget={len(forget)} holdout={len(holdout)} retain={len(retain)} "
          f"(real locuslab/TOFU cache)")

    run_meta = {
        "base_model": args.model,
        "device": args.device,
        "seed": args.seed,
        "config_epsilon_sweep": cfg["privacy"]["epsilon_sweep"],
        "dataset": provenance["provenance"]["dataset_id"],
        "author_cluster_method": provenance["disjointness"]["cluster_method"],
    }

    # ---- PR1 isolation (trust boundary must reject engine access to holdout)
    proxy = TrustBoundaryProxy(role="engine")
    pr1_pass, overlap = True, 0
    try:
        proxy.request_dataset("holdout10_reference_set")
        pr1_pass = False  # should never be granted
    except SecurityError:
        pass
    iso = proxy.validate_split_disjointness(
        [r["record_hash"] for r in retain], [r["record_hash"] for r in forget],
        [r["record_hash"] for r in holdout])
    overlap = iso["overlap"]
    pr1_pass = pr1_pass and overlap == 0
    save_json("pr1_isolation.json", {"generated_by": "scripts/run_pilot_audit.py",
                                     "overlap": overlap, "pr1_pass": pr1_pass,
                                     "deny_log": proxy.deny_log, **run_meta})

    logger = CryptographicAuditLogger(args.ledger) if args.ledger else CryptographicAuditLogger()

    # ---- Positive control (A1): fine-tune base on retain+forget, audit.
    model, tok = load_base_model(args.model, args.device, args.bits)
    model, adapter = attach_lora(model, cfg)
    run_meta["adapter"] = adapter
    ft_trace = fine_tune(model, tok, retain + forget, args.ft_epochs,
                         cfg["training"]["fine_tune_lr"], args.batch_size, args.seed,
                         args.max_steps, "finetune")
    logger.log_event("FINE_TUNE_COMPLETE", {"model": args.model, "steps": len(ft_trace),
                                            "final_loss_mean": ft_trace[-5:], **run_meta})
    ft_audit = audit_and_write("ft_audit.json", model, tok, forget, holdout, cfg,
                               {**run_meta, "role": "positive_control",
                                "criterion": f"AUC >= {cfg['audit']['mia_auc_positive_control_min']}"})
    logger.log_event("AUDIT_POSITIVE_CONTROL", {"MIA_AUC": ft_audit["MIA_AUC"],
                                                "evidence": "results/ft_audit.json"})

    # ---- Snapshot the fine-tuned (attacked) state as the unlearning starting point.
    ft_state = copy.deepcopy({k: v.detach().clone() for k, v in
                              model.state_dict().items() if v.dtype in (torch.float32, torch.bfloat16)})

    def reset_to_ft(m):
        live = m.state_dict()
        m.load_state_dict({k: ft_state[k] for k in ft_state}, strict=False)

    # ---- GA (A2): real gradient ascent on forget set, audit afterwards.
    engine = UnlearningEngine(model, tok, forget, retain, device=args.device, config=cfg)
    _, ga_rec = engine.run_gradient_ascent(epochs=args.unlearn_epochs,
                                           lr=cfg["training"]["unlearn_lr"],
                                           retain_weight=cfg["training"]["ga_retain_weight"],
                                           batch_size=args.batch_size, seed=args.seed,
                                           max_steps=args.max_steps)
    ga_rec.update(run_meta)
    logger.log_event("UNLEARN_GA", ga_rec)
    ga_audit = audit_and_write("ga_audit.json", model, tok, forget, holdout, cfg,
                               {**run_meta, "role": "post_ga", "ga_record": ga_rec})

    # ---- DP2U (A3): reset to fine-tuned state, DP-SGD on retain only.
    reset_to_ft(model)
    _, dp_rec = engine.run_dp2unlearning(epsilon=args.epsilon, delta=cfg["privacy"]["delta"],
                                         epochs=args.unlearn_epochs,
                                         lr=cfg["training"]["unlearn_lr"],
                                         max_grad_norm=cfg["privacy"]["max_grad_norm"],
                                         batch_size=args.batch_size, seed=args.seed,
                                         max_steps=args.max_steps)
    dp_rec.update(run_meta)
    logger.log_event("UNLEARN_DP2U", dp_rec)
    dp2u_audit = audit_and_write("dp2u_audit.json", model, tok, forget, holdout, cfg,
                                 {**run_meta, "role": "post_dp2u", "dp2u_record": dp_rec})

    # ---- Utility (PR3): token-F1 ratio of post-DP2U model vs the fine-tuned reference.
    em_un = utility_metrics.token_f1(model, tok, retain, limit=20)
    un_ce = utility_metrics.answer_ce(model, tok, retain, limit=50)
    reset_to_ft(model)
    em_ref = utility_metrics.token_f1(model, tok, retain, limit=20)
    ref_ce = utility_metrics.answer_ce(model, tok, retain, limit=50)
    util = {
        "generated_by": "scripts/run_pilot_audit.py",
        "unlearned_answer_ce": un_ce,
        "reference_answer_ce": ref_ce,
        "reference_note": "reference = fine-tuned checkpoint before unlearning",
        **run_meta,
    }
    util.update(utility_metrics.utility_retention(em_un, em_ref,
                                                  cfg["utility"]["retention_threshold_f1_ratio"]))
    save_json("utility_eval.json", util)
    logger.log_event("UTILITY_EVAL", {"f1_ratio": util.get("f1_ratio"),
                                      "evidence": "results/utility_eval.json"})

    # ---- Signed certificate from REAL results only (A4/A5).
    key, key_id = load_or_create_dev_key()
    real_metrics = {
        "positive_control": {"MIA_AUC": ft_audit["MIA_AUC"],
                             "author_clustered_ci": ft_audit["author_clustered_ci"]},
        "dp2u_audit": {"MIA_AUC": dp2u_audit["MIA_AUC"],
                       "TPR_at_1pct_FPR": dp2u_audit["TPR_at_1pct_FPR"],
                       "author_clustered_ci": dp2u_audit["author_clustered_ci"]},
        "ga_audit": {"MIA_AUC": ga_audit["MIA_AUC"]},
        "pr1_pass": pr1_pass, "pr1_overlap": overlap,
        "utility": {"f1_ratio": util.get("f1_ratio")},
        "positive_control_threshold": cfg["audit"]["mia_auc_positive_control_min"],
        "mia_auc_limit": cfg["audit"]["mia_auc_pass_max"],
        "tpr_at_1pct_fpr_limit": cfg["audit"]["tpr_at_1pct_fpr_pass_max"],
    }
    try:
        cert = build_certificate(real_metrics, key, key_id)
        save_json("pilot_certificate.json", cert)
        logger.log_event("CERTIFICATE_ISSUED", {"certificate_id":
                                                cert["certificate_metadata"]["certificate_id"],
                                                "verdict": cert["verdict"]})
        print(f"[cert] verdict={cert['verdict']} -> results/pilot_certificate.json")
    except AssertionError as exc:
        # Honest failure: cannot certify (e.g. positive control below threshold).
        logger.log_event("CERTIFICATE_REFUSED", {"reason": str(exc)})
        print(f"[cert] REFUSED: {exc}", file=sys.stderr)
        return 2

    ok, msg = logger.verify_ledger_integrity()
    print(f"[ledger] integrity verified={ok}: {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
