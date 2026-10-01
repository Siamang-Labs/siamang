"""Reading a data file someone else made, and the codebook it brings.

siamang.io.read_snapshot / inspect_snapshot on files as researchers upload
them (a semicolon CSV in Windows-1251, Excel's "Unicode text", a title above
the names, a Qualtrics export), the questionnaire applied only to a file that
is its data, the Data file node's reading options, and check_flow knowing a
file's columns (``files=``). Every file is written here, with made-up values.
"""

from __future__ import annotations

import codecs
import importlib.util
import json

import pandas as pd
import pytest

from siamang.core import Variable, VariableMap
from siamang.data import SurveyData
from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow
from siamang.io import (
    READ_FORMATS,
    SnapshotReadError,
    inspect_snapshot,
    read_snapshot,
    snapshot_options,
    write_snapshot,
)
from siamang.io.file_codebook import infer_scale, personal_data, suspected_missing
from siamang.io.tabular import detect_encoding, sniff_delimiter
from siamang.model import from_document, loads

from .test_model import DOCUMENTS

HAS_XLWT = importlib.util.find_spec("xlwt") is not None
HAS_XLRD = importlib.util.find_spec("xlrd") is not None


@pytest.fixture(scope="module")
def project():
    """A project's questionnaire (document and survey) that shares a few
    variable names — age, region, gender — with files that are not its data."""

    document = loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))
    return document, from_document(document).survey


# ─── text files: encoding, delimiter, decimal mark ──────────────────────────

SEMICOLON = (
    "id;gender;age;score;comment\n"
    "1;1;34;4,5;Хорошо\n"
    '2;2;27;3;"Нормально; но долго"\n'
    "3;1;45;5,0;Отлично, спасибо\n"
    "4;2;51;2,5;\n"
)


def test_a_semicolon_csv_with_a_bom_and_decimal_commas_reads_into_its_columns(tmp_path):
    path = tmp_path / "survey.csv"
    path.write_bytes(codecs.BOM_UTF8 + SEMICOLON.encode("utf-8"))
    data = read_snapshot(path)
    frame = data.frame
    # One column "id;gender;age;score;comment" before, and "5;Хорошо" shown
    # where pandas moved the leading fields into a hidden index.
    assert list(frame.columns) == ["id", "gender", "age", "score", "comment"]
    assert frame["score"].tolist() == [4.5, 3.0, 5.0, 2.5]
    assert frame["comment"].tolist()[:3] == ["Хорошо", "Нормально; но долго", "Отлично, спасибо"]
    assert pd.isna(frame["comment"].iloc[3])
    assert list(frame.index) == [0, 1, 2, 3]
    read = inspect_snapshot(path)["read"]
    assert (read["encoding"], read["delimiter"], read["decimal"]) == ("utf-8-sig", ";", ",")


def test_a_windows_1251_csv_is_read_and_a_wrong_encoding_is_named(tmp_path):
    path = tmp_path / "anketa.csv"
    path.write_bytes(
        (
            "Номер;Пол респондента;Город;Оценка\n"
            "1;Мужской;Москва;4,5\n"
            "2;Женский;Санкт-Петербург;3,5\n"
            "3;Женский;Нижний Новгород;5\n"
        ).encode("cp1251")
    )
    assert detect_encoding(path) == "cp1251"
    frame = read_snapshot(path).frame
    assert list(frame.columns) == ["Номер", "Пол респондента", "Город", "Оценка"]
    assert frame["Город"].tolist() == ["Москва", "Санкт-Петербург", "Нижний Новгород"]
    assert frame["Оценка"].tolist() == [4.5, 3.5, 5.0]
    # Given the wrong one, the error says what the file is and what to set.
    with pytest.raises(SnapshotReadError, match=r"not UTF-8.*Windows-1251.*cp1251"):
        read_snapshot(path, encoding="utf-8")
    # Given the right one, it is used.
    assert read_snapshot(path, encoding="cp1251").frame.shape == (3, 4)


def test_unicode_text_and_other_delimiters(tmp_path):
    table = "id\tanswer\tscore\n1\tда\t4,5\n2\tнет\t3,25\n"
    unicode_text = tmp_path / "export.txt"
    unicode_text.write_bytes(codecs.BOM_UTF16_LE + table.encode("utf-16-le"))
    frame = read_snapshot(unicode_text).frame
    assert list(frame.columns) == ["id", "answer", "score"]
    assert frame["score"].tolist() == [4.5, 3.25]
    assert inspect_snapshot(unicode_text)["read"]["encoding"] == "utf-16"

    pipe = tmp_path / "pipe.csv"
    pipe.write_text("id|city|score\n1|Kazan, center|4.5\n2|Omsk|3\n", encoding="utf-8")
    frame = read_snapshot(pipe).frame
    assert frame["city"].tolist() == ["Kazan, center", "Omsk"]

    tsv = tmp_path / "tabs.tsv"
    tsv.write_text("id\tq1\n1\t2\n2\t3\n", encoding="utf-8")
    assert read_snapshot(tsv).frame["q1"].tolist() == [2, 3]
    assert {".tsv", ".txt", ".xlsm"} <= set(READ_FORMATS)


def test_the_sniffer_respects_quotes_and_the_names_row():
    # Commas inside the answers do not make "," the delimiter of a ; file.
    text = 'id;city;note\n1;"Moscow, center";ok\n2;"Omsk, east";"a, b"\n3;Perm;x\n'
    assert sniff_delimiter(text) == ";"
    assert sniff_delimiter("a,b,c\n1,2,3\n4,5,6\n") == ","
    assert sniff_delimiter("one column\nx\ny\n") == ","


def test_given_options_win_over_what_is_detected(tmp_path):
    path = tmp_path / "survey.csv"
    path.write_text(SEMICOLON, encoding="utf-8")
    # Delimiter "," on a ; file: the caller's choice, and a row with a comma
    # in an answer then has a field too many — said so.
    with pytest.raises(SnapshotReadError, match=r"Line 4 has 3 fields.*delimiter ','"):
        read_snapshot(path, delimiter=",")
    assert read_snapshot(path, delimiter=";").frame.shape == (4, 5)
    # pandas' own keywords still work, and win.
    assert list(read_snapshot(path, sep=";").frame.columns)[:2] == ["id", "gender"]
    kept = read_snapshot(path, decimal=".").frame
    assert kept["score"].tolist()[0] == "4,5"
    by_hand = read_snapshot(path, sep=";", header=None, skiprows=1).frame
    assert by_hand.shape == (4, 5) and list(by_hand.columns) == [0, 1, 2, 3, 4]
    with pytest.raises(SnapshotReadError, match="Delimiter"):
        read_snapshot(path, delimiter="::")
    with pytest.raises(SnapshotReadError, match="Unknown encoding"):
        read_snapshot(path, encoding="no-such-codec")


def test_numbers_written_the_local_way_become_numbers(tmp_path):
    path = tmp_path / "money.csv"
    path.write_text(
        "id;income;share;code;country;q5\n"
        "1;1 234,5;12,5%;00123;NA;1\n"
        "2;980;7%;00124;DE; \n"
        "3;12 000;0,5%;00125;None;-\n",
        encoding="utf-8",
    )
    frame = read_snapshot(path).frame
    assert frame["income"].tolist() == [1234.5, 980.0, 12000.0]
    assert frame["share"].tolist() == [12.5, 7.0, 0.5]
    # A code with a leading zero stays a code; "NA" (Namibia) and "None"
    # written in a text column stay what they are.
    assert frame["code"].tolist() == ["00123", "00124", "00125"]
    assert frame["country"].tolist() == ["NA", "DE", "None"]
    # A blank and a "-" in a column of numbers are blanks, not text.
    assert frame["q5"].iloc[0] == 1 and frame["q5"].isna().sum() == 2


