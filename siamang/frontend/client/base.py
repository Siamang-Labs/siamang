"""Abstract backend-client template (renders the ``env.js`` snippet)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ClientEnv:
    """Frontend-safe configuration handed to the in-bundle JS client.

    Only values that can safely be exposed to anonymous survey respondents go
    here. Secrets (service keys, admin tokens) must stay server-side.
    """

    survey_id: str
    backend: str
    settings: dict[str, Any]


class BackendClientTemplate(ABC):
    """Template that emits an ``env.js`` snippet for a specific backend.

    The snippet registers a transport on ``window.SURVLIB_TRANSPORTS`` keyed
    by ``ClientEnv.backend`` and assigns ``window.SURVLIB_ENV``.
    """

    name: str

    @abstractmethod
    def render_env_js(self, env: ClientEnv) -> str:
        """Return the JS source for ``env.js``."""
