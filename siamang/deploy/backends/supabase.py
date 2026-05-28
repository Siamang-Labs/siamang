"""Supabase backend adapter — provisions response storage with RLS and migration support."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from siamang.deploy.backend_config import BackendConfig
from siamang.deploy.base import BackendAdapter

if TYPE_CHECKING:
    import pandas as pd

    from siamang.frontend.schema import SurveySchema


# --------------------------------------------------------------------------
# Schema: single shared table `responses` with survey_id column.
# This mirrors the local SQLite backend model for consistency.
# --------------------------------------------------------------------------

_RESPONSES_TABLE = """
CREATE TABLE IF NOT EXISTS responses (
    id BIGSERIAL PRIMARY KEY,
    survey_id TEXT NOT NULL,
    data JSONB NOT NULL,
    respondent_id UUID DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_RLS_POLICIES = """
ALTER TABLE responses ENABLE ROW LEVEL SECURITY;

-- Anon users can only INSERT their own responses
CREATE POLICY "anon_insert_responses" ON responses
    FOR INSERT TO anon
    WITH CHECK (true);

-- Authenticated users can read all responses
CREATE POLICY "auth_select_responses" ON responses
    FOR SELECT TO authenticated
    USING (true);

-- Authenticated users can delete responses
CREATE POLICY "auth_delete_responses" ON responses
    FOR DELETE TO authenticated
    USING (true);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_responses_survey_id
    ON responses (survey_id);
CREATE INDEX IF NOT EXISTS idx_responses_created
    ON responses (survey_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_responses_respondent
    ON responses (respondent_id);
"""

_SURVEY_META_TABLE = """
CREATE TABLE IF NOT EXISTS survey_meta (
    id BIGSERIAL PRIMARY KEY,
    survey_id TEXT UNIQUE NOT NULL,
    title TEXT,
    schema_json JSONB,
    max_responses INTEGER,
    schema_hash TEXT,
    variables_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_QUOTA_TABLE = """
CREATE TABLE IF NOT EXISTS quota_counters (
    id BIGSERIAL PRIMARY KEY,
    survey_id TEXT NOT NULL,
    variable TEXT NOT NULL,
    value TEXT NOT NULL,
    target INTEGER NOT NULL,
    current INTEGER NOT NULL DEFAULT 0,
    UNIQUE (survey_id, variable, value)
);
"""


def _compute_schema_hash(survey_id: str, variables: list[dict[str, Any]]) -> str:
    """Compute a hash of the variable schema for migration tracking."""
    payload = json.dumps(variables, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _default_session() -> Any:
    try:
        import requests
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "requests is required for the Supabase backend. "
            "Install with: pip install requests"
        ) from exc
    return requests.Session()


def _get_env(new_name: str, legacy_name: str, default: str = "") -> str:
    """Read env var with fallback to legacy SURVLIB_* name."""
    return os.environ.get(new_name, os.environ.get(legacy_name, default))


@dataclass(slots=True)
class SupabaseBackend(BackendAdapter):
    """Supabase storage backend with RLS policies and migration tracking.

    Uses a single shared ``responses`` table with a ``survey_id`` column,
    mirroring the local SQLite backend model for consistency.

    Environment variables (with legacy fallback):
        SIAMANG_SUPABASE_URL (fallback: SURVLIB_SUPABASE_URL)
        SIAMANG_SUPABASE_ANON_KEY (fallback: SURVLIB_SUPABASE_ANON_KEY)
        SIAMANG_SUPABASE_SERVICE_KEY (fallback: SURVLIB_SUPABASE_SERVICE_KEY)
    """

    name: str = "supabase"
    url: str = ""
    anon_key: str = ""
    service_key: str = ""
    table: str = "responses"
    quota_function: str = "quota-check"
    session: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.url = self.url or _get_env(
            "SIAMANG_SUPABASE_URL", "SURVLIB_SUPABASE_URL"
        )
        self.anon_key = self.anon_key or _get_env(
            "SIAMANG_SUPABASE_ANON_KEY", "SURVLIB_SUPABASE_ANON_KEY"
        )
        self.service_key = self.service_key or _get_env(
            "SIAMANG_SUPABASE_SERVICE_KEY", "SURVLIB_SUPABASE_SERVICE_KEY"
        )
        if not self.url:
            raise ValueError(
                "SupabaseBackend requires 'url' "
                "(or env SIAMANG_SUPABASE_URL / SURVLIB_SUPABASE_URL)."
            )
        if not self.anon_key:
            raise ValueError(
                "SupabaseBackend requires 'anon_key' "
                "(or env SIAMANG_SUPABASE_ANON_KEY / SURVLIB_SUPABASE_ANON_KEY)."
            )
        if not self.service_key:
            raise ValueError(
                "SupabaseBackend requires 'service_key' "
                "(or env SIAMANG_SUPABASE_SERVICE_KEY / SURVLIB_SUPABASE_SERVICE_KEY)."
            )
        if self.session is None:
            self.session = _default_session()

    def _admin_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
        }

    def _table_url(self) -> str:
        return f"{self.url.rstrip('/')}/rest/v1/{self.table}"

    def _exec_sql(self, query: str) -> bool:
        """Execute raw SQL via Supabase REST API (requires exec_sql RPC function)."""
        try:
            rpc_url = f"{self.url.rstrip('/')}/rest/v1/rpc/exec_sql"
            response = self.session.post(
                rpc_url,
                headers=self._admin_headers(),
                data=json.dumps({"query": query}),
                timeout=30,
            )
            return response.status_code in (200, 201, 204)
        except Exception:
            return False

    def _extract_variables(self, schema: "SurveySchema") -> list[dict[str, Any]]:
        """Extract variable definitions from survey schema for migration tracking."""
        data = schema.to_dict()
        return data.get("variables", [])

    def provision(
        self, schema: "SurveySchema", migration_dir: str | None = None
    ) -> BackendConfig:
        """Create/update Supabase tables with migration tracking and RLS.

        Creates a shared ``responses`` table (if not exists), registers the
        survey in ``survey_meta``, and sets up quota counters.
        """
        survey_id = uuid.uuid4().hex[:12]
        variables = self._extract_variables(schema)
        schema_hash = _compute_schema_hash(survey_id, variables)

        dashboard_url = f"{self.url.rstrip('/')}/project/_/editor"

        # 1. Ensure shared tables exist
        self._exec_sql(_SURVEY_META_TABLE)
        self._exec_sql(_RESPONSES_TABLE)
        self._exec_sql(_RLS_POLICIES)
        self._exec_sql(_INDEXES)
        self._exec_sql(_QUOTA_TABLE)

        # 2. Register survey in survey_meta
        meta_url = f"{self.url.rstrip('/')}/rest/v1/survey_meta"
        meta_payload = {
            "survey_id": survey_id,
            "title": schema.title,
            "schema_json": json.dumps(schema.to_dict(), ensure_ascii=False),
            "max_responses": schema.max_responses,
            "schema_hash": schema_hash,
            "variables_json": json.dumps(variables, ensure_ascii=False),
        }
        response = self.session.post(
            meta_url,
            headers=self._admin_headers() | {"Prefer": "return=minimal"},
            data=json.dumps(meta_payload),
        )
        response.raise_for_status()

        # 3. Create quota_counters if needed
        if schema.quotas:
            quota_url = f"{self.url.rstrip('/')}/rest/v1/quota_counters"
            quota_rows = [
                {
                    "survey_id": survey_id,
                    "variable": quota["variable"],
                    "value": json.dumps(quota["target_value"]),
                    "target": quota["limit"],
                    "current": 0,
                }
                for quota in schema.quotas
            ]
            response = self.session.post(
                quota_url,
                headers=self._admin_headers() | {"Prefer": "return=minimal"},
                data=json.dumps(quota_rows),
            )
            response.raise_for_status()

        # 4. Export migration SQL if requested
        if migration_dir:
            from pathlib import Path

            migrations = Path(migration_dir)
            migrations.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            migration_sql = (
                "-- Auto-generated by siamang deploy\n"
                f"-- Survey: {schema.title}\n"
                f"-- Survey ID: {survey_id}\n"
                f"-- Schema hash: {schema_hash}\n\n"
                f"{_SURVEY_META_TABLE}\n\n"
                f"{_RESPONSES_TABLE}\n\n"
                f"{_RLS_POLICIES}\n\n"
                f"{_INDEXES}\n\n"
                f"{_QUOTA_TABLE}\n"
            )
            (migrations / f"{timestamp}_provision_{survey_id}.sql").write_text(
                migration_sql
            )

        return BackendConfig(
            backend=self.name,
            survey_id=survey_id,
            settings={
                "url": self.url,
                "anon_key": self.anon_key,
                "table": self.table,
                "quota_function": self.quota_function,
                "schema_hash": schema_hash,
            },
            dashboard_url=dashboard_url,
        )

    def get_responses(
        self,
        survey_id: str,
        *,
        limit: int = 1000,
        offset: int = 0,
    ) -> "pd.DataFrame":
        """Fetch responses for a specific survey from the shared table."""
        import pandas as pd

        params = {
            "survey_id": f"eq.{survey_id}",
            "select": "*",
            "limit": str(limit),
            "offset": str(offset),
            "order": "created_at.desc",
        }
        response = self.session.get(
            self._table_url(), headers=self._admin_headers(), params=params
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return pd.DataFrame()

        processed = []
        for r in rows:
            row = r.get("data", r)
            if isinstance(row, dict):
                row["_response_id"] = r.get("id")
                row["_respondent_id"] = r.get("respondent_id")
                row["_submitted_at"] = r.get("created_at")
            processed.append(row)

        return pd.json_normalize(processed)

    def get_all_responses(
        self, survey_id: str, page_size: int = 1000
    ) -> "pd.DataFrame":
        """Fetch all responses with pagination."""
        import pandas as pd

        all_frames = []
        offset = 0
        while True:
            df = self.get_responses(survey_id, limit=page_size, offset=offset)
            if df.empty:
                break
            all_frames.append(df)
            offset += page_size
            if len(df) < page_size:
                break

        if not all_frames:
            return pd.DataFrame()
        return pd.concat(all_frames, ignore_index=True)

    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool:
        """Check if a quota is still open for the given variable/value."""
        quota_url = f"{self.url.rstrip('/')}/rest/v1/quota_counters"
        params = {
            "survey_id": f"eq.{survey_id}",
            "variable": f"eq.{variable}",
            "value": f"eq.{json.dumps(value)}",
            "select": "target,current",
        }
        response = self.session.get(
            quota_url, headers=self._admin_headers(), params=params
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            return True
        row = rows[0]
        return int(row["current"]) < int(row["target"])