def test_a_title_above_the_names_is_not_read_as_them(tmp_path):
    path = tmp_path / "titled.csv"
    path.write_text(
        "Customer survey, March 2026,,,,\n"
        ",,,,,\n"
        "id,gender,age,q1,q2,q3\n"
        "1,1,34,2,3,4\n"
        "2,2,27,1,5,3\n",
        encoding="utf-8",
    )
    frame = read_snapshot(path).frame
    assert list(frame.columns) == ["id", "gender", "age", "q1", "q2", "q3"]
    assert frame["age"].tolist() == [34, 27]
    assert inspect_snapshot(path)["read"]["skip_rows"] == 2
    # Said by hand: the rows above the names.
    assert list(read_snapshot(path, skip_rows=2).frame.columns)[:2] == ["id", "gender"]


def test_a_title_with_a_comma_above_a_narrow_table(tmp_path):
    path = tmp_path / "narrow.csv"
    path.write_text(
        "Опрос клиентов, март 2026,,\nid,gender,age\n1,1,34\n2,2,27\n", encoding="utf-8"
    )
    assert list(read_snapshot(path).frame.columns) == ["id", "gender", "age"]


def test_a_broken_row_and_an_empty_file_are_said_in_words(tmp_path):
    broken = tmp_path / "broken.csv"
    broken.write_text("id;q1;q2\n1;2;3\n2;3;4\n3;4;5;6;7\n", encoding="utf-8")
    with pytest.raises(SnapshotReadError, match=r"Line 4 has 5 fields where the table has 3"):
        read_snapshot(broken)
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(SnapshotReadError, match="empty"):
        read_snapshot(empty)


# ─── workbooks ───────────────────────────────────────────────────────────────


def test_the_first_sheet_that_holds_a_table_is_read(tmp_path):
    path = tmp_path / "book.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"Описание": ["Опрос клиентов, 2026", "Коды: 1 = да, 2 = нет"]}).to_excel(
            writer, sheet_name="README", index=False
        )
        pd.DataFrame({"id": [1, 2, 3], "q1": [1, 2, 1]}).to_excel(
            writer, sheet_name="Данные", index=False
        )
        pd.DataFrame({"x": [9], "y": [8]}).to_excel(writer, sheet_name="Other", index=False)
    frame = read_snapshot(path).frame
    assert list(frame.columns) == ["id", "q1"] and len(frame) == 3
    read = inspect_snapshot(path)["read"]
    assert read["sheet"] == "Данные" and read["sheets"] == ["README", "Данные", "Other"]
    assert list(read_snapshot(path, sheet="3").frame.columns) == ["x", "y"]
    assert list(read_snapshot(path, sheet="other").frame.columns) == ["x", "y"]
    assert list(read_snapshot(path, sheet_name=0).frame.columns) == ["Описание"]
    with pytest.raises(SnapshotReadError, match="README, Данные, Other"):
        read_snapshot(path, sheet="Answers")


def test_a_workbook_s_text_cells_get_their_types_and_a_title_is_skipped(tmp_path):
    path = tmp_path / "titled.xlsx"
    rows = [
        ["Client survey, wave 2", None, None, None, None],
        [None, None, None, None, None],
        ["id", "q1", "when", "income", "done"],
        ["1", "1", "01.02.2026", "1 200,50", "True"],
        ["2", "2", "02.02.2026", "1 201,50", "False"],
        ["3", "3", "03.02.2026", "980", "True"],
    ]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)
    frame = read_snapshot(path).frame
    assert list(frame.columns) == ["id", "q1", "when", "income", "done"]
    assert frame["q1"].tolist() == [1, 2, 3]
    assert str(frame["when"].dtype).startswith("datetime64")
    assert frame["when"].iloc[0] == pd.Timestamp("2026-02-01")
    assert frame["income"].tolist() == [1200.5, 1201.5, 980.0]
    assert frame["done"].tolist() == [True, False, True]


def test_a_total_row_under_the_table_is_pointed_out(tmp_path):
    path = tmp_path / "totals.xlsx"
    pd.DataFrame({"id": ["1", "2", "Итого"], "income": [100, 200, 300]}).to_excel(path, index=False)
    notes = inspect_snapshot(path)["notes"]
    assert any("'Итого', like a total" in note for note in notes)


def test_an_xls_is_read_by_what_it_is(tmp_path):
    # An .xlsx saved with an .xls name opens with openpyxl.
    fake = tmp_path / "renamed.xls"
    pd.DataFrame({"id": [1, 2]}).to_excel(tmp_path / "real.xlsx", index=False)
    fake.write_bytes((tmp_path / "real.xlsx").read_bytes())
    assert read_snapshot(fake).frame["id"].tolist() == [1, 2]
    # A web page some systems export as "Excel" is named for what it is.
    page = tmp_path / "report.xls"
    page.write_text("<html><body><table><tr><td>1</td></tr></table></body></html>")
    with pytest.raises(SnapshotReadError, match="web page"):
        read_snapshot(page)


@pytest.mark.skipif(not (HAS_XLWT and HAS_XLRD), reason="xlwt and xlrd")
def test_an_excel_97_workbook_is_read(tmp_path):
    import xlwt

    book = xlwt.Workbook()
    sheet = book.add_sheet("Data")
    for column, name in enumerate(["id", "q1"]):
        sheet.write(0, column, name)
    for row, values in enumerate([[1, 2], [2, 1]], start=1):
        for column, value in enumerate(values):
            sheet.write(row, column, value)
    path = tmp_path / "old.xls"
    book.save(str(path))
    assert read_snapshot(path).frame["q1"].tolist() == [2, 1]


# ─── Qualtrics ───────────────────────────────────────────────────────────────

QUALTRICS_NAMES = [
    "StartDate",
    "EndDate",
    "Status",
    "IPAddress",
    "Progress",
    "Duration (in seconds)",
    "Finished",
    "RecordedDate",
    "ResponseId",
    "RecipientEmail",
    "LocationLatitude",
    "LocationLongitude",
    "UserLanguage",
    "Q1",
    "Q2_1",
    "Q2_2",
    "age",
    "comment",
]
QUALTRICS_LABELS = [
    "Start Date",
    "End Date",
    "Response Type",
    "IP Address",
    "Progress",
    "Duration (in seconds)",
    "Finished",
    "Recorded Date",
    "Response ID",
    "Recipient Email",
    "Location Latitude",
    "Location Longitude",
    "User Language",
    "How satisfied are you?",
    "How much do you agree? - Price",
    "How much do you agree? - Service",
    "What is your age?",
    "Anything else?",
]
QUALTRICS_ANSWERS = [
    [
        "2026-03-01 10:00:00",
        "2026-03-01 10:05:00",
        "IP Address",
        "192.0.2.10",
        "100",
        "300",
        "True",
        "2026-03-01 10:05:01",
        "R_fake01",
        "",
        "55.75",
        "37.62",
        "EN",
        "Very satisfied",
        "Agree",
        "Disagree",
        "25 - 34",
        "Fine, thanks",
    ],
    [
        "2026-03-02 11:00:00",
        "2026-03-02 11:09:00",
        "IP Address",
        "192.0.2.11",
        "100",
        "540",
        "True",
        "2026-03-02 11:09:02",
        "R_fake02",
        "",
        "59.93",
        "30.31",
        "EN",
        "Neutral",
        "Neither agree nor disagree",
        "Agree",
        "18 - 24",
        "",
    ],
    [
        "2026-03-03 12:00:00",
        "2026-03-03 12:01:00",
        "IP Address",
        "192.0.2.12",
        "40",
        "60",
        "False",
        "2026-03-03 12:01:30",
        "R_fake03",
        "",
        "",
        "",
        "EN",
        "Dissatisfied",
        "",
        "",
        "35 or older",
        "",
    ],
]


def _qualtrics_csv(path):
    import csv

    import_ids = [json.dumps({"ImportId": f"QID{index}"}) for index in range(len(QUALTRICS_NAMES))]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        for row in (QUALTRICS_NAMES, QUALTRICS_LABELS, import_ids, *QUALTRICS_ANSWERS):
            writer.writerow(row)
    return path


def _qualtrics_xlsx(path):
    rows = [QUALTRICS_NAMES, QUALTRICS_LABELS, *QUALTRICS_ANSWERS]
    pd.DataFrame(rows).to_excel(path, header=False, index=False, sheet_name="Sheet0")
    return path


