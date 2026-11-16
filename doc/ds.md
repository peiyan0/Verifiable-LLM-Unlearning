# Full Review: All Documents — Fabrications, Summary, and Fix Plan

## 1. Inventory of artifacts reviewed

| # | File | Type | Honest content | Fabricated content |
|---|---|---|---|---|
| 1 | `A2_brief.md` | Assignment spec | Reference document | None |
| 2 | `full.md` | Assignment 1 proposal | Literature review, design, legal analysis, timeline | None (proposal, not results) |
| 3 | `audit_ledger.json` | Runtime evidence | Hash chain, seeds, ε, durations, timestamps | Durations from **no-op** unlearning (see F3) |
| 4 | `audit_logger.py` | Code | Real hash-chain logger | None |
| 5 | `audit_probe.py` | Code | Real AUC/TPR/bootstrap logic | Bootstrap is record-level not author-clustered (F6) |
| 6 | `baseline_proof_of_setup.py` | Code | Harness structure | **All MIA scores are `np.random.normal`** (F1) |
| 7 | `dataset_profiler.py` | Code | Schema fixture generator | **Called "TOFU" but generates fictitious data** (F2) |
| 8 | `statistical_tests.py` | Code | Real Wilcoxon | None |
| 9 | `trust_boundary_proxy.py` | Code | Real isolation check | `SecurityError` undefined (F8) |
| 10 | `unlearning_engine.py` | Code | Interface | **All methods are `print()` + return model** (F3) |
| 11 | `utility_evaluator.py` | Code | Real EM/perplexity | Perplexity masks wrong; swallows all exceptions (F9) |
| 12 | `final_sweep_compliance_certificate.json` | Certificate | Metadata | **Metrics from simulated Step 7**, SHA-256 mislabeled "signature" (F4, F5) |
| 13 | `pilot_compliance_certificate.json` | Certificate | Metadata | **Same fabricated metrics**; unsigned (F4, F5) |
| 14 | `run_full_sweep.py` | Orchestrator | Loop structure | Iterates no-op unlearning; timings meaningless (F3) |
| 15 | `tofu_unlearning_colab_pipeline.ipynb` | Run log | **Real** Phi-1.5B load, real TOFU load, **real loss audit (AUC 0.4292)** | Step 7 uses `rng.normal`; certificates cite Step 7 not Step 6 (F1, F4) |
| 16 | `compliance_verification_tests.py` | Test suite | Structure of PR1/PR2 | **PR3 uses hard-coded + `rng.normal`**, always passes (F1) |
| 17 | `pilot_config.json` | Config | Reproducibility params | Inconsistent with notebook/certs (F7) |

---

## 2. All fabrications, ranked by severity

**F1 — Simulated MIA scores presented as model results (CRITICAL)**
Locations:
- `baseline_proof_of_setup.py` lines ~38–55: `forget_scores_ft = np.random.normal(0.85, 0.10, ...)`, etc.
- Notebook Step 7: `pos_forget_losses = rng.normal(0.65, 0.15, 200)` … `dp_forget_losses = rng.normal(2.50, 0.25, 200)`
- `compliance_verification_tests.py` Test PR3: `ga_forget_scores = [0.82]*50 + [0.75]*50`, `dp_forget_scores = np.random.normal(0.50, 0.10, 100)`

Effect: the "AUC=0.5062 PASS" that appears in both certificates is generated from two N(0.5,0.1) samples. It is guaranteed to pass by construction. This is the pattern B.3 penalises as "fabricated results" → **zero for C2/C6 + academic-integrity referral**.

**F2 — Synthetic dataset labeled "TOFU" (HIGH)**
`dataset_profiler.py` generates fictitious authors and calls them `tofu_processed_dataset.json`, `tofu_retain.json`, etc. The notebook correctly loads real `locuslab/TOFU`, but the local `data/` folder the tests read from is the synthetic fixture. The report must not present these as the benchmark.

