"""Tables and charts narrower than the page share a row.

"Two items at 48% sit side by side" was documented and offered in a host's
size control, and never happened: a figure is a block, so a second one at
48% started under the first. Narrow figures that follow one another now go
into a `siamang-row`, a wrapping flex row — as many as fit on a line, the
rest under them, each on its own line on a phone.

The browser test measures where they land in headless Chromium and is
skipped without Node, the ``playwright`` package and a Chromium it can
launch (``NODE_PATH`` and ``PLAYWRIGHT_CHROMIUM`` as
``tests/test_runtime_browser.py`` says).
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess

import pandas as pd
import pytest

from siamang.reporting import Report
from siamang.reporting.theme import ReportTheme

FRAME = pd.DataFrame({"Value": ["Low", "Mid", "High"], "N": [1, 2, 3]})
HAS_MPL = importlib.util.find_spec("matplotlib") is not None


def _html(report: Report, theme: ReportTheme | None = None) -> str:
    return report.to_html(standalone=True, theme=theme or ReportTheme())


def _body(html: str) -> str:
    return html.split('<main class="siamang-report">', 1)[1].split("</main>", 1)[0]


def _shape(html: str) -> list[str]:
    """The report's top-level blocks: `row(n)` for a row of n figures."""

    body = _body(html)
    shape: list[str] = []
    for match in re.finditer(
        r'<div class="siamang-row[^"]*"[^>]*>(.*?)\n</div>|<figure class="siamang-figure|<(h1|h2|p)\b',
        body,
        re.S,
    ):
        if match.group(1) is not None:
            shape.append(f"row({match.group(1).count('<figure')})")
        elif match.group(2):
            shape.append(match.group(2))
        else:
            shape.append("figure")
    return shape


def test_narrow_figures_that_follow_one_another_share_a_row():
    report = (
        Report(title="R")
        .add(FRAME, caption="full")
        .add(FRAME, caption="a", width="48%")
        .add(FRAME, caption="b", width="48%")
        .add(FRAME, caption="full again")
    )
    assert _shape(_html(report)) == ["h1", "figure", "row(2)", "figure"]


def test_a_row_holds_as_many_as_follow_and_the_browser_wraps_the_rest():
    report = Report(title="R")
    for width in ("33%", "33%", "33%", "66%", "33%"):
        report.add(FRAME, width=width)
    assert _shape(_html(report)) == ["h1", "row(5)"]


def test_text_a_full_width_figure_a_page_break_or_a_space_above_start_again():
    report = (
        Report(title="R")
        .add(FRAME, width="48%")
        .text("Between them.")
        .add(FRAME, width="48%")
        .add(FRAME, width="48%", break_before=True)
        .add(FRAME, width="48%")
        .add(FRAME, width="48%", space_before="40px")
    )
    html = _html(report)
    assert _shape(html) == ["h1", "figure", "p", "figure", "row(2)", "figure"]
    # The row starts the page its first figure asked to start.
    assert '<div class="siamang-row siamang-break" data-align="center">' in html


def test_a_lone_narrow_figure_is_not_wrapped():
    html = _html(Report(title="R").add(FRAME, width="60%", align="left"))
    assert "siamang-row" not in _body(html)
    assert '<figure class="siamang-figure" data-align="left" style="--fig-w:60%">' in html


def test_the_row_hangs_from_the_edge_its_figures_name_or_the_left():
    def row_align(*aligns: str | None) -> str:
        report = Report(title="R")
        for align in aligns:
            report.add(FRAME, width="33%", align=align)
        found = re.search(r'<div class="siamang-row[^"]*" data-align="(\w+)"', _html(report))
        assert found
        return found.group(1)

    assert row_align(None, None) == "center"  # the theme's figure_align
    assert row_align("right", "right") == "right"
    assert row_align("left", "right") == "left"


def test_a_theme_width_narrower_than_the_page_sets_every_figure_in_rows():
    theme = ReportTheme(figure_width="48%")
    report = Report(title="R").add(FRAME).add(FRAME).text("x").add(FRAME).add(FRAME)
    assert _shape(_html(report, theme)) == ["h1", "row(2)", "p", "row(2)"]


def test_the_markdown_has_no_rows():
    markdown = Report(title="R").add(FRAME, width="48%").add(FRAME, width="48%").to_markdown()
    assert "siamang-row" not in markdown


def test_every_stylesheet_sets_rows_and_stacks_them_on_a_phone():
    for density in ("compact", "comfortable", "spacious"):
        css = ReportTheme(density=density).stylesheet()
        assert ".siamang-row {" in css
        assert "flex: 0 0 var(--fig-w, var(--report-figure-width));" in css
        assert "@media (max-width: 480px)" in css
        # Only a table holds its figure open; a chart is drawn to its width.
        assert ".siamang-row > .siamang-figure:has(table) { min-width: min-content; }" in css


_HARNESS = r"""
let chromium;
try { ({ chromium } = require("playwright")); }
catch (e) { console.log(JSON.stringify({ skip: "playwright is not installed" })); process.exit(0); }
(async () => {
  let browser;
  try {
    const exe = process.env.PLAYWRIGHT_CHROMIUM;
    browser = await chromium.launch(exe ? { executablePath: exe } : {});
  } catch (e) { console.log(JSON.stringify({ skip: "no Chromium: " + e.message.split("\n")[0] })); process.exit(0); }
  const out = {};
  for (const width of [1100, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.goto("file://" + process.argv[2]);
    out[width] = await page.evaluate(() => {
      const main = document.querySelector(".siamang-report");
      const style = getComputedStyle(main);
      const left = main.getBoundingClientRect().left + parseFloat(style.paddingLeft);
      const right = main.getBoundingClientRect().right - parseFloat(style.paddingRight);
      return {
        column: Math.round(right - left),
        tables: [...document.querySelectorAll("figure table")].map((t) => {
          const r = t.getBoundingClientRect();
          return { caption: t.closest("figure").querySelector("figcaption").textContent,
                   left: Math.round(r.left - left), right: Math.round(r.right - left), top: Math.round(r.top) };
        }),
        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      };
    });
    await page.close();
  }
  console.log(JSON.stringify({ ok: true, out }));
  await browser.close();
})();
"""