PILOT = {
    "schema_version": "1.0",
    "title": "Pilot",
    "pages": [
        {
            "name": "p1",
            "items": [
                {
                    "type": "SingleChoice",
                    "id": "q_1",
                    "text": "How satisfied are you?",
                    "var": "q1",
                },
                {
                    "type": "Matrix",
                    "id": "q_2",
                    "text": "How much do you agree?",
                    "var": ["q2_1", "q2_2"],
                },
                {"type": "SingleChoice", "id": "q_age", "text": "What is your age?", "var": "age"},
                {"type": "OpenText", "id": "q_comment", "text": "Anything else?", "var": "comment"},
            ],
        }
    ],
    "variables": {
        "q1": {
            "scale": "ordinal",
            "label": "Satisfaction",
            "labels": [
                {"code": code, "label": label}
                for code, label in enumerate(
                    ["Very dissatisfied", "Dissatisfied", "Neutral", "Satisfied", "Very satisfied"],
                    start=1,
                )
            ],
        },
        **{
            name: {
                "scale": "ordinal",
                "label": label,
                "labels": [
                    {"code": 1, "label": "Disagree"},
                    {"code": 2, "label": "Neither agree nor disagree"},
                    {"code": 3, "label": "Agree"},
                ],
            }
            for name, label in (("q2_1", "Price"), ("q2_2", "Service"))
        },
        "age": {
            "scale": "ordinal",
            "label": "Age group",
            "labels": [
                {"code": 1, "label": "18 - 24"},
                {"code": 2, "label": "25 - 34"},
                {"code": 3, "label": "35 or older"},
            ],
        },
        "comment": {"scale": "nominal", "label": "Comment"},
    },
}


@pytest.mark.parametrize("make", [_qualtrics_csv, _qualtrics_xlsx], ids=["csv", "xlsx"])
def test_a_qualtrics_export_reads_its_labels_and_types(make, tmp_path):
    path = make(tmp_path / ("export.csv" if make is _qualtrics_csv else "export.xlsx"))
    data = read_snapshot(path)
    frame = data.frame
    # The question texts (and the CSV's ImportId row) are not respondents.
    assert len(frame) == 3
    assert data.variables["Q1"].label == "How satisfied are you?"
    assert data.variables["StartDate"].label == "Start Date"
    assert str(frame["StartDate"].dtype).startswith("datetime64")
    assert frame["Finished"].tolist() == [True, True, False]
    assert frame["Progress"].tolist() == [100, 100, 40]
    assert frame["Duration (in seconds)"].tolist() == [300, 540, 60]
    assert frame["LocationLatitude"].iloc[0] == 55.75
    schema = inspect_snapshot(path)
    assert schema["read"]["qualtrics"] is True
    assert schema["read"]["header_rows"] == (3 if path.suffix == ".csv" else 2)
    # Without the questionnaire the answers stay the texts they are.
    assert frame["Q1"].tolist() == ["Very satisfied", "Neutral", "Dissatisfied"]
    # Header rows said by hand: 1 reads the question texts as a respondent.
    assert len(read_snapshot(path, header_rows="1").frame) == len(frame) + (
        2 if path.suffix == ".csv" else 1
    )


def test_a_numeric_values_export_is_the_questionnaire_s_codes(tmp_path):
    # Qualtrics' recommended route: the survey imported from its .qsf, the
    # data exported with "Use numeric values".
    import csv

    survey = from_document(PILOT).survey
    path = tmp_path / "numeric.csv"
    answers = [
        [*row[:13], code_1, code_2, code_3, age, row[17]]
        for row, (code_1, code_2, code_3, age) in zip(
            QUALTRICS_ANSWERS,
            [("5", "3", "1", "2"), ("3", "2", "3", "1"), ("2", "", "", "3")],
            strict=True,
        )
    ]
    import_ids = [json.dumps({"ImportId": f"QID{i}"}) for i in range(len(QUALTRICS_NAMES))]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for row in (QUALTRICS_NAMES, QUALTRICS_LABELS, import_ids, *answers):
            writer.writerow(row)
    data = read_snapshot(path, questionnaire=survey)
    assert data.frame["q1"].tolist() == [5, 3, 2]
    assert str(data.frame["q2_1"].dtype) == "Int64"
    table = data.analysis.frequencies("q1", labels=True)
    assert "What is your age?" not in set(table["label"].dropna())
    assert set(table["label"].dropna()) <= set(data.variables["q1"].labels.values())


def test_a_matching_questionnaire_turns_choice_texts_into_codes(tmp_path):
    survey = from_document(PILOT).survey
    path = _qualtrics_xlsx(tmp_path / "export.xlsx")
    data = read_snapshot(path, questionnaire=survey)
    # Q1 is the questionnaire's q1 (as its .qsf import names it).
    assert data.questionnaire is survey
    assert "q1" in data.frame.columns and "Q1" not in data.frame.columns
    assert data.frame["q1"].tolist() == [5, 3, 2]
    assert data.frame["q2_1"].tolist()[:2] == [3, 2] and pd.isna(data.frame["q2_1"].iloc[2])
    assert data.frame["age"].tolist() == [2, 1, 3]
    assert str(data.frame["q1"].dtype) in {"int64", "Int64"}
    assert str(data.frame["q2_1"].dtype) == "Int64"
    assert data.variables["q1"].labels[5] == "Very satisfied"
    # The Qualtrics columns stay, typed.
    assert data.frame["Finished"].tolist() == [True, True, False]
    schema = inspect_snapshot(path, questionnaire=survey)
    assert schema["codebook"] == "questionnaire"
    assert schema["questionnaire"]["matches"] is True
    assert schema["questionnaire"]["renamed"] == {"Q1": "q1", "Q2_1": "q2_1", "Q2_2": "q2_2"}
    assert set(schema["converted"]) == {"q1", "q2_1", "q2_2", "age"}

    # An answer that is none of the labels keeps the column's text, and says so.
    rows = [QUALTRICS_NAMES, QUALTRICS_LABELS, *QUALTRICS_ANSWERS]
    rows[2] = list(rows[2])
    rows[2][QUALTRICS_NAMES.index("Q1")] = "Extremely satisfied"
    pd.DataFrame(rows).to_excel(tmp_path / "odd.xlsx", header=False, index=False)
    odd = inspect_snapshot(tmp_path / "odd.xlsx", questionnaire=survey)
    assert odd["kept_text"] == {"q1": 1}
    assert any("q1: 1 of its answers are not among its value labels" in n for n in odd["notes"])


# ─── a file that is not the survey's data ────────────────────────────────────


def _national_survey(path):
    frame = pd.DataFrame(
        {
            "saves_regularly": [1, 2, 2, -9, 1, 2, 1, 2],
            "saving_for_1": [0, 1, -7, -7, 1, 0, 0, 1],
            "dwelling": [1, 2, 1, 2, 2, 1, 1, 2],
            "age_band": [1, 2, 3, 4, 5, 6, 7, 2],
            "region": [1, 3, 5, 7, 9, 11, 12, 2],
            "gender": [1, 2, 1, 2, 1, 2, 1, 2],
            "aware": ["yes; really", "no", "yes", "no", "yes", "no", "yes", "no"],
            "balance_change": [1500.5, -2300.0, 800.25, -7.0, 0.0, 12000.0, 55.5, -120.75],
        }
    )
    frame.to_excel(path, index=False)
    return path