**F3 — "Unlearning" does nothing; ledger durations are no-op timings (CRITICAL)**
`unlearning_engine.py`:
```python
def run_gradient_ascent(...):
    print(...); return self.model      # no weight update
def run_dp2unlearning(...):
    print(...); return self.model      # no weight update
def run_projected_gradient_unlearning(...):
    print(...); return self.model      # no weight update
```
`run_full_sweep.py` then records `duration_seconds` for 108 runs of these no-ops. `final_sweep_compliance_certificate.json` reports `mean_execution_overhead_seconds: 0.00189` and `p=0.3072` as if they measured real DP2U vs GA. They measured `print()` vs `print()`.

**F4 — Certificates cite simulated metrics, not the real notebook audit (CRITICAL)**
Notebook Step 6 (real): **AUC 0.4292, TPR@1% 0.0000** on the un-fine-tuned base.
Certificates cite: **AUC 0.506175, TPR 0.02** — sourced from Step 7's `rng.normal`.
Neither matches. Worse: 0.4292 < 0.5 means the "PASS" in Step 6 is also unsupportable (no positive control was run — see F10).

**F5 — "Cryptographic signature" is a SHA-256 checksum (HIGH)**
`final_sweep_compliance_certificate.json`: `"cryptographic_verification_signature": hashlib.sha256(json).hexdigest()`. Anyone can recompute. Not a signature. GDPR Art. 32 / PDPA s.9 evidence requires HMAC (keyed) or Ed25519 (asymmetric) + `key_id` + `verify_certificate()`.

**F6 — Bootstrap is record-level, not author-clustered (MEDIUM)**
`audit_probe.py` and notebook both resample records. Proposal Sec 5.4 mandates author-clustered bootstrap. With ~5 authors per split, CIs are far too narrow — overstates confidence in the PASS/FAIL.

**F7 — Config ↔ execution inconsistencies (MEDIUM)**
- `pilot_config.json`: `pilot_epsilon: 4.0` (single). Ledger/certs: sweep {2, 4, 8}.
- Config: 160 retain / 20 forget / 20 holdout. Notebook: `retain90` = 180 authors / 3600 QA.
- Proposal: ε ∈ {1, 2, 4}.
- Proposal Sec 7.1 cites "consent-withdrawal deletion (s.6)"; certificates use s.38 (correct). The s.6 slip must be fixed.

**F8 — `SecurityError` undefined (LOW but breaks a test)**
`trust_boundary_proxy.py` raises `SecurityError` which is never defined. `compliance_verification_tests.py` wraps it in bare `except Exception`, so PR1 appears to run but is silently broken if a real violation occurred.

**F9 — `UtilityEvaluator` bugs (LOW-MEDIUM)**
`evaluate_perplexity` computes loss on `question + answer` with no `-100` prompt mask → not comparable to `compute_record_loss`. `except Exception: self.rouge_metric = None` hides install failures. `evaluate_exact_match` calls `model.generate` which `LightweightTextEncoder` doesn't have.

**F10 — No positive control anywhere (CRITICAL, root cause)**
Proposal O2 requires positive-control AUC ≥ 0.75 on the fine-tuned model. No notebook cell or script fine-tunes Phi-1.5B on retain+forget and audits it. Without that, the entire "PASS" verdict is unsupported — you're claiming erasure on a model that was never trained on the data.

---

## 3. Summary of what is genuinely working

- Real Colab run on Tesla T4, PyTorch 2.14.1+cu130, Phi-1.5B 4-bit NF4, 977 MB footprint.
- Real `locuslab/TOFU` `retain90/forget10/holdout10` loaded with SHA-256 disjointness assertion (3600/400/400).
- Real `compute_record_loss` (answer-only, `-100` masked) executed on 50 forget + 50 holdout → real AUC 0.4292, CI [0.3209, 0.5471].
- Chained ledger with genesis `6421a6…`, verified integrity across 109 entries.
- Real Wilcoxon, real hash-chain logger, real isolation proxy (once `SecurityError` is defined).
- Requirements FR1–5, NFR1–3, PR1–3, threat model, PET matrix, legal basis all present in `full.md`.

