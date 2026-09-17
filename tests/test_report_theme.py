"""The report's own look: the theme, the stylesheet it compiles to, and the
document `to_html` builds with it."""

from __future__ import annotations

import json
import re
from dataclasses import fields

import pandas as pd
import pytest

from siamang.reporting import Report
from siamang.reporting.theme import PRESETS, ReportTheme, ReportThemeError, sample_report

GOLDEN = "tests/documents"


# ─── the theme ───────────────────────────────────────────────────────────────


def test_a_theme_stores_only_what_was_chosen():
    """A document carries the decisions, not the defaults, so a theme that was
    never touched is absent rather than a copy of the engine's own values."""

    assert ReportTheme().to_dict() == {}
    theme = ReportTheme(font_preset="modern", width="900px", number_tables=True)
    assert theme.to_dict() == {
        "font_preset": "modern",
        "width": "900px",
        "number_tables": True,
    }
    assert ReportTheme.from_dict(theme.to_dict()) == theme
    assert ReportTheme.from_dict(None) == ReportTheme()


@pytest.mark.parametrize(
    ("kwargs", "says"),
    [
        ({"font_preset": "serif"}, "font_preset"),
        ({"density": "tight"}, "density"),
        ({"page": "a3"}, "page"),
        ({"width": "wide"}, "width"),
        ({"width": "720"}, "width"),
        ({"figure_width": "60"}, "figure_width"),
        ({"line_height": "1.6rem"}, "line_height"),
        ({"text_color": "not a color;"}, "text_color"),
        ({"figure_dpi": 5000}, "figure_dpi"),
        ({"figure_dpi": "300"}, "figure_dpi"),
        ({"custom_css": "</style><script>alert(1)</script>"}, "custom_css"),
    ],
)
def test_a_bad_theme_value_names_its_field(kwargs, says):
    """The point of checking is to name the typo before a run, not after one."""

    with pytest.raises(ReportThemeError, match=says):
        ReportTheme(**kwargs)


def test_an_unknown_field_is_named_rather_than_ignored():
    with pytest.raises(ReportThemeError, match="font_prest"):
        ReportTheme.from_dict({"font_prest": "academic"})


def test_from_env_reads_a_file_and_survives_a_missing_one(tmp_path, monkeypatch):
    """Mirrors SIAMANG_PROVENANCE: whatever runs a flow can say how its reports
    should look. A theme that cannot be read is not a reason to lose the run."""

    monkeypatch.delenv("SIAMANG_REPORT_THEME", raising=False)
    assert ReportTheme.from_env() == ReportTheme()

    path = tmp_path / "theme.json"
    path.write_text(json.dumps({"font_preset": "modern", "page": "a4"}), encoding="utf-8")
    monkeypatch.setenv("SIAMANG_REPORT_THEME", str(path))
    assert ReportTheme.from_env() == ReportTheme(font_preset="modern", page="a4")

    monkeypatch.setenv("SIAMANG_REPORT_THEME", str(tmp_path / "gone.json"))
    assert ReportTheme.from_env() == ReportTheme()
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("SIAMANG_REPORT_THEME", str(path))
    assert ReportTheme.from_env() == ReportTheme()


def test_the_report_and_the_questionnaire_agree_on_what_a_preset_is():
    """`academic` has to name the same typefaces in a report as in the survey it
    came from; the two tables are separate so that `siamang.reporting` does not
    depend on the frontend, and this is what keeps them from drifting."""

    from siamang.frontend.theme.ui_config import FONT_PRESETS

    assert set(PRESETS) == set(FONT_PRESETS)
    for name, stacks in PRESETS.items():
        assert stacks["body"] == FONT_PRESETS[name]["body"], name
        assert stacks["heading"] == FONT_PRESETS[name]["heading"], name


# ─── the stylesheet ──────────────────────────────────────────────────────────

# Fields that change the document rather than the stylesheet. Everything else
# must move at least one byte of CSS, or it is a control that does nothing.
_NOT_IN_CSS = {"figure_dpi", "number_tables", "number_figures", "table_label", "figure_label"}