_NARROWED = r"""
let chromium;
try { ({ chromium } = require("playwright")); }
catch (e) { console.log(JSON.stringify({ skip: "playwright is not installed" })); process.exit(0); }
(async () => {
  let browser;
  try {
    const exe = process.env.PLAYWRIGHT_CHROMIUM;
    browser = await chromium.launch(exe ? { executablePath: exe } : {});
  } catch (e) { console.log(JSON.stringify({ skip: "no Chromium: " + e.message.split("\n")[0] })); process.exit(0); }
  const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
  await page.goto("file://" + process.argv[2]);
  await page.waitForFunction(() => document.querySelectorAll(".siamang-row svg").length >= 2, null, { timeout: 30000 });
  const out = {};
  for (const width of [1100, 700, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.waitForTimeout(600);
    out[width] = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      spill: Math.max(0, ...[...document.querySelectorAll(".siamang-row > .siamang-figure")].map((f) => {
        const edge = f.getBoundingClientRect().right;
        return Math.max(0, ...[...f.querySelectorAll("svg")].map((e) => Math.round(e.getBoundingClientRect().right - edge)));
      })),
    }));
  }
  console.log(JSON.stringify({ ok: true, out }));
  await browser.close();
})();
"""


@pytest.mark.skipif(not HAS_MPL, reason="matplotlib")
def test_charts_in_a_row_are_drawn_narrower_when_the_window_narrows(tmp_path):
    """An interactive chart is redrawn to its figure's width; a row that held a
    figure at the width its chart was first drawn at left the page wider than
    a phone once the window narrowed."""

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    from siamang.data import SurveyData
    from siamang.reporting.charts import BarChart

    data = SurveyData(
        pd.DataFrame({"region": ["N", "S", "E", "W"] * 25, "sat": [1, 2, 3, 4, 5] * 20})
    )
    report = (
        Report(title="Charts in a row")
        .add(BarChart(data, column="region"), caption="a", width="66%")
        .add(BarChart(data, column="sat"), caption="b", width="33%")
    )
    page = tmp_path / "report.html"
    page.write_text(report.to_html(standalone=True, interactive=True), encoding="utf-8")
    harness = tmp_path / "harness.js"
    harness.write_text(_NARROWED, encoding="utf-8")
    run = subprocess.run(
        [node, str(harness), str(page)], capture_output=True, text=True, timeout=120
    )
    lines = [line for line in run.stdout.splitlines() if line.startswith("{")]
    status = json.loads(lines[-1]) if lines else {"error": run.stderr[-2000:]}
    if "skip" in status:
        pytest.skip(status["skip"])
    assert status.get("ok"), status
    assert {width: (o["overflow"], o["spill"]) for width, o in status["out"].items()} == {
        "1100": (0, 0),
        "700": (0, 0),
        "390": (0, 0),
    }


def test_where_a_reader_sees_them(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    wide = pd.DataFrame({"Value": ["Low", "High"], "N": [1, 2]})
    report = (
        Report(title="Rows")
        .add(wide, caption="half a", width="48%", align="left")
        .add(wide, caption="half b", width="48%", align="left")
        .add(wide, caption="two thirds", width="66%", align="left")
        .add(wide, caption="a third", width="33%", align="left")
        .add(wide, caption="full")
    )
    page = tmp_path / "report.html"
    page.write_text(_html(report), encoding="utf-8")
    harness = tmp_path / "harness.js"
    harness.write_text(_HARNESS, encoding="utf-8")
    run = subprocess.run(
        [node, str(harness), str(page)], capture_output=True, text=True, timeout=120
    )
    lines = [line for line in run.stdout.splitlines() if line.startswith("{")]
    status = json.loads(lines[-1]) if lines else {"error": run.stderr[-2000:]}
    if "skip" in status:
        pytest.skip(status["skip"])
    assert status.get("ok"), status

    desk = status["out"]["1100"]
    by = {t["caption"]: t for t in desk["tables"]}
    column, gap = desk["column"], 20
    # Two halves on one line, the gap between them, inside the column.
    assert by["half a"]["top"] == by["half b"]["top"]
    assert by["half b"]["left"] - by["half a"]["right"] == gap
    assert by["half a"]["left"] == 0 and by["half b"]["right"] <= column
    # Two thirds and a third on the next line, together.
    assert by["two thirds"]["top"] == by["a third"]["top"] > by["half a"]["top"]
    assert by["a third"]["left"] - by["two thirds"]["right"] == gap
    assert by["a third"]["right"] <= column
    # The full-width table after the row spans the column, under the row.
    assert (by["full"]["left"], by["full"]["right"]) == (0, column)
    assert by["full"]["top"] > by["a third"]["top"]
    assert not desk["overflow"]

    # On a phone every table takes the whole column, one under another.
    phone = status["out"]["390"]
    tops = [t["top"] for t in phone["tables"]]
    assert tops == sorted(tops) and len(set(tops)) == len(tops)
    assert all((t["left"], t["right"]) == (0, phone["column"]) for t in phone["tables"])
    assert not phone["overflow"]
