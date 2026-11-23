"""HMAC-signed compliance certificates (ds.md A5, F5).

The previous draft called a bare SHA-256 checksum of the JSON a
"cryptographic_verification_signature".  Anyone could recompute it, so it proved
only well-formedness, not authorship.  This module provides a keyed HMAC-SHA-256
signature with an explicit ``key_id`` and a verification function that fails on
tampering.  Ed25519 is the production upgrade path (see report Sec. 4 key
management); the interface is identical so only ``_mac`` changes.

Key handling: the signing key is NEVER stored in the repository.  It is read from
the environment variable ``UNLEARNING_CERT_HMAC_KEY`` (hex) or generated into an
untracked file under ``data/secrets/`` for local runs.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone

from .paths import DATA_DIR, RESULTS_DIR, save_json
from . import legal_refs as L

ALG = "HMAC-SHA-256"
KEY_ENV = "UNLEARNING_CERT_HMAC_KEY"
DEV_KEY_FILE = DATA_DIR / "secrets" / "cert_hmac_key.json"
DEV_KEY_ID = "dev-local-hmac-key-1"


def _canonical_bytes(cert: dict) -> bytes:
    body = {k: v for k, v in cert.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _mac(key: bytes, payload: bytes) -> str:
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def load_or_create_dev_key() -> tuple[bytes, str]:
    """Return (key, key_id). Env var wins; otherwise a dev key file is created."""
    env = os.environ.get(KEY_ENV)
    if env:
        return bytes.fromhex(env.strip()), os.environ.get("UNLEARNING_CERT_KEY_ID", "env-hmac-key-1")
    if DEV_KEY_FILE.exists():
        data = json.loads(DEV_KEY_FILE.read_text())
        return bytes.fromhex(data["key_hex"]), data["key_id"]
    key = secrets.token_bytes(32)
    DEV_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    DEV_KEY_FILE.write_text(json.dumps({"key_id": DEV_KEY_ID, "key_hex": key.hex(),
                                       "note": "local dev key - do not commit, do not use in production"}, indent=2))
    os.chmod(DEV_KEY_FILE, 0o600)
    return key, DEV_KEY_ID


def sign_certificate(cert: dict, key: bytes, key_id: str) -> dict:
    body = {k: v for k, v in cert.items() if k != "signature"}
    mac = _mac(key, _canonical_bytes(body))
    return {**body, "signature": {"alg": ALG, "key_id": key_id, "mac": mac}}


def verify_certificate(cert: dict, key: bytes, expected_key_id: str | None = None) -> bool:
    sig = cert.get("signature") or {}
    if sig.get("alg") != ALG:
        return False
    if expected_key_id is not None and sig.get("key_id") != expected_key_id:
        return False
    mac = sig.get("mac", "")
    if not isinstance(mac, str) or len(mac) != 64:
        return False
    return hmac.compare_digest(_mac(key, _canonical_bytes(cert)), mac)


def build_certificate(real_metrics: dict, key: bytes, key_id: str,
                      certificate_prefix: str = "CERT-ERASURE") -> dict:
    """Assemble a certificate ONLY from real metrics produced by real runs.

    ``real_metrics`` keys required:
      positive_control.MIA_AUC, dp2u_audit.{MIA_AUC,TPR_at_1pct_FPR},
      ga_audit.MIA_AUC, pr1_pass, utility.{f1_ratio}
    Refuses to certify when the positive control is missing or below threshold,
    because then the audit harness itself is unproven (ds.md F10).
    """
    pc = real_metrics["positive_control"]["MIA_AUC"]
    if pc < real_metrics.get("positive_control_threshold", 0.75):
        raise AssertionError(
            f"Positive control AUC {pc:.4f} < 0.75 - audit probe is not proven to detect "
            "membership, so no PASS can be certified (Proposal Validation Strategy).")

    dp = real_metrics["dp2u_audit"]
    auc_lim = real_metrics.get("mia_auc_limit", 0.55)
    tpr_lim = real_metrics.get("tpr_at_1pct_fpr_limit", 0.05)
    pr2_pass = dp["MIA_AUC"] <= auc_lim and dp["TPR_at_1pct_FPR"] <= tpr_lim
    util = real_metrics.get("utility", {})
    pr3_pass = util.get("f1_ratio", 0.0) >= real_metrics.get("utility_retention_threshold", 0.90)

    now = datetime.now(timezone.utc)
    cert = {
        "certificate_metadata": {
            "certificate_id": f"{certificate_prefix}-{now.strftime('%Y%m%dT%H%M%SZ')}",
            "timestamp_utc": now.isoformat(),
            "legal_authority_frameworks": L.FRAMEWORKS,
            "evidence_policy": "Every metric below is read from results/*.json written by a real run; "
                               "no simulated or hard-coded score distribution is used.",
        },
        "positive_control": real_metrics["positive_control"],
        "controls": [
            {"id": "PR1", "legal": "GDPR Art. 25; PDPA s. 9", "control": "TB4 auditor/engine separation",
             "evidence": "results/pr1_isolation.json", "test": "overlap == 0",
             "measured": real_metrics.get("pr1_overlap"), "pass_criterion": "overlap == 0",
             "passed": bool(real_metrics.get("pr1_pass"))},
            {"id": "PR2", "legal": "GDPR Art. 17; GDPR Art. 32; PDPA s. 9", "control": "empirical MIA leakage bound",
             "evidence": "results/dp2u_audit.json", "test": f"AUC <= {auc_lim} and TPR@1%FPR <= {tpr_lim}",
             "measured": {"MIA_AUC": dp["MIA_AUC"], "TPR_at_1pct_FPR": dp["TPR_at_1pct_FPR"],
                          "author_clustered_ci": dp.get("author_clustered_ci")},
             "pass_criterion": f"AUC <= {auc_lim} and TPR@1%FPR <= {tpr_lim}", "passed": bool(pr2_pass)},
            {"id": "PR3", "legal": "GDPR Art. 5(1)(d); PDPA s. 17", "control": "retain-set utility retention",
             "evidence": "results/utility_eval.json", "test": "F1 >= 90% of exact-retraining F1",
             "measured": util, "pass_criterion": "f1_ratio >= 0.90", "passed": bool(pr3_pass)},
        ],
        "ga_reference": real_metrics.get("ga_audit"),
        "verdict": "PASS" if (real_metrics.get("pr1_pass") and pr2_pass and pr3_pass) else "FAIL",
    }
    return sign_certificate(cert, key, key_id)


def write_signed_certificate(cert: dict, name: str) -> str:
    p = save_json(name, cert)
    return str(p)
