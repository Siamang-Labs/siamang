"""Side by side as a reader sees it: a share of the line, a width of its own,
a table wider than its share, a caption longer than its figure.

Rows set narrow figures side by side (tests/test_report_rows.py). Their
gutter was padding inside each figure, with the row reaching half a gap past
the column on either side, and that had four costs:

- a width that is not a percentage lost the gap: two figures of 360px drew
  pictures of 340px in a row, and 360px alone;
- the row reached past the paper when printed, so a report with a row was
  printed a little smaller on every page, and past the window of a page-sized
  theme on screen;
- a table wider than its share took what it needed even past the column, and
  one not in a row ran out of its figure, past the column and over the page;
- a word longer than its figure — a variable's name in a caption — ran out of
  it, over the figure beside it.

The gap is now the row's own (`gap`), the row is the column, and a figure's
width in it is a share of the line less its share of the gaps: a percentage
is a share (`--fig-share`, 0.5 for 50%), any other length the figure's own
width, the gap beside it. A table sits in a box that scrolls sideways on
screen; its figure takes what the table needs up to the column. A caption
breaks a word that does not fit. On a phone every narrow figure takes the
whole width, in a row or not; a centered or right-hand row that holds a
table wider than the paper starts it at the left edge; a width is more than
zero.

The browser test measures it in headless Chromium and is skipped without
Node, the ``playwright`` package and a Chromium it can launch (``NODE_PATH``
and ``PLAYWRIGHT_CHROMIUM`` as ``tests/test_runtime_browser.py`` says).
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pandas as pd
import pytest

from siamang.data import SurveyData
from siamang.reporting import Report
from siamang.reporting.document import layout_problem
from siamang.reporting.theme import ReportTheme, ReportThemeError, figure_share

FRAME = pd.DataFrame({"Value": ["Low", "Mid", "High"], "N": [1, 2, 3]})
WIDE = pd.DataFrame(
    {"Brand": ["Acme", "Brightline"], **{f"Wave {i} share (%)": [10.5, 22.5] for i in range(1, 15)}}
)
LONG_NAME = "satisfaction_with_public_charging_near_home_weighted_by_region_wave3"


def _html(report: Report, theme: ReportTheme | None = None) -> str:
    return report.to_html(standalone=True, theme=theme or ReportTheme())


@pytest.mark.parametrize(
    ("width", "share"),
    [
        ("50%", "0.5"),
        ("33%", "0.33"),
        ("66.5%", "0.665"),
        ("48%", "0.48"),
        ("100%", "1"),
        ("320px", "1"),
        ("12em", "1"),
        ("40vw", "1"),
    ],
)
def test_a_percentage_is_a_share_of_the_line_and_any_other_length_the_whole(width, share):
    assert figure_share(width) == share


def test_a_figure_s_width_carries_its_share():
    report = (
        Report(title="R")
        .add(FRAME, width="50%")
        .add(FRAME, width="320px", align="left")
        .add(FRAME, width="33%", space_before="40px")
        .add(FRAME)
    )
    html = _html(report)
    assert (
        '<figure class="siamang-figure" data-align="center" style="--fig-w:50%;--fig-share:0.5">'
        in html
    )
    assert (
        '<figure class="siamang-figure" data-align="left" style="--fig-w:320px;--fig-share:1">'
        in html
    )
    assert (
        '<figure class="siamang-figure" data-align="center" '
        'style="--fig-w:33%;--fig-share:0.33;--fig-space:40px">'
    ) in html
    # A figure with no width of its own has no share of its own either: the
    # theme's stands for it.
    assert '<figure class="siamang-figure" data-align="center">' in html


@pytest.mark.parametrize(
    ("figure_width", "share"), [(None, "1"), ("48%", "0.48"), ("50%", "0.5"), ("480px", "1")]
)
def test_the_theme_s_figure_width_has_its_share_beside_it(figure_width, share):
    tokens = ReportTheme(figure_width=figure_width).tokens()
    assert tokens["--report-figure-share"] == share
    assert (
        f"  --report-figure-share: {share};" in ReportTheme(figure_width=figure_width).stylesheet()
    )


@pytest.mark.parametrize("width", ["0px", "0%", "0.0em", "-20%", "-320px"])
def test_a_width_is_more_than_zero(width):
    # A length, but a figure that wide is drawn as nothing in a row: its
    # share of the gaps leaves it less than nothing.
    problem = layout_problem({"width": width}) or ""
    assert problem == f"width: {width!r} is not a width of more than zero (e.g. '50%', '320px')."
    with pytest.raises(ValueError, match="more than zero"):
        Report(title="R").add(FRAME, width=width)
    with pytest.raises(ReportThemeError, match="figure_width: .* more than zero"):
        ReportTheme(figure_width=width)


@pytest.mark.parametrize("width", ["0.5in", "1px", "50%", "12em", "100%"])
def test_any_width_of_more_than_zero_is_taken(width):
    assert layout_problem({"width": width}) is None
    assert ReportTheme(figure_width=width).figure_width == width


def test_a_table_sits_in_a_box_that_scrolls():
    data = SurveyData(pd.DataFrame({"region": [1, 2, 1, 2, 1, 2], "gender": [1, 1, 2, 2, 1, 2]}))
    report = (
        Report(title="R")
        .add(FRAME, caption="frame")
        .add(data.report.crosstab("gender", "region"), caption="table")
    )
    html = _html(report)
    assert html.count('<div class="siamang-scroll">\n<table') == 2
    # The statistics under a table are in the box with it, wrapped to it.
    body = html.split("<main", 1)[1]
    box = body.split('<div class="siamang-scroll">', 2)[2].split("\n</div>\n<figcaption", 1)[0]
    assert "siamang-stats" in box


def test_every_stylesheet_sets_the_gap_in_the_row_and_the_row_in_the_column():
    for density in ("compact", "comfortable", "spacious"):
        css = ReportTheme(density=density).stylesheet()
        row = css.split(".siamang-row {", 1)[1].split("}", 1)[0]
        assert "gap: var(--report-block-gap);" in row
        # Nothing reaches past the column: no negative margin, no gutter
        # inside the figures.
        assert "margin-left" not in row and "margin-right" not in row
        assert "padding: 0 calc(var(--report-block-gap) / 2)" not in css
        assert (
            "flex: 0 0 calc(var(--fig-w, var(--report-figure-width)) - var(--report-block-gap) "
            "* (1 - var(--fig-share, var(--report-figure-share))));"
        ) in css
        assert ".siamang-figure:has(> .siamang-scroll) { min-width: min-content; }" in css
        assert ".siamang-report { container-type: inline-size; }" in css
        assert ".siamang-scroll { overflow-x: auto; max-width: 100cqw; }" in css
        assert ".siamang-figcaption { overflow-wrap: anywhere; }" in css
        # Only on screen: a page has nothing to scroll a table with.
        screen = css.split("@media screen {", 1)[1].split("\n}", 1)[0]
        assert "overflow-x: auto" in screen and "container-type" in screen
        # A line wider than the page starts at its left edge, the plain value
        # kept for a browser that does not know `safe`.
        assert (
            '.siamang-row[data-align="center"] '
            "{ justify-content: center; justify-content: safe center; }"
        ) in css
        assert (
            '.siamang-row[data-align="right"] '
            "{ justify-content: flex-end; justify-content: safe flex-end; }"
        ) in css
        # On a phone every narrow figure takes the whole width, in a row or not.
        phone = css.split("@media (max-width: 480px) {", 1)[1].split("\n}", 1)[0]
        assert ".siamang-figure { width: 100%; }" in phone
        assert ".siamang-row > .siamang-figure { flex-basis: 100%; }" in phone


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
  for (const [key, file, width, media] of JSON.parse(process.argv[2])) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.emulateMedia({ media });
    await page.goto("file://" + file);
    out[key] = await page.evaluate(() => {
      const main = document.querySelector(".siamang-report");
      const style = getComputedStyle(main);
      const left = main.getBoundingClientRect().left + parseFloat(style.paddingLeft);
      const right = main.getBoundingClientRect().right - parseFloat(style.paddingRight);
      const x = (v) => Math.round((v - left) * 100) / 100;
      return {
        column: Math.round((right - left) * 100) / 100,
        figures: [...document.querySelectorAll("figure.siamang-figure")].map((f) => {
          const r = f.getBoundingClientRect();
          const cap = f.querySelector("figcaption");
          const range = document.createRange();
          range.selectNodeContents(cap);
          const text = range.getBoundingClientRect();
          const box = f.querySelector(".siamang-scroll");
          const top = (el) => (el ? Math.round(el.getBoundingClientRect().top) : null);
          return {
            caption: cap.textContent, left: x(r.left), right: x(r.right), top: Math.round(r.top),
            bottom: Math.round(r.bottom), text: [x(text.left), x(text.right)],
            scrolls: box ? box.scrollWidth > box.clientWidth : null,
            order: { caption: top(cap), table: top(f.querySelector("table")), stats: top(f.querySelector(".siamang-stats")) },
          };
        }),
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      };
    });
    await page.close();
  }
  console.log(JSON.stringify({ ok: true, out }));
  await browser.close();
})();
"""


