"""Local backend client — POSTs responses to the bundled FastAPI server."""

from __future__ import annotations

import json

from siamang.frontend.client.base import BackendClientTemplate, ClientEnv


class LocalClientTemplate(BackendClientTemplate):
    name = "local"

    def render_env_js(self, env: ClientEnv) -> str:
        env_payload = {
            "transport": "local",
            "survey_id": env.survey_id,
            "endpoint": env.settings.get("endpoint", "/responses"),
            "quota_endpoint": env.settings.get("quota_endpoint", "/quota-check"),
        }
        return _TEMPLATE.replace("__ENV__", json.dumps(env_payload, ensure_ascii=False))


_TEMPLATE = """\
window.SIAMANG_ENV = __ENV__;
window.SIAMANG_TRANSPORTS = window.SIAMANG_TRANSPORTS || {};
window.SIAMANG_TRANSPORTS.local = {
  async submit(responses) {
    const env = window.SIAMANG_ENV;
    const payload = { survey_id: env.survey_id, responses: responses };
    const res = await fetch(env.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error("submit failed: " + res.status);
    }
    return await res.json();
  },
  async checkQuota(variable, value) {
    const env = window.SIAMANG_ENV;
    const res = await fetch(env.quota_endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ survey_id: env.survey_id, variable: variable, value: value }),
    });
    if (!res.ok) return { ok: false };
    return await res.json();
  }
};
"""
