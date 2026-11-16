"""Retention enforcement (PDPA s. 16, GDPR Art. 5(1)(e)) - ds.md B3 row."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def purge_expired(records, now: datetime | None = None, max_age_days: int = 30):
    """Return (kept, deleted) splitting raw extracts on the retention clock.

    ``records``: iterable of dicts with a ``stored_at`` ISO-8601 timestamp.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    kept, deleted = [], []
    for r in records:
        ts = datetime.fromisoformat(r["stored_at"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        (deleted if ts < cutoff else kept).append(r)
    return kept, deleted


def retention_report(records, now=None, max_age_days: int = 30) -> dict:
    kept, deleted = purge_expired(records, now=now, max_age_days=max_age_days)
    return {
        "max_age_days": max_age_days,
        "input_records": len(list(records)),
        "deleted_records": len(deleted),
        "remaining_records_older_than_limit": sum(
            1 for r in kept
            if (now or datetime.now(timezone.utc)) - datetime.fromisoformat(r["stored_at"])
            > timedelta(days=max_age_days)
        ),
        "pass_criterion": "zero rows older than the retention limit after the job",
    }
