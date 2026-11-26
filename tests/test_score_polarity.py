"""Regression test for MIA score polarity (higher = more member-like)."""
from __future__ import annotations

import pytest

from src.audit_probe import evaluate_audit_metrics


def test_member_scores_higher_than_nonmember():
    forget_rows = [
        {"question": f"q{i}", "answer": f"a{i}", "author_cluster": f"f{i // 2}", "is_member": True}
        for i in range(10)
    ]
    nonmember_rows = [
        {"question": f"q{i}", "answer": f"a{i}", "author_cluster": f"h{i // 2}", "is_member": False}
        for i in range(10)
    ]

    # Higher log-prob (less negative) for members than non-members
    def mock_logprob(_m, _t, row):
        return -0.5 if row["is_member"] else -2.5

    res = evaluate_audit_metrics(
        None, None, forget_rows, nonmember_rows, n_boot=50, seed=42, score_fn=mock_logprob
    )
    assert res["MIA_AUC"] == pytest.approx(1.0)
    assert res["TPR_at_1pct_FPR"] == pytest.approx(1.0)
    assert res["author_clustered_ci"]["ci_lower"] > 0.9
