"""A YouTube or Vimeo video as a question's or an option's media, and the
media a survey uses as a Content-Security-Policy's sources.

A media of kind ``embed`` names its provider and the video's id; the player's
address is built from them, never from the media's url, and the runtime shows
a play button until the respondent presses it. A host may also have a page
body's players wait for the press (``click_to_play``). None of it judges an
address: every other media loads from wherever its document says, as before.
The browser tests (``test_runtime_media_embed.py``) play it in Chromium.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

import siamang as sg
from siamang.cli.loader import load_survey_module
from siamang.codegen import generate_questionnaire
from siamang.core import safe_html
from siamang.core.media import EMBED_ASPECTS, EMBED_PROVIDERS, MAX_START, PLAYER_ALLOW, Media
from siamang.frontend import ClientEnv, FrontendBuilder, ReactRuntime, UIConfig
from siamang.frontend.compiler import compile_questionnaire
from siamang.frontend.compiler.react import compile_react_payload
from siamang.frontend.csp import MediaSources, MediaUse, media_sources, media_uses, survey_csp
from siamang.frontend.runtime.base import RuntimeRenderContext
from siamang.model import (
    DocumentError,
    from_document,
    load_schema,
    to_document,
    validate_document,
)

from .test_runtime_browser import _RecordingClient

YOUTUBE = "aBcDeFgHiJ0"
VIMEO = "123456789"


def _document(media: Any = None, *, choices: Any = None, **page: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"type": "SingleChoice", "id": "q", "var": "q", "text": "Which one?"}
    if media is not None:
        item["media"] = media
    if choices is not None:
        item["choices"] = choices
    return {
        "schema_version": "1.0",
        "title": "Videos",
        "variables": {
            "q": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "A"}, {"code": 2, "label": "B"}],
            }
        },
        "pages": [{"name": "p1", "title": "One", "items": [item], **page}],
    }


def _embed(provider: str = "youtube", **extra: Any) -> dict[str, Any]:
    video = YOUTUBE if provider == "youtube" else VIMEO
    return {
        "url": "https://videos.example/v",
        "kind": "embed",
        "provider": provider,
        "id": video,
        **extra,
    }


# ── The document schema ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "media",
    [
        _embed(),
        _embed(start=0),
        _embed(start=MAX_START, aspect="9:16", alt="Clip", caption="A clip."),
        _embed(id="a-b_C12345_"),
        _embed("vimeo"),
        _embed("vimeo", key="abcdef1234", start=62, aspect="4:3"),
        _embed("vimeo", id="1"),
        {"url": "https://media.example/a.png"},
        {"url": "img/a.png", "kind": "image"},  # a relative address, as before
        {"url": "data:image/png;base64,iVBORw0KGgo=", "kind": "image"},
        {"url": "rtmp://media.example/live", "kind": "video"},  # no scheme is judged
    ],
)
def test_the_schema_takes_a_video_and_every_file_it_took(media):
    validate_document(_document(media))
    from_document(_document(media))


@pytest.mark.parametrize(
    ("media", "why"),
    [
        (_embed(key="abcdef1234"), "a YouTube video has no key"),
        (_embed(id="aBcDeFgHiJ"), "a YouTube id has eleven characters"),
        (_embed(id="aBcDeFgHiJ0/x"), "not an id"),
        (_embed("vimeo", id="123456789a"), "a Vimeo id is digits"),
        (_embed("vimeo", key="ABCDEF"), "a hash is lower-case hex"),
        (_embed(provider="dailymotion"), "an unknown provider"),
        (_embed(aspect="2:1"), "not one of the shapes"),
        (_embed(start=-1), "before the start"),
        (_embed(start=MAX_START + 1), "longer than a day"),
        (_embed(start=1.5), "whole seconds"),
        ({"url": "x", "kind": "embed", "id": YOUTUBE}, "no provider"),
        ({"url": "x", "kind": "embed", "provider": "youtube"}, "no id"),
        ({"url": "https://youtu.be/x", "provider": "youtube", "id": YOUTUBE}, "not kind embed"),
        ({"url": "a.png", "kind": "image", "start": 5}, "a file has no start"),
        ({"url": "a.png", "kind": "image", "aspect": "1:1"}, "a file has no shape"),
        ({"kind": "embed", "provider": "youtube", "id": YOUTUBE}, "the url is still required"),
        ({**_embed(), "url": ""}, "an empty url"),
    ],
)
def test_the_schema_refuses_what_is_not_a_video(media, why):
    with pytest.raises(DocumentError):
        validate_document(_document(media))


def test_the_schema_lists_the_providers_shapes_and_wording():
    schema = load_schema()
    media = schema["$defs"]["media"]["properties"]
    assert media["kind"]["enum"] == ["image", "video", "audio", "embed"]
    assert media["provider"]["enum"] == sorted(EMBED_PROVIDERS) == ["vimeo", "youtube"]
    assert media["aspect"]["enum"] == list(EMBED_ASPECTS)
    assert media["url"] == {"type": "string", "minLength": 1}  # no scheme pattern
    ui = schema["$defs"]["ui"]["properties"]
    for name in (
        "media_play_text",
        "media_loads_from_text",
        "media_close_text",
        "media_preview_blocked_text",
    ):
        assert ui[name] == {"anyOf": [{"type": "string"}, {"type": "null"}]}


# ── Media ────────────────────────────────────────────────────────────────────


def test_a_video_is_never_inferred_from_its_address():
    with pytest.raises(ValueError, match="could not be inferred"):
        Media("https://www.youtube.com/watch?v=" + YOUTUBE)
    with pytest.raises(ValueError, match='kind="embed"'):
        Media("https://youtu.be/" + YOUTUBE, provider="youtube", id=YOUTUBE)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"provider": "loom", "id": "abc"}, "an embed plays from one of"),
        ({"provider": None, "id": YOUTUBE}, "an embed plays from one of"),
        ({"provider": "youtube", "id": "short"}, "not a YouTube video id"),
        ({"provider": "vimeo", "id": "12x"}, "not a Vimeo video id"),
        ({"provider": "youtube", "id": YOUTUBE, "key": "abcdef"}, "only an unlisted Vimeo"),
        ({"provider": "vimeo", "id": VIMEO, "key": "xyz"}, "not a Vimeo hash"),
        ({"provider": "vimeo", "id": VIMEO, "start": -1}, "whole seconds"),
        ({"provider": "vimeo", "id": VIMEO, "start": True}, "whole seconds"),
        ({"provider": "vimeo", "id": VIMEO, "start": "5"}, "whole seconds"),
        ({"provider": "vimeo", "id": VIMEO, "aspect": "21:9"}, "one of 16:9"),
    ],
)
def test_a_video_checks_its_provider_id_key_start_and_shape(kwargs, message):
    with pytest.raises(ValueError, match=message):
        Media("", kind="embed", **kwargs)


def test_a_video_without_an_address_gets_its_page():
    assert Media("", kind="embed", provider="youtube", id=YOUTUBE).url == (
        f"https://www.youtube.com/watch?v={YOUTUBE}"
    )
    assert Media(" ", kind="EMBED", provider="vimeo", id=VIMEO, key="abc123").url == (
        f"https://vimeo.com/{VIMEO}/abc123"
    )
    # An address the author gave stays as written (it is never the player).
    given = Media("https://youtu.be/x?si=abc", kind="embed", provider="youtube", id=YOUTUBE)
    assert given.url == "https://youtu.be/x?si=abc" and given.kind == "embed"


def test_the_player_is_built_from_the_provider_and_the_id():
    def src(**kwargs: Any) -> str | None:
        return Media("https://evil.example/", kind="embed", **kwargs).player_src

    assert src(provider="youtube", id=YOUTUBE) == (
        f"https://www.youtube-nocookie.com/embed/{YOUTUBE}?autoplay=1&rel=0&playsinline=1"
    )
    assert src(provider="youtube", id=YOUTUBE, start=62) == (
        f"https://www.youtube-nocookie.com/embed/{YOUTUBE}?autoplay=1&rel=0&playsinline=1&start=62"
    )
    assert src(provider="youtube", id=YOUTUBE, start=0).endswith("playsinline=1")
    assert src(provider="vimeo", id=VIMEO) == (
        f"https://player.vimeo.com/video/{VIMEO}?dnt=1&autoplay=1"
    )
    assert src(provider="vimeo", id=VIMEO, key="abcdef1234", start=62) == (
        f"https://player.vimeo.com/video/{VIMEO}?h=abcdef1234&dnt=1&autoplay=1#t=62s"
    )
    assert Media("https://media.example/a.mp4").player_src is None
    assert {name: EMBED_PROVIDERS[name]["origin"] for name in EMBED_PROVIDERS} == {
        "youtube": "https://www.youtube-nocookie.com",
        "vimeo": "https://player.vimeo.com",
    }


def test_one_allow_list_for_every_player():
    """A question's video and a body's player carry the same allow list."""

    assert safe_html._ALLOW is PLAYER_ALLOW
    body = safe_html.sanitize_html(f'<iframe src="https://youtu.be/{YOUTUBE}"></iframe>')
    assert f'allow="{PLAYER_ALLOW["youtube"]}"' in body


def test_a_video_reads_and_writes_its_fields():
    media = Media(
        "https://vimeo.com/123456789",
        kind="embed",
        provider="vimeo",
        id=VIMEO,
        key="abcdef1234",
        start=5,
        aspect="1:1",
        alt="Clip",
    )
    payload = media.to_dict()
    assert payload == {
        "url": "https://vimeo.com/123456789",
        "kind": "embed",
        "provider": "vimeo",
        "id": VIMEO,
        "key": "abcdef1234",
        "start": 5,
        "aspect": "1:1",
        "alt": "Clip",
    }
    assert Media.from_dict(payload) == media
    bare = Media.from_dict({"kind": "embed", "provider": "youtube", "id": YOUTUBE})
    assert bare.to_dict() == {
        "url": f"https://www.youtube.com/watch?v={YOUTUBE}",
        "kind": "embed",
        "provider": "youtube",
        "id": YOUTUBE,
    }
    # A file writes what it wrote before, and nothing more.
    assert Media("https://media.example/a.png", alt="A").to_dict() == {
        "url": "https://media.example/a.png",
        "kind": "image",
        "alt": "A",
    }


def _media_of(document: dict[str, Any]) -> list[Any]:
    item = document["pages"][0]["items"][0]
    return [item.get("media"), *(choice.get("media") for choice in item.get("choices", []))]


def _loaded(document: dict[str, Any]) -> tuple[Any, Any]:
    loaded = from_document(copy.deepcopy(document))
    return loaded.survey, loaded.options


def test_a_document_without_a_video_round_trips_as_it_did():
    document = _document(
        [{"url": "https://media.example/a.png", "kind": "image", "alt": "A"}],
        choices=[
            {"code": 1, "label": "A", "media": {"url": "b.mp4", "kind": "video", "loop": True}},
            {"code": 2, "label": "B"},
        ],
    )
    again = to_document(*_loaded(document))
    assert json.dumps(_media_of(again)) == json.dumps(_media_of(document))


def test_a_video_survives_the_document_the_python_and_the_document_again(tmp_path: Path):
    document = _document(
        [_embed(start=62, alt="Bees"), {"url": "https://media.example/a.png", "kind": "image"}],
        choices=[
            {"code": 1, "label": "A", "media": _embed("vimeo", key="abcdef1234", aspect="9:16")},
            {"code": 2, "label": "B"},
        ],
    )
    validate_document(document)
    normal = to_document(*_loaded(document))
    assert _media_of(normal) == _media_of(document)
    code = generate_questionnaire(normal)
    assert 'provider="youtube"' in code and f'id="{YOUTUBE}"' in code and "start=62" in code
    assert 'key="abcdef1234"' in code and 'aspect="9:16"' in code
    path = tmp_path / "videos.py"
    path.write_text(code, encoding="utf-8")
    module = load_survey_module(path)
    assert to_document(module.survey, getattr(module, "options", None)) == normal


# ── What the runtime is sent ─────────────────────────────────────────────────


def test_the_runtime_is_sent_the_video_and_its_wording():
    var = sg.Variable("q", scale="nominal", labels={1: "A", 2: "B"})
    video = Media("", kind="embed", provider="youtube", id=YOUTUBE, start=3, aspect="9:16")
    option = Media("", kind="embed", provider="vimeo", id=VIMEO)
    question = sg.SingleChoice(
        "Which?",
        var=var,
        media=video,
        choices=[sg.Option(1, "A", media=option), sg.Option(2, "B")],
    )
    survey = sg.Questionnaire(title="T", pages=[sg.Page(name="p", items=[question])])
    payload = compile_react_payload(survey)
    item = payload["PAGES"][0]["items"][0]
    assert item["media"] == [video.to_dict()]
    assert item["options"][0]["media"] == option.to_dict()
    survey_meta = payload["SURVEY"]
    for key in ("mediaPlayText", "mediaLoadsFromText", "mediaCloseText", "mediaPreviewBlockedText"):
        assert survey_meta[key] is None  # the runtime's English default
    worded = compile_react_payload(
        survey, ui=UIConfig(media_play_text="Abspielen", media_close_text="Schließen")
    )["SURVEY"]
    assert worded["mediaPlayText"] == "Abspielen" and worded["mediaCloseText"] == "Schließen"
    # Off by default: a body's players are frames, as before.
    assert "clickToPlay" not in survey_meta


def _built(document: dict[str, Any], **builder: Any) -> str:
    loaded = from_document(document)
    options = dict(loaded.options)
    ui = options.pop("ui", None) or UIConfig()
    schema = compile_questionnaire(loaded.survey, options=options)
    env = ClientEnv(survey_id="t", backend="test", settings={})
    bundle = FrontendBuilder(ui=ui, runtime=ReactRuntime(), **builder).build(
        schema, client=_RecordingClient(), env=env, survey=loaded.survey
    )
    return next(
        content
        for name, content in bundle.files.items()
        if name == "index.html" and isinstance(content, str)
    )


_CLICK_TO_PLAY = re.compile(r'"clickToPlay":\s*true')


def test_a_host_has_a_bodys_players_wait_for_a_press():
    document = _document(_embed())
    assert "clickToPlay" not in _built(document)
    assert _CLICK_TO_PLAY.search(_built(document, click_to_play=True))
    loaded = from_document(document)
    schema = compile_questionnaire(loaded.survey, options={})
    runtime = ReactRuntime()
    page = runtime.render_html(
        RuntimeRenderContext(schema=schema, ui=UIConfig(), survey=loaded.survey, click_to_play=True)
    )
    assert _CLICK_TO_PLAY.search(page)
    assert RuntimeRenderContext(schema=schema, ui=UIConfig()).click_to_play is False
    assert FrontendBuilder().click_to_play is False


# ── The media a survey uses ──────────────────────────────────────────────────

_PNG = "data:image/png;base64,iVBORw0KGgo="
_BODY = (
    '<p>Read.</p><img src="https://pics.example/a.png" '
    'srcset="https://pics.example/a-2x.png 2x, //cdn.example/a-3x.png 3x">'
    '<picture><source srcset="https://pics.example/a.webp"><img src="b.png"></picture>'
    '<video poster="https://pics.example/poster.jpg" src="https://clips.example/v.mp4">'
    '<source src="https://clips.example/v.webm"><track src="https://clips.example/v.vtt"></video>'
    '<audio src="http://sounds.example:8080/a.mp3"></audio>'
    f'<iframe src="https://www.youtube.com/watch?v={YOUTUBE}"></iframe>'
    '<iframe src="https://evil.example/frame"></iframe>'  # dropped by the sanitizer
    f'<img src="{_PNG}"><script src="https://evil.example/x.js"></script>'
)
_CSS = (
    "@import url('https://css.example/more.css');\n"
    "@font-face { font-family: Brand; src: url(https://fonts.example/brand.woff2); }\n"
    '.sd-page { background: url("https://pics.example/paper.png"); }\n'
    "/* url(https://comment.example/x.png) */\n"
    ".x { background-image: url( https://Pics.Example:443/y.png ), url(z.png); }"
)


def _every_site() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Everywhere",
        "variables": {
            "q": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "A"}, {"code": 2, "label": "B"}],
            },
            "o": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "title": "One",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "q",
                        "var": "q",
                        "text": "Q",
                        "media": [
                            {"url": "https://pics.example/q.jpg"},
                            _embed(start=62),
                            {"url": _PNG, "kind": "image"},
                        ],
                        "choices": [
                            {"code": 1, "label": "A", "media": _embed("vimeo", key="abcdef1234")},
                            {"code": 2, "label": "B", "media": {"url": "local/b.png"}},
                        ],
                    },
                    {
                        "type": "Block",
                        "items": [
                            {
                                "type": "Block",
                                "items": [
                                    {
                                        "type": "OpenText",
                                        "id": "o",
                                        "var": "o",
                                        "text": "O",
                                        "media": {"url": "https://sounds.example/n.ogg"},
                                    }
                                ],
                            }
                        ],
                    },
                ],
            },
            {
                "name": "p2",
                "title": "Two",
                "body": _BODY,
                "items": [
                    {
                        "type": "Conjoint",
                        "id": "c",
                        "var": ["c_t1", "c_version"],
                        "text": "C",
                        "alternatives": 2,
                        "tasks": 1,
                        "versions": 1,
                        "attributes": [
                            {
                                "name": "brand",
                                "levels": [
                                    {"code": 1, "label": "X"},
                                    {"code": 2, "label": "Y"},
                                    {
                                        "code": 3,
                                        "label": "Z",
                                        "media": {"url": "https://pics.example/z.png"},
                                    },
                                ],
                            },
                            {
                                "name": "price",
                                "levels": [{"code": 1, "label": "1"}, {"code": 2, "label": "2"}],
                            },
                        ],
                    }
                ],
            },
        ],
        "ui": {"logo_url": "https://brand.example/logo.svg", "custom_css": _CSS},
    }


def test_every_place_a_survey_shows_media_is_listed_with_its_pointer():
    document = _every_site()
    validate_document(document)
    youtube = f"https://www.youtube-nocookie.com/embed/{YOUTUBE}"
    assert media_uses(document) == [
        MediaUse(
            "/pages/0/items/0/media/0", "question", "img-src", "https://pics.example/q.jpg", "image"
        ),
        MediaUse(
            "/pages/0/items/0/media/1",
            "question",
            "frame-src",
            f"{youtube}?autoplay=1&rel=0&playsinline=1&start=62",
            "embed",
        ),
        MediaUse("/pages/0/items/0/media/2", "question", "img-src", _PNG, "image"),
        MediaUse(
            "/pages/0/items/0/choices/0/media",
            "option",
            "frame-src",
            f"https://player.vimeo.com/video/{VIMEO}?h=abcdef1234&dnt=1&autoplay=1",
            "embed",
        ),
        MediaUse("/pages/0/items/0/choices/1/media", "option", "img-src", "local/b.png", "image"),
        MediaUse(
            "/pages/0/items/1/items/0/items/0/media",
            "question",
            "media-src",
            "https://sounds.example/n.ogg",
            "audio",
        ),
        MediaUse(
            "/pages/1/items/0/attributes/0/levels/2/media",
            "option",
            "img-src",
            "https://pics.example/z.png",
            "image",
        ),
        MediaUse("/pages/1/body", "body", "img-src", "https://pics.example/a.png", None),
        MediaUse("/pages/1/body", "body", "img-src", "https://pics.example/a-2x.png", None),
        MediaUse("/pages/1/body", "body", "img-src", "//cdn.example/a-3x.png", None),
        MediaUse("/pages/1/body", "body", "img-src", "https://pics.example/a.webp", None),
        MediaUse("/pages/1/body", "body", "img-src", "b.png", None),
        MediaUse("/pages/1/body", "body", "img-src", "https://pics.example/poster.jpg", None),
        MediaUse("/pages/1/body", "body", "media-src", "https://clips.example/v.mp4", None),
        MediaUse("/pages/1/body", "body", "media-src", "https://clips.example/v.webm", None),
        MediaUse("/pages/1/body", "body", "media-src", "https://clips.example/v.vtt", None),
        MediaUse("/pages/1/body", "body", "media-src", "http://sounds.example:8080/a.mp3", None),
        MediaUse("/pages/1/body", "body", "frame-src", youtube, None),
        MediaUse("/pages/1/body", "body", "img-src", _PNG, None),
        MediaUse("/ui/logo_url", "logo", "img-src", "https://brand.example/logo.svg", "image"),
        MediaUse("/ui/custom_css", "css", "img-src", "https://pics.example/paper.png", None),
        MediaUse("/ui/custom_css", "css", "img-src", "https://Pics.Example:443/y.png", None),
        MediaUse("/ui/custom_css", "css", "img-src", "z.png", None),
    ]


def test_the_sources_are_the_origins_the_survey_loads_from():
    sources = media_sources(_every_site())
    assert sources == MediaSources(
        img=(
            "data:",
            "https://brand.example",
            "https://cdn.example",
            "https://pics.example",
        ),
        media=("http://sounds.example:8080", "https://clips.example", "https://sounds.example"),
        frame=("https://player.vimeo.com", "https://www.youtube-nocookie.com"),
    )
    # Neither a typeface's host, nor an imported stylesheet's, nor a dropped
    # script's or frame's.
    every = {*sources.img, *sources.media, *sources.frame}
    assert not every & {"https://fonts.example", "https://css.example", "https://evil.example"}
    # Each is a source the policy takes.
    policy = survey_csp(img_src=sources.img, media_src=sources.media, frame_src=sources.frame)
    assert "img-src 'self' data: https://brand.example https://cdn.example" in policy
    assert "frame-src https://player.vimeo.com https://www.youtube-nocookie.com;" in policy


def test_a_survey_without_media_has_a_closed_policy():
    sources = media_sources(_document())
    assert sources == MediaSources(img=(), media=(), frame=())
    policy = survey_csp(img_src=sources.img, media_src=sources.media, frame_src=sources.frame)
    assert "img-src 'self';" in policy and "media-src 'self';" in policy
    assert "frame-src 'none';" in policy


@pytest.mark.parametrize(
    "document",
    [
        {},
        [],
        {"pages": "p"},
        {"pages": [None, 3, {"items": "x", "body": 5}]},
        {"pages": [{"items": [None, {"media": "a.png"}, {"media": [3, None, {"url": 7}]}]}]},
        {
            "pages": [
                {"items": [{"media": {"url": "x", "kind": "embed", "provider": "loom", "id": "1"}}]}
            ]
        },
        {
            "pages": [
                {"items": [{"choices": [None, {"media": 4}], "attributes": [None, {"levels": 1}]}]}
            ]
        },
        {"ui": {"logo_url": 5, "custom_css": ["x"]}},
        {"ui": "plain"},
    ],
)
def test_what_is_not_a_media_is_passed_over(document):
    assert media_uses(document) == []
    assert media_sources(document) == MediaSources(img=(), media=(), frame=())


def test_an_address_no_source_can_name_is_left_out():
    document = _document(
        [
            {"url": "https://{answer:q}.example/a.png", "kind": "image"},
            {"url": "ftp://files.example/a.png", "kind": "image"},
            {"url": "https://user:pw@[::1]:99999/a.png", "kind": "image"},
            {"url": "data:video/mp4;base64,AAAA", "kind": "video"},
            {"url": "https://bücher.example/a.png", "kind": "image"},
        ]
    )
    sources = media_sources(document)
    assert sources.img == ("https://xn--bcher-kva.example",)
    assert sources.media == ()