_ALTERNATIVE = {
    "font_preset": "modern",
    "density": "spacious",
    "table_style": "zebra",
    "page": "a4",
    "width": "900px",
    "font_size": "13px",
    "line_height": "2.0",
    "table_font_size": "11px",
    "font_family": "Verdana, sans-serif",
    "heading_font_family": "Verdana, sans-serif",
    "mono_font_family": "Courier, monospace",
    "text_color": "#222222",
    "muted_text_color": "#777777",
    "border_color": "#cccccc",
    "accent_color": "#aa0000",
    "background_color": "#fafafa",
    "table_width": "full",
    "align_numeric": False,
    "figure_width": "60%",
    "figure_align": "left",
    "caption_position": "above",
    "custom_css": ".siamang-report { letter-spacing: .01em; }",
}


def test_every_styling_field_changes_the_stylesheet():
    """`web/components/builder/theme.tsx` states this rule in prose for the
    questionnaire — "a control for any of them would do nothing, so none is
    offered". Here it is a test, so a field cannot be added without the CSS that
    reads it."""

    base = ReportTheme().stylesheet()
    for field in fields(ReportTheme):
        if field.name in _NOT_IN_CSS:
            continue
        assert field.name in _ALTERNATIVE, f"{field.name} has no alternative value to test with"
        changed = ReportTheme(**{field.name: _ALTERNATIVE[field.name]}).stylesheet()
        assert changed != base, f"{field.name} changes nothing in the stylesheet"


def test_the_stylesheet_is_a_pure_function_of_the_theme():
    """Same theme, same bytes — which is what lets a golden pin it and a report
    render identically on two machines."""

    theme = ReportTheme(font_preset="humanist", density="compact", page="letter")
    assert theme.stylesheet() == theme.stylesheet()
    assert theme.stylesheet() == ReportTheme.from_dict(theme.to_dict()).stylesheet()
    # No network, no clock: a stylesheet that fetches a font renders differently
    # for a reader who is offline.
    assert "@import" not in theme.stylesheet()
    assert "http" not in theme.stylesheet()


@pytest.mark.parametrize("preset", sorted(PRESETS))
@pytest.mark.parametrize("density", ["compact", "comfortable", "spacious"])
def test_stylesheet_golden(preset, density, request):
    """Pins the compiled CSS per preset × density."""

    from pathlib import Path

    theme = ReportTheme(font_preset=preset, density=density)
    css = theme.stylesheet()
    golden = Path(GOLDEN) / f"report-theme.{preset}.{density}.css"
    if not golden.exists():  # pragma: no cover - first run writes the golden
        golden.write_text(css, encoding="utf-8")
    assert css == golden.read_text("utf-8"), f"run: rm {golden} and re-run to accept"


def test_page_size_reaches_the_print_rules():
    assert "@page" not in ReportTheme(page="screen").stylesheet()
    a4 = ReportTheme(page="a4").stylesheet()
    assert "@page { size: A4; margin: 22mm; }" in a4
    assert "size: Letter" in ReportTheme(page="letter").stylesheet()
    # Print rules exist whatever the page setting: a screen report is still
    # printed sometimes, and a table split across a page break is unreadable.
    assert "break-inside: avoid" in ReportTheme(page="screen").stylesheet()


def test_custom_css_comes_last_so_it_wins():
    css = ReportTheme(custom_css="body { color: red }").stylesheet()
    assert css.index("--report-text") < css.index("body { color: red }")


# ─── the document ────────────────────────────────────────────────────────────


def test_the_html_fragment_is_unchanged():
    """`to_html()` without `standalone` is what it has always been: the report's
    Markdown put through `markdown`, for a caller splicing it into a page of its
    own. Changing it would break them silently."""

    import markdown as md_lib

    report = Report(title="R").text("body").add(pd.DataFrame({"a": [1, 2]}), caption="T")
    expected = md_lib.markdown(report.to_markdown(embed_images=True), extensions=["tables"])
    assert report.to_html() == expected
    assert not report.to_html().startswith("<!doctype")


def test_a_standalone_report_is_a_document_that_carries_its_own_look():
    theme = ReportTheme(font_preset="modern", page="a4")
    html = Report(title="Quarterly", theme=theme).text("Body.").to_html(standalone=True)
    assert html.startswith("<!doctype html>")
    assert html.count("<style>") == 1
    assert '<meta name="siamang-report-theme" content="modern">' in html
    assert "<title>Quarterly</title>" in html
    assert theme.stylesheet() in html
    assert '<main class="siamang-report">' in html
    # An explicit theme beats the one on the document.
    other = Report(title="Q", theme=theme).to_html(standalone=True, theme=ReportTheme())
    assert 'content="academic"' in other