The **scaffold is right**; the **evidence layer is partly fabricated**.

---

## 4. Master TODO (ordered by blocking severity)

### Phase A — Remove fabrications (must do before submission)

| # | Task | Files | Done-when |
|---|---|---|---|
| A1 | Fine-tune Phi-1.5B on retain+forget (LoRA/PEFT, 1–3 epochs); audit → positive control AUC ≥ 0.75 | notebook new cell | JSON with `positive_control: {AUC, CI}` and `AUC ≥ 0.75` |
| A2 | Implement real GA (≥1 epoch on forget, retain regularization); re-audit → expect AUC > 0.55 | `unlearning_engine.py` | Real post-GA AUC in `results/ga_audit.json` |
| A3 | Implement real DP2U or DP-SGD (Opacus) fine-tune; re-audit → expect AUC ≤ 0.55 | `unlearning_engine.py` | Real post-DP2U AUC in `results/dp2u_audit.json` |
| A4 | Regenerate both certificates from **only** real JSONs; delete `rng.normal` and hard-coded arrays from `baseline_proof_of_setup.py`, notebook Step 7, `compliance_verification_tests.py` | all three | grep for `np.random.normal` in MIA context → 0 hits |
| A5 | HMAC-sign certificates with `key_id`, add `verify_certificate()` | new `src/cert_signer.py` | verifier returns True; tampered cert returns False |
| A6 | Author-clustered bootstrap in `audit_probe.py` + notebook `evaluate_audit_metrics` | both | CI computed by resampling `author_id` |
| A7 | Rename `tofu_*.json` synthetic fixtures → `synthetic_fixture_*.json`; add `data/README.md` stating provenance | `dataset_profiler.py`, `data/` | README + renamed files |

### Phase B — Compliance test suite (C5, 20 marks)

| # | Task | Done-when |
|---|---|---|
| B1 | Rewrite `compliance_verification_tests.py` to emit `results/compliance_summary.json` with columns `{id, legal, control, evidence, test, pass_criterion, measured, passed}` | File exists, parses, ≥8 rows |
| B2 | PR3 reads real `results/{ft,ga,dp2u}_audit.json`; **fails** if positive control < 0.75 | Script exits non-zero if any test fails |
| B3 | Add tests: retention deletion (no rows >30d), ledger tamper detection (flip payload → verify returns False), utility retention (F1 ≥ 90%), erasure-from-model hard case (DP bound + audit), breach-runbook tabletop | Each row present in summary |
| B4 | Fix `SecurityError` (define class); remove bare `except Exception` | grep `SecurityError` shows `class SecurityError` |
| B5 | Replace hard-coded paths with `Path(__file__).parents[1]/"data"` | tests run from repo root |

### Phase C — Consistency & repro (C1, C2, C6)

| # | Task | Done-when |
|---|---|---|
| C1 | Reconcile ε set ({1,2,4} vs {2,4,8}); author counts (160 vs 180); retain split name — pick one, log as A2 Section 1 change entries | `pilot_config.json` matches notebook + ledger + certs |
| C2 | Fix `full.md` s.6 → s.38 slip; record in change log | grep `s.6` returns no false citation |
| C3 | Pin versions in `requirements.txt` / `environment.yml` (torch 2.14.1+cu130, transformers, datasets, peft, accelerate, bitsandbytes, scikit-learn, scipy, opacus if used) | `pip freeze` from clean env matches |
| C4 | Commit `src/__init__.py`; ensure `%%writefile` cells correspond to committed files | clean clone runs `experiments/run_all.sh` |
| C5 | Fix `UtilityEvaluator.evaluate_perplexity` to mask prompt (`labels[:prompt_len] = -100`) | matches `compute_record_loss` semantics |

### Phase D — Report tables (A2 Sections 1–9)

