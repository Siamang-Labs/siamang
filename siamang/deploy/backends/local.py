"""Local SQLite backend — same interface as cloud backends, no network."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from siamang.deploy.backend_config import BackendConfig
from siamang.deploy.base import BackendAdapter

if TYPE_CHECKING:
    from siamang.frontend.schema import SurveySchema


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS survey_meta (
    survey_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    schema_json TEXT NOT NULL,
    max_responses INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    survey_id TEXT NOT NULL REFERENCES survey_meta(survey_id),
    payload_json TEXT NOT NULL,
    submitted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_responses_survey ON responses(survey_id);

CREATE TABLE IF NOT EXISTS quota_counters (
    survey_id TEXT NOT NULL,
    variable TEXT NOT NULL,
    value TEXT NOT NULL,
    target INTEGER NOT NULL,
    current INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (survey_id, variable, value)
);
"""


def cell_values(value: Any) -> list[str]:
    """The ``quota_counters.value`` texts one answer fills: its JSON encoding,
    as :meth:`LocalBackend.provision` writes a cell's target (a whole float is
    the integer it equals — a runtime that posts ``2.0`` answered code 2); for
    a list, each value it holds, once. Nothing else fills a cell: a quota
    target is a single code."""

    out: dict[str, None] = {}
    for item in value if isinstance(value, list) else [value]:
        if item is None or isinstance(item, dict | list):
            continue
        if isinstance(item, float) and item.is_integer():
            item = int(item)
        out.setdefault(json.dumps(item))
    return list(out)


def quota_cells(
    payload: dict[str, Any], list_variables: set[str] | frozenset[str] = frozenset()
) -> list[tuple[str, str]]:
    """Every ``(variable, value)`` cell a response's answers fill; the
    runtime's own ``__`` keys (``__status``) fill none. A list fills the cell
    of each value it holds only for a variable answered with one
    (``list_variables``: an array ``MultiChoice``, a ``Ranking``); posted for
    any other variable it fills none — one submission must not take a place
    in every cell of a single-answer quota."""

    return [
        (variable, cell)
        for variable, value in payload.items()
        if isinstance(variable, str) and not variable.startswith("__")
        if not isinstance(value, list) or variable in list_variables
        for cell in cell_values(value)
    ]


def list_variables(schema: dict[str, Any]) -> set[str]:
    """The variables a compiled survey (``SurveySchema.to_dict()``) stores a
    list in: an array ``MultiChoice``'s and a ``Ranking``'s."""

    out: set[str] = set()
    for page in schema.get("pages") or []:
        for element in (page.get("elements") if isinstance(page, dict) else None) or []:
            if not isinstance(element, dict) or not isinstance(element.get("name"), str):
                continue
            kind = element.get("type")
            if kind == "ranking" or (
                kind == "checkbox" and element.get("multiChoiceMode", "array") != "wide"
            ):
                out.add(element["name"])
    return out


