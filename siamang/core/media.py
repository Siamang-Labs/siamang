"""Media attachment for questions and answer options."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_FILE_KINDS = {"image", "video", "audio"}
_VALID_KINDS = _FILE_KINDS | {"embed"}
_EXT_TO_KIND = {
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "gif": "image",
    "webp": "image",
    "svg": "image",
    "avif": "image",
    "mp4": "video",
    "webm": "video",
    "mov": "video",
    "m4v": "video",
    "ogv": "video",
    "mp3": "audio",
    "wav": "audio",
    "ogg": "audio",
    "m4a": "audio",
    "flac": "audio",
}

# ─── players ─────────────────────────────────────────────────────────────────

#: The video services a ``kind="embed"`` media plays from: the name a
#: respondent is told ("Plays from YouTube when you press play") and the
#: origin the player is framed from — YouTube's privacy-enhanced host, Vimeo's
#: player host.
EMBED_PROVIDERS: dict[str, dict[str, str]] = {
    "youtube": {"label": "YouTube", "origin": "https://www.youtube-nocookie.com"},
    "vimeo": {"label": "Vimeo", "origin": "https://player.vimeo.com"},
}
#: What each provider's player is allowed in the survey's page (their own
#: embed snippets' lists). The runtime's players and the players a page's body
#: keeps (:mod:`siamang.core.safe_html`) carry the same.
PLAYER_ALLOW: dict[str, str] = {
    "youtube": (
        "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; "
        "picture-in-picture; web-share; fullscreen"
    ),
    "vimeo": "autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media; web-share",
}
#: The shapes a player's box can have (width:height).
EMBED_ASPECTS = ("16:9", "9:16", "4:3", "1:1")
#: The latest start an embed may have, in seconds (a day).
MAX_START = 86400
_EMBED_IDS = {
    "youtube": re.compile(r"^[A-Za-z0-9_-]{11}$"),
    "vimeo": re.compile(r"^[0-9]{1,20}$"),
}
# An unlisted Vimeo video's hash (its link's second number, or h=).
_VIMEO_KEY = re.compile(r"^[0-9a-f]{6,64}$")
_EMBED_FIELDS = ("provider", "id", "key", "start", "aspect")


@dataclass(frozen=True, slots=True)
class Media:
    """A media attachment that can be rendered next to a question or option.

    ``kind`` is one of: image, video, audio — a file the page loads — or
    embed, a YouTube or Vimeo video. A file's kind, when omitted, is inferred
    from the URL extension; a URL without a recognizable extension requires
    ``kind`` to be specified explicitly.

    An embed is never inferred: ``kind="embed"`` names its ``provider``
    (``"youtube"`` or ``"vimeo"``) and the video's ``id`` — eleven letters,
    digits, ``-`` or ``_`` on YouTube, digits on Vimeo — and may give an
    unlisted Vimeo video's ``key`` (its hash), a ``start`` in seconds and the
    player's ``aspect`` (``"16:9"`` when omitted). The player's address is
    built from these (:attr:`player_src`), never from ``url``, which is the
    video's page for a person to read; left empty, it is filled in
    (``https://www.youtube.com/watch?v=ID``, ``https://vimeo.com/ID``). The
    respondent sees a play button, and nothing is loaded from the provider
    until it is pressed.
    """

    url: str
    kind: str | None = None
    alt: str | None = None
    caption: str | None = None
    autoplay: bool = False
    loop: bool = False
    controls: bool = True
    provider: str | None = None
    id: str | None = None
    key: str | None = None
    start: int | None = None
    aspect: str | None = None

    def __post_init__(self) -> None:
        if (self.kind or "").strip().lower() == "embed":
            self._check_embed()
            return
        given = [name for name in _EMBED_FIELDS if getattr(self, name) is not None]
        if given:
            raise ValueError(
                f"Media.{', '.join(given)}: only a YouTube or Vimeo video "
                f'(kind="embed") has {"this" if len(given) == 1 else "these"}.'
            )
        if not self.url or not self.url.strip():
            raise ValueError("Media.url must not be empty.")
        kind = (self.kind or "").strip().lower() or _infer_kind(self.url)
        if kind is None:
            raise ValueError(
                f"Media.kind could not be inferred from URL {self.url!r}. "
                f"Specify kind explicitly: one of {sorted(_FILE_KINDS)}."
            )
        if kind not in _VALID_KINDS:
            raise ValueError(f"Unknown media kind {self.kind!r}. Allowed: {sorted(_VALID_KINDS)}.")
        object.__setattr__(self, "kind", kind)

    def _check_embed(self) -> None:
        object.__setattr__(self, "kind", "embed")
        provider = self.provider
        if provider not in EMBED_PROVIDERS:
            raise ValueError(
                f"Media.provider {provider!r}: an embed plays from one of {sorted(EMBED_PROVIDERS)}."
            )
        if not isinstance(self.id, str) or not _EMBED_IDS[provider].match(self.id):
            shape = (
                "eleven letters, digits, '-' or '_'"
                if provider == "youtube"
                else "up to twenty digits"
            )
            label = EMBED_PROVIDERS[provider]["label"]
            raise ValueError(f"Media.id {self.id!r} is not a {label} video id ({shape}).")
        if self.key is not None:
            if provider != "vimeo":
                raise ValueError("Media.key: only an unlisted Vimeo video has a key (its hash).")
            if not isinstance(self.key, str) or not _VIMEO_KEY.match(self.key):
                raise ValueError(
                    f"Media.key {self.key!r} is not a Vimeo hash (6 to 64 of 0-9 and a-f)."
                )
        if self.start is not None and (
            not isinstance(self.start, int)
            or isinstance(self.start, bool)
            or not 0 <= self.start <= MAX_START
        ):
            raise ValueError(f"Media.start {self.start!r}: whole seconds from 0 to {MAX_START}.")
        if self.aspect is not None and self.aspect not in EMBED_ASPECTS:
            raise ValueError(f"Media.aspect {self.aspect!r}: one of {', '.join(EMBED_ASPECTS)}.")
        if not isinstance(self.url, str) or not self.url.strip():
            object.__setattr__(self, "url", _page_link(provider, self.id, self.key))

    @property
    def player_src(self) -> str | None:
        """The address of an embed's player — on YouTube's privacy-enhanced
        host or Vimeo's player host with Do Not Track, starting to play when
        it is shown (the respondent pressed play to show it) — built from
        ``provider``, ``id``, ``key`` and ``start``; None for a file."""

        if self.kind != "embed":
            return None
        if self.provider == "youtube":
            start = f"&start={self.start}" if self.start else ""
            return (
                f"https://www.youtube-nocookie.com/embed/{self.id}"
                f"?autoplay=1&rel=0&playsinline=1{start}"
            )
        key = f"h={self.key}&" if self.key else ""
        start = f"#t={self.start}s" if self.start else ""
        return f"https://player.vimeo.com/video/{self.id}?{key}dnt=1&autoplay=1{start}"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": self.url, "kind": self.kind}
        for name in _EMBED_FIELDS:
            value = getattr(self, name)
            if value is not None:
                payload[name] = value
        if self.alt is not None:
            payload["alt"] = self.alt
        if self.caption is not None:
            payload["caption"] = self.caption
        if self.autoplay:
            payload["autoplay"] = True
        if self.loop:
            payload["loop"] = True
        if not self.controls:
            payload["controls"] = False
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Media:
        return cls(
            url=payload["url"] if payload.get("kind") != "embed" else payload.get("url", ""),
            kind=payload.get("kind"),
            alt=payload.get("alt"),
            caption=payload.get("caption"),
            autoplay=bool(payload.get("autoplay", False)),
            loop=bool(payload.get("loop", False)),
            controls=bool(payload.get("controls", True)),
            provider=payload.get("provider"),
            id=payload.get("id"),
            key=payload.get("key"),
            start=payload.get("start"),
            aspect=payload.get("aspect"),
        )


def _page_link(provider: str, video: str, key: str | None) -> str:
    """The video's own page, for a person to open."""

    if provider == "youtube":
        return f"https://www.youtube.com/watch?v={video}"
    return f"https://vimeo.com/{video}" + (f"/{key}" if key else "")


def _infer_kind(url: str) -> str | None:
    path = url.split("?", 1)[0].split("#", 1)[0]
    dot = path.rfind(".")
    if dot < 0:
        return None
    ext = path[dot + 1 :].lower()
    return _EXT_TO_KIND.get(ext)
