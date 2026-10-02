"""The space between a report's blocks, and the space an item asks for above it.

A table or a chart sat flush under whatever came before it: the figure's
`margin` shorthand, which places it left, center or right, also zeroed the gap
every other block has, so a table's caption touched the next table's head and a
section's paragraph ran straight into its first table. A figure now keeps that
gap, and an item can ask for its own (`space_before`), which is what a
researcher reaches for when two results belong apart.

The browser test measures the gaps in headless Chromium and is skipped without
Node, the ``playwright`` package and a Chromium it can launch (``NODE_PATH`` and
``PLAYWRIGHT_CHROMIUM`` as ``tests/test_runtime_browser.py`` says).
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pandas as pd
import pytest

from siamang.reporting import Report
from siamang.reporting.document import layout_problem
from siamang.reporting.theme import ReportTheme

FRAME = pd.DataFrame({"Value": ["Low", "Mid", "High"], "N": [1, 2, 3]})


@pytest.mark.parametrize("space", ["0px", "40px", "2em", "1.5rem", "18pt"])
def test_a_space_before_is_a_length_of_zero_or_more(space):
    assert layout_problem({"space_before": space}) is None
    Report(title="R").add(FRAME, space_before=space)


@pytest.mark.parametrize("space", ["-20px", "10%", "40", "big", ""])
def test_a_space_before_that_is_not_a_gap_is_named_where_it_is_written(space):
    assert "space_before" in (layout_problem({"space_before": space}) or "")
    with pytest.raises(ValueError, match="space_before"):
        Report(title="R").add(FRAME, space_before=space)
    with pytest.raises(ValueError, match="space_before"):
        Report(title="R").image("fig.png", space_before=space)


def test_an_unknown_key_names_every_key_there_is():
    problem = layout_problem({"gap": "20px"}) or ""
    assert "width, align, break_before, space_before" in problem


def test_the_space_is_an_inline_custom_property_beside_the_width():
    html = (
        Report(title="R")
        .add(FRAME, caption="plain")
        .add(FRAME, caption="spaced", space_before="48px")
        .add(FRAME, caption="both", width="60%", space_before="0px")
        .to_html(standalone=True)
    )
    assert '<figure class="siamang-figure" data-align="center">' in html
    assert '<figure class="siamang-figure" data-align="center" style="--fig-space:48px">' in html
    assert 'style="--fig-w:60%;--fig-share:0.6;--fig-space:0px"' in html


def test_the_markdown_says_nothing_about_the_space():
    markdown = Report(title="R").add(FRAME, caption="T", space_before="48px").to_markdown()
    assert "48px" not in markdown


def test_a_figure_keeps_the_gap_between_blocks_in_every_stylesheet():
    for density in ("compact", "comfortable", "spacious"):
        for align in ("left", "center", "right"):
            css = ReportTheme(density=density, figure_align=align).stylesheet()
            rule = ".siamang-report > * + .siamang-figure { margin-top: var(--fig-space, var(--report-block-gap)); }"
            assert rule in css
            # The shorthand that places the figure still comes first, so the
            # rule above is the one that decides the space over it.
            assert css.index("margin: ") < css.index(rule)
            # Nothing puts a figure flush against the one before it.
            assert "margin-top: 0;" not in css


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
  const page = await browser.newPage({ viewport: { width: 1000, height: 800 } });
  await page.goto("file://" + process.argv[2]);
  const gaps = await page.evaluate(() => {
    const kids = [...document.querySelectorAll(".siamang-report > *")];
    return kids.slice(1).map((el, i) => ({
      tag: el.tagName.toLowerCase(),
      gap: Math.round(el.getBoundingClientRect().top - kids[i].getBoundingClientRect().bottom),
    }));
  });
  console.log(JSON.stringify({ ok: true, gaps }));
  await browser.close();
})();
"""


def test_the_gaps_a_reader_sees(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    report = (
        Report(title="Spacing")
        .text("A paragraph that leads into the tables.")
        .add(FRAME, caption="First")
        .add(FRAME, caption="Second")
        .add(FRAME, caption="Half", width="48%", align="left")
        .add(FRAME, caption="Half again", width="48%", align="left")
        .add(FRAME, caption="Apart", space_before="72px")
        .add(FRAME, caption="Close", space_before="0px")
    )
    page = tmp_path / "report.html"
    page.write_text(report.to_html(standalone=True, theme=ReportTheme()), encoding="utf-8")
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
    # h1, paragraph, two figures, the two halves in one row (a <div>, see
    # tests/test_report_rows.py), then two more; the comfortable gap is 20px.
    assert [(g["tag"], g["gap"]) for g in status["gaps"]] == [
        ("p", 20),
        ("figure", 20),
        ("figure", 20),
        ("div", 20),
        ("figure", 72),
        ("figure", 0),
    ]