| # | Task |
|---|---|
| D1 | Section 1 change log: ε sweep, 180 vs 160 authors, synthetic→real TOFU, DP2U implementation status |
| D2 | Section 3 stack table with pinned versions + licences (Phi-1.5B Microsoft Research License, TOFU MIT, torch BSD-3, etc.) |
| D3 | Section 4 deployment diagram + component-to-tool table (TB1–TB4, KMS for HMAC key) |
| D4 | Section 5 WBS, Gantt, experiment matrix aligned to `pilot_config.json` |
| D5 | Section 6 ROPA + PDPA/GDPR principle mapping + DPIA screening + the `compliance_summary.json` table |
| D6 | Section 8 proof-of-setup: screenshots (GPU, TOFU load, real AUC 0.4292), ledger genesis→head hash, commit hash |

---

## 5. Key fixes, shown

### Fix A4/A5 — Real audit + signed certificate (replaces simulated certs)

```python
# src/cert_signer.py
import hmac, hashlib, json, os, datetime

def sign_certificate(cert: dict, key: bytes, key_id: str) -> dict:
    body = {k: v for k, v in cert.items() if k != "signature"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    mac = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return {**body, "signature": {"alg": "HMAC-SHA-256", "key_id": key_id, "mac": mac}}

def verify_certificate(cert: dict, key: bytes) -> bool:
    sig = cert.get("signature", {})
    body = {k: v for k, v in cert.items() if k != "signature"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hmac.compare_digest(hmac.new(key, payload, hashlib.sha256).hexdigest(), sig.get("mac", ""))

def build_certificate(real_metrics: dict, key: bytes, key_id: str) -> dict:
    # real_metrics must come from results/*.json produced by real runs
    pc = real_metrics["positive_control"]["MIA_AUC"]
    assert pc >= 0.75, f"Positive control {pc:.3f} < 0.75 — cannot certify"
    cert = {
        "certificate_id": "CERT-ERASURE-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "legal_frameworks": ["GDPR Art. 17", "PDPA 2010 s.38", "PDPA 2010 s.10", "PDPA (Amdt) 2024"],
        "controls": [
            {"id": "PR1", "legal": "GDPR Art. 25; PDPA s.9", "test": "isolation", "evidence": "results/pr1_isolation.json", "pass": real_metrics["pr1_pass"]},
            {"id": "PR2", "legal": "GDPR Art. 32; PDPA s.9", "test": "MIA AUC<=0.55 & TPR<=0.05",
             "evidence": "results/dp2u_audit.json", "measured": real_metrics["dp2u_audit"],
             "pass": real_metrics["dp2u_audit"]["MIA_AUC"] <= 0.55 and real_metrics["dp2u_audit"]["TPR_at_1pct_FPR"] <= 0.05},
        ],
        "positive_control": real_metrics["positive_control"],
        "verdict": "PASS" if real_metrics["pr1_pass"] and real_metrics["dp2u_audit"]["MIA_AUC"] <= 0.55 else "FAIL",
    }
    return sign_certificate(cert, key, key_id)
```

### Fix B1/B2 — Structured compliance test

```python
# compliance_verification_tests.py (rewritten core)
import json, sys
from pathlib import Path
RESULTS = Path(__file__).parents[1] / "results"

def load(p):  # raises if file missing — no silent pass
    return json.loads((RESULTS / p).read_text())

def run():
    rows = []
    # PR1 isolation
    iso = load("pr1_isolation.json")
    rows.append({"id":"PR1","legal":"GDPR Art.25; PDPA s.9","control":"TB4 isolation",
                 "evidence":"results/pr1_isolation.json",
                 "test":"overlap==0","measured":iso["overlap"],"pass_criterion":"overlap==0",
                 "passed": iso["overlap"]==0})
    # PR2 empirical leakage — REAL audit
    ft = load("ft_audit.json"); ga = load("ga_audit.json"); dp = load("dp2u_audit.json")
    rows.append({"id":"PR2-posctrl","legal":"RQ4","control":"fine-tuned base leaks",
                 "evidence":"results/ft_audit.json","test":"AUC>=0.75",
                 "measured":ft["MIA_AUC"],"pass_criterion":"AUC>=0.75","passed": ft["MIA_AUC"]>=0.75})
    rows.append({"id":"PR2-ga","legal":"Gap G1","control":"GA leaves leakage",
                 "evidence":"results/ga_audit.json","test":"AUC>0.55",
                 "measured":ga["MIA_AUC"],"pass_criterion":"AUC>0.55","passed": ga["MIA_AUC"]>0.55})
    rows.append({"id":"PR2-dp2u","legal":"GDPR Art.32; PDPA s.9","control":"DP2U bounded",
                 "evidence":"results/dp2u_audit.json","test":"AUC<=0.55 & TPR<=0.05",
                 "measured":{"AUC":dp["MIA_AUC"],"TPR":dp["TPR_at_1pct_FPR"]},
                 "pass_criterion":"AUC<=0.55 & TPR<=0.05",
                 "passed": dp["MIA_AUC"]<=0.55 and dp["TPR_at_1pct_FPR"]<=0.05})
    # ... add PR3 utility, retention, ledger tamper, breach tabletop
    summary = {"tests": rows, "all_passed": all(r["passed"] for r in rows)}
    (RESULTS / "compliance_summary.json").write_text(json.dumps(summary, indent=2))
    return 0 if summary["all_passed"] else 1

sys.exit(run())
```

