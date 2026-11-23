#!/usr/bin/env python3
"""Real parameter-update sweep (ds.md F3/A2/A3, C1).

Replaces the old loop that iterated over ``print()`` stubs: every run here
performs actual gradient steps on actual parameters, and the ledger payload
records what really happened (steps, loss deltas, wall-clock, backend,
accounting) so timings are meaningful.

The matrix is read from ``pilot_config.json`` (single source of truth, ds.md
C1): seeds x epsilon_sweep x methods = 3 x 3 x 3 = 27 runs by default.

Model choice:
* Default ``microsoft/phi-1.5`` requires a GPU (Colab T4).
* For CPU verification of the *mechanics* pass a tiny model and a small TOFU
  slice; the script then stamps every ledger entry with the model id so the
  evidence trail distinguishes pipeline checks from pilot results.

Usage:
    python experiments/run_real_sweep.py --device cuda
    python experiments/run_real_sweep.py --model sshleifer/tiny-gpt2 \
        --n-forget 8 --n-retain 16 --max-steps 3 --ledger data/sweep_check_ledger.json
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch  # noqa: E402

from src.audit_logger import CryptographicAuditLogger  # noqa: E402
from src.paths import load_config  # noqa: E402
from src.statistical_tests import UnlearningSignificanceTester  # noqa: E402
from src.tofu_data import read_cache  # noqa: E402
from src.unlearning_engine import UnlearningEngine  # noqa: E402


def build_model(name: str, device: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(name)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        name, torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32)
    return model.to(device), tok


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="microsoft/phi-1.5")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--n-forget", type=int, default=64)
    ap.add_argument("--n-retain", type=int, default=64)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--ledger", default=None)
    args = ap.parse_args()

    splits, _ = read_cache()
    forget = splits["forget10"][:args.n_forget]
    retain = splits["retain90"][:args.n_retain]

    base_model, tok = build_model(args.model, args.device)
    logger = (CryptographicAuditLogger(args.ledger) if args.ledger
              else CryptographicAuditLogger())
    tester = UnlearningSignificanceTester()

    seeds = cfg["seeds"]
    epsilons = cfg["privacy"]["epsilon_sweep"]
    methods = cfg["sweep"]["methods"]
    durations = {m: [] for m in methods}
    n_runs = 0

    print(f"Sweep matrix: {len(seeds)} seeds x {len(epsilons)} epsilons x "
          f"{len(methods)} methods = {len(seeds)*len(epsilons)*len(methods)} real runs "
          f"(model={args.model}, device={args.device})")

    for seed in seeds:
        for eps in epsilons:
            for method in methods:
                # Each run starts from the SAME checkpoint so runs are comparable.
                model = copy.deepcopy(base_model)
                engine = UnlearningEngine(model, tok, forget, retain,
                                          device=args.device, config=cfg)
                t0 = time.perf_counter()
                if method == "DP2Unlearning":
                    _, rec = engine.run_dp2unlearning(
                        epsilon=eps, delta=cfg["privacy"]["delta"],
                        epochs=cfg["training"]["unlearn_epochs"],
                        lr=cfg["training"]["unlearn_lr"],
                        max_grad_norm=cfg["privacy"]["max_grad_norm"],
                        batch_size=cfg["training"]["batch_size"],
                        seed=seed, max_steps=args.max_steps)
                elif method == "Gradient_Ascent":
                    _, rec = engine.run_gradient_ascent(
                        epochs=cfg["training"]["unlearn_epochs"],
                        lr=cfg["training"]["unlearn_lr"],
                        retain_weight=cfg["training"]["ga_retain_weight"],
                        batch_size=cfg["training"]["batch_size"],
                        seed=seed, max_steps=args.max_steps)
                elif method == "Projected_Gradient_Unlearning":
                    _, rec = engine.run_projected_gradient_unlearning(
                        epochs=cfg["training"]["unlearn_epochs"],
                        lr=cfg["training"]["unlearn_lr"],
                        batch_size=cfg["training"]["batch_size"],
                        seed=seed, max_steps=args.max_steps)
                else:
                    raise ValueError(f"Unknown method {method!r} in pilot_config.json")
                elapsed = time.perf_counter() - t0
                durations[method].append(elapsed)
                n_runs += 1
                payload = {
                    "seed": seed, "epsilon": eps, "method": method,
                    "duration_seconds": elapsed,
                    "model": args.model, "device": args.device,
                    **rec,
                }
                logger.log_event("EXPERIMENT_RUN", payload)
                print(f"[{n_runs:02d}] {method:<32} eps={eps:<4} seed={seed:<5} "
                      f"steps={rec.get('steps')} {elapsed:.2f}s", flush=True)

    # Paired-by-seed-order comparison DP2U vs GA on wall-clock (RQ1).
    if len(durations["DP2Unlearning"]) == len(durations["Gradient_Ascent"]) >= 2:
        stat = tester.run_signed_rank_test(
            durations["DP2Unlearning"], durations["Gradient_Ascent"],
            hypothesis_name="RQ1_Execution_Overhead_DP2U_vs_GA")
        logger.log_event("SWEEP_STATISTICS", {"runs": n_runs, **stat})
        print("RQ1:", stat["message"])

    ok, msg = logger.verify_ledger_integrity()
    print(f"Sweep complete: {n_runs} real runs. Ledger integrity verified={ok}: {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
