"""Supabase backend adapter — provisions response tables with RLS and migration support."""

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


_RESPONSES_TABLE = """
CREATE TABLE IF NOT EXISTS responses_{survey_id} (
    id BIGSERIAL PRIMARY KEY,
    data JSONB NOT NULL,
    variables JSONB,
    schema_hash TEXT,
    respondent_id UUID DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_RLS_POLICIES = """
ALTER TABLE responses_{survey_id} ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_insert_responses_{survey_id}" ON responses_{survey_id}
    FOR INSERT TO anon
    WITH CHECK (true);

CREATE POLICY "auth_select_responses_{survey_id}" ON responses_{survey_id}
    FOR SELECT TO authenticated
    USING (true);

CREATE POLICY "auth_delete_responses_{survey_id}" ON responses_{survey_id}
    FOR DELETE TO authenticated
    USING (true);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_responses_{survey_id}_created
    ON responses_{survey_id} (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_responses_{survey_id}_respondent
    ON responses_{survey_id} (respondent_id);
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
            "requests is required for the Supabase backend. Install with 'pip install siamang[supabase]'."
        ) from exc
    return requests.Session()


@dataclass(slots=True)
class SupabaseBackend(BackendAdapter):
    """Supabase storage backend with RLS policies and migration tracking."""

    name: str = "supabase"
    url: str = ""
    anon_key: str = ""
    service_key: str = ""
    table: str = "responses"
    quota_function: str = "quota-check"
    session: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.url = self.url or os.environ.get("SURVLIB_SUPABASE_URL", "")
        self.anon_key = self.anon_key or os.environ.get("SURVLIB_SUPABASE_ANON_KEY", "")
        self.service_key = self.service_key or os.environ.get(
            "SURVLIB_SUPABASE_SERVICE_KEY", ""
        )
        if not self.url:
            raise ValueError(
                "SupabaseBackend requires 'url' (or SURVLIB_SUPABASE_URL)."
            )
        if not self.anon_key:
            raise ValueError(
                "SupabaseBackend requires 'anon_key' (or SURVLIB_SUPABASE_ANON_KEY)."
            )
        if not self.service_key:
            raise ValueError(
                "SupabaseBackend requires 'service_key' (or SURVLIB_SUPABASE_SERVICE_KEY)."
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
        """Execute raw SQL via Supabase REST API (requires pg_net or exec_sql function)."""
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
        """Create/update Supabase tables with migration tracking and RLS."""
        survey_id = uuid.uuid4().hex[:12]
        variables = self._extract_variables(schema)
        schema_hash = _compute_schema_hash(survey_id, variables)

        dashboard_url = f"{self.url.rstrip('/')}/project/_/editor"

        # 1. Create survey_meta table with migration tracking
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

        # 2. Create per-survey responses table with RLS
        self._exec_sql(_RESPONSES_TABLE.format(survey_id=survey_id))
        self._exec_sql(_RLS_POLICIES.format(survey_id=survey_id))
        self._exec_sql(_INDEXES.format(survey_id=survey_id))

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
                    "schema_hash": schema_hash,
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
            (migrations / f"{timestamp}_provision_{survey_id}.sql").write_text(
                "-- Auto-generated by siamang deploy\n"
                f"-- Survey: {schema.title}\n"
                f"-- Survey ID: {survey_id}\n"
                f"-- Schema hash: {schema_hash}\n\n"
                f"{_RESPONSES_TABLE.format(survey_id=survey_id)}\n\n"
                f"{_RLS_POLICIES.format(survey_id=survey_id)}\n\n"
                f"{_INDEXES.format(survey_id=survey_id)}\n"
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

        # Try to extract data from JSONB column if present
        processed = []
        for r in rows:
            row = r.get("data", r)
            if isinstance(row, dict):
                row["_response_id"] = r.get("id", r.get("_response_id"))
                row["_respondent_id"] = r.get("respondent_id", r.get("_respondent_id"))
                row["_submitted_at"] = r.get("created_at", r.get("_submitted_at"))
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