def test_a_file_from_elsewhere_keeps_its_own_names_and_labels(project, tmp_path):
    _document, survey = project
    path = _national_survey(tmp_path / "survey.xlsx")
    data = read_snapshot(path, questionnaire=survey)
    # Not this survey's data: region, gender and aware share names only.
    assert data.questionnaire is None
    assert data.variables["region"].labels == {}  # not the project's Capital/North/South
    assert data.variables["gender"].labels == {}
    # A text column named like a multiple-choice question is not split.
    assert data.frame["aware"].iloc[0] == "yes; really"
    assert list(data.variables) == list(data.frame.columns)
    assert data.variables["saves_regularly"].scale == "nominal"
    assert data.variables["age_band"].scale == "ordinal"
    assert data.variables["balance_change"].scale == "interval"
    schema = inspect_snapshot(path, questionnaire=survey)
    assert schema["codebook"] == "file"
    assert schema["questionnaire"]["matches"] is False
    assert set(schema["questionnaire"]["shared"]) == {"region", "gender", "aware"}
    assert all(schema["variables"][name]["inferred"] for name in schema["variables"])
    # Said in a sentence that names the columns and agrees in number with them.
    assert (
        "3 of the file's 8 columns share names with questionnaire variables (region, gender, "
        "aware), but 2 of them (region, aware) hold answers that don't fit their variables, "
        "so they keep the file's own labels. Set Codebook to questionnaire to use the "
        "questionnaire's."
    ) in schema["notes"]
    # Codebook: questionnaire says it is the survey's data after all.
    forced = read_snapshot(path, questionnaire=survey, codebook="questionnaire")
    assert forced.questionnaire is survey
    assert forced.variables["region"].labels == survey.variables["region"].labels
    # Codebook: file on the survey's own export keeps the file's codebook.
    simulated = survey.simulate(n=10, seed=3)
    own = write_snapshot(SurveyData(frame=simulated.frame), tmp_path / "own.csv")
    assert read_snapshot(own, questionnaire=survey).questionnaire is survey
    assert read_snapshot(own, questionnaire=survey, codebook="file").questionnaire is None
    with pytest.raises(ValueError, match="codebook must be one of"):
        read_snapshot(own, codebook="survey")


def test_a_small_file_sharing_common_names_is_not_the_survey_s_data(project, tmp_path):
    # gender, age and comment are three of this survey's eight variables, and
    # three of the file's four answer columns: common names, not its data.
    _document, survey = project
    path = tmp_path / "client.csv"
    path.write_text(
        "id,gender,age,score,comment\n1,1,34,4.5,ok\n2,2,27,3.0,\n3,1,45,5.0,fine\n",
        encoding="utf-8",
    )
    schema = inspect_snapshot(path, questionnaire=survey)
    assert schema["codebook"] == "file"
    match = schema["questionnaire"]
    assert (match["columns"], match["variables"], len(match["shared"])) == (4, 8, 3)
    assert read_snapshot(path, questionnaire=survey).variables["gender"].labels == {}
    # The note counts the answer columns it means, beside the table's width.
    assert (
        "3 of the file's 4 answer columns (5 in all, response metadata aside) share names "
        "with questionnaire variables (gender, age, comment), but 3 names in common don't "
        "make the file the survey's data, so they keep the file's own labels. Set Codebook "
        "to questionnaire to use the questionnaire's."
    ) in schema["notes"]
    # One shared column is named, in the singular.
    (tmp_path / "one.csv").write_text("id,age,score\n1,young,4\n2,old,5\n", encoding="utf-8")
    one = inspect_snapshot(tmp_path / "one.csv", questionnaire=survey)
    assert (
        "age shares its name with a questionnaire variable, but its answers don't fit it, so "
        "it keeps the file's own labels. Set Codebook to questionnaire to use the "
        "questionnaire's."
    ) in one["notes"]


def test_the_survey_s_own_export_still_reads_with_the_questionnaire(project, tmp_path):
    _document, survey = project
    simulated = survey.simulate(n=30, seed=5)
    target = write_snapshot(SurveyData(frame=simulated.frame), tmp_path / "responses.xlsx")
    schema = inspect_snapshot(target, questionnaire=survey)
    assert schema["codebook"] == "questionnaire" and schema["questionnaire"]["matches"]
    data = read_snapshot(target, questionnaire=survey)
    assert data.questionnaire is survey
    assert set(data.variables) == set(survey.variables)
    assert data.frame["aware"].map(lambda v: isinstance(v, list) or pd.isna(v)).all()


def test_a_table_a_flow_wrote_is_still_the_survey_s(project, tmp_path):
    # A Write table's snapshot: two of the survey's variables beside three a
    # flow made, with the dictionary it carries (the survey's own labels).
    _document, survey = project
    simulated = survey.simulate(n=12, seed=7)
    frame = simulated.frame[["aware", "region"]].assign(
        score_a=range(12), score_b=range(12), score_c=range(12)
    )
    variables = VariableMap()
    variables.add_many(
        [
            survey.variables["aware"],
            survey.variables["region"],
            *(Variable(name, "ratio", label=name) for name in ("score_a", "score_b", "score_c")),
        ]
    )
    table = write_snapshot(SurveyData(frame=frame, variables=variables), tmp_path / "t.csv")
    data = read_snapshot(table, questionnaire=survey)
    assert data.questionnaire is survey
    assert data.frame["aware"].map(lambda v: isinstance(v, list) or pd.isna(v)).all()
    schema = inspect_snapshot(table, questionnaire=survey)
    assert schema["codebook"] == "dictionary" and schema["questionnaire"]["agrees"] is True
    # Without its dictionary it is no longer known to be the survey's, but
    # the multiple answers are still the question's, and split.
    table.with_name("t.dictionary.json").unlink()
    bare = read_snapshot(table, questionnaire=survey)
    assert bare.questionnaire is None
    assert bare.frame["aware"].map(lambda v: isinstance(v, list) or pd.isna(v)).all()


def test_missing_codes_are_suspected_and_can_be_declared(tmp_path):
    path = _national_survey(tmp_path / "survey.xlsx")
    columns = {c["name"]: c for c in inspect_snapshot(path)["columns"]}
    assert columns["saves_regularly"]["suspected_missing"] == [-9]
    assert columns["saving_for_1"]["suspected_missing"] == [-7]
    # A column of genuine negative amounts is not suspected.
    assert columns["balance_change"]["suspected_missing"] == []
    assert suspected_missing(pd.Series([1, 2, 3, 99, 1, 2])) == [99]
    assert suspected_missing(pd.Series([-7, -7, -7])) == [-7]
    assert suspected_missing(pd.Series([1999, 2005, 2011])) == []
    data = read_snapshot(path, missing="-7, -9")
    assert data.variables["saves_regularly"].missing_values == (-9,)
    assert data.variables["saving_for_1"].missing_values == (-7,)
    assert data.variables["dwelling"].missing_values == ()
    blanked = data.apply_missing_values()
    assert blanked.frame["saves_regularly"].isna().sum() == 1
    declared = {c["name"]: c for c in inspect_snapshot(path, missing=[-7, -9])["columns"]}
    assert declared["saves_regularly"]["missing"] == [-9]
    assert declared["saves_regularly"]["suspected_missing"] == []
    # Only the column named, in the {column: codes} form.
    only = read_snapshot(path, missing={"saving_for_1": [-7]})
    assert only.variables["saves_regularly"].missing_values == ()


def test_columns_that_hold_personal_data_are_pointed_out(tmp_path):
    path = _qualtrics_csv(tmp_path / "export.csv")
    flagged = {c["name"]: c["personal"] for c in inspect_snapshot(path)["columns"] if c["personal"]}
    assert flagged == {
        "IPAddress": "IP address",
        "RecipientEmail": "e-mail",
        "LocationLatitude": "location",
        "LocationLongitude": "location",
    }
    assert personal_data("PROLIFIC_PID") == "participant ID"
    assert personal_data("Телефон") == "phone"
    assert personal_data("contact", pd.Series(["a@example.org", "b@example.org", None])) == "e-mail"
    assert personal_data("satisfaction", pd.Series([1, 2])) is None


def test_the_schema_is_json_and_carries_no_answers(tmp_path):
    path = tmp_path / "contacts.csv"
    path.write_text(
        "id,email,note,score\n1,anna@example.org,likes tea,4\n2,boris@example.org,,5\n",
        encoding="utf-8",
    )
    schema = inspect_snapshot(path)
    text = json.dumps(schema, ensure_ascii=False)
    assert "anna@example.org" not in text and "likes tea" not in text
    column = next(c for c in schema["columns"] if c["name"] == "email")
    assert column["personal"] == "e-mail" and column["type"] == "text"
    assert column["n_missing"] == 0 and column["n_unique"] == 2
    # The codebook as check_flow takes it: a guessed scale is marked so.
    assert schema["variables"]["score"] == {"scale": "nominal", "inferred": True}
    sampled = inspect_snapshot(path, rows=1)
    assert sampled["rows"] == 1 and sampled["sampled"] is True


