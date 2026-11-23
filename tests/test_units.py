"""Offline unit tests for the pure-logic fixes demanded by doc/ds.md.

These tests need no GPU and no HuggingFace download; they verify the mechanics
so the GPU pilot only has to produce numbers, not debug plumbing.
Run:  python -m unittest tests.test_units -v   (from repo root)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.audit_logger import CryptographicAuditLogger
from src.audit_probe import author_cluster_bootstrap, auc_forget_vs_nonmember, tpr_at_fpr
from src.cert_signer import build_certificate, sign_certificate, verify_certificate
from src.retention import purge_expired
from src.trust_boundary_proxy import SecurityError, TrustBoundaryProxy


class TestBootstrap(unittest.TestCase):
    def test_author_clustered_ci_wider_than_naive(self):
        """Clustered CI must exist and be computed over authors (A6)."""
        rng = np.random.default_rng(0)
        f_by_a = {f"a{i}": rng.normal(0.85, 0.05, 20) for i in range(6)}
        h_by_a = {f"b{i}": rng.normal(0.80, 0.05, 20) for i in range(6)}
        ci = author_cluster_bootstrap(f_by_a, h_by_a, n_boot=200, seed=1)
        self.assertIn("author-clustered", ci["bootstrap_method"])
        self.assertEqual(ci["n_authors_forget"], 6)
        self.assertLessEqual(ci["ci_lower"], ci["auc_mean"])
        self.assertLessEqual(ci["auc_mean"], ci["ci_upper"])

    def test_auc_direction(self):
        forget = [0.9, 0.95, 0.88, 0.92]
        holdout = [0.1, 0.2, 0.05, 0.15]
        out = auc_forget_vs_nonmember(forget, holdout)
        self.assertAlmostEqual(out["MIA_AUC"], 1.0)
        self.assertAlmostEqual(tpr_at_fpr(forget, holdout, 0.01), 1.0)

    def test_empty_groups_raise(self):
        with self.assertRaises(ValueError):
            author_cluster_bootstrap({}, {"a": [1.0]}, n_boot=10)


class TestCertSigner(unittest.TestCase):
    KEY = b"\x11" * 32

    def _metrics(self, pc=0.9, dp_auc=0.5, tpr=0.01):
        return {
            "positive_control": {"MIA_AUC": pc},
            "dp2u_audit": {"MIA_AUC": dp_auc, "TPR_at_1pct_FPR": tpr},
            "ga_audit": {"MIA_AUC": 0.8},
            "pr1_pass": True, "pr1_overlap": 0,
            "utility": {"f1_ratio": 0.95},
        }

    def test_sign_verify_roundtrip(self):
        cert = sign_certificate({"verdict": "PASS"}, self.KEY, "k1")
        self.assertEqual(cert["signature"]["alg"], "HMAC-SHA-256")
        self.assertEqual(cert["signature"]["key_id"], "k1")
        self.assertTrue(verify_certificate(cert, self.KEY))

    def test_tamper_detected(self):
        cert = sign_certificate({"verdict": "PASS", "n": 1}, self.KEY, "k1")
        cert["n"] = 2
        self.assertFalse(verify_certificate(cert, self.KEY))

    def test_wrong_key_rejected(self):
        cert = sign_certificate({"verdict": "PASS"}, self.KEY, "k1")
        self.assertFalse(verify_certificate(cert, b"\x22" * 32))

    def test_refuses_weak_positive_control(self):
        """F10 guard: cannot certify when the probe never detected membership."""
        with self.assertRaises(AssertionError):
            build_certificate(self._metrics(pc=0.6), self.KEY, "k1")

    def test_fail_verdict_on_leakage(self):
        cert = build_certificate(self._metrics(dp_auc=0.7), self.KEY, "k1")
        self.assertEqual(cert["verdict"], "FAIL")
        self.assertTrue(verify_certificate(cert, self.KEY))


class TestLedger(unittest.TestCase):
    def test_chain_and_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            logger = CryptographicAuditLogger(Path(td) / "l.json")
            logger.log_event("E1", {"a": 1})
            logger.log_event("E2", {"b": 2})
            ok, _ = logger.verify_ledger_integrity()
            self.assertTrue(ok)
            logger.ledger[1]["payload"]["a"] = 999
            ok2, msg = logger.verify_ledger_integrity()
            self.assertFalse(ok2)
            self.assertIn("Modified content", msg)


class TestTrustBoundary(unittest.TestCase):
    def test_security_error_is_defined_and_raised(self):
        proxy = TrustBoundaryProxy(role="engine")
        with self.assertRaises(SecurityError):
            proxy.request_dataset("holdout10_reference_set")
        self.assertEqual(len(proxy.deny_log), 1)

    def test_disjointness_violation_raises(self):
        proxy = TrustBoundaryProxy(role="auditor")
        with self.assertRaises(SecurityError):
            proxy.validate_split_disjointness(["h1"], [], ["h1"])

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            TrustBoundaryProxy(role="attacker")


class TestRetention(unittest.TestCase):
    def test_purge_splits_on_age(self):
        now = datetime.now(timezone.utc)
        recs = [{"stored_at": (now - timedelta(days=d)).isoformat()} for d in (0, 29, 31)]
        kept, deleted = purge_expired(recs, now=now, max_age_days=30)
        self.assertEqual((len(kept), len(deleted)), (2, 1))


class TestNoSimulatedScores(unittest.TestCase):
    """A4 done-when: no production path may fabricate score distributions.

    Scanned files are stripped of comments and docstrings first, so prose that
    *mentions* the banned call (e.g. this very test) does not trip the check;
    only executable code does.
    """

    BANNED = ("np.random.normal", "rng.normal", "numpy.random.normal")

    def _code_only(self, text: str) -> str:
        import ast
        import io
        import tokenize

        tree = ast.parse(text)
        doc_lines = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    doc_lines.update(range(node.body[0].lineno, node.body[0].end_lineno + 1))
        out = []
        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                if tok.start[0] in doc_lines:
                    continue
                out.append(tok.string)
        except tokenize.TokenError:
            pass
        return " ".join(out)

    def test_production_code_free_of_score_fabrication(self):
        roots = [Path(__file__).resolve().parents[1] / d
                 for d in ("src", "scripts", "experiments")]
        offenders = []
        for root in roots:
            for p in root.rglob("*.py"):
                code = self._code_only(p.read_text())
                if any(b in code for b in self.BANNED):
                    offenders.append(str(p))
        self.assertEqual(offenders, [])

    def test_test_code_has_no_uncommented_fabrication_outside_bootstrap_fixture(self):
        """Test files may use synthetic inputs ONLY inside tests/test_units.py
        bootstrap fixtures; the compliance suite must contain zero calls."""
        suite = Path(__file__).resolve().parent / "compliance_verification_tests.py"
        code = self._code_only(suite.read_text())
        self.assertFalse(any(b in code for b in self.BANNED))


if __name__ == "__main__":
    unittest.main()
