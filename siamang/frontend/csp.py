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

**A survey's own media.** ``img-src``, ``media-src`` and ``frame-src`` can
name exactly what one survey loads: :func:`media_uses` lists every picture,
sound, video and player a questionnaire document shows, and where (a JSON
pointer into the document); :func:`media_sources` turns them into the
origins of each directive::

    sources = media_sources(document)
    policy = survey_csp(page, img_src=sources.img, media_src=sources.media,
                        frame_src=sources.frame)

They judge no address: whatever the document uses is listed, from wherever
it is served. Which hosts a survey may use at all is the host's own policy.
"""

from __future__ import annotations

import base64
import hashlib
import html
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

from siamang.core.media import Media
from siamang.core.safe_html import sanitize_html

__all__ = [
    "CAPTCHA_ORIGIN",
    "PLAYER_ORIGINS",
    "MediaSources",
    "MediaUse",
    "csp_meta",
    "inline_script_hashes",
    "insert_csp_meta",
    "media_sources",
    "media_uses",
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


# ─── A survey's own media ────────────────────────────────────────────────────

#: The directive each kind of media is loaded under.
_DIRECTIVES = {
    "image": "img-src",
    "video": "media-src",
    "audio": "media-src",
    "embed": "frame-src",
}


@dataclass(frozen=True)
class MediaUse:
    """One address a survey's page loads media from.

    ``pointer`` is a JSON pointer into the questionnaire document
    (``/pages/0/items/2/media/0``, ``/pages/0/items/2/choices/1/media``,
    ``/pages/1/items/0/attributes/0/levels/2/media``, ``/ui/logo_url``,
    ``/pages/3/body``, ``/ui/custom_css``); ``where`` says what it is
    (``"question"``, ``"option"`` — an answer option or a conjoint level —
    ``"logo"``, ``"body"``, ``"css"``); ``directive`` is the policy's
    directive that governs the load (``"img-src"``, ``"media-src"``,
    ``"frame-src"``). ``url`` is what the page loads: a file's address as
    written, an embedded video's player (:attr:`~siamang.core.media.Media.player_src`),
    an address in a page's body as the sanitizer keeps it (one use per
    ``srcset`` candidate), a ``url()`` of the custom stylesheet. ``kind`` is
    the media's kind (``"image"``, ``"video"``, ``"audio"``, ``"embed"``), or
    None in a body or a stylesheet, where the element or the rule says how
    it loads.
    """

    pointer: str
    where: str
    directive: str
    url: str
    kind: str | None


@dataclass(frozen=True)
class MediaSources:
    """The sources of the media a survey uses, by directive: sorted, each
    once — an ``http(s)`` address's origin, ``data:`` for a picture written
    into the document."""

    img: tuple[str, ...]
    media: tuple[str, ...]
    frame: tuple[str, ...]


def _pointer(*parts: object) -> str:
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def _media_entry(value: Any, pointer: str, where: str) -> Iterator[MediaUse]:
    if not isinstance(value, Mapping):
        return
    try:
        media = Media.from_dict(dict(value))
    except (AttributeError, KeyError, TypeError, ValueError):
        return  # not something a page could show (from_document refuses it)
    url = media.player_src if media.kind == "embed" else media.url
    kind = media.kind or ""
    if url and kind in _DIRECTIVES:
        yield MediaUse(pointer, where, _DIRECTIVES[kind], url, kind)


def _options(value: Any, *base: object) -> Iterator[MediaUse]:
    if not isinstance(value, list):
        return
    for index, option in enumerate(value):
        if isinstance(option, Mapping):
            yield from _media_entry(option.get("media"), _pointer(*base, index, "media"), "option")


def _items(value: Any, *base: object) -> Iterator[MediaUse]:
    if not isinstance(value, list):
        return
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            continue
        here = (*base, index)
        media = item.get("media")
        if isinstance(media, list):
            for at, entry in enumerate(media):
                yield from _media_entry(entry, _pointer(*here, "media", at), "question")
        else:
            yield from _media_entry(media, _pointer(*here, "media"), "question")
        yield from _options(item.get("choices"), *here, "choices")
        attributes = item.get("attributes")
        if isinstance(attributes, list):
            for at, attribute in enumerate(attributes):
                if isinstance(attribute, Mapping):
                    yield from _options(attribute.get("levels"), *here, "attributes", at, "levels")
        # A block's questions, and a nested block's.
        yield from _items(item.get("items"), *here, "items")


class _BodyMedia(HTMLParser):
    """The addresses a sanitized body loads, as (directive, url)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[tuple[str, str]] = []
        self._open: list[str] = []

    def _add(self, directive: str, value: str | None) -> None:
        if value and value.strip():
            self.found.append((directive, value.strip()))

    def _srcset(self, value: str | None) -> None:
        for candidate in (value or "").split(","):
            parts = candidate.split()
            if parts:
                self._add("img-src", parts[0])

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        given = dict(reversed(attrs))
        parent = next((t for t in reversed(self._open) if t in {"picture", "video", "audio"}), None)
        if tag == "img":
            self._add("img-src", given.get("src"))
            self._srcset(given.get("srcset"))
        elif tag == "video":
            self._add("img-src", given.get("poster"))
            self._add("media-src", given.get("src"))
        elif tag == "audio":
            self._add("media-src", given.get("src"))
        elif tag == "source" and parent == "picture":
            self._srcset(given.get("srcset"))
        elif (tag == "source" and parent in {"video", "audio"}) or tag == "track":
            self._add("media-src", given.get("src"))
        elif tag == "iframe":
            self._add("frame-src", given.get("src"))
        if tag in {"picture", "video", "audio"}:
            self._open.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self._open:
            while self._open and self._open.pop() != tag:
                pass


