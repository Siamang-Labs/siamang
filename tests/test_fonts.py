"""The survey's typefaces come with the survey, not from Google Fonts.

A compiled survey used to link `fonts.googleapis.com` (and so fetch from
`fonts.gstatic.com`) on every page: the respondent's address went to Google
before they had read a word. The families of the font presets now ship with
the package, the stylesheet declares them with ``@font-face`` pointing at
``fonts/`` next to it, and the bundle carries those files and their licenses.
"""

from __future__ import annotations

import re

import pytest

import siamang as sg
from siamang.frontend import (
    ClientEnv,
    FrontendBuilder,
    LocalClientTemplate,
    ReactRuntime,
    RuntimeRenderContext,
    SurveyJSRuntime,
    UIConfig,
    compile_css,
)
from siamang.frontend.compiler import compile_questionnaire
from siamang.frontend.theme import fonts
from siamang.frontend.theme.ui_config import FONT_PRESETS

_THIRD_PARTY = re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com|googleapis|gstatic")


def _survey() -> sg.Questionnaire:
    age = sg.Variable("age", scale="ratio", label="Age")
    return sg.Questionnaire(
        title="T", pages=[sg.Page(name="p", items=[sg.NumericInput("Age?", var=age)])]
    )


def _bundle(ui: UIConfig, runtime=None) -> dict[str, str | bytes]:
    survey = _survey()
    schema = compile_questionnaire(survey)
    env = ClientEnv(survey_id="s1", backend="local", settings={})
    bundle = FrontendBuilder(ui=ui, runtime=runtime or ReactRuntime()).build(
        schema, client=LocalClientTemplate(), env=env, survey=survey
    )
    return bundle.files


def _stylesheet(files: dict[str, str | bytes]) -> str:
    (name,) = (n for n in files if re.fullmatch(r"style(\.[0-9a-f]+)?\.css", n))
    css = files[name]
    assert isinstance(css, str)
    return css


def _font_files(files: dict[str, str | bytes]) -> set[str]:
    return {name for name in files if name.startswith("fonts/")}


def _expected(*slugs: str) -> set[str]:
    out: set[str] = set()
    for family in fonts.BUNDLED_FAMILIES:
        if family.slug in slugs:
            out |= {"fonts/" + name for name in (*family.files, family.license)}
    return out


@pytest.mark.parametrize(
    ("preset", "slugs"),
    [
        ("academic", ("source-serif-4", "inter")),
        ("modern", ("inter",)),
        ("humanist", ("nunito",)),
    ],
)
def test_a_compiled_survey_serves_its_preset_typefaces_itself(preset, slugs):
    files = _bundle(UIConfig(font_preset=preset))
    html = files["index.html"]
    css = _stylesheet(files)
    assert isinstance(html, str)
    # No font CDN anywhere: not linked, not preconnected, not imported.
    assert not _THIRD_PARTY.search(html)
    assert not _THIRD_PARTY.search(css)
    # The stylesheet declares the preset's families from fonts/ …
    used = set(re.findall(r'url\("(fonts/[^"]+)"\)', css))
    assert used == {name for name in _expected(*slugs) if name.endswith(".woff2")}
    # … and the bundle carries exactly those files, with their licenses.
    assert _font_files(files) == _expected(*slugs)
    for name in _font_files(files):
        content = files[name]
        assert isinstance(content, bytes)
        if name.endswith(".woff2"):
            assert content[:4] == b"wOF2"
        else:
            assert b"SIL OPEN FONT LICENSE Version 1.1" in content


def test_the_font_rules_keep_google_fonts_subsets_and_variable_weights():
    css = fonts.font_face_css('"Source Serif 4", Georgia, serif', "Inter, sans-serif")
    faces = re.findall(r"@font-face \{(.*?)\}", css, re.S)
    assert len(faces) == 6  # latin, latin-ext, cyrillic of each
    assert all("font-display: swap;" in face for face in faces)
    serif = [face for face in faces if '"Source Serif 4"' in face]
    assert all("font-weight: 200 900;" in face and "-opsz-normal" in face for face in serif)
    latin = [face for face in faces if re.search(r"-latin-(wght|opsz)-", face)]
    assert len(latin) == 2
    assert all("unicode-range: U+0000-00FF," in face for face in latin)


def test_a_stack_of_its_own_uses_a_bundled_family_it_names():
    files = _bundle(UIConfig(font_family='"nunito", sans-serif'))
    # The body is Nunito (case-insensitive, as CSS family names are); the
    # headings and the interface keep the academic preset's Source Serif 4
    # and Inter.
    assert _font_files(files) == _expected("nunito", "source-serif-4", "inter")


def test_a_family_that_is_not_bundled_is_not_fetched_from_anywhere():
    ui = UIConfig(
        font_preset="modern",
        font_family='"Roboto", "Helvetica Neue", sans-serif',
        heading_font_family='"Playfair Display", serif',
        ui_font_family='"Roboto", sans-serif',
    )
    files = _bundle(ui)
    css = _stylesheet(files)
    assert "@font-face" not in css
    assert not _THIRD_PARTY.search(css) and not _THIRD_PARTY.search(str(files["index.html"]))
    assert _font_files(files) == set()


def test_the_surveyjs_runtime_serves_them_too():
    files = _bundle(UIConfig(), runtime=SurveyJSRuntime())
    assert not _THIRD_PARTY.search(str(files["index.html"]))
    assert not _THIRD_PARTY.search(_stylesheet(files))
    assert _font_files(files) == _expected("source-serif-4")


def test_a_host_that_inlines_the_stylesheet_points_it_at_its_own_font_url():
    """Studio's preview puts the stylesheet inline in a page it serves, so the
    rules cannot be relative to it: the host names the URL it serves
    font_file() at."""

    survey = _survey()
    context = RuntimeRenderContext(
        schema=compile_questionnaire(survey),
        ui=UIConfig(),
        survey=survey,
        font_base="https://api.example/runtime/react/fonts/",
    )
    css = ReactRuntime().stylesheet(context)
    used = re.findall(r'url\("([^"]+)"\)', css)
    assert used and all(u.startswith("https://api.example/runtime/react/fonts/") for u in used)
    assert 'url("https://api.example/runtime/react/fonts/inter-latin-wght-normal.woff2")' in css
    assert compile_css(UIConfig(), font_base="/f/").count('url("/f/') == 3


def test_font_file_serves_the_bundled_files_and_nothing_else():
    for name in fonts.FONT_FILES:
        assert fonts.font_file(name)
    for name in ("../react.production.min.js", "fonts/inter-OFL.txt", "README.md", "x.woff2"):
        with pytest.raises(KeyError):
            fonts.font_file(name)


def test_the_bundled_typefaces_stay_small():
    """What the package and an `academic` bundle carry (the README gives the
    figures); a new family or subset should be a decision, not a drift."""

    woff2 = sum(len(fonts.font_file(n)) for n in fonts.FONT_FILES if n.endswith(".woff2"))
    assert woff2 <= 600_000


def test_the_presets_name_no_font_cdn():
    assert all("google_fonts" not in preset for preset in FONT_PRESETS.values())
    assert not hasattr(UIConfig(), "effective_google_fonts_url")
