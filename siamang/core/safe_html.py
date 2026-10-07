"""Author HTML a respondent's browser is given: only what is safe to show.

A page's ``body`` is HTML the author writes in a survey editor, or that an
importer brings in from Qualtrics, LimeSurvey or SurveyJS. The runtime puts it
into the page as HTML, on the survey's origin — where every survey of a host
keeps its respondents' answers — so whatever runs there can read them, send
them anywhere and act as the survey. :func:`sanitize_html` keeps what a page
needs and drops the rest:

* **Kept:** text formatting (paragraphs, headings, emphasis, lists, quotes,
  code, tables, ``<details>``…), ``class`` and ``id``, ``style`` with its
  layout, color and type declarations; links to ``http(s):``, ``mailto:``
  and ``tel:`` (``target="_blank"`` gets ``rel="noopener noreferrer"``);
  pictures from ``http(s):`` and ``data:`` PNG, JPEG, GIF, WebP, AVIF and BMP;
  ``<audio>`` and ``<video>`` from ``http(s):``; a YouTube or Vimeo player,
  rebuilt from the video's id on ``www.youtube-nocookie.com/embed/`` or
  ``player.vimeo.com/video/`` with the provider's ``allow`` list and
  ``referrerpolicy="strict-origin-when-cross-origin"`` (which YouTube's player
  needs).
* **Dropped:** anything that runs a script (``<script>``, every ``on…``
  attribute, ``srcdoc``, a ``javascript:`` or ``vbscript:`` address, inline
  ``<svg>`` and ``<math>``), any other frame, ``<object>`` and ``<embed>``,
  forms and their fields, what changes the page around the body (``<meta>``,
  ``<base>``, ``<link>``, ``<style>``, CSS that loads something — ``url()``,
  ``@import`` — or covers the page — ``position: fixed``), addresses of any
  other scheme, an ``id`` the runtime uses itself. An element that is not on
  the list but is harmless (``<font>`` aside, ``<o:p>`` from Word, ``<form>``,
  ``<button>``) is unwrapped: its text stays.

**Why it is safe.** The input is read with the standard library's
:class:`html.parser.HTMLParser`, and the output is written from what was read:
only elements on the list, each attribute checked, quoted and escaped, text
escaped — no comment, no raw-text element (``script``, ``style``,
``textarea``, ``noscript``, a frame's content…) and no foreign content
(``svg``, ``math``). However differently a browser would have read the input
(the "mutation XSS" a sanitizer and a browser disagreeing on the input
allows, such as ``<noscript><p title="</noscript><img onerror=…>">``), the
output has one reading, the one checked. Attribute values are decoded as a
browser decodes them (``&region=`` in a link stays ``&region=``), and an
address is checked as a browser reads it (``" JaVaScRiPt:"`` and
``"java&#x09;script:"`` are ``javascript:``).

:func:`sanitize_html_report` also says what was dropped
(:class:`HtmlRemoval`), so that an editor can tell the author: ``dangerous``
marks what would have run a script, loaded or sent something, or changed the
page; the rest is formatting the list does not hold. Sanitizing is idempotent:
the output, sanitized again, is itself, with nothing to report.

**What it costs is bounded.** :class:`html.parser.HTMLParser` is pure Python
(about a second per megabyte) and builds every attribute of a tag before it
hands the tag over, a few bytes of input each, about 160 bytes of memory: a
host that sanitizes what an editor sends could be made to spend seconds and
hundreds of megabytes on one request. A body is at most
:data:`MAX_HTML_LENGTH` characters (``Page`` and the document schema refuse a
longer one, :func:`sanitize_html_report` raises ``ValueError``); an element
with more than :data:`MAX_ATTRIBUTES` attributes is dropped (its text kept),
counted before the parser builds them; and a report keeps the first few
hundred distinct removals of each kind, not one per repetition.

The page keeps the body as written; the compilers send the runtime what this
module keeps of it (:func:`siamang.frontend.compiler.react.compile_react_payload`).
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from html import parser as _html_parser
from html.entities import html5 as _HTML5_ENTITIES
from urllib.parse import parse_qsl, urlencode, urlsplit

from siamang.core.safe_url import PLACEHOLDER, normalize_url, url_scheme

__all__ = [
    "MAX_ATTRIBUTES",
    "MAX_HTML_LENGTH",
    "HtmlRemoval",
    "SanitizedHtml",
    "check_html_length",
    "embed_src",
    "json_for_script",
    "sanitize_html",
    "sanitize_html_report",
]

# ─── what is kept ────────────────────────────────────────────────────────────

#: Attributes any kept element may have (besides ``aria-*`` and ``data-*``).
_GLOBAL_ATTRIBUTES = frozenset(
    {"class", "id", "title", "lang", "dir", "style", "role", "hidden", "tabindex", "translate"}
)
_CELL = frozenset(
    {"abbr", "align", "bgcolor", "colspan", "headers", "height", "nowrap", "rowspan", "scope"}
    | {"valign", "width"}
)
#: The elements kept, with the attributes each may have besides the global ones.
_ELEMENTS: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "target", "rel", "hreflang", "name"}),
    "abbr": frozenset(),
    "address": frozenset(),
    "article": frozenset(),
    "aside": frozenset(),
    "audio": frozenset({"src", "controls", "autoplay", "loop", "muted", "preload"}),
    "b": frozenset(),
    "bdi": frozenset(),
    "bdo": frozenset(),
    "big": frozenset(),
    "blockquote": frozenset({"cite"}),
    "br": frozenset({"clear"}),
    "caption": frozenset({"align"}),
    "center": frozenset(),
    "cite": frozenset(),
    "code": frozenset(),
    "col": frozenset({"span", "width", "align", "valign"}),
    "colgroup": frozenset({"span", "width", "align", "valign"}),
    "dd": frozenset(),
    "del": frozenset({"cite", "datetime"}),
    "details": frozenset({"open"}),
    "dfn": frozenset(),
    "div": frozenset({"align"}),
    "dl": frozenset(),
    "dt": frozenset(),
    "em": frozenset(),
    "figcaption": frozenset(),
    "figure": frozenset(),
    "font": frozenset({"color", "face", "size"}),
    "footer": frozenset(),
    "h1": frozenset({"align"}),
    "h2": frozenset({"align"}),
    "h3": frozenset({"align"}),
    "h4": frozenset({"align"}),
    "h5": frozenset({"align"}),
    "h6": frozenset({"align"}),
    "header": frozenset(),
    "hgroup": frozenset(),
    "hr": frozenset({"align", "noshade", "size", "width"}),
    "i": frozenset(),
    "img": frozenset(
        {"src", "alt", "width", "height", "loading", "decoding", "srcset", "sizes", "border"}
        | {"align", "hspace", "vspace"}
    ),
    "ins": frozenset({"cite", "datetime"}),
    "kbd": frozenset(),
    "li": frozenset({"value", "type"}),
    "mark": frozenset(),
    "nav": frozenset(),
    "ol": frozenset({"start", "reversed", "type"}),
    "p": frozenset({"align"}),
    "picture": frozenset(),
    "pre": frozenset(),
    "q": frozenset({"cite"}),
    "rp": frozenset(),
    "rt": frozenset(),
    "ruby": frozenset(),
    "s": frozenset(),
    "samp": frozenset(),
    "section": frozenset(),
    "small": frozenset(),
    "source": frozenset({"src", "srcset", "sizes", "type", "media", "width", "height"}),
    "span": frozenset(),
    "strike": frozenset(),
    "strong": frozenset(),
    "sub": frozenset(),
    "summary": frozenset(),
    "sup": frozenset(),
    "table": frozenset(
        {"align", "bgcolor", "border", "cellpadding", "cellspacing", "width", "summary"}
        | {"frame", "rules"}
    ),
    "tbody": frozenset({"align", "valign"}),
    "td": _CELL,
    "tfoot": frozenset({"align", "valign"}),
    "th": _CELL,
    "thead": frozenset({"align", "valign"}),
    "time": frozenset({"datetime"}),
    "tr": frozenset({"align", "bgcolor", "valign"}),
    "track": frozenset({"src", "kind", "srclang", "label", "default"}),
    "tt": frozenset(),
    "u": frozenset(),
    "ul": frozenset({"type"}),
    "var": frozenset(),
    "video": frozenset(
        {"src", "controls", "autoplay", "loop", "muted", "preload", "playsinline", "poster"}
        | {"width", "height"}
    ),
    "wbr": frozenset(),
}
#: Elements with no content and no end tag.
_VOID = frozenset(
    {"area", "base", "basefont", "bgsound", "br", "col", "embed", "frame", "hr", "img"}
    | {"input", "keygen", "link", "meta", "param", "source", "track", "wbr"}
)
#: Dropped with everything inside, and why: their content is a script, a
#: style, a form's options, a frame's page, foreign content, or text a browser
#: does not show.
_DROPPED_WITH_CONTENT = {
    "script": "script",
    "style": "style",
    "svg": "svg",
    "math": "svg",
    "object": "embed",
    "applet": "embed",
    "frameset": "embed",
    "iframe": "embed",
    "textarea": "form",
    "select": "form",
    "datalist": "form",
    "head": "page",
    "title": "unsupported",
    "template": "unsupported",
    "noscript": "unsupported",
    "noembed": "unsupported",
    "noframes": "unsupported",
    "xmp": "unsupported",
    "plaintext": "unsupported",
    "canvas": "unsupported",
}
#: Foreign content: a self-closing tag is empty there.
_FOREIGN = frozenset({"svg", "math"})
#: Empty elements dropped, and why.
_DROPPED_VOID = {
    "meta": "page",
    "link": "page",
    "base": "page",
    "embed": "embed",
    "frame": "embed",
    "param": "embed",
    "input": "form",
    "keygen": "form",
    "area": "unsupported",
    "basefont": "unsupported",
    "bgsound": "unsupported",
}
#: Unwrapped (their content kept) because a form is not a page's business.
_FORM_CONTAINERS = frozenset(
    {"form", "button", "label", "fieldset", "legend", "option", "optgroup", "output"}
)
#: Unwrapped without a word: they change nothing a respondent sees.
_SILENT = frozenset({"html", "body"})

#: ``id`` and ``name`` values the runtime's own globals and elements use. An
#: element with one would stand in for them (``window.SIAMANG_DESIGN`` is then
#: the element) — "DOM clobbering".
_RESERVED_ID = re.compile(
    r"^(?:siamang|survlib|__)|^(?:survey|pages|react|reactdom|turnstile|root|surveycontainer)$",
    re.IGNORECASE,
)
_ID = re.compile(r"^[\w][\w:.\-]{0,99}$")

#: Where a link may open: a new tab, or this frame or the page around it (a
#: survey embedded in another site may want to leave the frame).
_TARGETS = frozenset({"_blank", "_self", "_parent", "_top"})
_REL_TOKENS = frozenset(
    {"nofollow", "noopener", "noreferrer", "external", "ugc", "sponsored", "author", "license"}
    | {"help", "tag", "bookmark"}
)
_SIZE = re.compile(r"^\s*\d{1,5}(?:\.\d+)?\s*(?:%|px)?\s*$")
_RASTER_DATA = re.compile(
    r"^data:image/(?:png|jpeg|jpg|pjpeg|gif|webp|avif|bmp|x-icon|vnd\.microsoft\.icon)"
    r"(?:;[^,]*)?,",
    re.IGNORECASE,
)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
#: The schemes each kind of address may have (a relative address is fine).
_LINK_SCHEMES = frozenset({"http", "https", "mailto", "tel"})
_MEDIA_SCHEMES = frozenset({"http", "https"})
#: Which attributes of which elements are addresses, and of what kind.
_URL_ATTRIBUTES: dict[tuple[str, str], str] = {
    ("a", "href"): "link",
    ("img", "src"): "image",
    ("video", "poster"): "image",
    ("video", "src"): "media",
    ("audio", "src"): "media",
    ("source", "src"): "media",
    ("track", "src"): "media",
    ("blockquote", "cite"): "media",
    ("q", "cite"): "media",
    ("del", "cite"): "media",
    ("ins", "cite"): "media",
}

# ─── style="" ────────────────────────────────────────────────────────────────

_STYLE_PROPERTIES = frozenset(
    """
    color background-color background background-image opacity visibility
    font font-family font-size font-style font-weight font-variant font-stretch
    text-align text-align-last text-decoration text-decoration-line
    text-decoration-color text-decoration-style text-decoration-thickness
    text-underline-offset text-transform text-indent text-shadow text-wrap
    letter-spacing word-spacing line-height white-space word-break overflow-wrap
    word-wrap hyphens vertical-align direction unicode-bidi text-overflow
    font-variant-numeric font-variant-caps font-feature-settings font-kerning
    margin margin-top margin-right margin-bottom margin-left margin-block
    margin-block-start margin-block-end margin-inline margin-inline-start
    margin-inline-end padding padding-top padding-right padding-bottom
    padding-left padding-block padding-block-start padding-block-end
    padding-inline padding-inline-start padding-inline-end
    border border-top border-right border-bottom border-left border-width
    border-style border-color border-top-width border-right-width
    border-bottom-width border-left-width border-top-style border-right-style
    border-bottom-style border-left-style border-top-color border-right-color
    border-bottom-color border-left-color border-radius border-top-left-radius
    border-top-right-radius border-bottom-left-radius border-bottom-right-radius
    border-collapse border-spacing outline outline-color outline-style
    outline-width box-shadow box-sizing
    width height min-width min-height max-width max-height aspect-ratio
    display float clear overflow overflow-x overflow-y position top right
    bottom left list-style list-style-type list-style-position table-layout
    caption-side empty-cells object-fit object-position gap row-gap column-gap
    flex flex-direction flex-wrap flex-flow flex-grow flex-shrink flex-basis
    justify-content justify-items align-items align-content align-self order
    grid-template-columns grid-template-rows grid-column grid-row
    columns column-count column-width
    """.split()  # noqa: SIM905 - one long list, written as words
)
_STYLE_FUNCTIONS = frozenset(
    {"rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab", "oklch", "calc", "min"}
    | {"max", "clamp", "var", "linear-gradient", "radial-gradient", "conic-gradient"}
    | {"repeating-linear-gradient", "repeating-radial-gradient", "repeat", "minmax"}
)
#: CSS that loads something, runs something or covers the survey.
_STYLE_DANGER = re.compile(
    r"url\s*\(|image-set|image\s*\(|element\s*\(|cross-fade|paint\s*\(|expression\s*\("
    r"|@import|javascript:|vbscript:|behavior|binding",
    re.IGNORECASE,
)
_STYLE_VALUE = re.compile(r"""^[\w\s#%.,()+\-*/!'"]*$""")
#: What no layout, color or type value holds, so only a declaration hiding
#: what it does writes it: a CSS escape (``u\72l(`` is ``url(``, ``fi\78ed``
#: is ``fixed``) or a character that ends a declaration, a rule or a <style>
#: (``;}</style>`` in a quoted font name).
_STYLE_DISGUISE = re.compile(r"[\\<>{}]")
_STYLE_FUNCTION = re.compile(r"([A-Za-z-]+)\s*\(")
_POSITIONS = frozenset({"static", "relative", "sticky"})

# ─── the players ─────────────────────────────────────────────────────────────

_YOUTUBE_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
    | {"youtube-nocookie.com", "www.youtube-nocookie.com", "youtu.be", "www.youtu.be"}
)
_VIMEO_HOSTS = frozenset({"vimeo.com", "www.vimeo.com", "player.vimeo.com"})
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_PARAMS = frozenset(
    {"start", "end", "autoplay", "mute", "loop", "playlist", "controls", "rel"}
    | {"cc_load_policy", "cc_lang_pref", "hl", "iv_load_policy", "list", "listType"}
    | {"playsinline", "fs", "color", "disablekb"}
)
_VIMEO_PARAMS = frozenset(
    {"h", "autoplay", "autopause", "background", "byline", "color", "controls", "dnt"}
    | {"keyboard", "loop", "muted", "pip", "playsinline", "portrait", "quality", "speed"}
    | {"texttrack", "title", "transparent", "badge"}
)
_PARAM_VALUE = re.compile(r"^[A-Za-z0-9_,.\-]{1,128}$")
_TIME = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$")
_VIMEO_TIME = re.compile(r"^t=\d+(?:\.\d+)?[hms\d]*$")
#: What each provider's player is allowed in the survey's page (their own
#: embed snippets' lists).
_ALLOW = {
    "youtube": (
        "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; "
        "picture-in-picture; web-share; fullscreen"
    ),
    "vimeo": "autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media; web-share",
}
_PLAYER_TITLES = {"youtube": "YouTube video player", "vimeo": "Vimeo video player"}
#: The attributes the sanitizer writes on a player itself, in this order.
_PLAYER_OWN = ("title", "allow", "allowfullscreen", "referrerpolicy", "loading")
#: An author's attributes a player keeps (the rest are the sanitizer's own or dropped).
_PLAYER_KEPT = frozenset({"width", "height", "frameborder"})


