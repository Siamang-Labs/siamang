"""Supabase backend client — POSTs responses to the Supabase REST endpoint."""

from __future__ import annotations

import json

from siamang.frontend.client.base import BackendClientTemplate, ClientEnv


class SupabaseClientTemplate(BackendClientTemplate):
    name = "supabase"

    def render_env_js(self, env: ClientEnv) -> str:
        env_payload = {
            "transport": "supabase",
            "survey_id": env.survey_id,
            "url": env.settings["url"],
            "anon_key": env.settings["anon_key"],
            "table": env.settings.get("table", "responses"),
            "quota_function": env.settings.get("quota_function", "quota-check"),
        }
        return _TEMPLATE.replace("__ENV__", json.dumps(env_payload, ensure_ascii=False))


_TEMPLATE = """\
window.SIAMANG_ENV = __ENV__;
window.SIAMANG_TRANSPORTS = window.SIAMANG_TRANSPORTS || {};
window.SIAMANG_TRANSPORTS.supabase = {
  async submit(responses) {
    const env = window.SIAMANG_ENV;
    const url = env.url.replace(/\\/$/, "") + "/rest/v1/" + env.table;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": env.anon_key,
        "Authorization": "Bearer " + env.anon_key,
        "Prefer": "return=minimal",
      },
      body: JSON.stringify({
        survey_id: env.survey_id,
        data: responses,
      }),
    });
    if (!res.ok) {
      throw new Error("supabase submit failed: " + res.status);
    }
    return { ok: true };
  },
  async checkQuota(variable, value) {
    const env = window.SIAMANG_ENV;
    const url = env.url.replace(/\\/$/, "") + "/functions/v1/" + env.quota_function;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": env.anon_key,
        "Authorization": "Bearer " + env.anon_key,
      },
      body: JSON.stringify({ survey_id: env.survey_id, variable: variable, value: value }),
    });
    if (!res.ok) return { ok: false };
    return await res.json();
  }
};
"""
