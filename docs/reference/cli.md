# CLI reference

`siamang` ships with a single executable, `siamang`, that wraps the
public Python API. Every subcommand loads the questionnaire from a
`.py` file (looking for a module-level attribute named `survey` by
default; override with `--attribute`).

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

Runs `survey.validate()` and prints any issues. Exit codes:

| Code | Meaning |
|------|---------|
| 0 | Questionnaire is valid (and lint clean if `--strict`). |
| 1 | Lint reported an `error`-severity warning (only when `--strict`). |
| 2 | `validate()` raised a `ValueError` (structural problem). |

Example:

```bash
$ siamang validate my_survey.py
OK: Questionnaire<Political Trust — 2026> with 5 questions
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
backend. The survey is reachable at `http://127.0.0.1:<port>`. Responses
land in `--db`. Press Ctrl+C to stop.

Uses FastAPI + uvicorn (installed automatically with the package).

Example:

```bash
$ siamang preview my_survey.py --port 8000 --open
Preview server: http://127.0.0.1:8000
SQLite db:      survey.db
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
| `--profile` | `default` | Selects a `[profile.<name>]` block in the config. |
| `--config` | `~/.siamang.toml` | Override config path. |

Loads `~/.siamang.toml` (or `--config`), resolves the backend and
frontend names, and runs the full pipeline. Backend and frontend
credentials come from the config file (created by `siamang init`).

Typical config (a TOML file written by `siamang init`):

```toml
[profile.default]
backend  = "supabase"
frontend = "vercel"

[profile.default.backend_kwargs]
url         = "https://abcdef.supabase.co"
anon_key    = "..."
service_key = "..."

[profile.default.frontend_kwargs]
token        = "..."
project_name = "political-trust-2026"
```

Example:

```bash
$ siamang deploy my_survey.py
URL:       https://political-trust-2026.vercel.app
Survey id: 42a1c0e9
Backend:   supabase
Frontend:  vercel
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

```toml
# ~/.siamang.toml

# Default profile — used when --profile isn't passed
[profile.default]
backend  = "local"            # or "supabase"
frontend = "local"            # or "vercel"

# Anything under <profile>.backend_kwargs is forwarded to the backend's
# adapter constructor. Same for frontend_kwargs.
[profile.default.backend_kwargs]
path = "preview.db"

[profile.default.frontend_kwargs]
host = "127.0.0.1"
port = 8000

# A different profile, selected with `--profile production`
[profile.production]
backend  = "supabase"
frontend = "vercel"

[profile.production.backend_kwargs]
url         = "https://abcdef.supabase.co"
anon_key    = "eyJ..."
service_key = "eyJ..."

[profile.production.frontend_kwargs]
token        = "vercel-token-..."
project_name = "political-trust-2026"
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
| `VERCEL_TOKEN` | `VercelFrontend.token` | |
