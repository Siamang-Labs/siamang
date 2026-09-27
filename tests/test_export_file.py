"""siamang.io.export_file — every file the Export file step writes, by extension.

The R bundle is also run through R itself when ``Rscript`` and ``jsonlite`` are
installed: a script that is only ever read by Python is a script nobody has
checked.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pandas as pd
import pytest

from siamang.core import Variable, VariableMap
from siamang.data import SurveyData
from siamang.io import DictionaryReader, export_file, read_snapshot


def _data() -> SurveyData:
    variables = VariableMap()
    variables.add(
        Variable(
            "sat",
            "ordinal",
            label="Satisfaction",
            labels={1: "Low", 2: "Mid", 3: "High", 99: "Don't know"},
            missing_values=(99,),
        )
    )
    variables.add(
        Variable("brands", "nominal", label="Brands", labels={1: "Acme", 2: "Globex", 3: "Ini"})
    )
    variables.add(Variable("age", "ratio", label="Age"))
    variables.add(Variable("city", "nominal", label='Город "в кавычках"', labels={"msk": "Москва"}))
    variables.add(Variable("why", "nominal", label="Why"))
    frame = pd.DataFrame(
        {
            "sat": pd.array([1, 2, 99, None, 7], dtype="Int64"),
            "brands": [[1, 3], [2], [], None, [3]],
            "age": [30, 41.5, None, 22, 50],
            "city": ["msk", "msk", None, "msk", "spb"],
            "why": ["NA", 'a, "b"', None, "x", "y"],
        }
    )
    return SurveyData(frame=frame, variables=variables)


def test_an_r_bundle_is_three_files_beside_each_other(tmp_path):
    script = export_file(_data(), tmp_path / "outputs" / "survey.R")
    assert script == tmp_path / "outputs" / "survey.R"
    assert sorted(path.name for path in script.parent.iterdir()) == [
        "survey.R",
        "survey.csv",
        "survey.dictionary.json",
    ]
    text = script.read_text("utf-8")
    assert 'multiple <- c("brands")' in text
    assert 'na.strings = ""' in text and 'fileEncoding = "UTF-8"' in text
    # The dictionary has the snapshot's name, so the CSV reads back with it.
    again = read_snapshot(script.parent / "survey.csv")
    assert again.variables["sat"].labels[1] == "Low"


def test_a_json_path_writes_the_codebook_alone(tmp_path):
    path = export_file(_data(), tmp_path / "outputs" / "codebook.json")
    assert [p.name for p in path.parent.iterdir()] == ["codebook.json"]
    assert DictionaryReader().read(path)["sat"].missing_values == (99,)
    with pytest.raises(ValueError, match="no codebook"):
        export_file(SurveyData(frame=pd.DataFrame({"x": [1]})), tmp_path / "x.json")


def test_the_snapshot_formats_are_written_as_before(tmp_path):
    path = export_file(_data(), tmp_path / "clean.csv")
    assert path.is_file() and (tmp_path / "clean.dictionary.json").is_file()


def test_an_excel_file_takes_times_with_a_time_zone_in_utc(tmp_path):
    """Excel holds no time zone, and pandas refused to write one: the response
    times Studio's data carries (timezone-aware) stopped a flow's Export file
    to .xlsx. They are written in UTC, a column of them or a single one; a
    formula-like text stays text beside them."""
    import datetime as dt

    import openpyxl

    frame = pd.DataFrame(
        {
            "created_at": pd.to_datetime(["2026-01-01T10:00:00+02:00", None], utc=True),
            "seen": [dt.datetime(2026, 3, 1, 12, tzinfo=dt.timezone(dt.timedelta(hours=-5))), None],
            "why": ["=1+1", "fine"],
        }
    )
    path = export_file(SurveyData(frame=frame), tmp_path / "coded.xlsx")
    back = pd.read_excel(path)
    assert back["created_at"][0] == pd.Timestamp("2026-01-01 08:00:00")
    assert pd.isna(back["created_at"][1])
    assert back["seen"][0] == pd.Timestamp("2026-03-01 17:00:00")
    sheet = openpyxl.load_workbook(path).active
    assert sheet["C2"].value == "=1+1" and sheet["C2"].data_type == "s"
    # The frame given is left as it was.
    assert str(frame["created_at"].dtype) == "datetime64[ns, UTC]"


def test_an_unknown_extension_names_the_ones_that_work(tmp_path):
    with pytest.raises(ValueError, match=r"'\.txt'.*\.parquet.*\.R, \.json"):
        export_file(_data(), tmp_path / "data.txt")
    with pytest.raises(ValueError, match="no extension"):
        export_file(_data(), tmp_path / "data")


def _r_available() -> bool:
    if shutil.which("Rscript") is None:
        return False
    probe = subprocess.run(
        ["Rscript", "-e", "quit(status = !requireNamespace('jsonlite', quietly = TRUE))"],
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


_R_ENV = {"LANG": "C.UTF-8", "PATH": "/usr/local/bin:/usr/bin:/bin"}


@pytest.mark.skipif(not _r_available(), reason="Rscript with jsonlite")
def test_r_reads_the_bundle_with_factors_and_missing_codes(tmp_path):
    """Sourced from another directory: missing codes are NA, labelled codes
    factors, an unlabelled code keeps a level of its own instead of vanishing,
    several answers stay text, and a text answer that reads "NA" is an answer."""

    script = export_file(_data(), tmp_path / "bundle" / "survey.R")
    summary = tmp_path / "summary.json"
    report = (
        "d <- survey_data; "
        "jsonlite::write_json(list("
        "sat = as.character(d$sat), sat_levels = levels(d$sat), "
        "brands = d$brands, why = d$why, city = as.character(d$city), "
        "age = d$age, label = attr(d$city, 'label')), "
        f"'{summary.as_posix()}', auto_unbox = TRUE, na = 'null')"
    )
    completed = subprocess.run(
        ["Rscript", "-e", f"source('{script.as_posix()}'); {report}"],
        cwd=tmp_path,  # not the bundle's directory
        capture_output=True,
        text=True,
        check=False,
        env=_R_ENV,
    )
    assert completed.returncode == 0, completed.stderr
    out = json.loads(summary.read_text("utf-8"))
    assert out["sat"] == ["Low", "Mid", None, None, "7"]
    assert out["sat_levels"] == ["Low", "Mid", "High", "7"]  # 99 is no level
    assert out["brands"] == ["1;3", "2", None, None, "3"]
    assert out["why"] == ["NA", 'a, "b"', None, "x", "y"]
    assert out["city"] == ["Москва", "Москва", None, "Москва", "spb"]
    assert out["age"][:2] == [30, 41.5]
    assert out["label"] == 'Город "в кавычках"'


@pytest.mark.skipif(not _r_available(), reason="Rscript with jsonlite")
def test_rscript_runs_the_bundle_from_anywhere(tmp_path):
    script = export_file(_data(), tmp_path / "bundle" / "survey.R")
    completed = subprocess.run(
        ["Rscript", str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=_R_ENV,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Москва" in completed.stdout and "1;3" in completed.stdout
