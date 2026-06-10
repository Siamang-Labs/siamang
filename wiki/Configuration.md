# Configuration

siamang reads deployment settings from `~/.siamang.toml`. It holds your default
backend/frontend, per-adapter credentials, and named profiles. The
`siamang.config` module loads, validates, and saves this file, applies environment
overrides, and warns when the file's permissions would leak secrets.

```python
from siamang.config import Config, load, save, use_profile, current, ConfigError
```

Create the file once with [`siamang init`](CLI-Reference#init); the
[`siamang deploy`](CLI-Reference#deploy) command reads it on every run.

---

## File format

The loader recognises four top-level tables. `[defaults]` names the default
backend/frontend; `[backends.<name>]` and `[frontends.<name>]` carry the kwargs
forwarded to each adapter's constructor; `[profiles.<name>]` are named overrides of
`[defaults]`.

```toml
# ~/.siamang.toml

[defaults]
backend  = "local"
frontend = "local"

# Adapter kwargs — forwarded to the backend/frontend constructor.
[backends.supabase]
url         = "https://abcdef.supabase.co"
anon_key    = "eyJ..."
service_key = "eyJ..."

[frontends.vercel]
token        = "vercel-token-..."
project_name = "political-trust-2026"

# A named profile, selected with `siamang deploy --profile production`.
# Keys here override [defaults].
[profiles.production]
backend  = "supabase"
frontend = "vercel"
```

> The `local` backend and `local` frontend take no kwargs, so a minimal config is
> just `[defaults]` with both set to `"local"` — which is exactly what
> `siamang init --non-interactive` writes.

---

## The `Config` object

```python
@dataclass(frozen=True, slots=True)
class Config:
    defaults:  dict[str, Any]
    backends:  dict[str, dict[str, Any]]
    frontends: dict[str, dict[str, Any]]
    profiles:  dict[str, dict[str, Any]]
    path:      Path | None
```

`Config` is the in-memory representation of the TOML file. Its methods:

| Method | Returns | Description |
| :--- | :--- | :--- |
| `default_backend()` | `str` | `defaults["backend"]` or `"local"`. |
| `default_frontend()` | `str` | `defaults["frontend"]` or `"local"`. |
| `backend(name)` | `dict` | Kwargs for a backend; raises `ConfigError` if unconfigured. |
| `frontend(name)` | `dict` | Kwargs for a frontend; raises `ConfigError` if unconfigured. |
| `with_profile(name)` | `Config` | A copy with `[profiles.name]` merged over `defaults`; raises `ConfigError` if undefined. |
| `to_toml()` | `str` | Serialise back to TOML. |

```python
from siamang.config import load

cfg = load()                          # ~/.siamang.toml
cfg.default_backend()                 # "local"
prod = cfg.with_profile("production") # merged defaults
prod.default_backend()                # "supabase"
cfg.backend("supabase")               # {"url": ..., "anon_key": ..., "service_key": ...}
```

---

## Module functions

```python
from siamang.config import load, save, use_profile, current
```

| Function | Description |
| :--- | :--- |
| `load(path="~/.siamang.toml")` | Read and parse the file, apply env overrides, and set it as the active config. A missing file yields an empty `Config` (no error). |
| `current()` | The active `Config` (set by the last `load`/`use_profile`), or an empty one. |
| `use_profile(name)` | Switch the active config to `current().with_profile(name)`. |
| `save(config, path=None)` | Write `config` to disk as TOML, creating parent dirs and applying `chmod 600`. Returns the `Path`. |

```python
from siamang.config import Config, save

cfg = Config(
    defaults={"backend": "supabase", "frontend": "vercel"},
    backends={"supabase": {"url": "...", "anon_key": "...", "service_key": "..."}},
    frontends={"vercel": {"token": "...", "project_name": "wave-4"}},
)
save(cfg, "~/.siamang.toml")          # chmod 600 applied
```

---

## Environment overrides

When `load()` parses the file, it overlays values from environment variables onto
the matching adapter kwargs. Prefixes map to an adapter, and the remainder of the
variable name (lowercased) becomes the kwarg key — so `SIAMANG_SUPABASE_URL` sets
`backends.supabase["url"]`. Both the canonical `SIAMANG_*` and the legacy `SURVLIB_*`
prefixes are recognised.

| Prefix | Target |
| :--- | :--- |
| `SIAMANG_SUPABASE_*` | `backends.supabase` |
| `SIAMANG_GSHEETS_*` | `backends.gsheets` |
| `SIAMANG_VERCEL_*` | `frontends.vercel` |
| `SIAMANG_NETLIFY_*` | `frontends.netlify` |
| `SURVLIB_*` (same suffixes) | Legacy fallback for each of the above |

```bash
export SIAMANG_SUPABASE_URL="https://abcdef.supabase.co"
export SIAMANG_SUPABASE_ANON_KEY="eyJ..."
export SIAMANG_SUPABASE_SERVICE_KEY="eyJ..."
export SIAMANG_GSHEETS_CREDENTIALS_FILE="./service-account.json"
```

Some adapters also read environment variables **directly** (independently of the
config loader) when their kwargs are blank — notably `VERCEL_TOKEN` for
`VercelFrontend` and `NETLIFY_AUTH_TOKEN` for `NetlifyFrontend`. This lets you keep
tokens out of the file entirely (ideal for CI). See [[Deployment]] for per-adapter
details.

---

## Profiles

Profiles let one config carry several deployment targets. Each `[profiles.<name>]`
block overrides the `[defaults]` table; the adapter credential blocks are shared.

```toml
[defaults]
backend  = "local"
frontend = "local"

[profiles.staging]
backend  = "supabase"
frontend = "netlify"

[profiles.production]
backend  = "supabase"
frontend = "vercel"
```

```bash
siamang deploy survey.py --profile production
```

```python
from siamang.config import load, use_profile

load()
cfg = use_profile("staging")
cfg.default_frontend()   # "netlify"
```

---

## Secrets and permissions

Because the file holds API tokens and service keys, `load()` calls
`check_permissions(path)` on POSIX systems and logs a warning if the file is group-
or world-accessible (any of the `0o077` bits set), suggesting `chmod 600`. `save()`
and `siamang init` set `0o600` for you.

```python
from siamang.config import check_permissions
from pathlib import Path

check_permissions(Path("~/.siamang.toml").expanduser())
# -> True if mode is 0600-clean; otherwise logs a warning and returns False
```

Keep secrets out of version control: prefer environment variables (`VERCEL_TOKEN`,
`SIAMANG_SUPABASE_*`) for CI, and reserve the file for your local machine with
`chmod 600`.

---

See also: [[CLI Reference|CLI-Reference]] · [[Deployment]] ·
[[Frontend and Theming|Frontend-and-Theming]] ·
[[API Reference Index|API-Reference-Index]]
