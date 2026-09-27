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


def test_the_codebook_describes_the_arm_a_script_assigns(tmp_path):
    # No question collects an arm, so the questions alone left it unlabeled:
    # a flow read "1" and "2" where respondents saw the two messages.
    import siamang as sg

    seen = Variable("seen", "nominal", label="Seen the ad", labels={1: "Yes", 2: "No"})

    def survey_with(variables: VariableMap | None) -> sg.Questionnaire:
        return sg.Questionnaire(
            title="A",
            pages=[
                sg.Page(
                    name="treated",
                    show_if=sg.compare("condition", "=", 2),
                    items=[sg.SingleChoice("Seen the ad?", var=seen, id="q_seen")],
                )
            ],
            scripts=[sg.Script.assign_condition("condition", [(1, "Control"), (2, "Treatment")])],
            variables=variables,
        )

    survey = survey_with(None)
    simulated = survey.simulate(n=20, seed=1)
    target = write_snapshot(SurveyData(frame=simulated.frame), tmp_path / "sim.csv")
    loaded = read_snapshot(target, questionnaire=survey)
    arm = loaded.variables["condition"]
    assert (arm.scale, arm.labels) == ("nominal", {1: "Control", 2: "Treatment"})
    # Named as words, not as the column it is: a table grouped by it says so.
    assert arm.label == "Condition"
    from siamang.local_simulator import _readable

    assert _readable("message_arm") == "Message arm" and _readable("arm") == "Arm"
    # Described as Simulated data describe it, and the codes stay integers.
    assert arm == simulated.variables["condition"]
    assert str(loaded.frame["condition"].dtype) in {"int64", "Int64"}
    table = loaded.analysis.frequencies("condition", labels=True)
    assert set(table["label"].dropna()) == {"Control", "Treatment"}

    # A declared codebook gets the arm too, and is not changed in place.
    declared = VariableMap()
    declared.add(seen)
    loaded = read_snapshot(target, questionnaire=survey_with(declared))
    assert loaded.variables["condition"].labels == {1: "Control", 2: "Treatment"}
    assert list(declared) == ["seen"]
    # One the codebook already declares is its own.
    declared.add(Variable("condition", "nominal", label="Arm", labels={1: "A", 2: "B"}))
    loaded = read_snapshot(target, questionnaire=survey_with(declared))
    assert loaded.variables["condition"].labels == {1: "A", 2: "B"}


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

    # A multiple-choice list comes back a list, as read_snapshot gives it: an
    # array was not multi.is_multi and Explode failed on its truth value.
    import pandas as pd

    from siamang.data import SurveyData, multi

    lists = SurveyData(frame=pd.DataFrame({"aware": [[1, 3], [2], None], "x": [1, 2, 3]}))
    write_snapshot(lists, tmp_path / "l.parquet", dictionary=False)
    back = SurveyDataReader().read(tmp_path / "l.parquet")
    assert back.frame["aware"].tolist() == [[1, 3], [2], None]
    assert multi.is_multi(back.frame["aware"])
    exploded = back.explode_multi("aware").frame
    assert exploded[["aware_1", "aware_2", "aware_3"]].values.tolist()[:2] == [[1, 0, 1], [0, 1, 0]]


def test_sav_and_dta_store_list_answers_next_to_missing_ones(tmp_path):
    """A multiple-choice list and a ranking mixed with respondents who never
    saw the question (routing) still write: lists become ';'-joined codes."""
    import pandas as pd

    from siamang.data import SurveyData
    from siamang.io import read_snapshot, write_snapshot

    frame = pd.DataFrame(
        {"age": [20, 31, 44], "manage": [[1, 3], None, [2]], "rank": [[2, 1], [1], None]}
    )
    for suffix in (".sav", ".dta"):
        path = write_snapshot(SurveyData(frame=frame), tmp_path / f"s{suffix}", dictionary=False)
        back = read_snapshot(path).frame
        assert back["manage"].tolist()[0] == "1;3" and back["rank"].tolist()[1] == "1"
        # A missing string reads back as NaN or "" depending on the format.
        gap = back["manage"].tolist()[1]
        assert gap == "" or pd.isna(gap)