def _body(value: Any, pointer: str) -> Iterator[MediaUse]:
    if not isinstance(value, str) or not value.strip():
        return
    try:
        cleaned = sanitize_html(value)
    except ValueError:
        return  # longer than a body may be (the schema refuses it)
    reader = _BodyMedia()
    reader.feed(cleaned)
    reader.close()
    for directive, url in reader.found:
        yield MediaUse(pointer, "body", directive, url, None)


_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_CSS_IMPORT = re.compile(r"@import\b[^;]*;?", re.IGNORECASE)
_CSS_FONT_FACE = re.compile(r"@font-face\s*\{[^}]*\}?", re.IGNORECASE)
_CSS_URL = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)'"\s]*))\s*\)""", re.IGNORECASE)


def _stylesheet(value: Any, pointer: str) -> Iterator[MediaUse]:
    """The pictures a custom stylesheet loads: every ``url()`` but a
    typeface's (``@font-face``, ``font-src``) and another stylesheet's
    (``@import``, ``style-src``)."""

    if not isinstance(value, str) or not value.strip():
        return
    text = _CSS_FONT_FACE.sub("", _CSS_IMPORT.sub("", _CSS_COMMENT.sub("", value)))
    for match in _CSS_URL.finditer(text):
        url = next((group for group in match.groups() if group is not None), "").strip()
        if url:
            yield MediaUse(pointer, "css", "img-src", url, None)


def media_uses(document: Mapping[str, Any]) -> list[MediaUse]:
    """Every picture, sound, video and player a questionnaire document holds
    for its pages, in document order: each question's media (a block's
    questions too), each answer option's and conjoint level's (some of
    which a page never draws, such as an option's in a dropdown, so a
    policy built from them can allow a source the page does not use), the logo
    (``ui.logo_url``), what each page's body loads once sanitized
    (:func:`siamang.core.safe_html.sanitize_html`: ``<img>`` and its
    ``srcset``, a ``<picture>``'s sources, a ``<video>``'s poster,
    ``<video>``, ``<audio>``, their ``<source>`` and ``<track>``, the players
    it keeps) and every ``url()`` of the custom stylesheet outside
    ``@font-face`` and ``@import``.

    The document is read as it is (a Save's JSON): an entry of the wrong
    type, or a media object a survey could not show, is passed over, and
    nothing a valid document holds makes it raise. No address is judged.
    """

    uses: list[MediaUse] = []
    if not isinstance(document, Mapping):
        return uses
    pages = document.get("pages")
    for index, page in enumerate(pages if isinstance(pages, list) else []):
        if not isinstance(page, Mapping):
            continue
        uses.extend(_items(page.get("items"), "pages", index, "items"))
        uses.extend(_body(page.get("body"), _pointer("pages", index, "body")))
    ui = document.get("ui")
    if isinstance(ui, Mapping):
        logo = ui.get("logo_url")
        if isinstance(logo, str) and logo.strip():
            uses.append(
                MediaUse(_pointer("ui", "logo_url"), "logo", "img-src", logo.strip(), "image")
            )
        uses.extend(_stylesheet(ui.get("custom_css"), _pointer("ui", "custom_css")))
    return uses


def _origin(url: str) -> str | None:
    """``scheme://host[:port]`` of an http(s) address (a protocol-relative
    ``//host/…`` read as https), as a CSP source; None for anything else (a
    relative address is ``'self'``'s already)."""

    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").rstrip(".")
    if scheme not in {"http", "https"} or not host:
        return None
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None
    default = {"http": 80, "https": 443}[scheme]
    origin = f"{scheme}://{host}" + (f":{port}" if port not in (None, default) else "")
    return origin if _SOURCE.match(origin) else None


def media_sources(document: Mapping[str, Any]) -> MediaSources:
    """The sources :func:`survey_csp` needs for the media a document uses
    (:func:`media_uses`): the origin of each ``http(s)`` address (``https``
    for a protocol-relative one), ``data:`` for a picture written into the
    document (``img-src`` only); nothing for a relative or empty address,
    which the page's own origin (``'self'``) already serves, or for an
    address no source expression can name."""

    found: dict[str, set[str]] = {"img-src": set(), "media-src": set(), "frame-src": set()}
    for use in media_uses(document):
        url = use.url.strip()
        if use.directive == "img-src" and url[:11].lower() == "data:image/":
            found["img-src"].add("data:")
            continue
        origin = _origin(url)
        if origin is not None:
            found[use.directive].add(origin)
    return MediaSources(
        img=tuple(sorted(found["img-src"])),
        media=tuple(sorted(found["media-src"])),
        frame=tuple(sorted(found["frame-src"])),
    )
