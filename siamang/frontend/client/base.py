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

    The snippet registers a transport on ``window.SIAMANG_TRANSPORTS`` keyed
    by ``ClientEnv.backend`` and assigns ``window.SIAMANG_ENV``.

    ``transport`` is the key the snippet always registers its transport
    under, for a template whose ``env.js`` is the only way the answers can
    reach the backend. A page built with such a template says so in its own
    HTML (``RuntimeRenderContext.transport``), and the React runtime then
    treats a missing transport — ``env.js`` failed to load, or loaded without
    registering one — as a failed submission rather than as a response sent:
    the respondent gets the retry dialog, and no ending page, completion
    screen or redirect. None, the default, keeps a page that runs without a
    transport as it always has: it ends as if the answers were sent (a
    preview, a host that supplies no backend).
    """

    name: str
    transport: str | None = None

    @abstractmethod
    def render_env_js(self, env: ClientEnv) -> str:
        """Return the JS source for ``env.js``."""
