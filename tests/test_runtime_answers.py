"""What the survey runtime stores, as the compiled payload fixes it.

Every key of the answers object that reaches a backend is a codebook variable
and every value one of its codes: these tests pin the payload fields the
runtime reads to get there. The runtime itself is driven in
``test_runtime_browser.py``.
"""

from __future__ import annotations

import siamang as sg
from siamang.frontend.compiler.react import compile_react_payload


def _only_item(survey):
    (page,) = (p for p in compile_react_payload(survey)["PAGES"] if p.get("items"))
    (item,) = page["items"]
    return item


def _matrix(column_labels=None, labels=None, **kwargs):
    rows = [
        sg.Variable("r1", scale="ordinal", labels=dict(labels or {})),
        sg.Variable("r2", scale="ordinal", labels=dict(labels or {})),
    ]
    return sg.Matrix("Rate", var=rows, column_labels=column_labels, **kwargs)


def _survey(*items):
    return sg.Questionnaire(title="T", pages=[sg.Page(name="p", items=list(items))])


# ── Matrix: a column stores its code ─────────────────────────────────────────


class TestMatrixColumnCodes:
    def test_headers_that_name_the_labels_take_their_codes(self):
        """The codebook may list the scale in any order; a header names its code."""

        labels = {5: "Agree", 1: "Disagree", 3: "Neutral"}
        matrix = _matrix(["Disagree", "Neutral", "Agree"], labels)
        assert matrix.columns() == [(1, "Disagree"), (3, "Neutral"), (5, "Agree")]
        item = _only_item(_survey(matrix))
        assert item["columns"] == ["Disagree", "Neutral", "Agree"]
        assert item["columnCodes"] == [1, 3, 5]

    def test_a_zero_to_ten_scale_is_coded_zero_to_ten(self):
        """The ESS trust block: headers "0" … "10" over labels coded 0 … 10."""

        labels = {0: "No trust at all", **{n: str(n) for n in range(1, 10)}, 10: "Complete"}
        matrix = _matrix([str(n) for n in range(11)], labels)
        assert [code for code, _ in matrix.columns()] == list(range(11))

    def test_headers_match_by_position_when_the_texts_differ(self):
        labels = {10: "low", 20: "mid", 30: "high"}
        matrix = _matrix(["L", "M", "H"], labels)
        assert matrix.columns() == [(10, "L"), (20, "M"), (30, "H")]

    def test_without_headers_the_columns_are_the_codebook_in_code_order(self):
        labels = {9: "Refused", 2: "Low", 1: "None"}
        matrix = _matrix(None, labels)
        assert matrix.columns() == [(1, "None"), (2, "Low"), (9, "Refused")]
        item = _only_item(_survey(matrix))
        assert item["columns"] == ["None", "Low", "Refused"]
        assert item["columnCodes"] == [1, 2, 9]

    def test_headers_the_codebook_cannot_place_count_from_one(self):
        """No codebook, or one that neither names nor lines up with the headers:
        1, 2, 3 … as before — the only coding there is to go on."""

        assert _matrix(["A", "B"]).columns() == [(1, "A"), (2, "B")]
        assert _matrix(["A", "B"], {1: "x", 2: "y", 3: "z"}).columns() == [(1, "A"), (2, "B")]

    def test_a_header_named_twice_in_the_codebook_is_placed_by_position(self):
        matrix = _matrix(["Same", "Other"], {7: "Same", 8: "Same"})
        assert matrix.columns() == [(7, "Same"), (8, "Other")]