# ─── the report ──────────────────────────────────────────────────────────────

_REASONS = {
    "script": "it would run a script",
    "unsafe_url": "only http(s), mailto and tel links and http(s) or data:image pictures and media are kept",
    "piped_url": (
        "an answer piped into an address cannot supply its scheme; "
        "start the address with https:// written out"
    ),
    "embed": "only YouTube and Vimeo players are embedded",
    "svg": "inline SVG and MathML can run scripts; show a picture with <img> instead",
    "form": "a page's body cannot collect or send answers",
    "page": "it would change the page around the body",
    "style": "it would load something or cover the survey; restyle the survey with custom CSS",
    "style_escape": (
        "a CSS escape or a character that ends a declaration can hide what a style "
        "does; write the value out plainly"
    ),
    "reserved_id": "the survey's runtime uses that name itself",
    "unsupported": "not something a page's body can hold",
    "attributes": "an element of a page's body has a few attributes, not hundreds",
}
#: The reasons that mark a removal as dangerous.
_DANGEROUS = frozenset(
    {"script", "unsafe_url", "piped_url", "embed", "svg", "form", "page", "style", "style_escape"}
)
_REPORTED_VALUE = 80

#: The longest page body, in characters. Formatted text of a few dozen pages
#: is a few hundred thousand; what is longer is a picture pasted in as
#: ``data:``, which belongs in a file the body links to, or a body written to
#: make whoever sanitizes it spend seconds and memory on it.
MAX_HTML_LENGTH = 1_000_000
#: The most attributes an element keeps; one with more is dropped, its text
#: kept. Word's busiest elements have about a dozen.
MAX_ATTRIBUTES = 100
# The distinct removals a report keeps of each kind (dangerous or not).
_MAX_REMOVALS = 500


