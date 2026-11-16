# Execution status against `doc/ds.md` (DeepSeek full review)

This file tracks which items of the review's Master TODO have been executed in this
repository, and which remain blocked on hardware we do not have here.

Legend: DONE = implemented and verified by an automated test in this repo.
PARTIAL = code written, but the number/result needs a GPU run. BLOCKED = cannot run here.

| Item | Status | Notes |
|---|---|---|
| A1 Positive control (fine-tune + audit, AUC >= 0.75) | PARTIAL/BLOCKED | `scripts/run_pilot_audit.py` performs a real LoRA fine-tune + real MIA audit; no GPU/CUDA and only ~2 GB RAM here, so the reported number must come from the Colab run. |
| A2 Real gradient ascent | DONE (code) | `src/unlearning_engine.py::run_gradient_ascent` now does real GA + retain regularisation with in-place Adam updates. |
| A3 Real DP2U / DP-SGD | DONE (code) | `run_dp2unlearning` uses Opacus DP-SGD when available, else a documented Gaussian noise-mechanism fallback; returns a real `(eps, delta)` accounting record. |
| A4 Remove simulated metrics | DONE | No `np.random.normal`/`rng.normal` remains anywhere in the repo; certificates are rebuilt from `results/*.json` only. |
| A5 HMAC-signed certificates | DONE | `src/cert_signer.py`; verifier returns True on genuine cert, False on tampered cert. |
| A6 Author-clustered bootstrap | DONE | `src/audit_probe.py::author_cluster_bootstrap`, used by the notebook script path. |
| A7 Honest dataset naming + provenance | DONE | `src/dataset_profiler.py` writes `data/synthetic_fixture_*.json`; `data/README.md` states provenance. |
| B1 Compliance summary JSON | DONE | `tests/compliance_verification_tests.py` -> `results/compliance_summary.json`. |
| B2 Fail on missing/fabricated evidence | DONE | `load()` raises if a results file is absent; positive control < 0.75 fails the suite (exit non-zero). |
| B3 Extra tests (retention, tamper, utility, erasure, breach) | DONE | Present as rows in the summary. |
| B4 `SecurityError` defined, no bare except | DONE | `src/trust_boundary_proxy.py`. |
| B5 No hard-coded paths | DONE | All modules resolve paths from `Path(__file__).parents[1]`. |
| C1 Reconcile config vs ledger vs certs | DONE | `pilot_config.json` is the single source of truth; sweep uses it; mismatch is asserted in tests. |
| C2 s.6 -> s.38 citation slip | DONE | Corrected in `doc/A2_report_sections.md` change log; legal citations centralised in `src/legal_refs.py`. |
| C3 Pinned environment | DONE | `requirements.txt` pins what this repo was actually run with (torch 2.7.1+cpu), and records the Colab/T4 versions separately instead of inventing them. |
| C4 `src/__init__.py`, `experiments/run_all.sh` | DONE | |
| C5 Perplexity prompt masking | DONE | `src/utility_evaluator.py::evaluate_perplexity` masks the prompt with `-100`. |
| D1-D6 Report tables | PARTIAL | Drafted in `doc/A2_report_sections.md` with placeholders for the numbers that require the GPU pilot. |
| F10 Honesty paragraph (Sec 1 / Sec 8) | DONE | Written into `doc/A2_report_sections.md`. |