def test_scale_guesses():
    assert infer_scale(pd.Series([1, 2, 1, 2])) == "nominal"
    assert infer_scale(pd.Series([1, 2, 3, 4, 5, 3, 2, 4, 1, 5])) == "ordinal"
    assert infer_scale(pd.Series([1, 5, 9, 12, 1, 5, 9, 12])) == "nominal"
    assert infer_scale(pd.Series([34, 51, 29, 40])) == "ratio"
    assert infer_scale(pd.Series([1.5, -2.0, 3.25])) == "interval"
    assert infer_scale(pd.Series(["a", "b"])) == "nominal"
    assert infer_scale(pd.Series([True, False])) == "nominal"
    assert infer_scale(pd.to_datetime(pd.Series(["2026-01-01", "2026-02-01"]))) == "interval"
    # Missing codes are left out of the guess: 1/2 with -9 is two answers.
    assert infer_scale(pd.Series([1, 2, -9, 1, 2])) == "nominal"


def test_spss_codes_are_integers_and_labelled_stata_variables_nominal(tmp_path):
    variables = VariableMap()
    variables.add_many(
        [
            Variable("sat", "ordinal", label="Sat", labels={1: "Low", 2: "Mid", 3: "High"}),
            Variable("age", "ratio", label="Age"),
        ]
    )
    frame = pd.DataFrame({"sat": [1, 2, 3, 2], "age": [30, 41, 52, 63]})
    data = SurveyData(frame=frame, variables=variables)
    sav = read_snapshot(write_snapshot(data, tmp_path / "s.sav", dictionary=False))
    assert sav.variables["sat"].labels == {1: "Low", 2: "Mid", 3: "High"}
    assert str(sav.frame["sat"].dtype) == "Int64"
    dta = read_snapshot(write_snapshot(data, tmp_path / "s.dta", dictionary=False))
    assert dta.variables["sat"].scale == "nominal"  # Stata keeps no level; labels mean codes
    assert dta.variables["age"].scale == "interval"


# ─── the Data file node ──────────────────────────────────────────────────────


def _flow(nodes, edges=()):
    return {
        "schema_version": "1.0",
        "name": "file_flow",
        "nodes": [
            {"id": node_id, "type": node_type, "params": params, "position": [0, index]}
            for index, (node_id, node_type, params) in enumerate(nodes)
        ],
        "edges": [
            {"from": {"node": source, "port": "data"}, "to": {"node": target, "port": "data"}}
            for source, target in edges
        ],
    }


def test_the_node_passes_only_the_options_set(tmp_path):
    spec = default_registry().get("source.file")
    assert {
        "codebook",
        "header_rows",
        "skip_rows",
        "sheet",
        "delimiter",
        "encoding",
        "decimal",
        "missing",
    } <= set(spec.params)
    plain = _flow([("src", "source.file", {"path": "assets/data.csv"})])
    code = generate_flow(plain, format=False)
    assert "read_snapshot(\n    'assets/data.csv',\n    questionnaire=survey,\n)" in code
    chosen = _flow(
        [
            (
                "src",
                "source.file",
                {
                    "path": "assets/data.csv",
                    "delimiter": ";",
                    "encoding": "cp1251",
                    "decimal": ",",
                    "header_rows": "2",
                    "skip_rows": 0,
                    "codebook": "file",
                    "missing": "-7, -9",
                    "sheet": "",
                },
            )
        ]
    )
    code = generate_flow(chosen, format=False)
    for line in (
        "delimiter=';'",
        "encoding='cp1251'",
        "decimal=','",
        "header_rows='2'",
        "skip_rows=0",
        "codebook='file'",
        "missing='-7, -9'",
    ):
        assert line in code
    assert "sheet=" not in code and "dictionary=" not in code
    compile(code, "file_flow.py", "exec")
    assert snapshot_options(chosen["nodes"][0]["params"]) == {
        "codebook": "file",
        "header_rows": "2",
        "skip_rows": 0,
        "delimiter": ";",
        "encoding": "cp1251",
        "decimal": ",",
        "missing": "-7, -9",
    }
    bad = _flow([("src", "source.file", {"path": "a.csv", "delimiter": ":"})])
    assert any(issue.code == "PARAM_INVALID" for issue in check_flow(bad))


def test_the_node_reads_with_its_options_and_without_a_questionnaire(tmp_path):
    path = tmp_path / "anketa.csv"
    path.write_bytes("id;оценка\n1;4,5\n2;3,5\n".encode("cp1251"))
    flow = _flow(
        [
            ("src", "source.file", {"path": str(path), "encoding": "cp1251", "delimiter": ";"}),
            ("ds", "analyze.describe", {}),
        ],
        [("src", "ds")],
    )
    # No questionnaire at all (the project's could not be imported): `survey`
    # is None, and a Data file needs none.
    result = FlowRunner(flow).run(cwd=tmp_path)
    data = result.outputs["src"]["data"]
    assert data.frame["оценка"].tolist() == [4.5, 3.5]
    # Describe describes the file's own columns.
    described = result.outputs["ds"]["table"]
    assert set(described["name"]) == {"id", "оценка"}


# ─── check_flow knows a file's columns ───────────────────────────────────────


def test_check_flow_knows_a_data_file_s_columns(project, tmp_path):
    document, survey = project
    path = _national_survey(tmp_path / "survey.xlsx")
    schema = inspect_snapshot(path, questionnaire=survey)
    flow = _flow(
        [
            ("src", "source.file", {"path": str(path)}),
            ("fr", "analyze.freq", {"variable": "saves_regularly"}),
            ("xt", "analyze.crosstab", {"row": "dwelling", "col": "age_band"}),
            ("ds", "analyze.descriptives", {"variables": ["dwelling"]}),
        ],
        [("src", "fr"), ("src", "xt"), ("src", "ds")],
    )
    # Without the file's codebook every column is unknown (the Save's error).
    codes = {(issue.code, issue.node) for issue in check_flow(flow, questionnaire=document)}
    assert ("UNKNOWN_VARIABLE", "fr") in codes and ("UNKNOWN_VARIABLE", "xt") in codes
    # With it, by node id or by the path the node reads.
    for key in ("src", str(path)):
        issues = check_flow(flow, questionnaire=document, files={key: schema})
        assert [i for i in issues if i.severity == "error"] == []
        # A guessed scale that does not fit is a warning, not an error.
        (warning,) = issues
        assert warning.code == "VARIABLE_SCALE" and warning.node == "ds"
        assert "as guessed from its file's values" in warning.message
    # The questionnaire's own variables are not the file's.
    flow["nodes"].append(
        {
            "id": "tr",
            "type": "analyze.freq",
            "params": {"variable": "trust_acme"},
            "position": [1, 0],
        }
    )
    flow["edges"].append(
        {"from": {"node": "src", "port": "data"}, "to": {"node": "tr", "port": "data"}}
    )
    issues = check_flow(flow, questionnaire=document, files={"src": schema})
    assert [(i.code, i.node) for i in issues if i.severity == "error"] == [
        ("UNKNOWN_VARIABLE", "tr")
    ]
    # A file not read yet: nothing below it is checked for names.
    assert [
        i
        for i in check_flow(flow, questionnaire=document, files={"src": None})
        if i.severity == "error"
    ] == []
    # The runner and the generator take the same files.
    runnable = _flow(
        [
            ("src", "source.file", {"path": str(path)}),
            ("fr", "analyze.freq", {"variable": "saves_regularly"}),
        ],
        [("src", "fr")],
    )
    generate_flow(runnable, document, files={"src": schema}, format=False)
    result = FlowRunner(
        runnable, questionnaire=survey, questionnaire_document=document, files={"src": schema}
    ).run(cwd=tmp_path)
    assert result.ok


