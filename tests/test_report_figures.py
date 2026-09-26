"""A report's figures: drawn once, let go once written, named by their report.

A figure holds its drawing (megabytes at a report's resolution) for as long as
its chart refers to it, closed or not, and a flow keeps every node's chart: a
Save report of thirty charts held thirty figures and was killed in a 512 MB
sandbox. These tests pin what replaced that — each chart the report draws is
rendered once (its Markdown and its HTML write the same bytes) and released,
a flow run releases each chart once its node rendered it, and a chart keeps
its picture so nothing is drawn again — and that two reports saved in one
folder no longer write over each other's figures.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from siamang.core.variable import Variable, VariableMap  # noqa: E402
from siamang.data import SurveyData  # noqa: E402
from siamang.flow import FlowRunner, check_flow  # noqa: E402
from siamang.model import from_document, loads  # noqa: E402
from siamang.reporting import Report  # noqa: E402
from siamang.reporting import charts as charts_module  # noqa: E402
from siamang.reporting import result_charts as rc  # noqa: E402

DOCUMENTS = Path(__file__).resolve().parent / "documents"
AGREE = {1: "Strongly disagree", 2: "Disagree", 3: "Neither", 4: "Agree", 5: "Strongly agree"}


@pytest.fixture(autouse=True)
def _close_figures():
    plt.close("all")
    yield
    plt.close("all")


def _data() -> SurveyData:
    rng = np.random.default_rng(11)
    n = 400
    frame = pd.DataFrame(
        {
            "region": rng.integers(1, 5, n),
            "sat": rng.integers(1, 6, n),
            "t1": rng.integers(1, 6, n),
            "t2": rng.integers(1, 6, n),
            "score": rng.normal(50, 10, n),
            "w": rng.uniform(0.5, 2.0, n),
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "region",
                "nominal",
                label="Region",
                labels={1: "North", 2: "South", 3: "East", 4: "West"},
            ),
            Variable("sat", "ordinal", label="Satisfaction", labels=AGREE),
            Variable("t1", "ordinal", label="Trust: Acme", labels=AGREE),
            Variable("t2", "ordinal", label="Trust: Globex", labels=AGREE),
            Variable("score", "interval", label="Score"),
            Variable("w", "ratio", label="Weight"),
        ]
    )
    return SurveyData(frame=frame, variables=variables).with_weight("w")


def _charts(data: SurveyData) -> list:
    """The classic forms, the newer ones and a Result chart."""
    return [
        data.plot.bar("region"),
        data.plot.bar("sat", show="percent", split="region", letters=True),
        data.plot.bar("region", show="percent", intervals=True),
        data.plot.bar("sat", layout="donut"),
        data.plot.bar("score", layout="histogram"),
        data.plot.boxplot("score", by="region"),
        data.plot.likert(["t1", "t2"]),
        rc.chart(data.report.means("score", by="region")),
    ]


@pytest.fixture
def builds(monkeypatch):
    """How many times each chart drew a figure."""
    counted: dict[int, int] = {}
    original = charts_module.SurveyChart._ensure_built

    def counting(self):
        if self._fig is None:
            counted[id(self)] = counted.get(id(self), 0) + 1
        original(self)

    monkeypatch.setattr(charts_module.SurveyChart, "_ensure_built", counting)
    return counted


def _embedded(html: str) -> list[bytes]:
    return [base64.b64decode(data) for data in re.findall(r'data:image/png;base64,([^"]+)', html)]


def test_a_report_draws_each_chart_once_and_keeps_no_figure_open(tmp_path, builds):
    data = _data()
    charts = _charts(data)
    report = Report(title="Figures")
    for chart in charts:
        report.add(chart)

    report.save(tmp_path / "report.md")
    report.save(tmp_path / "report.html")

    # Nothing is left open: each figure was released once written ...
    assert plt.get_fignums() == []
    assert all(chart._fig is None and chart._ax is None for chart in charts)
    # ... having been drawn once for the Markdown and the HTML both, which
    # show the same picture.
    assert [builds.get(id(chart)) for chart in charts] == [1] * len(charts)
    text = (tmp_path / "report.md").read_text("utf-8")
    names = re.findall(r"\]\((report_fig_\d+\.png)\)", text)
    assert len(names) == len(charts)
    written = [(tmp_path / name).read_bytes() for name in names]
    assert _embedded((tmp_path / "report.html").read_text("utf-8")) == written
    assert all(picture.startswith(b"\x89PNG") for picture in written)


def test_a_chart_the_caller_drew_is_left_open_for_them(tmp_path):
    chart = _data().plot.bar("region")
    ax = chart.plot()
    ax.set_title("Mine")
    Report().add(chart).save(tmp_path / "r.md")
    assert chart._ax is ax and chart._fig.number in plt.get_fignums()
    # What they changed is what the report shows.
    assert (tmp_path / "r_fig_0.png").read_bytes() == chart.png()


def test_a_released_chart_keeps_its_picture_and_draws_again_when_asked(tmp_path, monkeypatch):
    chart = _data().plot.bar("sat", show="percent", split="region", letters=True)
    picture = chart.png()
    note = chart.weight_note
    chart.release()
    assert chart._fig is None and plt.get_fignums() == []

    def refuse(self):
        raise AssertionError("drawn again")

    with monkeypatch.context() as patch:
        patch.setattr(type(chart), "_build", refuse)
        # The picture, the file and the notes need no drawing ...
        assert chart.png() == picture
        assert chart.save(tmp_path / "again.png").read_bytes() == picture
        assert chart.weight_note == note == "weighted by 'w'"
    # ... a figure does: plot() draws it again, the same picture.
    assert chart.plot() is chart._ax and chart._fig is not None
    assert chart.png() == picture
    # Another resolution or format is drawn from the figure.
    chart.release()
    assert chart.png(dpi=72) != picture
    assert chart.save(tmp_path / "again.svg").read_text("utf-8").lstrip().startswith("<?xml")


def test_save_writes_the_bytes_savefig_writes(tmp_path):
    chart = _data().plot.bar("region", show="percent")
    chart.plot()
    chart._fig.savefig(tmp_path / "direct.png", dpi=150, bbox_inches="tight")
    assert chart.save(tmp_path / "saved.png").read_bytes() == (tmp_path / "direct.png").read_bytes()


def _two_reports_flow() -> dict:
    nodes = [
        ("sim", "source.simulated", {"n": 150, "seed": 3}),
        ("by_region", "visualize.bar", {"variable": "region"}),
        ("by_gender", "visualize.bar", {"variable": "gender"}),
        ("s1", "output.report_section", {"heading": "Region"}),
        ("s2", "output.report_section", {"heading": "Gender"}),
        (
            "full",
            "output.save_report",
            {"title": "Full report", "path": "outputs/report.md", "html": False},
        ),
        (
            "short",
            "output.save_report",
            {"title": "Summary", "path": "outputs/summary.md", "html": False},
        ),
    ]
    edges = [
        ("sim", "data", "by_region", "data"),
        ("sim", "data", "by_gender", "data"),
        ("by_region", "chart", "s1", "items"),
        ("by_gender", "chart", "s2", "items"),
        ("s1", "report", "full", "sections"),
        ("s2", "report", "short", "sections"),
    ]
    return {
        "schema_version": "1.0",
        "name": "two_reports",
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


def test_a_run_releases_its_charts_and_two_reports_in_one_folder_keep_their_figures(
    tmp_path, monkeypatch
):
    document = loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))
    survey = from_document(document).survey
    flow = _two_reports_flow()
    assert check_flow(flow, questionnaire=document) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run(
        cwd=tmp_path
    )
    assert result.ok

    region, gender = result.output("by_region"), result.output("by_gender")
    # Rendered at their nodes and let go: the run holds no figure.
    assert region._fig is None and gender._fig is None and plt.get_fignums() == []

    outputs = tmp_path / "outputs"
    full = (outputs / "report.md").read_text("utf-8")
    short = (outputs / "summary.md").read_text("utf-8")
    assert re.findall(r"\]\(([^)]+)\)", full) == ["report_fig_1.png"]
    assert re.findall(r"\]\(([^)]+)\)", short) == ["summary_fig_1.png"]
    # Each report shows its own chart.
    assert (outputs / "report_fig_1.png").read_bytes() == region.png()
    assert (outputs / "summary_fig_1.png").read_bytes() == gender.png()
    assert region.png() != gender.png()

    # A preview written after the run is the picture the node rendered: the
    # chart is not drawn again for it.
    monkeypatch.setattr(type(region), "_build", lambda self: pytest.fail("drawn again"))
    assert region.save(tmp_path / "preview.png").read_bytes() == region.png()


def test_a_report_s_markdown_names_its_figures_by_its_file(tmp_path):
    chart = _data().plot.bar("region")
    report = Report(title="R").add(chart, caption="Regions")
    report.save(tmp_path / "Q3 results.md")
    text = (tmp_path / "Q3 results.md").read_text("utf-8")
    # A link and any file system take the name as it is.
    assert "![Regions](Q3-results_fig_0.png)" in text
    assert (tmp_path / "Q3-results_fig_0.png").is_file()
    # to_markdown alone keeps the plain names (a host's preview folder).
    assert "![Regions](fig_0.png)" in report.to_markdown(tmp_path / "preview")
    assert json.dumps(sorted(p.name for p in (tmp_path / "preview").iterdir())) == ('["fig_0.png"]')
