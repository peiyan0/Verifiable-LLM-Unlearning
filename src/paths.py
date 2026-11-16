"""Single source of truth for repository paths and pilot configuration.

Fixes ds.md B5 (hard-coded absolute paths) and C1 (config <-> ledger <->
certificate inconsistencies): every script and test reads the same
``pilot_config.json``.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"
CONFIG_PATH = REPO_ROOT / "pilot_config.json"
LEDGER_PATH = DATA_DIR / "audit_ledger.json"


def load_config(path: Path | None = None) -> dict:
    path = path or CONFIG_PATH
    with open(path) as f:
        return json.load(f)


def save_json(rel_or_abs, payload) -> Path:
    """Write JSON under results/ (or an absolute path) creating parents."""
    p = Path(rel_or_abs)
    if not p.is_absolute():
        p = RESULTS_DIR / p
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=False)
    return p


def read_result(name: str) -> dict:
    """Read a results/*.json file. Raises FileNotFoundError - never silently passes.

    ds.md B2: missing evidence must fail the compliance suite, not pass it.
    """
    p = name if Path(name).is_absolute() else RESULTS_DIR / name
    with open(p) as f:
        return json.load(f)