### Fix A6 — Author-clustered bootstrap

```python
def author_cluster_bootstrap(forget_by_author, holdout_by_author, n=1000, seed=42):
    rng = np.random.default_rng(seed)
    fa, ha = list(forget_by_author), list(holdout_by_author)
    aucs = []
    for _ in range(n):
        f = rng.choice(fa, size=len(fa), replace=True)
        h = rng.choice(ha, size=len(ha), replace=True)
        fs = np.concatenate([forget_by_author[a] for a in f])
        hs = np.concatenate([holdout_by_author[a] for a in h])
        y = np.r_[np.ones(len(fs)), np.zeros(len(hs))]
        aucs.append(roc_auc_score(y, np.r_[fs, hs]))
    return np.percentile(aucs, [2.5, 97.5])
```

### Fix A7 — Honest dataset naming

```python
# dataset_profiler.py — rename outputs
for s_name, s_data in splits.items():
    out = os.path.join(output_dir, f"synthetic_fixture_{s_name}.json")  # was tofu_{s_name}.json
```
Plus `data/README.md`:
> `synthetic_fixture_*.json` are **synthetic schema fixtures** generated by `dataset_profiler.py` for unit tests only. They are NOT the TOFU benchmark. The real benchmark is loaded from `locuslab/TOFU` (`retain90/forget10/holdout10`) by `tofu_unlearning_colab_pipeline.ipynb`.

---

## 6. What the report must say (so the marker sees honesty)

In A2 Section 1 (change log) and Section 8 (reproducibility), state explicitly:

- "The pilot audit in the notebook (AUC 0.4292) was run on the **un-fine-tuned** Phi-1.5B base; it is a harness smoke test, not an erasure result. The positive control (fine-tuned base, AUC ≥ 0.75) and the real GA/DP2U audits are produced by `notebook cells X–Y` and stored in `results/{ft,ga,dp2u}_audit.json`."
- "Earlier draft artifacts (`baseline_proof_of_setup.py`, notebook Step 7, `compliance_verification_tests.py` PR3) contained **simulated score distributions** for harness testing. They have been removed/relabelled and do not feed any certificate. Certificates cite only `results/*.json` from real runs."
- "Ledger durations for `EXPERIMENT_RUN` events before commit `<hash>` measured orchestration overhead of **no-op** unlearning stubs and are not reported as unlearning timings."

That paragraph alone converts F1/F3/F4 from "fabrication" to "declared limitation" — which is the difference between a referral and a pass.

**Bottom line:** the design, legal analysis, and harness are strong enough for a high mark. The evidence layer is currently three simulations masquerading as results, and the certificates are signed with a checksum. Phase A (A1–A7) is non-negotiable before submission; Phase B–D turn the harness into the C5 artifact the rubric wants. Want me to start by writing the fine-tune + re-audit notebook cell (A1), or the rewritten `compliance_verification_tests.py` (B1/B2)?