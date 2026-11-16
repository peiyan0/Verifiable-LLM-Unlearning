"""Trust-boundary enforcement proxy (FR4 separation of duties, ds.md B4/F8).

The Unlearning Engine (TB3) must never see the non-member reference set, the
audit seeds or the probe's synonym lists.  This proxy raises a *defined*
``SecurityError`` (the earlier draft raised an undefined name, which a bare
``except Exception`` swallowed) and the test suite asserts the exception type.
"""
from __future__ import annotations

import fnmatch

# Resources the engine role may never read (ds.md F8: was previously undefined).
ENGINE_FORBIDDEN_PATTERNS = (
    "*holdout*",           # non-member reference set lives here
    "*nonmember*",
    "*reference_set*",
    "*audit_seeds*",
    "*synonym_lists*",
    "*secret*",
    "*.pem",
    "*hmac_key*",
)

FORBIDDEN_KEYS = ("holdout", "nonmember", "reference_set", "audit_seed", "synonym_list", "secret_key")


class SecurityError(RuntimeError):
    """Raised when a role attempts an access outside its trust boundary."""


class TrustBoundaryProxy:
    """Mediates resource access for a named role across trust boundaries."""

    ROLES = ("engine", "auditor", "controller")

    def __init__(self, role: str):
        if role not in self.ROLES:
            raise ValueError(f"Unknown role '{role}'. Expected one of {self.ROLES}.")
        self.role = role
        self.deny_log = []

    def _is_forbidden(self, name: str) -> bool:
        low = str(name).lower()
        return any(fnmatch.fnmatch(low, pat.lower()) for pat in ENGINE_FORBIDDEN_PATTERNS)

    def request_dataset(self, dataset_name: str):
        """Engine requests a partition by name; auditor/controller may request any."""
        if self.role == "engine" and self._is_forbidden(dataset_name):
            self.deny_log.append({"role": self.role, "resource": dataset_name,
                                  "rule": "engine cannot read audit-side resources"})
            raise SecurityError(
                f"Trust violation: role 'engine' requested audit-side resource '{dataset_name}'")
        return {"granted": True, "role": self.role, "resource": dataset_name}

    def validate_split_disjointness(self, retain_ids, forget_ids, reference_ids):
        """Assert the engine-visible sets exclude the reference set entirely."""
        r = set(retain_ids) | set(forget_ids)
        overlap = r & set(reference_ids)
        if overlap:
            self.deny_log.append({"role": self.role, "overlap": sorted(map(str, overlap))[:10],
                                  "rule": "reference set leaked into engine-visible partitions"})
            raise SecurityError(
                f"Non-member reference records present in engine-visible partitions ({len(overlap)} ids)")
        return {"overlap": 0, "n_retain": len(retain_ids), "n_forget": len(forget_ids),
                "n_reference": len(reference_ids)}