def check_html_length(text: str | None, what: str = "the HTML") -> None:
    """Raise ``ValueError`` when ``text`` is longer than
    :data:`MAX_HTML_LENGTH` characters."""

    if text is not None and len(text) > MAX_HTML_LENGTH:
        raise ValueError(
            f"{what} is {len(text):,} characters long, more than the {MAX_HTML_LENGTH:,} "
            "a page's body may have; show a picture from its https:// address rather "
            "than writing it into the body"
        )


@dataclass(frozen=True, slots=True)
class HtmlRemoval:
    """One thing :func:`sanitize_html` dropped.

    ``element`` is the element it was or was on; ``attribute`` the attribute
    (``"style"`` for a CSS declaration), None for an element; ``value`` the
    address, declaration or attribute value (shortened), when there is one;
    ``reason`` one of ``script``, ``unsafe_url``, ``piped_url``, ``embed``, ``svg``,
    ``form``, ``page``, ``style``, ``style_escape``, ``reserved_id``, ``unsupported``,
    ``attributes`` (an element with more than :data:`MAX_ATTRIBUTES` attributes);
    ``dangerous`` whether it would have run a script, loaded or sent
    something, or changed the page around the body; ``kept_content`` whether
    the element's text stayed (an unwrapped element).
    """

    element: str
    attribute: str | None
    value: str | None
    reason: str
    dangerous: bool
    kept_content: bool = False

    @property
    def message(self) -> str:
        """What was dropped and why, in a sentence an author reads."""

        tag = f"<{self.element}>"
        if self.attribute is None and self.value:
            what = f"{tag} “{self.value}” removed"
        elif self.attribute is None:
            what = f"{tag} removed" + (" (its text is kept)" if self.kept_content else "")
        elif self.attribute == "style" and self.value:
            what = f"the style “{self.value}” of {tag} removed"
        elif self.value and self.reason in {"script", "unsafe_url", "piped_url", "embed"}:
            what = f"the {self.attribute} “{self.value}” of {tag} removed"
        else:
            what = f"the {self.attribute} attribute of {tag} removed"
        return f"{what}: {_REASONS[self.reason]}."


