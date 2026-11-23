# `data/` provenance (ds.md F2 / A7)

| File | What it actually is | Source of truth |
|---|---|---|
| `tofu_real_cache.json` | **Real benchmark data.** `retain90` / `forget10` / `holdout10` from HuggingFace `locuslab/TOFU`, with SHA-256 record hashes, deterministic author clusters (blocks of 20 QA per fictitious author) and a pairwise disjointness report. | produced by `src/tofu_data.py::materialise_cache` |
| `synthetic_fixture_retain.json`, `synthetic_fixture_forget.json`, `synthetic_fixture_holdout.json`, `synthetic_fixture_manifest.json` | **Synthetic schema fixtures only** — fictitious records generated offline to exercise unit-test plumbing. They are NOT the TOFU benchmark and must never be cited as such. Every file embeds a `provenance` block saying so. | produced by `src/dataset_profiler.py` |
| `audit_ledger.json` | Live chained audit ledger written by `src/audit_logger.py` during real runs (genesis entry has payload `{"message": "Audit Ledger Initialized"}`). | created at run time |
| `secrets/cert_hmac_key.json` | Local development HMAC key for certificate signing (mode 0600). Never commit; production uses env var `UNLEARNING_CERT_HMAC_KEY` / KMS. | created by `src/cert_signer.py` |

Historical note: earlier drafts wrote synthetic fixtures under the names
`tofu_processed_dataset.json` / `tofu_retain.json` …, which misrepresented them
as the benchmark (review finding F2). Those names no longer exist; the renamed
fixtures carry an explicit provenance header.

The fabricated legacy artifacts (no-op sweep ledger, simulated-metric
certificates) were moved to `results/LEGACY_FABRICATED/` with a README
explaining why they must not be cited.

Licences: `locuslab/TOFU` — MIT; generated/fictitious personal data, no real
persons. Phi-1.5 — Microsoft Research License Agreement.
