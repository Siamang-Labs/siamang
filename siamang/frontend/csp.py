"""A Content-Security-Policy for a survey: what the runtime needs, and no more.

A survey's page carries author content — a page's body, pictures, a theme,
for some hosts custom CSS and JavaScript — on an origin that may hold other
surveys' answers. The bundle cleans what it is given (the body's HTML,
:mod:`siamang.core.safe_html`; the theme's tokens,
:mod:`siamang.frontend.theme.tokens`; the addresses a respondent is sent to,
:mod:`siamang.core.safe_url`); a policy is the second line, binding whatever
gets past the first: it says where the page may load scripts, styles,
pictures, frames from and connect to.

What the React runtime needs (:func:`survey_csp` writes exactly this; each
host adds its own origins):

``script-src``
    ``'self'`` — ``bundle.js``, ``vendor/react*.js``, ``env.js`` (and
    ``/_vercel/insights/script.js`` with ``UIConfig.enable_analytics``).
    The inline script in ``index.html`` that sets ``window.SURVEY`` and
    ``window.PAGES``: its hash (``'sha256-…'``, :func:`inline_script_hashes`
    of the built page), or ``'unsafe-inline'``. With the hash and without
    ``'unsafe-inline'``, no inline handler (``onerror=``) and no
    ``javascript:`` address can run, whatever reaches the page.
    ``'unsafe-eval'`` — **required.** Show/hide and routing conditions are
    compiled once with ``new Function`` (``visibility.jsx``) and custom
    scripts run as an ``AsyncFunction`` (``app.jsx``). Without it every
    condition evaluates to true — a question with ``show_if`` is always
    shown, one with ``hide_if`` always hidden, the first routing rule always
    taken — and no custom script runs, with nothing on screen to say so.
    ``https://challenges.cloudflare.com`` when the host's ``env.js`` loads a
    Turnstile captcha (``captcha=True``).
``style-src``
    ``'self'`` (``style.css``) and ``'unsafe-inline'``: a page body's
    ``style="…"`` attributes (sanitized: layout, color and type only). The
    runtime's own styles are set through the CSSOM and need neither.
``font-src``
    ``'self'`` — the bundled typefaces in ``fonts/``; add the hosts a custom
    stylesheet's ``@font-face`` loads from.
``img-src``, ``media-src``
    ``'self'`` and, until hosts narrow them to a list of their own,
    ``https:`` and ``data:`` — the logo, a question's and an option's media,
    a body's pictures, audio and video.
``frame-src``
    The players a body may hold — ``https://www.youtube-nocookie.com`` and
    ``https://player.vimeo.com`` (the sanitizer rebuilds every YouTube and
    Vimeo frame on these) — and Turnstile's frame with ``captcha=True``.
``connect-src``
    ``'self'`` and where the host's ``env.js`` sends the answers (the ingest
    API's origin) — and whatever a custom script's ``api.get``/``api.post``
    call must reach.
``object-src 'none'; base-uri 'none'; form-action 'none'``
    The runtime has no plug-in, no ``<base>`` and no ``<form>``.

A policy in a ``<meta>`` must come before anything it governs: the bundle's
pages have a slot right after ``<meta charset="utf-8">``
(``RuntimeRenderContext.csp``), and :func:`insert_csp_meta` puts a policy
there in a page built elsewhere. A ``<meta>`` policy cannot say
``frame-ancestors``, ``report-to`` or ``sandbox`` (a host sends those as a
header); a header and a meta are both enforced, the stricter winning.
"""

from __future__ import annotations

import base64
import hashlib
import html
import re
from collections.abc import Iterable
from html.parser import HTMLParser

__all__ = [
    "CAPTCHA_ORIGIN",
    "PLAYER_ORIGINS",
    "csp_meta",
    "inline_script_hashes",
    "insert_csp_meta",
    "survey_csp",
]

#: Where the YouTube and Vimeo players a body may hold are served from.
PLAYER_ORIGINS = ("https://www.youtube-nocookie.com", "https://player.vimeo.com")
#: Cloudflare Turnstile's script and frame.
CAPTCHA_ORIGIN = "https://challenges.cloudflare.com"
#: Media sources until a host narrows them (``https:`` and ``data:``).
OPEN_MEDIA = ("https:", "data:")

# A source expression: a keyword or hash in quotes, a scheme ("https:"), or a
# host with an optional scheme, port and path — nothing that could end a
# directive (";", ",") or a source (whitespace), or break out of an attribute.
_SOURCE = re.compile(
    r"^(?:'(?:self|none|unsafe-inline|unsafe-eval|wasm-unsafe-eval|strict-dynamic"
    r"|unsafe-hashes|(?:sha256|sha384|sha512)-[A-Za-z0-9+/=_-]+|nonce-[A-Za-z0-9+/=_-]+)'"
    r"|[A-Za-z][A-Za-z0-9+.\-]*:"
    r"|(?:[A-Za-z][A-Za-z0-9+.\-]*://)?(?:\*\.)?[A-Za-z0-9.\-]+(?::(?:\d{1,5}|\*))?"
    r"(?:/[A-Za-z0-9._~!$&()*+=:@%/\-]*)?)$"
)
_PAGE_HEAD = re.compile(
    r"\A(?P<head>\s*<!doctype html>\s*<html\b[^<>]*>\s*<head>\s*<meta charset=\"utf-8\">)"
    r"(?:\s*<meta http-equiv=\"Content-Security-Policy\" content=\"[^\"<>]*\">)?",
    re.IGNORECASE,
)


