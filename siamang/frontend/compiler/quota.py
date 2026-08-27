"""Compile Quota objects into a payload for the backend + client snippet."""

from __future__ import annotations

from typing import Any

from siamang.core.quota import Quota


def compile_quota(quota: Quota) -> dict[str, Any]:
    """Serialise a Quota into a JSON-friendly dict.

    The result is consumed by:
    - the backend (to create quota_counters rows and enforce limits server-side);
    - the frontend client (to display 'quota full' when the backend returns 403).
    """

    return {
        "variable": quota.variable,
        "target_value": quota.target_value,
        "limit": quota.limit,
    }