def _measure(
    tmp_path,
    pages: dict[str, Report | tuple[Report, ReportTheme]],
    views: list[tuple[str, str, int, str]],
):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    files = {}
    for name, page in pages.items():
        report, theme = page if isinstance(page, tuple) else (page, None)
        files[name] = tmp_path / f"{name}.html"
        files[name].write_text(_html(report, theme), encoding="utf-8")
    harness = tmp_path / "harness.js"
    harness.write_text(_HARNESS, encoding="utf-8")
    plan = [[key, str(files[name]), width, media] for key, name, width, media in views]
    run = subprocess.run(
        [node, str(harness), json.dumps(plan)], capture_output=True, text=True, timeout=180
    )
    lines = [line for line in run.stdout.splitlines() if line.startswith("{")]
    status = json.loads(lines[-1]) if lines else {"error": run.stderr[-2000:]}
    if "skip" in status:
        pytest.skip(status["skip"])
    assert status.get("ok"), status
    return status["out"]


def _apart(figures: list[dict]) -> None:
    """No two figures' boxes, nor their captions' text, intersect; every
    caption's text is inside its own figure."""

    for i, a in enumerate(figures):
        assert a["left"] - 0.5 <= a["text"][0] and a["text"][1] <= a["right"] + 0.5, a
        for b in figures[i + 1 :]:
            across = min(a["right"], b["right"]) - max(a["left"], b["left"]) > 0.5
            down = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]) > 0.5
            assert not (across and down), (a, b)


