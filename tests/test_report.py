from pathlib import Path

import pandas as pd
import pytest

from siamang.reporting import Report
from siamang.reporting.charts import SurveyChart


class _FakeChart(SurveyChart):
    """Minimal SurveyChart that writes a stand-in PNG, bypassing matplotlib."""

    def __init__(self) -> None:  # noqa: D401 - intentionally no super().__init__
        pass

    def save(self, path, dpi: int = 150) -> Path:
        p = Path(path)
        p.write_bytes(b"\x89PNG\r\n\x1a\n-fake")
        return p


def test_fluent_chain_returns_self_and_builds_markdown():
    df = pd.DataFrame({"value": [1, 2], "count": [10, 20]})
    md = (
        Report(title="Satisfaction", description="Q2 2026")
        .heading("Overview")
        .text("Measured on a 5-point scale.")
        .add(df, caption="Table 1. Frequencies")
        .note("49 cases dropped.")
        .value("Mean", 3.8)
        .divider()
        .to_markdown()
    )
    assert "# Satisfaction" in md
    assert "*Q2 2026*" in md
    assert "## Overview" in md
    assert "*Table 1. Frequencies*" in md
    # GFM table from DataFrame (columns padded for alignment)
    assert "value" in md and "count" in md and "|---" in md.replace(" ", "")
    assert "> **Note:** 49 cases dropped." in md
    assert "**Mean:** 3.8" in md


def test_add_rejects_unsupported_type():
    with pytest.raises(TypeError):
        Report().add("not a component")


def test_chart_writes_png_and_links_it(tmp_path):
    md = Report().add(_FakeChart(), caption="Fig 1").to_markdown(asset_dir=tmp_path)
    assert (tmp_path / "fig_0.png").exists()
    assert "(fig_0.png)" in md
    assert "*Fig 1*" in md


def test_save_markdown_writes_file(tmp_path):
    out = Report(title="R").text("hello").save(tmp_path / "report.md")
    assert out.exists()
    assert "hello" in out.read_text()


def test_to_html_renders_table_and_embeds_chart(tmp_path):
    df = pd.DataFrame({"a": [1], "b": [2]})
    html = Report(title="R").add(df).add(_FakeChart()).to_html()
    assert "<table>" in html
    assert "<h1>" in html  # title rendered
    assert "data:image/png;base64," in html  # chart embedded inline


def test_combine_builds_toc_and_sections():
    r1 = Report(title="Cleaning", description="prep").text("done")
    r2 = Report(title="Final tables").text("tables")
    combined = Report.combine([r1, r2], title="Full report")
    md = combined.to_markdown()
    assert "# Full report" in md
    assert "## Contents" in md
    assert "- [Cleaning](#cleaning)" in md
    assert "## Final tables" in md
