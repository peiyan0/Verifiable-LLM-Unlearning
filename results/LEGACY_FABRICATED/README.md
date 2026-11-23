# LEGACY — FABRICATED EVIDENCE (do not cite)

Files in this folder were produced by the state audited in `doc/ds.md` and are
retained **only** as evidence of what was wrong. They must never be cited as
results:

- `final_sweep_compliance_certificate.json` — cites MIA AUC 0.506175 / TPR 0.02
  that came from `rng.normal` simulation (ds.md F1/F4), and its
  "cryptographic_verification_signature" is a bare SHA-256 checksum, not a
  signature (ds.md F5).
- `audit_ledger_noop_sweep.json` — hash chain is genuine, but every
  `EXPERIMENT_RUN` duration measures a no-op `print()` stub (ds.md F3), so the
  timing statistics built on it are meaningless.

Replacement pipeline (real runs only):

| Evidence | Produced by |
|---|---|
| `results/ft_audit.json` (positive control) | `scripts/run_pilot_audit.py` |
| `results/ga_audit.json`, `results/dp2u_audit.json` | `scripts/run_pilot_audit.py` |
| `results/utility_eval.json`, `results/pr1_isolation.json` | `scripts/run_pilot_audit.py` |
| `results/pilot_certificate.json` (HMAC-signed, key_id) | `src/cert_signer.py` via the script above |
| real sweep ledger | `experiments/run_real_sweep.py` |
| compliance table | `tests/compliance_verification_tests.py` → `results/compliance_summary.json` |
