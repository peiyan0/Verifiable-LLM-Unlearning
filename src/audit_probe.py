"""Independent membership-inference audit probe (FR4, TB4 trust boundary).

Real code paths only: scores come from model forward passes supplied by the
caller; no random distributions are generated here (ds.md F1/F4).

Implements ds.md A6: confidence intervals use an **author-clustered** bootstrap
(resample authors, not records), matching Proposal Sec. 5.4.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score

from .paths import save_json


def sequence_logprob(model, tokenizer, question: str, answer: str, max_len: int = 256) -> float:
    """Answer-only log-probability of ``answer`` given ``question``.

    Prompt tokens are masked with label -100 so this is directly comparable to
    ``utility_evaluator.compute_record_loss`` (ds.md F9/C5).
    Returns total (not mean) log-prob; higher = more "member-like".
    """
    import torch

    prompt = f"Question: {question}\nAnswer: "
    dev = next(model.parameters()).device
    enc = tokenizer(prompt + answer, return_tensors="pt", truncation=True, max_length=max_len)
    prompt_enc = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=max_len)
    prompt_len = min(prompt_enc["input_ids"].shape[1], enc["input_ids"].shape[1])

    ids = enc["input_ids"].to(dev)
    labels = ids.clone()
    labels[:, :prompt_len] = -100  # mask the prompt

    with torch.no_grad():
        logits = model(input_ids=ids).logits[:, :-1, :]
        targets = ids[:, 1:]
        lab = labels[:, 1:]
        logsm = torch.log_softmax(logits.float(), dim=-1)
        tok_lp = logsm.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
        mask = lab != -100
        if int(mask.sum()) == 0:
            return 0.0
        return float(tok_lp[mask].mean().item())


def mia_scores_to_arrays(score_pairs):
    """score_pairs: iterable of (label, score) with label 1 = forget(member)."""
    y = np.array([p[0] for p in score_pairs], dtype=int)
    s = np.array([p[1] for p in score_pairs], dtype=float)
    return y, s


def auc_forget_vs_nonmember(forget_scores, nonmember_scores) -> dict:
    """AUC where the positive class is 'forget record'. Chance level = 0.5."""
    y = np.r_[np.ones(len(forget_scores)), np.zeros(len(nonmember_scores))]
    s = np.r_[np.asarray(forget_scores, dtype=float), np.asarray(nonmember_scores, dtype=float)]
    if len(np.unique(y)) < 2:
        raise ValueError("Both forget and non-member samples are required")
    return {"MIA_AUC": float(roc_auc_score(y, s)), "n_forget": int(len(forget_scores)),
            "n_nonmember": int(len(nonmember_scores))}


def tpr_at_fpr(forget_scores, nonmember_scores, target_fpr: float = 0.01) -> float:
    """TPR of a member-vs-nonmember attack at a fixed FPR set on non-members."""
    f = np.asarray(forget_scores, dtype=float)
    h = np.asarray(nonmember_scores, dtype=float)
    thr = float(np.quantile(h, 1.0 - target_fpr))
    return float((f >= thr).mean())


def author_cluster_bootstrap(forget_by_author, nonmember_by_author, n_boot: int = 1000,
                            seed: int = 42, alpha: float = 0.05) -> dict:
    """95% CI for MIA AUC by resampling AUTHORS with replacement (ds.md A6).

    Parameters map author_id -> array of scores. The effective sample size is the
    number of authors per side, which is what the proposal's Sec. 5.4 requires.
    """
    rng = np.random.default_rng(seed)
    fa, ha = list(forget_by_author.keys()), list(nonmember_by_author.keys())
    if not fa or not ha:
        raise ValueError("Empty author groups - cannot bootstrap")
    aucs = []
    for _ in range(n_boot):
        fs_idx = rng.choice(fa, size=len(fa), replace=True)
        hs_idx = rng.choice(ha, size=len(ha), replace=True)
        fs = np.concatenate([np.asarray(forget_by_author[a], dtype=float) for a in fs_idx])
        hs = np.concatenate([np.asarray(nonmember_by_author[a], dtype=float) for a in hs_idx])
        try:
            aucs.append(roc_auc_score(np.r_[np.ones(len(fs)), np.zeros(len(hs))], np.r_[fs, hs]))
        except ValueError:
            continue
    if len(aucs) < max(50, n_boot // 10):
        raise ValueError("Too few valid bootstrap replicates to report a CI")
    lo, hi = np.percentile(aucs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {
        "bootstrap_method": "author-clustered (resample authors with replacement)",
        "n_authors_forget": len(fa),
        "n_authors_nonmember": len(ha),
        "n_replicates_used": len(aucs),
        "auc_mean": float(np.mean(aucs)),
        "ci_lower": float(lo),
        "ci_upper": float(hi),
        "alpha": alpha,
    }


def evaluate_audit_metrics(model, tokenizer, forget_rows, nonmember_rows, n_boot=1000, seed=42,
                           score_fn=None) -> dict:
    """Full audit: score every record, compute AUC, TPR@1%FPR, clustered CI.

    ``score_fn(model, tokenizer, row) -> float`` defaults to the negated
    answer-only log-probability (members have lower loss => higher score).
    """
    score_fn = score_fn or (lambda m, t, r: -sequence_logprob(m, t, r["question"], r["answer"]))
    forget_scores = [score_fn(model, tokenizer, r) for r in forget_rows]
    non_scores = [score_fn(model, tokenizer, r) for r in nonmember_rows]

    f_by_a, n_by_a = {}, {}
    for r, s in zip(forget_rows, forget_scores):
        f_by_a.setdefault(r.get("author_cluster", "unknown"), []).append(s)
    for r, s in zip(nonmember_rows, non_scores):
        n_by_a.setdefault(r.get("author_cluster", "unknown"), []).append(s)

    point = auc_forget_vs_nonmember(forget_scores, non_scores)
    point["TPR_at_1pct_FPR"] = tpr_at_fpr(forget_scores, non_scores, 0.01)
    boot = author_cluster_bootstrap(f_by_a, n_by_a, n_boot=n_boot, seed=seed)
    rec_boot = author_cluster_bootstrap(
        {"all": forget_scores}, {"all": non_scores}, n_boot=n_boot, seed=seed)
    return {
        "MIA_AUC": point["MIA_AUC"],
        "TPR_at_1pct_FPR": point["TPR_at_1pct_FPR"],
        "n_forget": point["n_forget"],
        "n_nonmember": point["n_nonmember"],
        "author_clustered_ci": boot,
        "record_level_ci_deprecated": rec_boot,
        "scoring": "negative answer-only log-probability (prompt masked with -100)",
    }


def write_audit_result(name: str, metrics: dict, extra: dict | None = None) -> str:
    payload = dict(extra or {})
    payload.update(metrics)
    p = save_json(name, payload)
    return str(p)
