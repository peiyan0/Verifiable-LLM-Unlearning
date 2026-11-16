"""Verifiable-unlearning pilot package (MAC5043 Assignment 2 proof of setup).

Every module in this package resolves repository paths from ``REPO_ROOT`` so the
code runs from any working directory (ds.md fix B5).
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"
LEDGER_PATH = DATA_DIR / "audit_ledger.json"
CONFIG_PATH = REPO_ROOT / "pilot_config.json"

__all__ = ["REPO_ROOT", "DATA_DIR", "RESULTS_DIR", "LEDGER_PATH", "CONFIG_PATH"]
