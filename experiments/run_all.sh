#!/usr/bin/env bash
# Reproducible entry point (ds.md C4): clean clone -> bash experiments/run_all.sh
# Stage 1 (CPU, no network beyond HF datasets download): plumbing + compliance suite.
# Stage 2 (GPU): real pilot producing citable numbers.
set -uo pipefail
cd "$(dirname "$0")/.."

echo "== [1/4] materialise real TOFU cache (network) =="
python -c "from src.tofu_data import materialise_cache; m=materialise_cache(); print(m['disjointness'])" || exit 1

echo "== [2/4] synthetic schema fixtures (offline) =="
python src/dataset_profiler.py >/dev/null || exit 1

echo "== [3/4] unit tests (pure logic, CPU) =="
python -m unittest discover -s tests -p 'test_*.py' -v || exit 1

echo "== [4/4] compliance verification suite =="
python tests/compliance_verification_tests.py
rc=$?
echo "compliance suite exit code: $rc"
echo "(exit 1 is EXPECTED before the GPU pilot has produced results/*_audit.json;"
echo " run 'python scripts/run_pilot_audit.py --device cuda' on the T4 to fill them.)"

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  echo "== GPU detected: running the real pilot =="
  python scripts/run_pilot_audit.py --device cuda || exit $?
  python tests/compliance_verification_tests.py || exit $?
fi
exit $rc