def test_each_branch_is_checked_against_its_own_source(project, tmp_path):
    document, survey = project
    path = _national_survey(tmp_path / "survey.xlsx")
    schema = inspect_snapshot(path, questionnaire=survey)
    flow = _flow(
        [
            ("src", "source.file", {"path": str(path)}),
            ("fr", "analyze.freq", {"variable": "saves_regularly"}),
            ("sim", "source.simulated", {}),
            ("fq", "analyze.freq", {"variable": "trust_acme"}),
            ("bad", "analyze.freq", {"variable": "saves_regularly"}),
        ],
        [("src", "fr"), ("sim", "fq"), ("sim", "bad")],
    )
    issues = check_flow(flow, questionnaire=document, files={"src": schema})
    assert [(i.code, i.node) for i in issues if i.severity == "error"] == [
        ("UNKNOWN_VARIABLE", "bad")
    ]


def test_a_matching_file_knows_the_questionnaire_and_its_own_extra_columns(tmp_path):
    survey = from_document(PILOT).survey
    path = _qualtrics_xlsx(tmp_path / "export.xlsx")
    schema = inspect_snapshot(path, questionnaire=survey)
    flow = _flow(
        [
            ("src", "source.file", {"path": str(path)}),
            ("q", "analyze.freq", {"variable": "q1"}),
            ("d", "analyze.descriptives", {"variables": ["Duration (in seconds)"]}),
            ("x", "analyze.crosstab", {"row": "q2_1", "col": "age"}),
        ],
        [("src", "q"), ("src", "d"), ("src", "x")],
    )
    assert check_flow(flow, questionnaire=PILOT, files={"src": schema}) == []
    result = FlowRunner(
        flow, questionnaire=survey, questionnaire_document=PILOT, files={"src": schema}
    ).run(cwd=tmp_path)
    assert result.ok


def test_the_cli_check_reads_the_flow_s_data_files(project, tmp_path, monkeypatch, capsys):
    from siamang.cli.flow import run_check

    document, _survey = project
    _national_survey(tmp_path / "survey.xlsx")
    (tmp_path / "q.json").write_text(json.dumps(document), encoding="utf-8")
    flow = _flow(
        [
            ("src", "source.file", {"path": "survey.xlsx"}),
            ("fr", "analyze.freq", {"variable": "saves_regularly"}),
        ],
        [("src", "fr")],
    )
    (tmp_path / "flow.json").write_text(json.dumps(flow), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert run_check("flow.json", questionnaire="q.json") == 0
    assert "OK" in capsys.readouterr().out


# ─── review: encodings of short files ────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "encoding"),
    [
        ("id;пол\r\n1;м\r\n2;ж\r\n", "cp1251"),
        (
            "id;ответ\r\n" + "".join(f"{i};{'да' if i % 2 else 'нет'}\r\n" for i in range(20)),
            "cp1251",
        ),
        ("id;в1;в2;в3;пол\r\n1;1;2;3;м\r\n2;2;2;1;ж\r\n", "cp1251"),
        ("№;Пол;Возр\r\n1;1;23\r\n2;2;45\r\n", "cp1251"),
        ("ID;ПОЛ;ГОРОД\r\n1;М;МОСКВА\r\n2;Ж;ОРЁЛ\r\n", "cp1251"),
        ("id;сумма\r\n1;100 €\r\n2;200 €\r\n", "cp1251"),
        ("id;commentaire\r\n1;très bien\r\n2;déçu\r\n", "cp1252"),
        ("id;name;city\r\n1;Müller;Köln\r\n2;Weiß;Düsseldorf\r\n", "cp1252"),
        ("id;miasto\r\n1;Łódź\r\n2;Gdańsk\r\n3;Kraków\r\n", "cp1250"),
        ("id;пол;город\n1;муж;Москва\n2;жен;Тверь\n", "koi8_r"),
        ("id;ответ\n1;да\n2;нет\n3;не знаю\n", "koi8_r"),
        ("id;пол;город\n1;муж;Москва\n2;жен;Тверь\n", "cp866"),
    ],
)
def test_a_short_file_s_code_page_is_told_by_its_words(tmp_path, text, encoding):
    # Russian Excel's CSV is Windows-1251; a few letters are all a file of
    # codes holds. It was read as Windows-1252 ("îòâåò") with no error.
    path = tmp_path / "short.csv"
    path.write_bytes(text.encode(encoding))
    assert detect_encoding(path) == codecs.lookup(encoding).name
    frame = read_snapshot(path).frame
    names = text.replace("\r", "").split("\n")[0].split(";")
    assert list(frame.columns) == names
    schema = inspect_snapshot(path)
    assert schema["read"]["encoding_guessed"] is True
    assert any("not UTF-8" in note and "Encoding" in note for note in schema["notes"])


def test_cyrillic_past_an_ascii_head_decides_the_encoding(tmp_path):
    # 300 KB of codes before the first answer in words.
    text = "id,code,comment\r\n" + "".join(f"{i},{i % 5},\r\n" for i in range(30000))
    text += "30001,1,Очень хорошо\r\n30002,2,плохо\r\n"
    path = tmp_path / "late.csv"
    path.write_bytes(text.encode("cp1251"))
    assert detect_encoding(path) == "cp1251"
    frame = read_snapshot(path).frame
    assert frame["comment"].dropna().tolist() == ["Очень хорошо", "плохо"]


# ─── review: delimiters and decimal marks ────────────────────────────────────


def test_a_semicolon_file_whose_names_hold_a_comma(tmp_path):
    # Russian Excel: "Рост, см;Вес, кг" — every row as many , as ; — was read
    # with "," into "id;Рост", "см;Вес", "кг".
    path = tmp_path / "units.csv"
    rows = "".join(f"{i};{170 + i % 20},{i % 10};{60 + i % 30},5\r\n" for i in range(30))
    path.write_bytes(("id;Рост, см;Вес, кг\r\n" + rows).encode("cp1251"))
    data = read_snapshot(path)
    assert list(data.frame.columns) == ["id", "Рост, см", "Вес, кг"]
    assert data.frame["Рост, см"].iloc[3] == 173.3
    read = inspect_snapshot(path)["read"]
    assert (read["delimiter"], read["decimal"]) == (";", ",")
    two = tmp_path / "income.csv"
    two.write_text(
        "Регион;Доход, руб.\r\n" + "".join(f"R{i};{1000 + i},50\r\n" for i in range(10)),
        encoding="utf-8-sig",
    )
    assert list(read_snapshot(two).frame.columns) == ["Регион", "Доход, руб."]
    # A comma file whose lists ("1;3") vary per row is still a comma file.
    lists = tmp_path / "lists.csv"
    lists.write_text("id,q2,comment\n1,1;3,good\n2,2,ok\n3,1;2;3,fine\n", encoding="utf-8")
    assert list(read_snapshot(lists).frame.columns) == ["id", "q2", "comment"]


def test_a_one_column_file_of_decimal_commas_keeps_its_name(tmp_path):
    path = tmp_path / "score.csv"
    path.write_text("score\r\n4,5\r\n3,2\r\n1,0\r\n2,7\r\n", encoding="utf-8")
    frame = read_snapshot(path).frame
    assert list(frame.columns) == ["score"]
    assert frame["score"].tolist() == [4.5, 3.2, 1.0, 2.7]
    income = tmp_path / "income.csv"
    income.write_text("Доход, руб.\n1000,50\n2000,75\n950\n", encoding="utf-8")
    frame = read_snapshot(income).frame
    assert list(frame.columns) == ["Доход, руб."]
    assert frame["Доход, руб."].tolist() == [1000.5, 2000.75, 950.0]
    # Two columns of whole numbers are two columns.
    pairs = tmp_path / "pairs.csv"
    pairs.write_text("a,b\n1,5\n2,3\n4,4\n", encoding="utf-8")
    assert read_snapshot(pairs).frame.to_dict("list") == {"a": [1, 2, 4], "b": [5, 3, 4]}


def test_decimals_that_come_past_the_first_rows_are_read(tmp_path):
    path = tmp_path / "weights.csv"
    text = "id;income;weight\r\n" + "".join(f"{i};{1000 + i};1\r\n" for i in range(300))
    text += "".join(f"{i};{2000 + i};0,85\r\n" for i in range(300, 320))
    path.write_bytes(text.encode("cp1251"))
    columns = {c["name"]: c["type"] for c in inspect_snapshot(path)["columns"]}
    assert columns["weight"] == "number"
    assert read_snapshot(path).frame["weight"].iloc[-1] == 0.85


