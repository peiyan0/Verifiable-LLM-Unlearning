"""Dataset profiler emitting SYNTHETIC SCHEMA FIXTURES (ds.md F2/A7 rename).

The previous draft generated fictitious authors and wrote them as
``tofu_processed_dataset.json`` / ``tofu_retain.json`` …, which made the local
``data/`` folder look like the TOFU benchmark. It never was: the real benchmark
is loaded from ``locuslab/TOFU`` by ``src/tofu_data.py``.

This module now writes ``synthetic_fixture_*.json`` files whose sole purpose is
to exercise record schemas in unit tests offline (no network, no HF download).
Provenance is stated inside every emitted file and in ``data/README.md``.
"""
from __future__ import annotations

import json
import os
import random

FIXTURE_PREFIX = "synthetic_fixture_"

PROVENANCE = {
    "kind": "synthetic schema fixture — NOT the TOFU benchmark",
    "generator": "src/dataset_profiler.py",
    "benchmark_of_record": "locuslab/TOFU (loaded by src/tofu_data.py; see data/README.md)",
    "purpose": "offline unit-test fixtures for record schema / disjointness plumbing",
}


def _make_author(rng: random.Random, i: int):
    first = rng.choice(["Aina", "Bryan", "Chong", "Devi", "Elaine", "Farid"])
    last = rng.choice(["Abdul", "Lim", "Nair", "Tan", "Yusof"])
    return f"{first} {last}-{i}"


def generate_fixtures(output_dir: str, n_authors: int = 8, qa_per_author: int = 5,
                      seed: int = 1234) -> dict:
    """Write synthetic_fixture_{retain,forget,holdout}.json and return a manifest."""
    rng = random.Random(seed)
    splits = {"retain": [], "forget": [], "holdout": []}
    for a in range(n_authors):
        author = _make_author(rng, a)
        target = ["retain", "retain", "forget", "holdout"][a % 4]
        for q in range(qa_per_author):
            topic = rng.choice(["painting", "baking", "cycling", "chess"])
            splits[target].append({
                "author_name": author,
                "author_cluster": f"synthetic#{a}",
                "question": f"What type of {topic} project does {author} enjoy? (fixture {q})",
                "answer": f"{author} enjoys {topic} fixture answer {q}.",
            })

    os.makedirs(output_dir, exist_ok=True)
    written = {}
    for name, rows in splits.items():
        out = os.path.join(output_dir, f"{FIXTURE_PREFIX}{name}.json")
        with open(out, "w") as f:
            json.dump({"provenance": PROVENANCE, "records": rows}, f, indent=2)
        written[name] = out
    manifest = {"provenance": PROVENANCE, "files": written,
                "counts": {k: len(v) for k, v in splits.items()}}
    with open(os.path.join(output_dir, f"{FIXTURE_PREFIX}manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    print(json.dumps(generate_fixtures(os.path.join(here, "..", "data")), indent=2))
