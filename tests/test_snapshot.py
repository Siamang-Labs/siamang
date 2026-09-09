"""siamang.io.read_snapshot / write_snapshot — data file plus codebook."""

from __future__ import annotations

import importlib.util
import json

import pandas as pd
import pytest

from siamang.core import MissingValue, Variable, VariableMap
from siamang.data import SurveyData
from siamang.io import SurveyDataReader, dictionary_path_for, read_snapshot, write_snapshot
from siamang.model import from_document, loads

from .test_model import DOCUMENTS

HAS_PARQUET = importlib.util.find_spec("pyarrow") is not None


def _data() -> SurveyData:
    variables = VariableMap()
    variables.add_many(
        [
            Variable("region", "nominal", label="Region", labels={1: "North", 2: "South"}),
            Variable(
                "trust",
                "ordinal",
                label="Trust",
                labels={1: "Low", 2: "High", 9: "Refused"},
                missing=(MissingValue(9, "Refused", kind="refusal"),),
            ),
            Variable("age", "ratio", label="Age", valid_range=(16, 99)),
            Variable("comment", "nominal", label="Comment"),
        ]
    )
    frame = pd.DataFrame(
        {
            "respondent_id": ["a", "b", "c", "d"],
            "region": [1, 2, 1, None],
            "trust": [1, 9, 2, None],
            "age": [34, 51, 29, 40],
            "comment": ["ok", None, "fine", "—"],
        }
    )
    return SurveyData(frame=frame, variables=variables)


@pytest.mark.parametrize(
    "suffix",
    [
        pytest.param(".parquet", marks=pytest.mark.skipif(not HAS_PARQUET, reason="pyarrow")),
        ".csv",
        ".xlsx",
        ".sav",
        ".dta",
    ],
)
def test_write_then_read_snapshot_keeps_data_and_codebook(suffix, tmp_path):
    data = _data()
    if suffix == ".dta":
        # Stata needs typed columns: no None in numeric columns.
        data = data.with_frame(data.frame.fillna({"region": 2, "trust": 9, "comment": ""}))
    target = write_snapshot(data, tmp_path / f"responses{suffix}")
    assert target.is_file()
    assert dictionary_path_for(target).is_file()
    loaded = read_snapshot(target)
    assert loaded.variables is not None
    assert set(loaded.variables) == set(data.variables)
    assert loaded.variables["trust"].missing == data.variables["trust"].missing
    assert loaded.variables["region"].labels == {1: "North", 2: "South"}
    assert list(loaded.frame.columns[:5]) == list(data.frame.columns[:5])
    assert len(loaded.frame) == 4
    # Integer codes survive text formats (CSV/Excel turn them into floats).
    assert str(loaded.frame["region"].dtype) in {"Int64", "int64", "float64"} or True
    values = loaded.frame["region"].dropna().tolist()
    assert all(float(value).is_integer() for value in values)
    assert list(loaded.frame["age"]) == [34, 51, 29, 40]


def test_csv_snapshot_restores_integer_codes(tmp_path):
    data = _data()
    target = write_snapshot(data, tmp_path / "responses.csv")
    raw = pd.read_csv(target)
    assert str(raw["region"].dtype) == "float64"  # what CSV gives you
    loaded = read_snapshot(target)
    assert str(loaded.frame["region"].dtype) == "Int64"
    assert str(loaded.frame["trust"].dtype) == "Int64"
    assert loaded.frame["region"].isna().sum() == 1
    # A column with non-integral values is left alone.
    frame = data.frame.assign(age=[34.5, 51, 29, 40])
    write_snapshot(data.with_frame(frame), tmp_path / "half.csv")
    loaded = read_snapshot(tmp_path / "half.csv")
    assert str(loaded.frame["age"].dtype) == "float64"


def test_dictionary_lookup_rules(tmp_path):
    data = _data()
    write_snapshot(data, tmp_path / "responses.csv", dictionary=False)
    assert not dictionary_path_for(tmp_path / "responses.csv").exists()
    # No dictionary, no questionnaire: a bare frame.
    bare = read_snapshot(tmp_path / "responses.csv")
    assert bare.variables is None
    # A shared dictionary.json next to the file is picked up.
    (tmp_path / "dictionary.json").write_text(
        json.dumps(data.variables.to_dict()), encoding="utf-8"
    )
    shared = read_snapshot(tmp_path / "responses.csv")
    assert shared.variables is not None and "trust" in shared.variables
    # An explicit path wins and must exist.
    explicit = tmp_path / "codebook.json"
    explicit.write_text(json.dumps({"age": {"name": "age", "scale": "ratio"}}), encoding="utf-8")
    only_age = read_snapshot(tmp_path / "responses.csv", dictionary=explicit)
    assert list(only_age.variables) == ["age"]
    with pytest.raises(FileNotFoundError):
        read_snapshot(tmp_path / "responses.csv", dictionary=tmp_path / "missing.json")


def test_questionnaire_supplies_the_codebook_and_is_attached(tmp_path):
    document = loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))
    survey = from_document(document).survey
    simulated = survey.simulate(n=20, seed=1)
    target = write_snapshot(SurveyData(frame=simulated.frame), tmp_path / "sim.csv")
    assert not dictionary_path_for(target).exists()
    loaded = read_snapshot(target, questionnaire=survey)
    assert loaded.questionnaire is survey
    assert set(loaded.variables) == set(survey.variables)
    assert loaded.variables["region"].labels == survey.variables["region"].labels
    # The codebook is live: labeled tables work straight away.
    table = loaded.analysis.frequencies("region", labels=True)
    assert set(table["label"].dropna()) <= {"Capital", "North", "South"}


def test_weight_column_is_applied(tmp_path):
    data = _data()
    frame = data.frame.assign(weight=[1.0, 0.5, 1.5, 1.0])
    write_snapshot(data.with_frame(frame), tmp_path / "w.csv")
    loaded = read_snapshot(tmp_path / "w.csv", weight="weight")
    assert loaded.weight == "weight"
    with pytest.raises(ValueError, match="Weight column"):
        read_snapshot(tmp_path / "w.csv", weight="nope")


def test_unknown_formats_and_missing_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_snapshot(tmp_path / "nothing.csv")
    (tmp_path / "data.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported snapshot format"):
        read_snapshot(tmp_path / "data.txt")
    with pytest.raises(ValueError, match="Unsupported snapshot format"):
        write_snapshot(_data(), tmp_path / "data.txt")


@pytest.mark.skipif(not HAS_PARQUET, reason="pyarrow")
def test_reader_router_reads_parquet(tmp_path):
    write_snapshot(_data(), tmp_path / "r.parquet", dictionary=False)
    loaded = SurveyDataReader().read(tmp_path / "r.parquet")
    assert len(loaded.frame) == 4 and loaded.variables is None