def test_side_by_side_fits_and_never_overlaps(tmp_path):
    rows = Report(title="Rows")
    for caption, width in (("half a", "50%"), ("half b", "50%")):
        rows.add(FRAME, caption=caption, width=width, align="left")
    rows.text("Thirds.")
    for caption in ("third a", "third b", "third c"):
        rows.add(FRAME, caption=caption, width="33%", align="left")
    rows.text("Two thirds and a third.")
    rows.add(FRAME, caption="two thirds", width="66%", align="left")
    rows.add(FRAME, caption="one third", width="33%", align="left")
    rows.text("Pixels that fill the column: 326 + 20 + 326 = 672.")
    rows.add(FRAME, caption="326 a", width="326px", align="left")
    rows.add(FRAME, caption="326 b", width="326px", align="left")
    rows.text("Pixels that do not: 360 + 20 + 360 > 672.")
    rows.add(FRAME, caption="360 a", width="360px", align="left")
    rows.add(FRAME, caption="360 b", width="360px", align="left")
    rows.text("Long names.")
    rows.add(FRAME, caption=LONG_NAME, width="33%", align="left")
    rows.add(FRAME, caption=LONG_NAME + "_b", width="33%", align="left")
    rows.add(FRAME, caption="short", width="33%", align="left")

    wide = (
        Report(title="Wide")
        .add(FRAME, caption="beside", width="33%")
        .add(WIDE, caption="wide", width="33%")
        .text("Not in a row.")
        .add(WIDE, caption="wide alone", width="33%")
    )
    out = _measure(
        tmp_path,
        {"rows": rows, "wide": wide},
        [
            ("rows desk", "rows", 1100, "screen"),
            ("rows phone", "rows", 390, "screen"),
            ("rows print", "rows", 794, "print"),
            ("wide desk", "wide", 1100, "screen"),
            ("wide phone", "wide", 390, "screen"),
        ],
    )

    desk = out["rows desk"]
    column, gap = desk["column"], 20
    assert column == 672
    by = {f["caption"]: f for f in desk["figures"]}
    # Two at 50% fill the line with the gap between them.
    assert by["half a"]["top"] == by["half b"]["top"]
    assert (by["half a"]["left"], by["half b"]["right"]) == (0, column)
    assert by["half b"]["left"] - by["half a"]["right"] == gap
    # Three at 33%, and a 66% with a 33%, on one line each.
    assert len({by[c]["top"] for c in ("third a", "third b", "third c")}) == 1
    assert by["two thirds"]["top"] == by["one third"]["top"]
    # A width in pixels is the figure's own, the gap beside it: two of 326px
    # fill the column, two of 360px do not and take a line each.
    for caption in ("326 a", "326 b", "360 a", "360 b"):
        assert by[caption]["right"] - by[caption]["left"] == int(caption.split()[0])
    assert by["326 a"]["top"] == by["326 b"]["top"] and by["326 b"]["right"] == column
    assert by["360 b"]["top"] > by["360 a"]["top"]
    # A name longer than a third breaks inside it: three to the line.
    assert by[LONG_NAME]["top"] == by["short"]["top"]
    _apart(desk["figures"])
    assert desk["overflow"] == 0

    # On a phone one to a line, each the whole column.
    phone = out["rows phone"]
    assert all((f["left"], f["right"]) == (0, phone["column"]) for f in phone["figures"])
    _apart(phone["figures"])
    assert phone["overflow"] == 0

    # On paper the row is the column: nothing reaches past the page, which
    # the browser would otherwise shrink to fit.
    paper = out["rows print"]
    by = {f["caption"]: f for f in paper["figures"]}
    assert (by["half a"]["left"], by["half b"]["right"]) == (0, paper["column"])
    _apart(paper["figures"])
    assert paper["overflow"] == 0

    # A table wider than its share takes the line, and scrolls inside it
    # rather than run past the column; so does one that is not in a row.
    for view in ("wide desk", "wide phone"):
        page = out[view]
        by = {f["caption"]: f for f in page["figures"]}
        for caption in ("wide", "wide alone"):
            assert (by[caption]["left"], by[caption]["right"]) == (0, page["column"]), view
            assert by[caption]["scrolls"], view
        assert by["beside"]["scrolls"] is False
        assert by["wide"]["top"] > by["beside"]["top"]
        _apart(page["figures"])
        assert page["overflow"] == 0, view


