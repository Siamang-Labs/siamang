"""Addresses a respondent's browser is sent to, checked before it goes there.

A survey sends its respondent somewhere at the end — a final page's
``redirect_url``, ``UIConfig.redirect_url``, the screen-out and quota-full
returns of a panel — and links to the study's privacy notice
(``UIConfig.privacy_url``). The runtime puts these in ``location.href`` and
in a link's ``href``, where a ``javascript:`` address runs as a script of the
survey's own origin, and a ``data:`` one opens a page the author wrote. Only
``http://`` and ``https://`` addresses are allowed.

The check reads an address as a browser does: it first drops the spaces and
control characters at either end and every tab and line break inside, so
``" javascript:"`` and ``"java\\tscript:"`` are the ``javascript:`` they are
to a browser. HTML character references are not decoded (``jav&#x61;script:``
in a link's ``href`` is the HTML sanitizer's business,
:mod:`siamang.core.safe_html`): a navigation address is used as it is, never
as markup.

A template (``{url:NAME}``, ``{answer:x}``, ``{label:x}``, ``{var:x}``) may sit
anywhere after the scheme. The runtime URL-encodes what it puts in, so a
placeholder never adds a ``:`` or a ``/`` — but it could supply the letters of a
scheme (``{url:s}script:…`` with ``?s=java``), so the scheme itself must be
written out: an address starts with a literal ``http://`` or ``https://``.
"""

from __future__ import annotations

import re

#: What a browser strips from both ends of an address before parsing it
#: (the URL Standard: C0 controls and space).
_C0_AND_SPACE = "".join(chr(code) for code in range(0x21))
#: What a browser removes anywhere in an address (ASCII tab and newlines).
_TAB_OR_NEWLINE = re.compile(r"[\t\n\r]")
#: A control character left inside an address after that.
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
#: The scheme a browser reads at the start of an address.
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")
#: An address a respondent may be sent to.
_HTTP = re.compile(r"^https?://", re.IGNORECASE)
#: … with a host (or a placeholder for one) right after the two slashes.
_HTTP_HOST = re.compile(r"^https?://[^/\\\s]", re.IGNORECASE)
#: The runtime's template placeholders.
PLACEHOLDER = re.compile(r"\{(?:url|answer|label|var):[A-Za-z0-9_]+\}")

#: The schemes a navigation address may have.
NAVIGATION_SCHEMES = ("http", "https")


def normalize_url(url: str) -> str:
    """``url`` as a browser reads it before parsing: spaces and control
    characters at either end and every tab and newline inside removed."""

    return _TAB_OR_NEWLINE.sub("", url.strip(_C0_AND_SPACE))


def url_scheme(url: str) -> str | None:
    """The scheme a browser reads in ``url`` (lower case, after
    :func:`normalize_url`), or None for a relative address."""

    match = _SCHEME.match(normalize_url(url))
    return match.group(1).lower() if match else None


def navigation_url_problem(url: object) -> str | None:
    """Why ``url`` cannot be an address a respondent is sent to, or None when
    it can. None and the empty string (no address) are fine.

    >>> navigation_url_problem("https://panel.example/done?id={url:pid}") is None
    True
    >>> navigation_url_problem("javascript:alert(1)")
    "a 'javascript:' address runs a script; only http:// and https:// addresses are allowed"
    """

    if url is None:
        return None
    if not isinstance(url, str):
        return f"an address is text, got {type(url).__name__}"
    value = normalize_url(url)
    if not value:
        return None
    if _CONTROL.search(value):
        return "the address holds a control character"
    if _HTTP.match(value):
        if not _HTTP_HOST.match(value):
            return "the address has no host after the scheme"
        return None
    scheme = url_scheme(value)
    if scheme in {"javascript", "vbscript"}:
        return (
            f"a '{scheme}:' address runs a script; only http:// and https:// addresses are allowed"
        )
    if scheme is not None and scheme not in NAVIGATION_SCHEMES:
        return (
            f"a '{scheme}:' address cannot be opened from a survey; "
            "only http:// and https:// addresses are allowed"
        )
    if PLACEHOLDER.match(value) or (scheme is None and PLACEHOLDER.search(value.split("/", 1)[0])):
        return (
            "the address must start with http:// or https:// written out: "
            "a placeholder cannot supply the scheme"
        )
    if scheme in NAVIGATION_SCHEMES:
        # "https:example.com", "https:/example.com", "https:\\example.com":
        # a browser repairs them, the check does not guess.
        return "write the address as https://host/…, with two slashes"
    return "the address must start with https:// (or http://)"


def check_navigation_url(url: object, field: str) -> None:
    """Raise :class:`ValueError` naming ``field`` when ``url`` cannot be an
    address a respondent is sent to (:func:`navigation_url_problem`)."""

    problem = navigation_url_problem(url)
    if problem:
        raise ValueError(f"{field}: {url!r}: {problem}.")


def navigation_url(url: str | None) -> str | None:
    """The address the runtime is given: :func:`normalize_url` of a valid
    ``url``, None for an empty or invalid one."""

    if not url or navigation_url_problem(url):
        return None
    return normalize_url(url) or None


def is_plain_http(url: str | None) -> bool:
    """Whether ``url`` is an ``http://`` (not ``https://``) address — one a
    respondent's browser warns about or blocks on an HTTPS survey."""

    return bool(url) and url_scheme(url or "") == "http"
