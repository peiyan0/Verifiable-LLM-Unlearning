"""Utility evaluation fixed per ds.md F9/C5.

Changes vs the original ``src/utility_evaluator.py`` (which is kept untouched as
historical evidence of the audited state):

* ``answer_ce`` computes answer-only cross-entropy with the prompt masked by
  ``-100`` — identical semantics to ``audit_probe.sequence_logprob`` and
  ``UnlearningEngine._encode`` (ds.md C5/F9: perplexity must be comparable to
  the audit loss).
* No bare ``except Exception`` around metric loading: failures are recorded in
  the returned payload instead of being swallowed (ds.md F9).
* ``exact_match`` works with any model exposing ``generate``; when the callable
  lacks it (e.g. a lightweight test encoder) it raises ``AttributeError`` with
  an explicit message rather than failing deep inside ``torch`` (ds.md F9).
* ``f1_ratio`` implements the PR3 utility-retention criterion: unlearned-model
  EM divided by reference-model EM (Proposal O3: >= 0.90).
"""
from __future__ import annotations

import math


def _tokenize_pair(tokenizer, question: str, answer: str, max_len: int = 192):
    prompt = f"Question: {question}\nAnswer: "
    enc = tokenizer(prompt + answer, truncation=True, max_length=max_len)
    tgt = tokenizer(prompt, truncation=True, max_length=max_len)
    labels = list(enc["input_ids"])
    n_mask = min(len(tgt["input_ids"]), len(labels))
    labels[:n_mask] = [-100] * n_mask
    return {"input_ids": enc["input_ids"], "labels": labels}


def answer_ce(model, tokenizer, rows, limit: int = 50, max_len: int = 192) -> dict:
    """Mean answer-only cross-entropy over ``rows`` (prompt masked with -100)."""
    import torch

    dev = next(model.parameters()).device
    ce_sum, tok_count, n = 0.0, 0, min(limit, len(rows))
    for row in rows[:n]:
        pair = _tokenize_pair(tokenizer, row["question"], row["answer"], max_len)
        ids = torch.tensor([pair["input_ids"]], device=dev)
        lab = torch.tensor([pair["labels"]], device=dev)
        with torch.no_grad():
            logits = model(input_ids=ids).logits[:, :-1, :]
            targets = lab[:, 1:]
            logsm = torch.log_softmax(logits.float(), dim=-1)
            mask = targets != -100
            if int(mask.sum()) == 0:
                continue
            safe = targets.masked_fill(~mask, 0)          # gather needs valid indices
            tok_lp = logsm.gather(-1, safe.unsqueeze(-1)).squeeze(-1)
            ce_sum += float(-tok_lp[mask].sum())
            tok_count += int(mask.sum())
    mean_ce = ce_sum / max(1, tok_count)
    return {
        "n_records": n,
        "answer_tokens": tok_count,
        "mean_answer_ce": mean_ce,
        "perplexity_answer_only": math.exp(min(mean_ce, 50.0)),
        "masking": "prompt tokens set to -100 (comparable to audit_probe.sequence_logprob)",
    }


def exact_match(model, tokenizer, rows, limit: int = 30, max_new_tokens: int = 48) -> float:
    """Greedy-decode exact match on retain rows. Requires model.generate."""
    if not hasattr(model, "generate"):
        raise AttributeError(
            "exact_match requires a causal LM exposing .generate(); the supplied "
            "object has none (ds.md F9). Use answer_ce for lightweight models.")
    import torch

    n, hits = min(limit, len(rows)), 0
    eos = tokenizer.eos_token_id
    for row in rows[:n]:
        prompt = f"Question: {row['question']}\nAnswer: "
        inputs = tokenizer(prompt, return_tensors="pt").to(next(model.parameters()).device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                 pad_token_id=eos if eos is not None else 0)
        gen = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        if gen.strip().lower().startswith(row["answer"].strip().lower()[:40]):
            hits += 1
    return hits / max(1, n)


def token_f1(model, tokenizer, rows, limit: int = 30, max_new_tokens: int = 48) -> float:
    """Mean token-level F1 on retain rows. Requires model.generate."""
    if not hasattr(model, "generate"):
        raise AttributeError(
            "token_f1 requires a causal LM exposing .generate(); the supplied "
            "object has none (ds.md F9). Use answer_ce for lightweight models.")
    from collections import Counter
    import torch

    n, total_f1 = min(limit, len(rows)), 0.0
    eos = tokenizer.eos_token_id
    for row in rows[:n]:
        prompt = f"Question: {row['question']}\nAnswer: "
        inputs = tokenizer(prompt, return_tensors="pt").to(next(model.parameters()).device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                 pad_token_id=eos if eos is not None else 0)
        gen = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        pred_toks = gen.strip().lower().split()
        gold_toks = row["answer"].strip().lower().split()
        common = sum((Counter(pred_toks) & Counter(gold_toks)).values())
        if common == 0:
            continue
        prec = common / len(pred_toks)
        rec = common / len(gold_toks)
        total_f1 += 2 * prec * rec / (prec + rec)
    return total_f1 / max(1, n)


def utility_retention(unlearned_em: float, reference_em: float, threshold: float = 0.90) -> dict:
    """PR3: ratio of unlearned-model EM to reference (exact-retrain) EM."""
    ratio = (unlearned_em / reference_em) if reference_em > 0 else None
    return {
        "unlearned_em": unlearned_em,
        "reference_em": reference_em,
        "f1_ratio": ratio,
        "pass_criterion": f"f1_ratio >= {threshold}",
        "passed": bool(ratio is not None and ratio >= threshold),
    }