@dataclass(frozen=True, slots=True)
class SanitizedHtml:
    """What :func:`sanitize_html_report` returns: the ``html`` kept and what
    was ``removed``, in the order it was met."""

    html: str
    removed: tuple[HtmlRemoval, ...]

    @property
    def dangerous(self) -> tuple[HtmlRemoval, ...]:
        """The removals that would have run a script, loaded or sent
        something, or changed the page."""

        return tuple(item for item in self.removed if item.dangerous)

    def messages(self, *, dangerous_only: bool = False) -> list[str]:
        """Each distinct removal's :attr:`HtmlRemoval.message`, in order, as a
        sentence of its own (capitalized), to be joined with spaces."""

        seen: dict[str, None] = {}
        for item in self.removed:
            if item.dangerous or not dangerous_only:
                message = item.message
                seen.setdefault(message[:1].upper() + message[1:], None)
        return list(seen)


def _shorten(value: str) -> str:
    value = " ".join(value.split())
    return value if len(value) <= _REPORTED_VALUE else value[: _REPORTED_VALUE - 1] + "…"


# ─── attribute values, as a browser decodes them ─────────────────────────────

_CHARREF = re.compile(r"&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)")
_ASCII_ALNUM = re.compile(r"[A-Za-z0-9]")


def _attribute_reference(match: re.Match[str]) -> str:
    name = match.group(1)
    if name.startswith("#") or name.endswith(";"):
        return html.unescape(match.group(0))
    # A named reference without its semicolon (one of the legacy names): in an
    # attribute a browser leaves it as written when "=" or a letter or digit
    # follows, so "?a=1&region=eu" keeps its "&region=".
    for size in range(len(name), 1, -1):
        legacy = name[:size]
        if legacy in _HTML5_ENTITIES:
            follow = name[size : size + 1] or match.string[match.end() : match.end() + 1]
            if follow == "=" or _ASCII_ALNUM.match(follow):
                return match.group(0)
            return _HTML5_ENTITIES[legacy] + name[size:]
    return match.group(0)


