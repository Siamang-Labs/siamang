# `siamang.deploy` — deployment pipeline reference

The `deploy` subpackage turns a `Questionnaire` into a publicly
reachable URL. It's pluggable: backends and frontends are registered
through Python entry points, and you can ship custom ones in a third-
party package.

```python
from siamang.deploy import (
    DeployPipeline, DeployResult, BackendConfig,
    BackendAdapter, FrontendAdapter,
    backend_factory, frontend_factory,
    list_backends, list_frontends,
)
```

The recommended entry point is `Questionnaire.deploy(...)`, which
takes care of compiling, provisioning, building, and publishing in one
call. Everything below is the machinery.

---

## High-level shape

```
Questionnaire.deploy(
    backend="supabase",          # name → BackendAdapter class via entry points
    frontend="vercel",           # name → FrontendAdapter class via entry points
    backend_kwargs={...},        # passed to the adapter's __init__
    frontend_kwargs={...},
    **options,                   # forwarded to compile_questionnaire
) → DeployResult
```

Internally:

```python
DeployPipeline(
    backend=BackendAdapter(...),
    frontend=FrontendAdapter(...),
    builder=FrontendBuilder(...),
).run(survey, options=options)
```

---

## `BackendAdapter` (abstract base)

```python
class BackendAdapter:
    name: str

    def provision(self, schema: SurveySchema) -> BackendConfig: ...
    def get_responses(self, survey_id: str) -> pd.DataFrame: ...
    def check_quota(self, survey_id: str, variable: str, value: Any) -> bool: ...
```

A backend is responsible for:

- **Provisioning** storage (tables, RLS policies, quota counters) and
  returning a `BackendConfig` whose `settings` are safe to embed in the
  client bundle.
- **Reading back** accumulated responses as a `pandas.DataFrame`.
- **Quota checks** — the frontend calls this before each submission;
  returns `True` if the cell still has capacity.

Subclasses may add behaviour-specific methods (e.g. `LocalBackend.
store_response`, `LocalBackend.increment_quota`).

---

## `BackendConfig`

```python
@dataclass(frozen=True, slots=True)
class BackendConfig:
    backend: str
    survey_id: str
    settings: dict[str, Any] = {}      # frontend-safe (URLs, anon keys)
    internal: dict[str, Any] = {}      # server-only secrets
    dashboard_url: str | None = None   # optional response dashboard URL
```

The boundary between server-only secrets (`internal`) and frontend-safe
config (`settings`). Only `settings` and `dashboard_url` ever cross
into the bundle.

---

## `FrontendAdapter` (abstract base)

```python
class FrontendAdapter:
    name: str

    def publish(self, bundle: SurveyBundle, config: BackendConfig) -> str: ...
```

A frontend receives the compiled `SurveyBundle` and the
`BackendConfig`, deploys the static files somewhere reachable, and
returns the public URL.

---

## Bundled backends

### `LocalBackend`

```python
@dataclass
class LocalBackend(BackendAdapter):
    name: str = "local"
    path: str | Path = "survey.db"     # SQLite file; parent dir auto-created
```

In-process SQLite store. `provision` creates three tables —
`survey_meta`, `responses`, `quota_counters`. Used by `siamang preview`
and `survey.deploy(backend="local")`.

Extra methods on top of the abstract base:

- `store_response(survey_id, payload)` — insert a response, return its
  row id.
- `increment_quota(survey_id, variable, value)` — atomic check-and-
  increment; returns `False` when the cell is full.

### `SupabaseBackend`

```python
@dataclass
class SupabaseBackend(BackendAdapter):
    name: str = "supabase"
    url: str = ""
    anon_key: str = ""
    service_key: str = ""
    table: str = "responses"           # base name; per-survey: responses_<survey_id>
    quota_function: str = "quota-check"
```

The `supabase` Python client comes pre-installed. Credentials fall back to
`SIAMANG_SUPABASE_URL`, `SIAMANG_SUPABASE_ANON_KEY`,
`SIAMANG_SUPABASE_SERVICE_KEY` if the kwargs are blank (legacy `SURVLIB_*`
names are also accepted). The constructor raises `ValueError` if any of the
three are still empty.

Data model:

- A single shared `responses` table with a `survey_id` column.
- RLS policies created at provision time so anon clients can `INSERT`
  but not `SELECT`.
- Quota counters live in a single `quota_counters` table updated by an
  Edge Function (named via `quota_function`).

