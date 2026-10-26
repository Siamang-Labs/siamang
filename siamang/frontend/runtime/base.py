"""Abstract runtime adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from siamang.frontend.schema import SurveySchema
from siamang.frontend.theme.fonts import FONT_BASE
from siamang.frontend.theme.ui_config import UIConfig

if TYPE_CHECKING:
    from siamang.core.questionnaire import Questionnaire


@dataclass(frozen=True, slots=True)
class RuntimeRenderContext:
    """Inputs required by every runtime adapter to produce HTML.

    ``survey`` is optional; only runtimes that emit the questionnaire on the
    client side (the React runtime) need direct access to the live
    :class:`Questionnaire` objects. SurveyJS-style runtimes work from the
    already-compiled :class:`SurveySchema` alone.

    ``font_base`` is where the stylesheet's ``@font-face`` rules find the
    bundled typefaces (:mod:`siamang.frontend.theme.fonts`): ``fonts/`` next to
    the stylesheet in a bundle. A host that puts the stylesheet somewhere else
    — inline in a page it serves — passes the URL (ending in ``/``) it serves
    the files at.

    ``csp`` is a Content-Security-Policy the pages carry in a
    ``<meta http-equiv>`` right after ``<meta charset>`` (before anything it
    governs); None writes none, as before. :mod:`siamang.frontend.csp` says
    what the runtime needs and builds one (``survey_csp``), and a host that
    writes the policy after the build puts it in the same place
    (``insert_csp_meta``).

    ``click_to_play`` turns the YouTube and Vimeo players a page's body holds
    into a play button that loads the player when it is pressed, as a
    question's own video (media of kind ``"embed"``) always is: nothing is
    requested from the provider before. Off, the default, a body's player is
    a frame as the author wrote it (rebuilt by :mod:`siamang.core.safe_html`).
    The React runtime reads it as ``SURVEY.clickToPlay``.

    ``transport`` names the transport the page's ``env.js`` registers when
    the page cannot send its answers without it
    (``BackendClientTemplate.transport``; ``FrontendBuilder`` passes the
    client template's). It travels in the page's own inline script, as
    ``SURVEY.transport``, so the page knows it even when ``env.js`` never
    loads: the React runtime then counts an attempt to send the answers
    without a transport as a failed one (the retry dialog, Save locally and
    finish, the error screen after the third) and never ends as if they were
    sent. With it the page also carries ``survey_id``, as ``SURVEY.surveyId``
    (the id ``env.js`` gives, from the same ``ClientEnv``), which keys what
    the browser keeps for the survey: the answers Save locally and finish
    kept while ``env.js`` was missing are under the key the next visit reads,
    and it offers Resume. None, the default, writes neither, and a page
    without a transport ends as before: a preview that stores nothing, a page
    a host gives its own transport after the build. ``SurveyJSRuntime``
    ignores it.
    """

    schema: SurveySchema
    ui: UIConfig
    css_href: str = "style.css"
    env_src: str = "env.js"
    survey_id: str | None = None
    survey: Questionnaire | None = None
    font_base: str = FONT_BASE
    csp: str | None = None
    click_to_play: bool = False
    transport: str | None = None


class RuntimeAdapter(ABC):
    """A pluggable rendering engine (SurveyJS, React, custom JS, etc.)."""

    name: str

    @abstractmethod
    def render_html(self, context: RuntimeRenderContext) -> str:
        """Return the contents of ``index.html`` for the bundle."""

    @abstractmethod
    def render_closed_page(self, context: RuntimeRenderContext, reason: str) -> str:
        """Return the contents of ``closed.html`` (quota full / deadline / closed)."""

    def static_assets(self) -> dict[str, str | bytes]:
        """Return any additional files (default: none)."""

        return {}

    def stylesheet(self, context: RuntimeRenderContext) -> str | None:
        """Return CSS for the bundle, or ``None`` to use the default theme.

        Runtimes that ship their own design system (the React runtime)
        override this and return a full stylesheet. The builder will write
        whatever this returns to ``style.css`` instead of
        :func:`siamang.frontend.theme.css.compile_css`.
        """

        return None