def _unescape_attribute(value: str) -> str:
    return _CHARREF.sub(_attribute_reference, value)


# ─── addresses ───────────────────────────────────────────────────────────────


def _address_problem(value: str, kind: str) -> str | None:
    """The reason an address of ``kind`` (link, image, media) is dropped, or
    None when it is kept."""

    url = normalize_url(value)
    if _CONTROL.search(url):
        return "unsafe_url"
    scheme = url_scheme(url)
    if scheme is None:
        # A relative address — unless a placeholder could supply its scheme:
        # the runtime pipes answers into a body HTML-escaped, not URL-encoded.
        head = re.split(r"[/?#]", url, maxsplit=1)[0]
        return "piped_url" if PLACEHOLDER.search(head) else None
    if scheme in {"javascript", "vbscript"}:
        return "script"
    if kind == "link" and scheme in _LINK_SCHEMES:
        return None
    if kind != "link" and scheme in _MEDIA_SCHEMES:
        return None
    if kind == "image" and _RASTER_DATA.match(url):
        return None
    return "unsafe_url"


def _srcset(value: str) -> str | None:
    """A ``srcset`` whose every candidate is an http(s) or relative picture,
    written out again; None otherwise."""

    candidates = []
    for candidate in value.split(","):
        parts = candidate.split()
        if not parts:
            continue
        url, descriptors = parts[0], parts[1:]
        if _address_problem(url, "media") is not None:
            return None
        if any(not re.match(r"^\d+(?:\.\d+)?[wx]$", d) for d in descriptors):
            return None
        candidates.append(" ".join([url, *descriptors]))
    return ", ".join(candidates) if candidates else None


# ─── players ─────────────────────────────────────────────────────────────────


def _seconds(value: str) -> str | None:
    match = _TIME.match(value)
    if not match or not any(match.groups()):
        return None
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return str(hours * 3600 + minutes * 60 + seconds)


def _youtube(parts, query: list[tuple[str, str]]) -> str | None:  # type: ignore[no-untyped-def]
    host = parts.hostname or ""
    segments = [segment for segment in parts.path.split("/") if segment]
    params = dict(query)
    video: str | None = None
    if host.endswith("youtu.be"):
        video = segments[0] if segments else None
    elif segments[:1] == ["watch"]:
        video = params.get("v")
    elif len(segments) >= 2 and segments[0] in {"embed", "shorts", "live", "v", "e"}:
        video = segments[1]
    if video == "videoseries" and params.get("list"):
        pass
    elif not video or not _YOUTUBE_ID.match(video):
        return None
    kept: list[tuple[str, str]] = []
    for key, value in query:
        if key == "t" and "start" not in params:
            key, value = "start", _seconds(value.rstrip("s") + "s") or ""
        if key in _YOUTUBE_PARAMS and _PARAM_VALUE.match(value):
            kept.append((key, value))
    tail = f"?{urlencode(kept, safe=',')}" if kept else ""
    return f"https://www.youtube-nocookie.com/embed/{video}{tail}"


def _vimeo(parts, query: list[tuple[str, str]]) -> str | None:  # type: ignore[no-untyped-def]
    host = parts.hostname or ""
    segments = [segment for segment in parts.path.split("/") if segment]
    video: str | None = None
    unlisted: str | None = None
    if host == "player.vimeo.com":
        if len(segments) >= 2 and segments[0] == "video":
            video = segments[1]
    else:
        numbers = [index for index, segment in enumerate(segments) if segment.isdigit()]
        if numbers:
            video = segments[numbers[-1]]
            following = segments[numbers[-1] + 1 : numbers[-1] + 2]
            if following and re.match(r"^[0-9a-f]{6,64}$", following[0]):
                unlisted = following[0]
    if not video or not video.isdigit() or len(video) > 20:
        return None
    kept = [
        (key, value) for key, value in query if key in _VIMEO_PARAMS and _PARAM_VALUE.match(value)
    ]
    if unlisted and not any(key == "h" for key, _ in kept):
        kept.insert(0, ("h", unlisted))
    tail = f"?{urlencode(kept, safe=',')}" if kept else ""
    fragment = f"#{parts.fragment}" if _VIMEO_TIME.match(parts.fragment or "") else ""
    return f"https://player.vimeo.com/video/{video}{tail}{fragment}"


def embed_src(url: str) -> tuple[str, str] | None:
    """``(provider, src)`` for a YouTube or Vimeo address (a watch page, a
    share link, an embed address), the player's address rebuilt from the
    video's id and the player options that are kept; None for any other.

    >>> embed_src("https://youtu.be/aBcDeFgHiJ0?t=42")
    ('youtube', 'https://www.youtube-nocookie.com/embed/aBcDeFgHiJ0?start=42')
    """

    value = normalize_url(url)
    if value.startswith("//"):
        value = "https:" + value
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme.lower() not in {"http", "https"} or parts.username or parts.password:
        return None
    if port not in (None, 80, 443):
        return None
    host = (parts.hostname or "").lower()
    query = parse_qsl(parts.query, keep_blank_values=False)
    if host in _YOUTUBE_HOSTS:
        src = _youtube(parts, query)
        return ("youtube", src) if src else None
    if host in _VIMEO_HOSTS:
        src = _vimeo(parts, query)
        return ("vimeo", src) if src else None
    return None


# ─── CSS in style="" ─────────────────────────────────────────────────────────


def _declarations(text: str) -> list[str]:
    """``text`` split at the semicolons outside quotes and parentheses."""

    out: list[str] = []
    depth = 0
    quote = ""
    start = 0
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == ";" and depth == 0:
            out.append(text[start:index])
            start = index + 1
    out.append(text[start:])
    return out


