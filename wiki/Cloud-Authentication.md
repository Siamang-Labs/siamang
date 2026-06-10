# Cloud Authentication

siamang Cloud authenticates callers with bearer tokens behind a provider-agnostic
seam, authorizes actions with scoped roles, and isolates tenant data with
PostgreSQL Row-Level Security. This page covers the auth model, the auth
endpoints, API keys, the multi-tenant RLS model, roles, and SSO.

## The auth model

Every request (outside Health, the public Auth routes, the public Ingest API, and
the Gitea push webhook) carries `Authorization: Bearer <token>`. A raw bearer is
turned into a verified `Identity` by a **verifier** chosen from config
(`auth_provider`), then mapped onto a platform `User`:

- **`dev`** — a platform-issued HS256 JWT whose `sub` is the internal user id.
  This is the localhost / email+password path. JWTs are signed with `JWT_SECRET`,
  carry a `jti` (for revocation) and an `exp`, and live for `JWT_TTL_MINUTES`
  (default 720). The user is resolved directly by id.
- **`supabase`** — a Supabase-issued JWT (e.g. Google/GitHub/GitLab logins),
  validated with either a shared HS256 secret or asymmetric JWKS keys. The user
  is found-or-created by `(oauth_provider, oauth_sub)`, then linked by email, and
  lazily mirrored into Gitea. This path is wired in the Service Integration stage;
  until then the Supabase config stays empty and the verifier is never
  constructed.

A bearer that starts with `sck_` is treated as a personal API key and resolves
straight to its owning user (see below).

> The dev provider refuses to start in a client-facing config with a forgeable or
> weak secret: `assert_secure_config()` requires a strong `JWT_SECRET` (>= 32
> chars, not the dev default), a `FERNET_KEY`, and a non-default
> `GIT_WEBHOOK_SECRET`.

## Auth endpoints

Prefix `/auth`. Token, register, and redeem are public; the rest need a bearer.

| Method & path | Purpose |
| :--- | :--- |
| `POST /auth/register` | Create an account `{email, name, password}`; mirrors the user into Gitea |
| `POST /auth/token` | Exchange `{email, password}` for `{access_token, token_type}` |
| `POST /auth/password` | Change the signed-in user's password (verifies the current one) |
| `POST /auth/check-email` | Public probe: does an account exist for an email? |
| `POST /auth/logout` | Revoke the presented token (its `jti` goes on a Redis denylist for its TTL) |
| `POST /auth/redeem` | Redeem an invite code into a fresh trial org and auto-login |
| `GET /auth/me` | The current user plus their memberships |

```bash
curl -X POST http://localhost:8000/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"email":"pm@agency.com","password":"correct horse"}'
```

```json
{"access_token": "eyJhbGciOi...", "token_type": "bearer"}
```

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me
```

Passwords are hashed with bcrypt (passlib). `/auth/token` and `/auth/register`
are rate-limited per client IP + email to deter brute-forcing and enumeration;
`/auth/redeem` is rate-limited per client IP.

## API keys

Personal API keys give programmatic access (CI, scripts) without a JWT. A key is
shown **once** at creation as `sck_<random>`; only its SHA-256 hash is stored
(with a short display prefix). Present it as a bearer exactly like a JWT.

| Method & path | Purpose |
| :--- | :--- |
| `POST /auth/api-keys` | Create a key `{name, expires_days?}` → returns `token` once |
| `GET /auth/api-keys` | List the caller's keys (prefix + metadata, never the secret) |
| `DELETE /auth/api-keys/{key_id}` | Revoke a key |

```bash
curl -X POST http://localhost:8000/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"ci","expires_days":90}'
# → {"id":3,"name":"ci","token_prefix":"sck_xxxxxx","token":"sck_...","revoked":false, ...}

curl -H "Authorization: Bearer sck_..." http://localhost:8000/orgs
```

A key is rejected once it is revoked or past its `expires_at`.

## Multi-tenant RLS model

Authorization and data isolation are two independent layers:

1. **Org context per request.** Each request runs inside a single transaction.
   After resolving the caller's organization (directly for org routes, or via a
   `SECURITY DEFINER` function that maps a project to its org), the API issues
   `SET LOCAL app.current_org = <org_id>` for that transaction.
2. **Row-Level Security.** Every platform table with an `org_id` column has RLS
   enabled with a policy of the form
   `org_id = current_setting('app.current_org')::bigint`. Even if an
   application-level check is missed, Postgres will not return another tenant's
   rows.

```sql
-- set once per request, after authentication
SELECT set_config('app.current_org', '1', true);   -- true = LOCAL (this txn only)
```

`require_role(...)` is authorization *by action*; RLS is isolation *by data*. For
a self-hosted single-tenant install the policies stay in place but
`app.current_org` always points at the one organization.

Project data lives in a separate schema (`project_<id>`), and the analysis
sandbox connects with a Postgres role scoped to a single schema, so a leaked
token still cannot read another project's data.

## Scoped roles

The canonical product roles are **`owner` > `admin` > `member`**; older
fine-grained roles map onto the same rank scale so existing code and memberships
keep working. `role_at_least(role, minimum)` compares ranks:

| Role | Rank | Can (cumulatively) |
| :--- | :--- | :--- |
| `viewer` | 0 | Read everything |
| `analyst` | 1 | Run analysis scripts; write to data tables |
| `member` / `developer` | 2 | Push code; create/stop deployments; edit the repo; manage secrets/mirrors |
| `admin` / `manager` | 3 | Invite members; create/delete projects; branch protection |
| `owner` | 4 | Billing; change org type; SSO config |

Some examples from the routers: editing repository files requires `developer`;
creating a deployment requires `developer`; running an analysis script requires
`analyst`; inviting members requires `admin`; setting the plan, billing, and SSO
require `owner`. Ownership is never granted through an invite (no admin → owner
self-escalation, no second owner).

Git access mirrors the role: `member`+ get write access to the project's Gitea
repo, viewers get read-only.

## SSO (OIDC / SAML)

Enterprise SSO is a Pro/Corporate feature (`FEATURE_SSO`). The platform stores a
per-organization SSO configuration; the actual login/verification flow plugs into
the same verifier seam in the Service Integration stage.

| Method & path | Auth | Purpose |
| :--- | :--- | :--- |
| `GET /orgs/{org}/sso` | admin | Read the org's SSO config + whether the feature is available on its plan |
| `PUT /orgs/{org}/sso` | owner | Set the config (`provider` is `oidc` or `saml`) |

```bash
curl -X PUT http://localhost:8000/orgs/agency/sso \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"provider":"oidc","enabled":true,"issuer":"https://idp.example.com","client_id":"siamang"}'
```

The config fields are `provider`, `enabled`, `issuer`, `client_id`, and
`metadata_url` (the relevant subset per provider). The matching server-side
settings (`SSO_PROVIDER`, `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `SAML_METADATA_URL`)
are the seam through which a real IdP is wired.

## Operator admin token

The operator invite API (`/admin/invites`) is gated separately by an
`X-Admin-Token` header compared in constant time against `ADMIN_TOKEN`. An empty
`ADMIN_TOKEN` disables the router entirely (every call returns `403`), so the
admin surface ships closed by default.

## See also

[[Cloud REST API|Cloud-REST-API]] · [[Cloud Domain Model|Cloud-Domain-Model]] · [[Cloud Architecture|Cloud-Architecture]] · [[Cloud Configuration|Cloud-Configuration]]
