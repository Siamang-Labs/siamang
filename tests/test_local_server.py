"""The local server's quota endpoint only looks; completed responses count.

`/quota-check` used to answer with `LocalBackend.increment_quota`, which
claimed a place in the cell for every respondent whose answer was checked —
those who dropped out afterwards or were screened out included — so cells
filled with people who never completed. A check now only reads the counter,
and `store_response` counts a completed response in every cell it fills.
"""

from __future__ import annotations

import sqlite3
import warnings
from contextlib import closing
from types import SimpleNamespace

import pytest

import siamang as sg
from siamang.core import Quota
from siamang.deploy.backends.local import LocalBackend
from siamang.deploy.frontends.local import build_app
from siamang.frontend.compiler import compile_questionnaire

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient


def _survey() -> sg.Questionnaire:
    gender = sg.Variable("gender", scale="nominal", labels={1: "Man", 2: "Woman"})
    brands = sg.Variable("brands", scale="nominal", labels={1: "A", 2: "B", 3: "C"})
    return sg.Questionnaire(
        title="Quotas",
        pages=[
            sg.Page(
                name="p1",
                items=[sg.SingleChoice("Gender?", var=gender), sg.MultiChoice("Brands?", brands)],
            )
        ],
    )


@pytest.fixture
def server(tmp_path):
    quotas = [
        Quota("gender", 1, limit=1),
        Quota("gender", 2, limit=2),
        Quota("brands", 1, limit=1),
        Quota("brands", 2, limit=2),
    ]
    schema = compile_questionnaire(_survey(), options={"quota": quotas})
    backend = LocalBackend(path=tmp_path / "survey.db")
    survey_id = backend.provision(schema).survey_id
    bundle = SimpleNamespace(files={"index.html": "<!doctype html>"})
    client = TestClient(build_app(bundle, backend, survey_id))

    def check(variable, value):
        response = client.post("/quota-check", json={"variable": variable, "value": value})
        assert response.status_code == 200
        return response.json()["ok"]

    def submit(answers):
        response = client.post("/responses", json={"responses": answers})
        assert response.status_code == 200

    def counts():
        with closing(sqlite3.connect(backend.path)) as conn:
            rows = conn.execute("SELECT variable, value, current FROM quota_counters").fetchall()
        return {(variable, value): current for variable, value, current in rows}

    return SimpleNamespace(check=check, submit=submit, counts=counts)


def test_a_check_takes_no_place(server):
    for _ in range(3):
        assert server.check("gender", 1) is True
    assert set(server.counts().values()) == {0}


def test_a_completed_response_counts_and_a_screen_out_does_not(server):
    server.submit({"gender": 1, "__status": "screened_out"})
    assert server.counts()[("gender", "1")] == 0
    assert server.check("gender", 1) is True
    # A survey finished on its last question page sends no __status; one
    # ended on a final page sends "completed". Both are completes.
    server.submit({"gender": 1.0})
    server.submit({"gender": 2, "__status": "completed"})
    assert server.counts()[("gender", "1")] == 1
    assert server.counts()[("gender", "2")] == 1
    assert server.check("gender", 1) is False
    assert server.check("gender", 2) is True


def test_a_list_answer_counts_in_every_cell_it_holds_and_is_full_when_any_is(server):
    server.submit({"brands": [1, 2, 2]})
    assert server.counts()[("brands", "1")] == 1
    assert server.counts()[("brands", "2")] == 1
    assert server.check("brands", [2, 3]) is True
    assert server.check("brands", [3, 1]) is False
    # A value no cell names is never full.
    assert server.check("brands", 3) is True
