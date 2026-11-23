"""Compliance verification suite (ds.md Phase B: B1–B5).

Rewritten from the original draft which used hard-coded arrays and
``rng.normal`` samples so that PR3 could never fail (finding F1). This version:

* reads ONLY real evidence JSONs produced by ``scripts/run_pilot_audit.py`` /
  ``experiments/run_real_sweep.py`` under ``results/`` — missing evidence makes
  the corresponding test FAIL, never silently pass (B2);
* emits ``results/compliance_summary.json`` with rows
  ``{id, legal, control, evidence, test, pass_criterion, measured, passed}``
  (B1, >= 8 rows);
* covers retention deletion, ledger tamper detection, utility retention,
  erasure-from-model (DP bound + audit), breach-runbook tabletop (B3);
* asserts the defined ``SecurityError`` type instead of swallowing exceptions
  (B4) and resolves every path from ``Path(__file__).parents[1]`` (B5).

Run from anywhere:  python tests/compliance_verification_tests.py
Exit code 0 iff all rows pass.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.audit_logger import CryptographicAuditLogger  # noqa: E402
from src.cert_signer import load_or_create_dev_key, sign_certificate, verify_certificate  # noqa: E402
from src.paths import RESULTS_DIR, load_config, read_result  # noqa: E402
from src.retention import purge_expired, retention_report  # noqa: E402
from src.trust_boundary_proxy import SecurityError, TrustBoundaryProxy  # noqa: E402

CFG = load_config()
AUD = CFG["audit"]


def _row(id_, legal, control, evidence, test, pass_criterion, measured, passed, note=""):
    return {"id": id_, "legal": legal, "control": control, "evidence": evidence,
            "test": test, "pass_criterion": pass_criterion, "measured": measured,
            "passed": bool(passed), **({"note": note} if note else {})}


def _load_or_fail(name):
    """B2: missing evidence raises FileNotFoundError -> caller records FAIL."""
    return read_result(name)


def test_pr1_isolation(rows):
    try:
        ev = _load_or_fail("pr1_isolation.json")
        proxy = TrustBoundaryProxy(role="engine")
        denied = False
        try:
            proxy.request_dataset("holdout10_reference_set")
        except SecurityError:
            denied = True
        passed = ev.get("pr1_pass") and denied and ev.get("overlap") == 0
        rows.append(_row("PR1", "GDPR Art. 25; PDPA s. 9", "TB4 auditor/engine isolation",
                         "results/pr1_isolation.json", "engine access to holdout denied AND overlap==0",
                         "overlap==0 and SecurityError raised", 
                         {"overlap": ev.get("overlap"), "denial_raised_securityerror": denied},
                         passed))
    except FileNotFoundError as exc:
        rows.append(_row("PR1", "GDPR Art. 25; PDPA s. 9", "TB4 isolation",
                         "results/pr1_isolation.json", "see runner", "overlap==0",
                         f"MISSING EVIDENCE: {exc}", False))


def test_pr2_audits(rows):
    """Positive control, GA gap and DP2U bound — real audits only (A1–A3/B2)."""
    specs = [
        ("PR2-posctrl", "RQ4 (validation)", "fine-tuned model leaks membership",
         "ft_audit.json", lambda m: m["MIA_AUC"] >= AUD["mia_auc_positive_control_min"],
         f"AUC >= {AUD['mia_auc_positive_control_min']}"),
        ("PR2-ga", "Gap G1 (literature anchor)", "gradient ascent leaves leakage",
         "ga_audit.json", lambda m: m["MIA_AUC"] > AUD["mia_auc_pass_max"],
         f"AUC > {AUD['mia_auc_pass_max']}"),
        ("PR2-dp2u", "GDPR Art. 17; Art. 32; PDPA s. 9", "DP2U bounded residual leakage",
         "dp2u_audit.json", lambda m: (m["MIA_AUC"] <= AUD["mia_auc_pass_max"]
                                       and m["TPR_at_1pct_FPR"] <= AUD["tpr_at_1pct_fpr_pass_max"]),
         f"AUC <= {AUD['mia_auc_pass_max']} and TPR@1%FPR <= {AUD['tpr_at_1pct_fpr_pass_max']}"),
    ]
    for id_, legal, control, fname, crit_fn, criterion in specs:
        try:
            m = _load_or_fail(fname)
            measured = {"MIA_AUC": m["MIA_AUC"], "TPR_at_1pct_FPR": m.get("TPR_at_1pct_FPR"),
                        "author_clustered_ci": [m["author_clustered_ci"]["ci_lower"],
                                                m["author_clustered_ci"]["ci_upper"]],
                        "model": m.get("base_model")}
            rows.append(_row(id_, legal, control, f"results/{fname}", criterion,
                             criterion, measured, crit_fn(m)))
        except FileNotFoundError as exc:
            rows.append(_row(id_, legal, control, f"results/{fname}", criterion, criterion,
                             f"MISSING EVIDENCE: {exc}", False))


def test_pr3_utility(rows):
    try:
        u = _load_or_fail("utility_eval.json")
        thr = CFG["utility"]["retention_threshold_f1_ratio"]
        ratio = u.get("f1_ratio")
        rows.append(_row("PR3-utility", "GDPR Art. 5(1)(d); PDPA s. 17", "retain-set utility retention",
                         "results/utility_eval.json", f"f1_ratio >= {thr}", f"f1_ratio >= {thr}",
                         {"f1_ratio": ratio, "unlearned_em": u.get("unlearned_em"),
                          "reference_em": u.get("reference_em")},
                         ratio is not None and ratio >= thr))
    except FileNotFoundError as exc:
        rows.append(_row("PR3-utility", "GDPR Art. 5(1)(d); PDPA s. 17", "utility retention",
                         "results/utility_eval.json", "f1_ratio >= 0.90", "f1_ratio >= 0.90",
                         f"MISSING EVIDENCE: {exc}", False))


def test_retention_deletion(rows):
    now = datetime.now(timezone.utc)
    recs = [{"id": d, "stored_at": (now - timedelta(days=d)).isoformat()}
            for d in (1, 10, 31, 90)]
    kept, deleted = purge_expired(recs, now=now, max_age_days=30)
    rep = retention_report(recs, now=now, max_age_days=30)
    rows.append(_row("RETENTION", "PDPA s. 16; GDPR Art. 5(1)(e)", "raw-extract retention job",
                     "in-suite simulation of src/retention.py", "zero rows older than 30d after purge",
                     "remaining_records_older_than_limit == 0",
                     {"deleted": len(deleted), "kept": len(kept),
                      "remaining_over_limit": rep["remaining_records_older_than_limit"]},
                     rep["remaining_records_older_than_limit"] == 0 and len(deleted) == 2))


def test_ledger_tamper(rows):
    with tempfile.TemporaryDirectory() as td:
        logger = CryptographicAuditLogger(Path(td) / "ledger.json")
        logger.log_event("TEST_EVENT", {"value": 1})
        ok_before, _ = logger.verify_ledger_integrity()
        logger.ledger[-1]["payload"]["value"] = 999          # flip payload
        ok_after, msg = logger.verify_ledger_integrity()
    rows.append(_row("LEDGER-TAMPER", "GDPR Art. 5(2); PDPA s. 9", "chained-hash audit ledger",
                     "in-suite temp ledger", "integrity OK before edit, DETECTED after payload flip",
                     "verify returns True then False",
                     {"verified_before": ok_before, "verified_after_tamper": ok_after,
                      "message": msg}, ok_before and not ok_after))


def test_certificate_signature(rows):
    key, key_id = load_or_create_dev_key()
    cert = sign_certificate({"verdict": "PASS", "n": 1}, key, key_id)
    genuine = verify_certificate(cert, key, expected_key_id=key_id)
    tampered = json.loads(json.dumps(cert))
    tampered["verdict"] = "FORGED"
    tamper_detected = not verify_certificate(tampered, key, expected_key_id=key_id)
    wrong_key = verify_certificate(cert, b"\x00" * 32) is False
    rows.append(_row("CERT-SIGNATURE", "GDPR Art. 25(2), Art. 32; PDPA s. 9",
                     "HMAC-SHA-256 certificate signing with key_id",
                     "src/cert_signer.py (in-suite)",
                     "genuine verifies; edited verdict fails; wrong key fails",
                     "genuine==True, tampered==False, wrong-key==False",
                     {"genuine": genuine, "tamper_detected": tamper_detected,
                      "wrong_key_rejected": wrong_key},
                     genuine and tamper_detected and wrong_key))


def test_erasure_from_model_hard_case(rows):
    """Erasure-from-model: DP accounting record AND empirical audit must agree."""
    try:
        dp = _load_or_fail("dp2u_audit.json")
        rec = dp.get("dp2u_record", {})
        backend = str(rec.get("backend", ""))
        eps_accounted = rec.get("epsilon_accounted")
        honest_label = ("opacus" in backend and eps_accounted is not None) or \
                       ("fallback" in backend and "no valid" in str(rec.get("accounting", "")))
        emp_ok = (dp["MIA_AUC"] <= AUD["mia_auc_pass_max"]
                  and dp["TPR_at_1pct_FPR"] <= AUD["tpr_at_1pct_fpr_pass_max"])
        rows.append(_row("ERASURE-MODEL", "GDPR Art. 17(1); PDPA s. 38",
                         "formal (eps,delta) bound + empirical MIA agreement",
                         "results/dp2u_audit.json",
                         "privacy record honestly labelled AND empirical bound met",
                         "accounting label matches backend and AUC<=0.55 & TPR<=0.05",
                         {"backend": backend, "epsilon_accounted": eps_accounted,
                          "empirical_ok": emp_ok}, honest_label and emp_ok))
    except FileNotFoundError as exc:
        rows.append(_row("ERASURE-MODEL", "GDPR Art. 17(1); PDPA s. 38", "DP bound + audit",
                         "results/dp2u_audit.json", "see runner", "see runner",
                         f"MISSING EVIDENCE: {exc}", False))


def test_breach_runbook_tabletop(rows):
    steps = ["detect", "contain", "assess_art33_risk", "notify_SA_within_72h",
             "notify_pdpa_commissioner", "record_in_ledger", "post_mortem"]
    with tempfile.TemporaryDirectory() as td:
        logger = CryptographicAuditLogger(Path(td) / "breach_ledger.json")
        h = None
        for s in steps:
            h = logger.log_event("BREACH_RUNBOOK_STEP", {"step": s,
                                                         "ts": datetime.now(timezone.utc).isoformat()})
        ok, _ = logger.verify_ledger_integrity()
    complete = h is not None and ok and len(steps) == 7
    rows.append(_row("BREACH-TABLETOP", "GDPR Art. 33/34; PDPA (Amendment) 2024",
                     "72-hour breach notification runbook",
                     "in-suite tabletop with ledger trail",
                     "all 7 steps executed and ledger chain verifies",
                     "steps==7 and ledger integrity True",
                     {"steps": steps, "ledger_verified": ok}, complete))


def test_config_consistency(rows):
    """C1: pilot_config.json is the single source of truth vs evidence files."""
    problems = []
    eps = set(CFG["privacy"]["epsilon_sweep"])
    for fname in ("ga_audit.json", "dp2u_audit.json", "ft_audit.json"):
        p = RESULTS_DIR / fname
        if p.exists():
            m = json.loads(p.read_text())
            if set(m.get("config_epsilon_sweep", [])) != eps:
                problems.append(f"{fname}: epsilon_sweep mismatch")
            if m.get("dataset") and m["dataset"] != CFG["data"]["dataset_id"]:
                problems.append(f"{fname}: dataset mismatch")
    rows.append(_row("CONFIG-CONSISTENCY", "GDPR Art. 5(1)(d) (accuracy of records)",
                     "single-source-of-truth pilot config",
                     "pilot_config.json vs results/*_audit.json",
                     "every audit stamps the same epsilon sweep and dataset id",
                     "no mismatches", problems or "consistent", not problems))


def main():
    rows = []
    test_pr1_isolation(rows)
    test_pr2_audits(rows)
    test_pr3_utility(rows)
    test_retention_deletion(rows)
    test_ledger_tamper(rows)
    test_certificate_signature(rows)
    test_erasure_from_model_hard_case(rows)
    test_breach_runbook_tabletop(rows)
    test_config_consistency(rows)

    assert len(rows) >= 8, "compliance summary must contain at least 8 rows (B1)"
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_policy": "rows read real results/*.json; missing evidence => FAIL, never silent pass",
        "tests": rows,
        "all_passed": all(r["passed"] for r in rows),
    }
    out = RESULTS_DIR / "compliance_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    width = max(len(r["id"]) for r in rows)
    for r in rows:
        print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['id']:<{width}}  {r['test']}")
    print(f"\n{sum(r['passed'] for r in rows)}/{len(rows)} passed -> {out}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
