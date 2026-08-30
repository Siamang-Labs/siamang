# CLI reference

`siamang` ships with a single executable, `siamang`, that wraps the
public Python API. The `validate`, `preview`, and `deploy` subcommands
load the questionnaire from a `.py` file (looking for a module-level
attribute named `survey` by default; override with `--attribute`);
`init` only writes the config file.

```bash
siamang --help
siamang <subcommand> --help
```

Subcommands:

- [`validate`](#validate) — structural and lint checks
- [`preview`](#preview) — local React frontend on `http://127.0.0.1`
- [`deploy`](#deploy) — publish to a backend/frontend pair
- [`init`](#init) — create or update `~/.siamang.toml`

You can also run it via the module: `python -m siamang …`.

---

## `validate`

```bash
siamang validate PATH [--attribute ATTR] [--strict]
```

| Flag | Default | Description |
|------|---------|-------------|
| `PATH` | (required) | Path to a Python file exposing a `Questionnaire`. |
| `--attribute` | `survey` | Module-level attribute name to load. |
| `--strict` | off | Treat `lint(level="strict")` errors as failures. |

Runs `survey.validate(strict=...)`, validates the module-level `options` dict if
the module exports one (e.g. `quota=[Quota(...)]` — quotas are checked only
here), then prints every `lint()` finding. Exit codes:

| Code | Meaning |
|------|---------|
| 0 | Questionnaire is valid; no `error`-severity lint findings. |
| 1 | A printed lint finding had `error` severity. |
| 2 | `validate()` or the `options` check raised a `ValueError` (structural problem). |

`error`-severity lint rules only run at the strict level, and with `--strict`
they are promoted by `validate(strict=True)` into a `ValueError` first — so in
practice they surface as exit code 2, and exit code 1 is a reserved part of the
contract.

Example:

```bash
$ siamang validate my_survey.py
OK — no warnings.
```

---

## `preview`

```bash
siamang preview PATH [--attribute ATTR] [--port PORT] [--open] [--db DB]
```

| Flag | Default | Description |
|------|---------|-------------|
| `PATH` | (required) | Path to the questionnaire `.py` file. |
| `--attribute` | `survey` | Module-level attribute name. |
| `--port` | `8000` | Bind port for the local server. |
| `--open` | off | Open the survey in the default browser on startup. |
| `--db` | `survey.db` | SQLite file used by the local backend. |

Spins up a local FastAPI server with the React frontend and the SQLite
backend. The server binds all interfaces (`0.0.0.0`); open the survey at
`http://127.0.0.1:<port>`. Responses land in `--db`. Press Ctrl+C to stop.

Uses FastAPI + uvicorn (installed automatically with the package).

Example:

```bash
$ siamang preview my_survey.py --port 8000 --open
Preview ready at http://0.0.0.0:8000
  survey_id: 42a1c0e9d3f5
  dashboard: sqlite:///survey.db
  [react] sucrase + esbuild minify available — fast path
Press Ctrl+C to stop.
```

---

## `deploy`

```bash
siamang deploy PATH [--attribute ATTR]
                   [--backend NAME] [--frontend NAME]
                   [--profile PROFILE] [--config PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `PATH` | (required) | Path to the questionnaire `.py` file. |
| `--attribute` | `survey` | Module-level attribute name. |
| `--backend` | from config | Backend name (see `list_backends()`). |
| `--frontend` | from config | Frontend name (see `list_frontends()`). |
| `--profile` | (none) | Selects a `[profiles.<name>]` block in the config. |
| `--config` | `~/.siamang.toml` | Override config path. |

Loads `~/.siamang.toml` (or `--config`), resolves the backend and
frontend names, and runs the full pipeline. Backend and frontend
credentials come from the config file (created by `siamang init`).

Typical config (a TOML file written by `siamang init`):

```toml
[defaults]
backend  = "supabase"
frontend = "vercel"

[backends.supabase]
url         = "https://abcdef.supabase.co"
anon_key    = "..."
service_key = "..."

[frontends.vercel]
token        = "..."
project_name = "political-trust-2026"
```

Example:

```bash
$ siamang deploy my_survey.py
Deployed: https://political-trust-2026.vercel.app
  survey_id: 42a1c0e9d3f5
  backend:   supabase
  frontend:  vercel
  dashboard: https://abcdef.supabase.co/project/_/editor
```

---

## `init`

```bash
siamang init [--path PATH] [--non-interactive]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--path` | `~/.siamang.toml` | Where to write the config. |
| `--non-interactive` | off | Use defaults (`backend="local"`, `frontend="local"`); skip prompts. |

Interactive walkthrough that asks for backend/frontend choice and
credentials, then writes the config with `chmod 600`.

---

## Configuration file format

The loader recognises four top-level tables: `[defaults]` (default
backend/frontend names, used when `--profile` isn't passed),
`[backends.<name>]` and `[frontends.<name>]` (kwargs forwarded to the
matching adapter constructor), and `[profiles.<name>]` (named overrides
of `[defaults]`, selected with `--profile`).

```toml
# ~/.siamang.toml

# Defaults — used when --profile isn't passed
[defaults]
backend  = "local"            # or "supabase"
frontend = "local"            # or "vercel"

# Anything under [backends.<name>] is forwarded to that backend's
# adapter constructor. Same for [frontends.<name>]. (`siamang deploy`
# does not pass kwargs to the `local` backend/frontend.)
[backends.supabase]
url         = "https://abcdef.supabase.co"
anon_key    = "eyJ..."
service_key = "eyJ..."

[frontends.vercel]
token        = "vercel-token-..."
project_name = "political-trust-2026"

# A profile, selected with `--profile production` — keys override [defaults]
[profiles.production]
backend  = "supabase"
frontend = "vercel"
```

Backend kwargs are also overridable via environment variables:

| Variable | Read by | Notes |
|----------|---------|-------|
| `SIAMANG_SUPABASE_URL` | `SupabaseBackend.url` | Canonical |
| `SIAMANG_SUPABASE_ANON_KEY` | `SupabaseBackend.anon_key` | Canonical |
| `SIAMANG_SUPABASE_SERVICE_KEY` | `SupabaseBackend.service_key` | Canonical |
| `SURVLIB_SUPABASE_URL` | `SupabaseBackend.url` | Legacy fallback |
| `SURVLIB_SUPABASE_ANON_KEY` | `SupabaseBackend.anon_key` | Legacy fallback |
| `SURVLIB_SUPABASE_SERVICE_KEY` | `SupabaseBackend.service_key` | Legacy fallback |
| `VERCEL_TOKEN` | `VercelFrontend.token` | Read directly by the adapter, only when `token` isn't set in the config |