def _clean_style(text: str) -> tuple[str, list[tuple[str, str]]]:
    """The declarations of ``style="…"`` that are kept, joined, and the ones
    dropped, each with the reason (``style``, ``style_escape`` or
    ``unsupported``)."""

    kept: list[str] = []
    dropped: list[tuple[str, str]] = []
    for declaration in _declarations(text):
        if not declaration.strip():
            continue
        prop, colon, value = declaration.partition(":")
        prop, value = prop.strip().lower(), value.strip()
        shown = _shorten(f"{prop}: {value}" if colon else declaration.strip())
        if _STYLE_DANGER.search(declaration):
            dropped.append((shown, "style"))
            continue
        if _STYLE_DISGUISE.search(declaration):
            # Dropped by the value check below too; said as dangerous, so the
            # author hears of a disguised url() or position: fixed.
            dropped.append((shown, "style_escape"))
            continue
        if not colon or not value or prop not in _STYLE_PROPERTIES:
            dropped.append((shown, "unsupported"))
            continue
        if (
            not _STYLE_VALUE.match(value)
            or value.count('"') % 2
            or value.count("'") % 2
            or any(name.lower() not in _STYLE_FUNCTIONS for name in _STYLE_FUNCTION.findall(value))
        ):
            dropped.append((shown, "unsupported"))
            continue
        if prop == "position":
            keyword = value.lower().replace("!important", "").strip()
            if keyword not in _POSITIONS:
                dropped.append((shown, "style"))
                continue
        kept.append(f"{prop}: {value}")
    return "; ".join(kept), dropped


# ─── the sanitizer ───────────────────────────────────────────────────────────

# What the output is written with most often, made once: a body of a million
# "<" or "<b>x</b>" otherwise holds a new string per piece (~60 bytes each).
_START_TAGS = {tag: f"<{tag}>" for tag in _ELEMENTS}
_END_TAGS = {tag: f"</{tag}>" for tag in _ELEMENTS}
_ESCAPED = {"<": "&lt;", ">": "&gt;", "&": "&amp;"}