# ─── review: workbooks ───────────────────────────────────────────────────────


def test_a_codebook_sheet_before_the_data_is_passed_over(tmp_path):
    named = tmp_path / "named.xlsx"
    unnamed = tmp_path / "unnamed.xlsx"
    data = pd.DataFrame({"id": range(1, 41), "sex": [1, 2] * 20, "age": list(range(20, 60))})
    codebook = pd.DataFrame({"Variable": ["id", "sex", "age"], "Description": ["ID", "Sex", "Age"]})
    for path, first in ((named, "Codebook"), (unnamed, "Sheet1")):
        with pd.ExcelWriter(path) as writer:
            codebook.to_excel(writer, sheet_name=first, index=False)
            data.to_excel(writer, sheet_name="Data", index=False)
        schema = inspect_snapshot(path)
        assert schema["read"]["sheet"] == "Data", first
        assert schema["rows"] == 40
    # A sheet named by hand is read, codebook or not.
    assert inspect_snapshot(named, sheet="Codebook")["rows"] == 3


def test_a_names_row_that_names_fewer_columns_than_the_answers_fill(tmp_path):
    path = tmp_path / "partial.xlsx"
    rows = [[f"c{i}" if i < 10 else None for i in range(25)]] + [[i] * 25 for i in range(40)]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)
    schema = inspect_snapshot(path)
    assert schema["rows"] == 40
    assert [c["name"] for c in schema["columns"]][:10] == [f"c{i}" for i in range(10)]


def test_text_numbers_as_ambiguous_as_1_500_are_not_guessed(tmp_path):
    ambiguous = tmp_path / "ambiguous.xlsx"
    pd.DataFrame([["id", "share"], [1, "1,250"], [2, "2,750"]]).to_excel(
        ambiguous, header=False, index=False
    )
    schema = inspect_snapshot(ambiguous)
    assert {c["name"]: c["type"] for c in schema["columns"]}["share"] == "text"
    assert any("Decimal mark" in note for note in schema["notes"])
    assert "1,250" not in json.dumps(schema)  # the note names no answer
    assert read_snapshot(ambiguous, decimal=",").frame["share"].tolist() == [1.25, 2.75]
    assert read_snapshot(ambiguous, decimal=".").frame["share"].tolist() == [1250, 2750]
    # Other text numbers of the sheet tell: "0,5" is a decimal comma.
    told = tmp_path / "told.xlsx"
    pd.DataFrame([["id", "share"], [1, "1,250"], [2, "2,750"], [3, "0,5"]]).to_excel(
        told, header=False, index=False
    )
    assert read_snapshot(told).frame["share"].tolist() == [1.25, 2.75, 0.5]


def test_status_progress_and_finished_alone_are_no_qualtrics_export(tmp_path):
    path = tmp_path / "tasks.xlsx"
    pd.DataFrame(
        {
            "task": ["a", "b", "c"],
            "Status": ["open", "done", "done"],
            "Progress": ["half", "all", "all"],
            "Finished": ["no", "yes", "yes"],
        }
    ).to_excel(path, index=False)
    schema = inspect_snapshot(path)
    assert schema["rows"] == 3 and schema["read"]["header_rows"] == 1
    assert "qualtrics" not in schema["read"]


# ─── review: whose codebook ──────────────────────────────────────────────────


def _studio_export(survey, rows=40):
    frame = survey.simulate(n=rows, seed=4).frame
    for column in frame.columns:
        if frame[column].map(lambda value: isinstance(value, list)).any():
            frame[column] = frame[column].map(
                lambda value: ";".join(map(str, value)) if isinstance(value, list) else value
            )
    meta = {
        "duration_s": 300,
        "started_at": "2026-01-02T10:00:00+00:00",
        "captcha": 0.9,
        "tab_switches": 0,
        "hidden_seconds": 3,
        "pastes": 0,
        **{f"url_{name}": "x" for name in ("utm_source", "utm_medium", "utm_campaign", "ref", "p")},
        "id": 1,
        "_created_at": "2026-01-02T10:05:00+00:00",
        "survey_id": "s1",
        "respondent_id": "u",
        "partial": False,
    }
    for name, value in meta.items():
        frame[name] = value
    return frame


def test_studio_s_own_data_export_is_the_survey_s_data(project, tmp_path):
    # captcha, tab_switches, hidden_seconds, pastes and url_* are fieldwork
    # signals: counted as answer columns they made the export "not the
    # survey's", and a flow's Likert lost its value labels at Save.
    document, survey = project
    path = tmp_path / "export.csv"
    _studio_export(survey).to_csv(path, index=False)
    schema = inspect_snapshot(path, questionnaire=survey)
    assert schema["codebook"] == "questionnaire"
    assert schema["questionnaire"]["columns"] == len(survey.variables)
    data = read_snapshot(path, questionnaire=survey)
    assert data.variables["region"].labels == survey.variables["region"].labels
    flow = _flow(
        [
            ("f", "source.file", {"path": str(path)}),
            ("lk", "visualize.likert", {"items": ["trust_acme", "trust_globex"]}),
        ],
        [("f", "lk")],
    )
    assert [i for i in check_flow(flow, questionnaire=document, files={"f": schema})] == []
    # Qualtrics' metadata, display orders and "Other" texts are no answers either.
    from siamang.io.file_codebook import is_metadata, questionnaire_match
    from siamang.io.snapshot import _questionnaire_variables

    assert all(is_metadata(name) for name in ("Q_RecaptchaScore", "Q1_DO", "FL_6_DO", "_id"))
    assert not is_metadata("region")
    variables = _questionnaire_variables(survey)
    extra = pd.read_csv(path).assign(region_other="x", Q_TotalDuration=1, FL_2_DO="1|2")
    assert questionnaire_match(extra, variables).columns == len(survey.variables)


def test_a_platform_source_s_snapshot_is_read_with_the_questionnaire(project, tmp_path):
    # A pilot's snapshot has the columns of the questions reached: the
    # research bundle (--data) and FlowRunner read it with the questionnaire
    # as the platform does, not by the half-of-its-variables rule.
    document, survey = project
    pilot = tmp_path / "responses.csv"
    frame = survey.simulate(n=20, seed=2).frame[["age", "region", "gender"]]
    frame.assign(id=1, partial=True).to_csv(pilot, index=False)
    flow = _flow(
        [
            ("resp", "source.responses", {}),
            ("xt", "analyze.crosstab", {"row": "region", "col": "gender"}),
        ],
        [("resp", "xt")],
    )
    code = generate_flow(flow, document, format=False)
    assert 'read_snapshot(args.data, questionnaire=survey, codebook="questionnaire")' in code
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run(
        sources={"resp": pilot}, cwd=tmp_path
    )
    data = result.outputs["resp"]["data"]
    assert data.questionnaire is survey
    assert data.variables["region"].labels == survey.variables["region"].labels