def test_on_a_phone_a_narrow_figure_alone_takes_the_whole_width_too(tmp_path):
    # Not in a row: alone, kept apart by a space above or a page break on the
    # second of a pair, or by a statistic between two.
    apart = (
        Report(title="Apart")
        .add(FRAME, caption="lone half", width="50%")
        .text("A third alone.")
        .add(FRAME, caption="lone third", width="33%")
        .text("Pixels alone.")
        .add(FRAME, caption="lone 320px", width="320px", align="left")
        .text("A pair kept apart by a space above.")
        .add(FRAME, caption="space a", width="50%")
        .add(FRAME, caption="space b", width="50%", space_before="40px")
        .text("And by a page break.")
        .add(FRAME, caption="break a", width="50%")
        .add(FRAME, caption="break b", width="50%", break_before=True)
        .text("And by a statistic.")
        .add(FRAME, caption="stat a", width="50%")
        .add({"p": 0.01}, caption="Test")
        .add(FRAME, caption="stat b", width="50%")
    )
    out = _measure(
        tmp_path,
        {"apart": apart},
        [("apart desk", "apart", 1100, "screen"), ("apart phone", "apart", 390, "screen")],
    )
    desk = {f["caption"]: f for f in out["apart desk"]["figures"]}
    # On a desktop each keeps its own width.
    assert desk["lone half"]["right"] - desk["lone half"]["left"] == 336
    assert desk["lone 320px"]["right"] - desk["lone 320px"]["left"] == 320
    phone = out["apart phone"]
    assert len(phone["figures"]) == 9
    assert all((f["left"], f["right"]) == (0, phone["column"]) for f in phone["figures"]), phone
    _apart(phone["figures"])
    assert phone["overflow"] == 0


def test_a_centered_row_starts_a_table_wider_than_the_paper_at_its_edge(tmp_path):
    # Printed, a table is shown whole; one wider than the paper runs past its
    # right edge, where the browser shrinks the page to fit, never past the
    # left, where it would not be printed.
    pages = {
        align: Report(title=align)
        .add(FRAME, caption="beside", width="33%", align=align)
        .add(WIDE, caption="wide", width="33%", align=align)
        for align in ("center", "right")
    }
    out = _measure(
        tmp_path,
        pages,
        [(f"{align} print", align, 718, "print") for align in pages]
        + [(f"{align} desk", align, 1100, "screen") for align in pages],
    )
    for align in pages:
        paper = {f["caption"]: f for f in out[f"{align} print"]["figures"]}
        assert paper["wide"]["left"] == 0, (align, paper["wide"])
        assert paper["wide"]["right"] > out[f"{align} print"]["column"]
        # On screen the table scrolls inside the column, as before.
        screen = {f["caption"]: f for f in out[f"{align} desk"]["figures"]}
        assert (screen["wide"]["left"], screen["wide"]["right"]) == (0, 672)


def test_with_the_caption_above_the_statistics_stay_under_their_table(tmp_path):
    # A table's statistics are in its box with it (`.siamang-scroll`), which
    # a caption above (the figure's column-reverse) does not turn over:
    # caption, table, statistics, as a table's notes go under it. Before the
    # box they sat between the caption and the table.
    data = SurveyData(pd.DataFrame({"region": [1, 2, 1, 2, 1, 2], "gender": [1, 1, 2, 2, 1, 2]}))
    table = data.report.crosstab("gender", "region")
    pages = {
        position: (
            Report(title=position).add(table, caption=f"caption {position}"),
            ReportTheme(caption_position=position),
        )
        for position in ("above", "below")
    }
    out = _measure(tmp_path, pages, [(position, position, 1100, "screen") for position in pages])
    above = out["above"]["figures"][0]["order"]
    below = out["below"]["figures"][0]["order"]
    assert above["caption"] < above["table"] < above["stats"]
    assert below["table"] < below["stats"] < below["caption"]
