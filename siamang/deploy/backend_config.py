"""BackendConfig — frontend-safe connection details handed to the bundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class BackendConfig:
    """Connection details safe to embed in the frontend bundle.

    ``settings`` is forwarded to the in-bundle JS client (anon keys, public
    URLs, survey ids). Anything that must stay server-side (file paths, db
    handles, service keys) goes into ``internal`` and is never serialised
    into the bundle.
    """

    backend: str
    survey_id: str
    settings: dict[str, Any] = field(default_factory=dict)
    internal: dict[str, Any] = field(default_factory=dict)
    dashboard_url: str | None = None