class _Sanitizer(_html_parser.HTMLParser):
    def __init__(self) -> None:
        try:
            # A browser runs the survey with scripting on: <noscript>'s
            # content is then raw text (Python 3.11.14+, 3.12.12+, 3.13.9+).
            super().__init__(convert_charrefs=True, scripting=True)  # type: ignore[call-arg]
        except TypeError:
            super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.removed: list[HtmlRemoval] = []
        self._recorded: set[HtmlRemoval] = set()
        self._kept = {True: 0, False: 0}  # removals recorded, dangerous or not
        self._skip: str | None = None
        self._skip_depth = 0

    # ── reporting ──
    def _drop(
        self,
        element: str,
        reason: str,
        attribute: str | None = None,
        value: str | None = None,
        *,
        kept_content: bool = False,
        dangerous: bool | None = None,
    ) -> None:
        item = HtmlRemoval(
            element=element,
            attribute=attribute,
            value=_shorten(value) if value else None,
            reason=reason,
            dangerous=reason in _DANGEROUS if dangerous is None else dangerous,
            kept_content=kept_content,
        )
        # The same removal repeated says nothing new, and a body built to
        # repeat thousands of them must not grow the report with it: each
        # kind keeps its first _MAX_REMOVALS (the output is sanitized either
        # way).
        if item in self._recorded or self._kept[item.dangerous] >= _MAX_REMOVALS:
            return
        self._recorded.add(item)
        self._kept[item.dangerous] += 1
        self.removed.append(item)

    # ── the parser's events ──
    def parse_starttag(self, i: int) -> int:  # type: ignore[override]
        # HTMLParser finds a start tag's end with a pattern that repeats a
        # group once per attribute, and then builds every attribute: each
        # costs it ~160 bytes of memory for 4 bytes of input ("<a x=y x=y …").
        # The attributes are counted first, one match at a time, and a tag
        # with too many is dropped before the parser reads it. (The two
        # patterns are HTMLParser's own, in every Python the engine supports;
        # without them the parser simply reads the tag.)
        overfull = self._overfull_tag(i)
        if overfull is None:
            return super().parse_starttag(i)
        tag, end = overfull
        if tag in _FOREIGN and self.rawdata.startswith("/>", end - 2):
            # "<svg …/>" is an empty <svg> (handle_startendtag): nothing to skip.
            if self._skip is None:
                self._drop(tag, _DROPPED_WITH_CONTENT[tag])
            return end
        self._too_many_attributes(tag)
        if tag in self.CDATA_CONTENT_ELEMENTS:
            # As the parser would after the tag, and a browser does: what
            # follows <script> or <style> is its text up to the end tag.
            self.set_cdata_mode(tag)
        return end

    def _overfull_tag(self, start: int) -> tuple[str, int] | None:
        """The name and end of the start tag at ``start`` when it has more
        than MAX_ATTRIBUTES attributes, else None. A tag that never ends runs
        to the end of the input, as a browser drops it there."""

        tagfind = getattr(_html_parser, "tagfind_tolerant", None)
        attrfind = getattr(_html_parser, "attrfind_tolerant", None)
        if tagfind is None or attrfind is None:
            return None
        rawdata = self.rawdata
        match = tagfind.match(rawdata, start + 1)
        if not match:
            return None
        pos, count = match.end(), 0
        while True:
            found = attrfind.match(rawdata, pos)
            if not found or found.end() <= pos:
                break
            count += 1
            pos = found.end()
        if count <= MAX_ATTRIBUTES:
            return None
        end = rawdata.find(">", pos)
        return match.group(1).lower(), (end + 1 if end >= 0 else len(rawdata))

    def _too_many_attributes(self, tag: str) -> None:
        """Drop an element with more than MAX_ATTRIBUTES attributes: its text
        is kept, and one whose content is dropped anyway is skipped."""

        if self._skip is not None:
            if tag == self._skip:
                self._skip_depth += 1
            return
        if tag in _DROPPED_WITH_CONTENT or tag == "iframe":
            self._drop(tag, _DROPPED_WITH_CONTENT.get(tag, "embed"))
            self._skip_content(tag)
            return
        self._drop(tag, "attributes", kept_content=True)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if len(attrs) > MAX_ATTRIBUTES:
            self._too_many_attributes(tag)
            return
        if self._skip is not None:
            if tag == self._skip:
                self._skip_depth += 1
            return
        self._start("img" if tag == "image" else tag, self._attributes(attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # "<div/>" opens a <div> in HTML: a browser ignores the slash (a void
        # element has no end anyway). Only foreign content honors it: "<svg/>"
        # is an empty <svg>, with nothing to skip.
        if tag in _FOREIGN:
            if self._skip is None:
                self._drop(tag, _DROPPED_WITH_CONTENT[tag])
            return
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._skip is not None:
            if tag == self._skip:
                self._skip_depth -= 1
                if self._skip_depth <= 0:
                    self._skip = None
            return
        if tag == "br":
            self.out.append("<br>")  # a browser reads </br> as <br>
        elif tag in _ELEMENTS and tag not in _VOID:
            # Passed on as written, matched or not: the browser then builds
            # the tree it would have built from the input.
            self.out.append(_END_TAGS[tag])

    def handle_data(self, data: str) -> None:
        if self._skip is None:
            self.out.append(_ESCAPED.get(data) or html.escape(data, quote=False))

    # Comments, declarations and processing instructions are dropped: a
    # respondent never sees them, and Word's conditional comments are noise.
    def handle_comment(self, data: str) -> None:
        pass

    def handle_decl(self, decl: str) -> None:
        pass

    def handle_pi(self, data: str) -> None:
        pass

    def unknown_decl(self, data: str) -> None:
        pass

    # ── attributes as written ──
    def _attributes(self, parsed: list[tuple[str, str | None]]) -> list[tuple[str, str | None]]:
        """The tag's attributes with values decoded as a browser decodes an
        attribute (HTMLParser decodes them as text)."""

        text = self.get_starttag_text()
        tagfind = getattr(_html_parser, "tagfind_tolerant", None)
        attrfind = getattr(_html_parser, "attrfind_tolerant", None)
        if not text or tagfind is None or attrfind is None:
            return parsed
        match = tagfind.match(text, 1)
        if not match:
            return parsed
        raw: list[tuple[str, str | None]] = []
        pos = match.end()
        while pos < len(text):
            found = attrfind.match(text, pos)
            if not found:
                break
            name, rest, value = found.group(1, 2, 3)
            if not rest:
                value = None
            elif value[:1] == "'" == value[-1:] or value[:1] == '"' == value[-1:]:
                value = value[1:-1]
            if value:
                value = _unescape_attribute(value)
            raw.append((name.lower(), value))
            pos = found.end()
        if [name for name, _ in raw] != [name for name, _ in parsed]:
            return parsed
        return raw

    # ── elements ──
    def _skip_content(self, tag: str) -> None:
        self._skip = tag
        self._skip_depth = 1

    def _start(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "iframe":
            self._player(attrs)
            return
        if tag in _DROPPED_WITH_CONTENT:
            self._drop(tag, _DROPPED_WITH_CONTENT[tag])
            self._skip_content(tag)
            return
        if tag in _DROPPED_VOID:
            self._drop(tag, _DROPPED_VOID[tag])
            return
        if tag in _ELEMENTS:
            self.out.append(self._tag(tag, attrs))
            return
        if tag in _SILENT:
            return
        if tag in _FORM_CONTAINERS:
            self._drop(tag, "form", kept_content=True)
            return
        self._drop(tag, "unsupported", kept_content=True)

    def _tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        allowed = _ELEMENTS[tag]
        kept: list[tuple[str, str | None]] = []
        seen: set[str] = set()
        rel: list[str] | None = None
        target: str | None = None
        for name, value in attrs:
            if name in seen:
                continue  # a browser keeps the first of a repeated attribute
            seen.add(name)
            cleaned = self._attribute(tag, name, value, allowed)
            if cleaned is _DROP:
                continue
            if tag == "a" and name == "rel":
                rel = [token for token in (value or "").lower().split() if token in _REL_TOKENS]
                kept.append((name, None))  # placeholder: written below
                continue
            if tag == "a" and name == "target":
                target = cleaned  # type: ignore[assignment]
            kept.append((name, cleaned))  # type: ignore[arg-type]
        if tag == "a" and target == "_blank":
            # The page a link opens must not reach back into the survey's
            # window (window.opener) nor learn which survey sent it.
            rel = rel or []
            for token in ("noopener", "noreferrer"):
                if token not in rel:
                    rel.append(token)
            if not any(name == "rel" for name, _ in kept):
                kept.append(("rel", None))
        if not kept:
            return _START_TAGS[tag]
        parts = [f"<{tag}"]
        for name, value in kept:
            if name == "rel" and tag == "a":
                if not rel:
                    continue
                value = " ".join(rel)
            parts.append(f" {name}" if value is None else f' {name}="{html.escape(value)}"')
        return "".join(parts) + ">"

    def _attribute(
        self, tag: str, name: str, value: str | None, allowed: frozenset[str]
    ) -> str | None | object:
        """The value an attribute is written with (None: a bare attribute), or
        _DROP."""

        if name.startswith("on"):
            self._drop(tag, "script", name)
            return _DROP
        if name in {"srcdoc", "formaction", "action"}:
            self._drop(tag, "script" if name == "srcdoc" else "form", name)
            return _DROP
        if not (
            name in allowed
            or name in _GLOBAL_ATTRIBUTES
            or re.match(r"^aria-[a-z]+$", name)
            or re.match(r"^data-[a-z0-9_.\-]+$", name)
        ):
            self._drop(tag, "unsupported", name, value)
            return _DROP
        if name in {"id", "name"}:
            if value is None or not _ID.match(value):
                self._drop(tag, "unsupported", name, value)
                return _DROP
            if _RESERVED_ID.match(value):
                self._drop(tag, "reserved_id", name, value, dangerous=True)
                return _DROP
            return value
        if name == "style":
            css, dropped = _clean_style(value or "")
            for declaration, reason in dropped:
                self._drop(tag, reason, "style", declaration)
            return css if css else _DROP
        if name == "target":
            lowered = (value or "").strip().lower()
            if lowered not in _TARGETS:
                self._drop(tag, "unsupported", name, value)
                return _DROP
            return lowered
        if name in {"width", "height"} and tag not in {
            "td",
            "th",
            "col",
            "colgroup",
            "table",
            "hr",
        }:
            if value is None or not _SIZE.match(value):
                self._drop(tag, "unsupported", name, value)
                return _DROP
            return value.strip()
        if name == "srcset":
            srcset = _srcset(value or "")
            if srcset is None:
                self._drop(tag, "unsafe_url", name, value)
                return _DROP
            return srcset
        kind = _URL_ATTRIBUTES.get((tag, name))
        if kind is not None:
            if value is None:
                return _DROP
            reason = _address_problem(value, kind)
            if reason is not None:
                self._drop(tag, reason, name, value)
                return _DROP
            return normalize_url(value)
        return value

    def _player(self, attrs: list[tuple[str, str | None]]) -> None:
        """A YouTube or Vimeo ``<iframe>``, rebuilt; any other frame dropped.
        Its content (which a browser never shows) is skipped either way."""

        self._skip_content("iframe")
        given = dict(reversed(attrs))  # the first of a repeated attribute wins
        src_value = given.get("src")
        found = embed_src(src_value) if src_value else None
        if "srcdoc" in given:
            # A browser shows srcdoc rather than src: the frame is the
            # author's own page, scripts and all, whatever its src.
            self._drop("iframe", "script", "srcdoc")
        if found is None:
            if given.get("src") or "srcdoc" not in given:
                self._drop("iframe", "embed", None, given.get("src") or None)
            return
        provider, src = found
        parts = [f'<iframe src="{html.escape(src)}"']
        for name, value in attrs:
            if name in _PLAYER_KEPT and value is not None:
                if name in {"width", "height"} and not _SIZE.match(value):
                    continue
                parts.append(f' {name}="{html.escape(value.strip())}"')
            elif name in {"class", "id", "style"}:
                cleaned = self._attribute("iframe", name, value, frozenset())
                if cleaned is not _DROP and cleaned is not None:
                    parts.append(f' {name}="{html.escape(str(cleaned))}"')
            elif name.startswith("on"):
                self._drop("iframe", "script", name)
        title = (given.get("title") or "").strip() or _PLAYER_TITLES[provider]
        loading = (given.get("loading") or "").strip().lower()
        own = {
            "title": title,
            "allow": _ALLOW[provider],
            "allowfullscreen": None,
            "referrerpolicy": "strict-origin-when-cross-origin",
            "loading": loading if loading in {"lazy", "eager"} else "lazy",
        }
        for name in _PLAYER_OWN:
            value = own[name]
            parts.append(f" {name}" if value is None else f' {name}="{html.escape(value)}"')
        self.out.append("".join(parts) + "></iframe>")

    def result(self) -> SanitizedHtml:
        self.close()
        return SanitizedHtml(html="".join(self.out), removed=tuple(self.removed))


_DROP = object()


def sanitize_html_report(text: str | None) -> SanitizedHtml:
    """``text`` with only what is safe to show kept, and what was dropped
    (:class:`SanitizedHtml`). Idempotent: sanitizing the result again gives
    the same HTML and drops nothing. ``ValueError`` for text longer than
    :data:`MAX_HTML_LENGTH` characters (:func:`check_html_length`)."""

    if not text:
        return SanitizedHtml(html=text or "", removed=())
    check_html_length(text)
    sanitizer = _Sanitizer()
    sanitizer.feed(text)
    return sanitizer.result()


def sanitize_html(text: str | None) -> str:
    """``text`` with only what is safe to show kept (see the module's
    docstring); the empty string for None."""

    return sanitize_html_report(text).html


# ─── data in a <script> ──────────────────────────────────────────────────────

_SCRIPT_ESCAPES = {
    "<": "\\u003c",
    ">": "\\u003e",
    "&": "\\u0026",
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}
_SCRIPT_UNSAFE = re.compile("[<>&\u2028\u2029]")


def json_for_script(value: object) -> str:
    """``value`` as JSON that can be written inside an inline ``<script>``.

    Every ``<``, ``>`` and ``&`` is written as its ``\\u`` escape, so no text in
    it — a title, a label, a phrase of the runtime's wording — can end the
    element (``</script>``, ``</SCRIPT >``), open a comment that changes how a
    browser reads the rest (``<!--``) or be read as markup; and the line
    separators U+2028 and U+2029, which older JavaScript engines do not accept
    in a string, are escaped too. JSON has these characters only inside
    strings, where the escape means the character itself: the value read back
    is the same.
    """

    text = json.dumps(value, ensure_ascii=False)
    return _SCRIPT_UNSAFE.sub(lambda match: _SCRIPT_ESCAPES[match.group(0)], text)