@dataclass(slots=True)
class LocalBackend(BackendAdapter):
    """SQLite-backed storage for the local deployment path.

    Resolves to ``./survey.db`` by default. Pass ``path`` to override.
    """

    name: str = "local"
    path: str | Path = "survey.db"
    _last_survey_id: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self._init_schema()

    @property
    def url(self) -> str:
        return f"sqlite:///{self.path}"

    def _init_schema(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as conn:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()

    def provision(self, schema: SurveySchema) -> BackendConfig:
        survey_id = uuid.uuid4().hex[:12]
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute(
                "INSERT INTO survey_meta (survey_id, title, schema_json, max_responses) VALUES (?, ?, ?, ?)",
                (
                    survey_id,
                    schema.title,
                    json.dumps(schema.to_dict(), ensure_ascii=False),
                    schema.max_responses,
                ),
            )
            for quota in schema.quotas:
                conn.execute(
                    "INSERT INTO quota_counters (survey_id, variable, value, target) VALUES (?, ?, ?, ?)",
                    (
                        survey_id,
                        quota["variable"],
                        json.dumps(quota["target_value"]),
                        quota["limit"],
                    ),
                )
            conn.commit()
        self._last_survey_id = survey_id
        return BackendConfig(
            backend=self.name,
            survey_id=survey_id,
            settings={"endpoint": "/responses", "quota_endpoint": "/quota-check"},
            internal={"backend_ref": self, "db_path": str(self.path)},
            dashboard_url=f"sqlite:///{self.path}",
        )

    def store_response(self, survey_id: str, payload: dict[str, Any]) -> int:
        """Store a submission. A completed one — anything but a screen-out
        (``__status: "screened_out"``) — also counts in every quota cell its
        answers fill, a list answer (a ``MultiChoice``) in the cell of each
        value it holds; the response and its counts are one transaction.
        Quota checks only look (:meth:`check_quota`), so a respondent who drops
        out or is screened out never takes a place."""

        with closing(sqlite3.connect(self.path)) as conn:
            cur = conn.execute(
                "INSERT INTO responses (survey_id, payload_json) VALUES (?, ?)",
                (survey_id, json.dumps(payload, ensure_ascii=False)),
            )
            if payload.get("__status") != "screened_out":
                # The survey's cells, looked up in a set: an answer posted with
                # thousands of values costs one pass, not a query per value.
                cells = {
                    (variable, value)
                    for variable, value in conn.execute(
                        "SELECT variable, value FROM quota_counters WHERE survey_id=?",
                        (survey_id,),
                    )
                }
                lists = self._list_variables(conn, survey_id) if cells else set()
                for variable, value in quota_cells(payload, lists):
                    if (variable, value) not in cells:
                        continue
                    conn.execute(
                        "UPDATE quota_counters SET current = current + 1 "
                        "WHERE survey_id=? AND variable=? AND value=?",
                        (survey_id, variable, value),
                    )
            conn.commit()
            return int(cur.lastrowid)

    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        """Whether the cell of ``value`` still has room; for a list, whether
        every value's cell has — a list for a variable not answered with one
        names no cell (see :func:`quota_cells`). It claims nothing — completed
        responses are counted when they are stored."""

        with closing(sqlite3.connect(self.path)) as conn:
            rows = conn.execute(
                "SELECT value, target, current FROM quota_counters WHERE survey_id=? AND variable=?",
                (survey_id, variable),
            ).fetchall()
            if not rows:
                return True
            if isinstance(value, list) and variable not in self._list_variables(conn, survey_id):
                return True
            wanted = set(cell_values(value))
            return not any(cell in wanted and current >= target for cell, target, current in rows)

    @staticmethod
    def _list_variables(conn: sqlite3.Connection, survey_id: str) -> set[str]:
        row = conn.execute(
            "SELECT schema_json FROM survey_meta WHERE survey_id=?", (survey_id,)
        ).fetchone()
        try:
            return list_variables(json.loads(row[0])) if row else set()
        except (TypeError, ValueError, AttributeError):
            return set()

    def increment_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        """Atomically check + increment a quota counter. Returns False when full.

        The local server no longer calls it: a check claimed a place for every
        respondent who reached it, screen-outs and drop-outs included.
        """

        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT target, current FROM quota_counters WHERE survey_id=? AND variable=? AND value=?",
                    (survey_id, variable, json.dumps(value)),
                ).fetchone()
                if row is None:
                    conn.commit()
                    return True
                target, current = row
                if current >= target:
                    conn.commit()
                    return False
                conn.execute(
                    "UPDATE quota_counters SET current = current + 1 WHERE survey_id=? AND variable=? AND value=?",
                    (survey_id, variable, json.dumps(value)),
                )
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise

    def get_responses(self, survey_id: str) -> pd.DataFrame:
        with closing(sqlite3.connect(self.path)) as conn:
            rows = conn.execute(
                "SELECT id, payload_json, submitted_at FROM responses WHERE survey_id=? ORDER BY id",
                (survey_id,),
            ).fetchall()
        if not rows:
            return pd.DataFrame()
        records = []
        for row_id, payload_json, submitted_at in rows:
            data = json.loads(payload_json)
            data["_response_id"] = row_id
            data["_submitted_at"] = submitted_at
            records.append(data)
        return pd.DataFrame(records)