def test_a_table_is_rendered_by_the_table_layer_not_by_markdown():
    """`SurveyTable.to_html()` and its `siamang-table` class have existed since
    the table components were written and nothing has ever called them."""

    from siamang.data import SurveyData

    data = SurveyData(pd.DataFrame({"region": ["N", "S", "N", "S"]}))
    table = data.report.freq("region")
    html = Report(title="R").add(table, caption="Region").to_html(standalone=True)
    assert "siamang-table" in html
    # The table's own footer (its base, its test) rides with it inside the figure.
    assert "siamang-stats" in html and "N valid = 4" in html
    assert '<figcaption class="siamang-figcaption">Region</figcaption>' in html
    # A bare DataFrame takes the same path, so the stylesheet has one thing to style.
    plain = Report(title="R").add(pd.DataFrame({"a": [1]})).to_html(standalone=True)
    assert "siamang-table" in plain


def test_numbering_is_off_until_it_is_asked_for_and_then_it_counts():
    frame = pd.DataFrame({"a": [1]})
    report = Report(title="R").add(frame, caption="One").add(frame, caption="Two")
    assert "Table 1." not in report.to_html(standalone=True)

    numbered = report.to_html(standalone=True, theme=ReportTheme(number_tables=True))
    assert '<span class="siamang-number">Table 1.</span> One' in numbered
    assert '<span class="siamang-number">Table 2.</span> Two' in numbered

    localized = report.to_html(
        standalone=True, theme=ReportTheme(number_tables=True, table_label="Таблица")
    )
    assert "Таблица 1." in localized


def test_markdown_is_unchanged_by_any_of_this():
    """The Markdown is the content and stays what it was: a theme changes how a
    report is rendered, never what it says."""

    frame = pd.DataFrame({"a": [1, 2]})
    plain = Report(title="R").text("Body").add(frame, caption="T").to_markdown()
    themed = (
        Report(title="R", theme=ReportTheme(font_preset="modern", number_tables=True))
        .text("Body")
        .add(frame, caption="T")
        .to_markdown()
    )
    assert plain == themed


def test_headings_get_the_ids_the_contents_links_point_at():
    """`Report.combine` writes `- [Cleaning](#cleaning)` and nothing has ever
    emitted the anchor it points at, so every contents link was dead."""

    merged = Report.combine(
        [Report(title="Cleaning").text("a"), Report(title="Final tables").text("b")],
        title="All",
        toc=True,
    )
    html = merged.to_html(standalone=True)
    assert 'id="cleaning"' in html and 'id="final-tables"' in html
    assert re.search(r'href="#cleaning"', html)


def test_combine_carries_a_theme():
    theme = ReportTheme(font_preset="humanist")
    assert Report.combine([Report(title="a")], title="t", theme=theme).theme == theme
    # A section that carries one hands it up, so a host that themed the parts
    # does not have to remember to theme the whole as well.
    section = Report(title="a", theme=theme)
    assert Report.combine([section], title="t").theme == theme


def test_saving_html_writes_a_document_and_pdf_says_what_to_do_instead(tmp_path):
    report = sample_report(ReportTheme(page="a4"))
    path = report.save(tmp_path / "r.html")
    text = path.read_text("utf-8")
    assert text.startswith("<!doctype html>") and "@page" in text
    # Self-contained: no sibling files to lose when it is mailed.
    assert "fig_" not in text

    report.save(tmp_path / "r.md")
    assert (tmp_path / "r.md").read_text("utf-8").startswith("# Satisfaction")

    with pytest.raises(NotImplementedError, match="pandoc"):
        report.save(tmp_path / "r.pdf")


def test_a_sample_report_can_be_rendered_without_data_or_a_run():
    """A host previewing a theme has a questionnaire but no results yet."""

    html = sample_report(ReportTheme(table_style="grid")).to_html(standalone=True)
    assert "siamang-table" in html and "Satisfaction by region" in html
