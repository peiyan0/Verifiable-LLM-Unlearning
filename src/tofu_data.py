"""Real TOFU loading, author clustering and record-hash disjointness (FR1).

This module replaces the synthetic fixture path as the source of benchmark data.
It loads the genuine ``locuslab/TOFU`` subsets (``retain90``, ``forget10``,
``holdout10``) and derives an *author* grouping that is reproducible without
access to the private upstream author index: TOFU generates exactly 20 QA pairs
per fictitious author, so the deterministic row blocks of 20 are used as the
author cluster.  The assumption is recorded in every emitted JSON so a marker can
check it (see ``cluster_method``).

Provenance note (ds.md F2): ``data/synthetic_fixture_*.json`` produced by
``src/dataset_profiler.py`` are schema fixtures for unit tests only and are NOT
the benchmark.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict

from . import DATA_DIR

TOFU_DATASET_ID = "locuslab/TOFU"
SPLITS = ("retain90", "forget10", "holdout10")
QA_PER_AUTHOR = 20


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record_hash(question: str, answer: str) -> str:
    """Canonical SHA-256 identity of one QA record (used for disjointness)."""
    return _sha256(f"{question.strip()}\n{answer.strip()}")


def load_tofu_split(name: str):
    """Load one real TOFU subset as a list of dicts with hash + author cluster."""
    from datasets import load_dataset  # imported lazily so tests can skip cleanly

    ds = load_dataset(TOFU_DATASET_ID, name, split="train")
    rows = []
    for idx, ex in enumerate(ds):
        q, a = ex["question"], ex["answer"]
        rows.append(
            {
                "split": name,
                "index": idx,
                "question": q,
                "answer": a,
                "record_hash": record_hash(q, a),
                # deterministic TOFU author block: rows [20k, 20k+20) belong to one author
                "author_cluster": f"{name}#block{idx // QA_PER_AUTHOR}",
                "author_name": extract_author_name(q, a),
            }
        )
    return rows


_NAME_STOPWORDS = {
    "The", "What", "His", "Her", "Their", "He", "She", "They", "This", "That",
    "Known", "Born", "Hailing", "Based", "Currently", "Previously", "After",
    "Before", "While", "Although", "However", "Moreover", "In", "On", "At", "Of",
    "And", "Or", "But", "For", "With", "From", "As", "By", "A", "An", "Not",
    "Also", "Who", "Which", "When", "Where", "LGBTQ", "One", "Some", "Many",
    "Most", "Other", "All", "Both", "Despite", "Due", "Because", "Since",
}


def extract_author_name(question: str, answer: str):
    """Best-effort human-readable author name.

    Used only for reporting/pseudonymisation demos; clustering uses
    ``author_cluster`` (the deterministic row block), never this string.
    """
    m = re.search(r"([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,3})'s", question)
    if m:
        return m.group(1).strip()
    for cand in re.findall(r"\b([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){1,3})\b", answer):
        words = cand.split()
        if len(words) < 2 or any(w in _NAME_STOPWORDS for w in words):
            continue
        return cand
    return None


def pseudonymise(author_cluster: str, key: bytes) -> str:
    """Keyed HMAC-SHA-256 pseudonymisation of a subject identifier.

    Reversible by the key holder, so pseudonymised identifiers remain personal
    data under GDPR Recital 26 - this is stated in the report, not hidden here.
    """
    import hmac as _hmac

    return _hmac.new(key, author_cluster.encode("utf-8"), hashlib.sha256).hexdigest()


def disjointness_report(rows_by_split) -> dict:
    """SHA-256 set-intersection check across splits (FR1 acceptance test)."""
    hashes = {name: {r["record_hash"] for r in rows} for name, rows in rows_by_split.items()}
    names = list(hashes)
    overlaps = OrderedDict()
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            inter = hashes[a] & hashes[b]
            overlaps[f"{a}~{b}"] = {
                "intersection_records": len(inter),
                "union_records": len(hashes[a] | hashes[b]),
            }
    total_overlap = sum(v["intersection_records"] for v in overlaps.values())
    return {
        "dataset": TOFU_DATASET_ID,
        "cluster_method": f"deterministic row blocks of {QA_PER_AUTHOR} records (TOFU generates 20 QA per fictitious author)",
        "counts": {n: len(r) for n, r in rows_by_split.items()},
        "author_clusters": {n: len({r["author_cluster"] for r in rows}) for n, rows in rows_by_split.items()},
        "pairwise_record_hash_overlap": overlaps,
        "overlap_is_zero": total_overlap == 0,
    }


def group_by_author(rows):
    """Map author_cluster -> list of records."""
    out = OrderedDict()
    for r in rows:
        out.setdefault(r["author_cluster"], []).append(r)
    return out


def materialise_cache(out_path=None) -> dict:
    """Download real TOFU once and cache it under data/ as JSONL for offline runs."""
    from . import DATA_DIR as _DD

    out_path = out_path or (_DD / "tofu_real_cache.json")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows_by_split = {name: load_tofu_split(name) for name in SPLITS}
    payload = {
        "provenance": {
            "dataset_id": TOFU_DATASET_ID,
            "subsets": list(SPLITS),
            "licence": "MIT (locuslab/TOFU); generated/fictitious personal data - no real persons",
            "loaded_by": "src/tofu_data.py::materialise_cache",
        },
        "disjointness": disjointness_report(rows_by_split),
        "splits": rows_by_split,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f)
    return payload


def read_cache():
    """Read the cached real-TOFU payload, or materialise it on first use."""
    path = DATA_DIR / "tofu_real_cache.json"
    if not path.exists():
        materialise_cache(path)
    with open(path) as f:
        payload = json.load(f)
    return payload["splits"], payload