def _sources(name: str, values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if not isinstance(value, str) or not _SOURCE.match(value):
            raise ValueError(f"{name}: {value!r} is not a CSP source expression.")
        if value not in out:
            out.append(value)
    return out


class _InlineScripts(HTMLParser):
    """The text of each inline ``<script>`` of a page, read as a browser reads
    the page: a ``<script`` inside a ``<style>``, a comment or another
    script's text is not a script."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.scripts: list[str] = []
        self._open: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self._open = None if any(name == "src" for name, _ in attrs) else []

    def handle_data(self, data: str) -> None:
        if self._open is not None:
            self._open.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            if self._open is not None:
                self.scripts.append("".join(self._open))
            self._open = None


def inline_script_hashes(page: str) -> list[str]:
    """The ``'sha256-…'`` source of each inline ``<script>`` (one without a
    ``src``) in ``page``, as a browser hashes it: the text between the tags,
    line breaks normalized to ``\\n``, UTF-8. The page is read with an HTML
    parser: a ``<script`` in an inline stylesheet or a comment is text, as it
    is to a browser, not a script whose hash would stand in for the real one."""

    reader = _InlineScripts()
    # An HTML parser reads CR LF and CR as LF before anything else.
    reader.feed(page.replace("\r\n", "\n").replace("\r", "\n"))
    reader.close()
    hashes: list[str] = []
    for text in reader.scripts:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        source = f"'sha256-{base64.b64encode(digest).decode('ascii')}'"
        if source not in hashes:
            hashes.append(source)
    return hashes


def survey_csp(
    page: str | None = None,
    *,
    connect_src: Iterable[str] = (),
    script_src: Iterable[str] = (),
    style_src: Iterable[str] = (),
    font_src: Iterable[str] = (),
    img_src: Iterable[str] = OPEN_MEDIA,
    media_src: Iterable[str] = OPEN_MEDIA,
    frame_src: Iterable[str] = PLAYER_ORIGINS,
    captcha: bool = False,
) -> str:
    """The policy the React runtime needs (the module's docstring), with the
    host's own sources added.

    ``page`` is the built ``index.html`` (or ``closed.html``): its inline
    scripts are allowed by their hashes and nothing else inline runs. Without
    it, inline scripts are allowed as such (``'unsafe-inline'``). Every
    source is checked to be a CSP source expression (``ValueError``).
    """

    if page is None:
        inline = ["'unsafe-inline'"]
    else:
        inline = inline_script_hashes(page)
    captcha_src = [CAPTCHA_ORIGIN] if captcha else []
    scripts = _sources(
        "script_src", ["'self'", "'unsafe-eval'", *inline, *script_src, *captcha_src]
    )
    frames = _sources("frame_src", [*frame_src, *captcha_src])
    directives = [
        ("default-src", ["'none'"]),
        ("script-src", scripts),
        ("style-src", _sources("style_src", ["'self'", "'unsafe-inline'", *style_src])),
        ("font-src", _sources("font_src", ["'self'", *font_src])),
        ("img-src", _sources("img_src", ["'self'", *img_src])),
        ("media-src", _sources("media_src", ["'self'", *media_src])),
        ("frame-src", frames or ["'none'"]),
        ("connect-src", _sources("connect_src", ["'self'", *connect_src])),
        ("object-src", ["'none'"]),
        ("base-uri", ["'none'"]),
        ("form-action", ["'none'"]),
    ]
    return "; ".join(f"{name} {' '.join(values)}" for name, values in directives)


def csp_meta(policy: str | None) -> str:
    """The ``<meta http-equiv="Content-Security-Policy">`` for ``policy``
    (the empty string for None or an empty policy)."""

    if not policy or not policy.strip():
        return ""
    return (
        f'\n  <meta http-equiv="Content-Security-Policy" content="{html.escape(policy.strip())}">'
    )


def insert_csp_meta(page: str, policy: str) -> str:
    """``page`` with ``policy`` in a ``<meta>`` right after its
    ``<meta charset="utf-8">``, replacing one already there.

    For a host that writes the policy after the bundle is built (and does not
    trust whoever built it): the page must start the way the runtime's pages
    do — doctype, ``<html …>``, ``<head>``, ``<meta charset="utf-8">`` —
    so that nothing comes before the policy; any other page is refused
    (``ValueError``).
    """

    match = _PAGE_HEAD.match(page)
    if not match:
        raise ValueError(
            "not a survey page: it must start with <!doctype html>, <html>, <head> and "
            '<meta charset="utf-8">, so that the policy comes before anything it governs.'
        )
    return match.group("head") + csp_meta(policy) + page[match.end() :]