def test_every_text_format_writes_the_same_multiple_answer(tmp_path):
    """Which download button was pressed must not change the answers.

    CSV used to write the Python repr of a list (`"[1, 3]"`), Excel the same,
    SPSS and Stata `1;3`. Same project, four files, three of them unreadable by
    anything that did not already know they came from pandas.
    """
    import pandas as pd

    import siamang as sg
    from siamang.data import SurveyData
    from siamang.io import read_snapshot, write_snapshot

    reasons = sg.Variable("reasons", scale="nominal", labels={1: "Price", 2: "Habit"})
    age = sg.Variable("age", scale="ratio", label="Age")
    survey = sg.Questionnaire(
        title="M",
        pages=[
            sg.Page(
                name="p",
                items=[
                    sg.MultiChoice("Why?", var=reasons, mode="array"),
                    sg.NumericInput("Age?", var=age),
                ],
            )
        ],
    )
    frame = pd.DataFrame({"reasons": [[1, 2], [2], None], "age": [20, 30, 40]})
    data = SurveyData(frame=frame, questionnaire=survey)

    csv_path = write_snapshot(data, tmp_path / "x.csv", dictionary=False)
    assert csv_path.read_text("utf-8").splitlines()[1] == "1;2,20"

    for suffix in (".csv", ".xlsx", ".sav", ".dta", ".parquet"):
        path = write_snapshot(data, tmp_path / f"x{suffix}", dictionary=False)
        back = read_snapshot(path, questionnaire=survey).frame["reasons"]
        assert list(back[0]) == [1, 2], suffix
        assert list(back[1]) == [2], suffix
        assert not isinstance(back[2], str), suffix  # never answered stays missing


def test_lists_are_only_restored_where_the_questionnaire_says_so(tmp_path):
    """A free-text answer with a semicolon in it is text, not two codes."""
    import pandas as pd

    import siamang as sg
    from siamang.data import SurveyData
    from siamang.io import read_snapshot, write_snapshot

    comment = sg.Variable("comment", scale="nominal", label="Comment")
    survey = sg.Questionnaire(
        title="T", pages=[sg.Page(name="p", items=[sg.OpenText("Say more", var=comment)])]
    )
    frame = pd.DataFrame({"comment": ["fast; cheap", "ok"]})
    path = write_snapshot(SurveyData(frame=frame), tmp_path / "t.csv", dictionary=False)
    back = read_snapshot(path, questionnaire=survey).frame
    assert back["comment"].tolist() == ["fast; cheap", "ok"]


@pytest.mark.skipif(not HAS_PARQUET, reason="pyarrow")
def test_a_parquet_snapshot_gives_back_lists_that_explode(tmp_path):
    """pandas reads a Parquet list back as a numpy array, which no multiple-choice
    helper takes for a list: a generated script run with --data …parquet failed
    at Explode ("the truth value of an array … is ambiguous"). The lists come
    back as lists, with or without a questionnaire."""
    from siamang.data import multi

    frame = pd.DataFrame({"aware": [[1, 3], [2], None, []], "x": [1, 2, 3, 4]})
    path = write_snapshot(SurveyData(frame=frame), tmp_path / "r.parquet", dictionary=False)
    back = read_snapshot(path)
    cells = back.frame["aware"].tolist()
    assert cells[0] == [1, 3] and isinstance(cells[0], list) and cells[1] == [2]
    assert cells[2] is None and cells[3] == []
    assert multi.is_multi(back.frame["aware"])
    exploded = back.explode_multi("aware").frame
    assert exploded["aware_1"].tolist()[:2] == [1, 0] and exploded["aware_3"].tolist()[0] == 1


def test_integer_codes_are_restored_in_the_frame_read_not_in_a_copy(tmp_path, monkeypatch):
    """Copying the frame to restore its codes held two frames at once (56 MB
    more for 20,000 x 177): the frame read is the snapshot's own, restored a
    column at a time."""
    from siamang.io import snapshot

    data = _data()
    target = write_snapshot(data, tmp_path / "responses.csv")
    read = []
    original = pd.read_csv

    def reading(*args, **kwargs):
        read.append(original(*args, **kwargs))
        return read[-1]

    monkeypatch.setattr(pd, "read_csv", reading)
    loaded = read_snapshot(target)
    assert loaded.frame is read[0]
    assert str(loaded.frame["region"].dtype) == "Int64"
    assert loaded.frame["trust"].tolist()[:3] == [1, 9, 2]
    frame = pd.DataFrame({"region": [1.0, 2.0, None]})
    assert snapshot._restore_integer_codes(frame, data.variables) is frame


@pytest.mark.skipif(not HAS_PARQUET, reason="pyarrow")
def test_reading_parquet_hands_arrow_s_pool_back(tmp_path, monkeypatch):
    """Arrow keeps the buffers pandas was built from in its pool (30 MB for
    20,000 x 177) unless asked to give them back."""
    import pyarrow

    target = write_snapshot(_data(), tmp_path / "responses.parquet")
    pool = pyarrow.default_memory_pool()
    released = []

    class Pool:
        def release_unused(self):
            released.append(True)
            pool.release_unused()

    monkeypatch.setattr(pyarrow, "default_memory_pool", lambda: Pool())
    assert len(read_snapshot(target).frame) == 4
    assert released == [True]