Extra method: `get_all_responses(survey_id, page_size=1000)` —
auto-paginates through all responses.

---

## Bundled frontends

### `LocalFrontend`

```python
@dataclass
class LocalFrontend(FrontendAdapter):
    name: str = "local"
    host: str = "127.0.0.1"
    port: int = 0                  # 0 → pick a free port
    open_browser: bool = False
```

FastAPI + uvicorn come pre-installed. `publish(...)` starts a background
FastAPI server that serves the bundle and forwards
`POST /responses` and `POST /quota-check` to the backend. The thread
stays alive until you call `local_frontend.stop()` (the CLI's
`siamang preview` blocks the main thread until Ctrl+C and then stops).

### `VercelFrontend`

```python
@dataclass
class VercelFrontend(FrontendAdapter):
    name: str = "vercel"
    token: str = ""                # falls back to VERCEL_TOKEN env var
    team_id: str | None = None
    project_name: str = "siamang-survey"
```

`publish(...)` strategy:

1. If `token` is set, use the Vercel REST API to deploy.
2. Otherwise, if `npx vercel` is available, fall back to the CLI.
3. Otherwise, write the bundle to `.vercel_deploy_<survey_id>/` for
   manual deployment and return that local path.

In all branches it injects a strict `vercel.json`:

- `Content-Security-Policy`,
- `X-Frame-Options: DENY`,
- cache-control headers for hashed assets,
- analytics route when `UIConfig.enable_analytics=True`.

---

## `DeployPipeline`

```python
@dataclass(frozen=True, slots=True)
class DeployPipeline:
    backend: BackendAdapter
    frontend: FrontendAdapter
    builder: FrontendBuilder

    def run(
        self,
        survey: Questionnaire,
        *,
        options: dict[str, Any] | None = None,
    ) -> DeployResult: ...
```

The orchestrator. `run()`:

1. compiles the questionnaire to a `SurveySchema`;
2. calls `backend.provision(schema)` → `BackendConfig`;
3. selects the matching `BackendClientTemplate` (`LocalClientTemplate`
   or `SupabaseClientTemplate`); raises `NotImplementedError` for
   unknown backend names;
4. calls `builder.build(schema, client=..., env=..., survey=...)` →
   `SurveyBundle`;
5. calls `frontend.publish(bundle, config)` → URL;
6. returns a populated `DeployResult`.

---

## `DeployResult`

```python
@dataclass(frozen=True, slots=True)
class DeployResult:
    url: str
    backend: str
    frontend: str
    survey_id: str = ""
    dashboard: str | None = None
    deployed_at: datetime = datetime.now(timezone.utc)
    backend_ref: BackendAdapter | None = None
    frontend_ref: FrontendAdapter | None = None
    extras: dict[str, Any] = {}

    def collect(self) -> pd.DataFrame: ...
```

What you get back from `survey.deploy(...)`. `collect()` re-uses the
cached `backend_ref` to fetch accumulated responses as a DataFrame;
raises `RuntimeError` if the reference is missing (which only happens
when you construct a `DeployResult` by hand).

Typical use:

```python
result = survey.deploy(backend="supabase", frontend="vercel",
                       backend_kwargs={...}, frontend_kwargs={...})
print(result.url, result.dashboard)

# later — the cached backend_ref lets you collect without re-wiring
responses = result.collect()
data = sg.SurveyData(frame=responses, variables=survey.variables,
                     questionnaire=survey)
```

---

## Registry & entry points

```python
list_backends()   → ["local", "supabase", ...]
list_frontends()  → ["local", "vercel", ...]

cls = backend_factory("supabase")        # SupabaseBackend
cls = frontend_factory("vercel")         # VercelFrontend
```

Both functions look up names first in the `siamang.backends` /
`siamang.frontends` Python entry points (so third-party packages can
contribute adapters), then fall back to siamang's built-in registry.

Built-in entry points (declared in `pyproject.toml`):

```toml
[project.entry-points."siamang.backends"]
local    = "siamang.deploy.backends.local:LocalBackend"
supabase = "siamang.deploy.backends.supabase:SupabaseBackend"

[project.entry-points."siamang.frontends"]
local  = "siamang.deploy.frontends.local:LocalFrontend"
vercel = "siamang.deploy.frontends.vercel:VercelFrontend"
```

To ship a custom backend, register an entry point under the same
group from your own package and implement `BackendAdapter`. Same for
frontends.