def test_qualtrics_numeric_multiple_answers_are_split_at_commas(tmp_path):
    import csv

    items = [
        {
            "type": "MultiChoice",
            "id": "q_2",
            "text": "Which brands?",
            "var": "q2",
            "choices": [
                {"code": 1, "label": "Acme"},
                {"code": 2, "label": "Globex, Inc."},
                {"code": 3, "label": "Initech"},
            ],
        },
        {"type": "SingleChoice", "id": "q_1", "text": "Satisfied?", "var": "q1"},
    ]
    document = {
        "schema_version": "1.0",
        "title": "P",
        "pages": [{"name": "p1", "items": items}],
        "variables": {
            "q2": {
                "scale": "nominal",
                "label": "Brands",
                "labels": [
                    {"code": 1, "label": "Acme"},
                    {"code": 2, "label": "Globex, Inc."},
                    {"code": 3, "label": "Initech"},
                ],
            },
            "q1": {
                "scale": "ordinal",
                "label": "Satisfied",
                "labels": [{"code": 1, "label": "No"}, {"code": 2, "label": "Yes"}],
            },
        },
    }
    survey = from_document(document).survey
    names = ["StartDate", "EndDate", "Progress", "Finished", "ResponseId", "Q1", "Q2"]
    labels = [
        "Start Date",
        "End Date",
        "Progress",
        "Finished",
        "Response ID",
        "Satisfied?",
        "Brands",
    ]
    stamps = ["2026-01-05 10:00:00", "2026-01-05 10:05:00", "100", "1", "R_x"]
    numeric = [[*stamps, "2", "1,3"], [*stamps, "1", "2"], [*stamps, "2", "1,2,3"]]
    text = [
        [*stamps, "Yes", "Acme,Initech"],
        [*stamps, "No", "Globex, Inc."],
        [*stamps, "Yes", "Acme,Globex, Inc.,Initech"],
    ]
    for rows, kind in ((numeric, "numeric"), (text, "text")):
        csv_path = tmp_path / f"{kind}.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            imports = [json.dumps({"ImportId": f"QID{i}"}) for i in range(len(names))]
            for row in (names, labels, imports, *rows):
                writer.writerow(row)
        xlsx_path = tmp_path / f"{kind}.xlsx"
        pd.DataFrame([names, labels, *rows]).to_excel(xlsx_path, header=False, index=False)
        for path in (csv_path, xlsx_path):
            data = read_snapshot(path, questionnaire=survey)
            assert data.questionnaire is survey, path.name
            assert data.frame["q2"].tolist() == [[1, 3], [2], [1, 2, 3]], path.name
            assert data.frame["q1"].tolist() == [2, 1, 2], path.name
            schema = inspect_snapshot(path, questionnaire=survey)
            assert schema["questionnaire"]["conflicts"] == {}, path.name


# ─── review: missing codes per column ────────────────────────────────────────


def test_missing_codes_per_column_spare_other_columns(tmp_path):
    from siamang.io.file_codebook import EVERY_COLUMN, missing_text, parse_missing

    path = tmp_path / "survey.xlsx"
    pd.DataFrame(
        {
            "q5": [1, 2, 2, -9, 1, 2, 1, 2],
            "q6_1": [0, 1, -7, -7, 1, 0, 0, 1],
            "balance": [1500.5, -2300.0, 800.25, -7.0, 0.0, 12000.0, 55.5, -120.75],
            "age": [18, 45, 97, 99, 98, 60, 33, 51],
            "rating": [1, 2, 3, 4, 5, 99, 3, 2],
        }
    ).to_excel(path, index=False)
    suspected = {
        column["name"]: column["suspected_missing"]
        for column in inspect_snapshot(path)["columns"]
        if column["suspected_missing"]
    }
    assert suspected == {"q5": [-9], "q6_1": [-7], "rating": [99]}
    text = missing_text(suspected)
    assert text == "q5: -9; q6_1: -7; rating: 99"
    assert parse_missing(text) == suspected
    data = read_snapshot(path, missing=text)
    declared = {name: data.variables[name].missing_values for name in data.variables}
    assert declared == {
        "q5": (-9,),
        "q6_1": (-7,),
        "balance": (),
        "age": (),
        "rating": (99,),
    }
    # Codes for every column spare a column of other negative amounts.
    every = read_snapshot(path, missing="-9, -7").variables
    assert every["q6_1"].missing_values == (-7,)
    assert every["balance"].missing_values == ()
    assert parse_missing('-9; "a;b": 99; income: -7') == {
        EVERY_COLUMN: [-9],
        "a;b": [99],
        "income": [-7],
    }
    assert parse_missing(missing_text({"Рост, см": [-7, -8], "x;y": [99], 'say "hi"': [-9]})) == {
        "Рост, см": [-7, -8],
        "x;y": [99],
        'say "hi"': [-9],
    }
    # As Studio's Columns panel writes it (suspectedMissingText).
    assert parse_missing('"a;b": 99; "say ""hi""": -7; Доля, %: -9, -8') == {
        "a;b": [99],
        'say "hi"': [-7],
        "Доля, %": [-9, -8],
    }


def test_labelled_missing_codes_do_not_part_a_table_from_its_survey(tmp_path):
    # SPSS keeps "9 refused" apart from the answers' labels; the questionnaire
    # among them. A table a flow wrote as .sav, with a variable of the survey
    # beside those it made, agrees with the survey.
    trust = Variable(
        "trust",
        "ordinal",
        label="Trust",
        labels={1: "Low", 2: "High", 9: "Refused"},
        missing_values=(9,),
        missing_labels={9: "Refused"},
    )
    others = [Variable(f"q{i}", "nominal", labels={1: "No", 2: "Yes"}) for i in range(4)]
    document = {
        "schema_version": "1.0",
        "title": "T",
        "pages": [{"name": "p", "items": []}],
        "variables": {
            "trust": {
                "scale": "ordinal",
                "label": "Trust",
                "labels": [
                    {"code": 1, "label": "Low"},
                    {"code": 2, "label": "High"},
                    {"code": 9, "label": "Refused"},
                ],
                "missing": [{"code": 9, "label": "Refused"}],
            },
            **{
                other.name: {
                    "scale": "nominal",
                    "labels": [{"code": 1, "label": "No"}, {"code": 2, "label": "Yes"}],
                }
                for other in others
            },
        },
    }
    survey = from_document(document).survey
    made = [Variable("score", "ratio", label="Score"), Variable("band", "ordinal", label="Band")]
    variables = VariableMap()
    variables.add_many([trust, *made])
    frame = pd.DataFrame(
        {"trust": [1, 2, 9, 1], "score": [1.5, 2.5, 3.0, 4.0], "band": [1, 2, 3, 1]}
    )
    path = write_snapshot(
        SurveyData(frame=frame, variables=variables), tmp_path / "t.sav", dictionary=False
    )
    schema = inspect_snapshot(path, questionnaire=survey)
    assert schema["questionnaire"]["agrees"] is True
    assert read_snapshot(path, questionnaire=survey).questionnaire is survey


# ─── review: small gaps ──────────────────────────────────────────────────────


def test_header_rows_given_as_a_number_is_that_choice(tmp_path):
    flow = _flow([("src", "source.file", {"path": "assets/export.csv", "header_rows": 2})])
    assert check_flow(flow) == []
    assert "header_rows='2'" in generate_flow(flow, format=False)
    wrong = _flow([("src", "source.file", {"path": "assets/export.csv", "header_rows": 5})])
    assert any(issue.code == "PARAM_INVALID" for issue in check_flow(wrong))


def test_an_empty_column_has_no_type_or_scale_to_guess_and_sampling_is_exact(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text("id,RecipientEmail,score\n1,,3\n2,,4\n3,,5\n", encoding="utf-8")
    columns = {c["name"]: c for c in inspect_snapshot(path)["columns"]}
    assert columns["RecipientEmail"]["type"] == "empty"
    assert columns["RecipientEmail"]["scale"] is None
    assert columns["RecipientEmail"]["inferred"] is False
    assert inspect_snapshot(path, rows=3)["sampled"] is False
    assert inspect_snapshot(path, rows=2)["sampled"] is True
    assert inspect_snapshot(path, rows=2)["rows"] == 2


def test_auto_is_run_as_the_file_s_schema_decided(project, tmp_path):
    # The check read the file against the questionnaire of that moment; the
    # run reads it the same way, however the questionnaire changes after.
    document, survey = project
    export = tmp_path / "export.csv"
    _studio_export(survey).to_csv(export, index=False)
    other = _national_survey(tmp_path / "other.xlsx")
    flow = _flow(
        [
            ("a", "source.file", {"path": str(export)}),
            ("b", "source.file", {"path": str(other)}),
            ("c", "source.file", {"path": str(other), "codebook": "questionnaire"}),
        ]
    )
    files = {
        "a": inspect_snapshot(export, questionnaire=survey),
        "b": inspect_snapshot(other, questionnaire=survey),
        "c": inspect_snapshot(other, questionnaire=survey, codebook="questionnaire"),
    }
    code = generate_flow(flow, document, files=files, format=False)
    blocks = code.split("read_snapshot(")[1:]
    assert "codebook='questionnaire'" in blocks[0]
    assert "codebook='file'" in blocks[1]
    assert "codebook='questionnaire'" in blocks[2]  # said by hand, kept
    # Without schemas, auto stays auto.
    assert "codebook=" not in generate_flow(flow, document, format=False).split("read_snapshot(")[1]
