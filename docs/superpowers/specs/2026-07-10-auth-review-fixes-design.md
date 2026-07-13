# Authentication Review Fixes Design

## Context

PR #1074 replaces process-local JWT state with database-backed sessions and
user-owned API/MCP tokens. Review found security and failure-path defects in
session transport, legacy JWT compatibility, credential mutation transactions,
legacy token migration, API-token audit writes, and the new access UI.

This design fixes those defects before the feature is merged. It deliberately
chooses secure browser-session semantics over compatibility with clients that
consume a login response's `access_token` field.

## Goals

- Keep browser sessions exclusively in an HttpOnly cookie.
- Make logout and credential changes reliably invalidate browser sessions.
- Remove the replayable legacy-JWT compatibility path.
- Make user mutation, session revocation, credential purge, and deletion atomic.
- Migrate legacy API/MCP tokens without storing recoverable token text or losing
  a scope when the same secret is configured for both APIs.
- Keep API-token authentication successful when best-effort audit metadata
  cannot be written.
- Never lose a newly created one-time token after its HTTP 201 response reaches
  the client, even if a subsequent list refresh fails.
- Surface FastAPI `detail` errors consistently in the frontend.

## Non-goals

- Adding roles or per-user authorization levels.
- Turning API and MCP scopes into fine-grained permissions.
- Preserving bearer-session compatibility for password or passkey login.
- Retaining upgrade compatibility for previously issued JWT cookies. Users will
  sign in once after upgrading.

## Session and Principal Model

Password login, passkey login, refresh, and current-user credential update set a
random persisted session in the `token` HttpOnly cookie. Every session-issuing
endpoint returns the exact non-secret DTO `{ "authenticated": true }`; it never
contains the raw session token. The frontend login and update types mirror this
DTO and contain no `access_token` field.

`Authorization: Bearer` accepts only database-backed tokens with `scope="api"`.
Persisted browser-session tokens are no longer accepted in that header. MCP
continues to require a token with `scope="mcp"` or an allowed client IP.

Authentication resolves a typed principal containing the database user and the
credential kind (`session`, `api_token`, or explicit development bypass).
Existing data-route dependencies continue exposing a username wrapper, while
credential-changing and passkey-management routes consume the typed principal
and require its session kind. This prevents an automation token from becoming
an account-recovery credential.
The current-user credential endpoint accepts only username/password changes;
enable/disable operations remain on the multi-user management endpoint.

The account-control route policy is explicit:

- `/auth/update`, every `/users` and `/tokens` operation, and passkey
  register/list/delete require a valid cookie session;
- `/auth/me`, application data APIs, and non-access-control configuration APIs
  may use either a cookie session or an `api` token;
- password/passkey login, refresh, logout, and setup retain their existing
  public-or-specialized entry conditions.

When a request carries both a Bearer API token and a session cookie, the
explicit Authorization credential takes precedence. A valid API token therefore
receives 403 from a session-only endpoint even if the request also carries a
cookie; the cookie cannot silently elevate the token's authority.

Logout revokes the cookie session, clears the cookie on the actual returned
response, and remains idempotent. Since header sessions no longer exist, there
is no second session transport that logout could overlook.

Passkey verification carries the database `user_id` and normalized credential
ID into session issuance. The signing transaction revalidates that the
credential still belongs to the user before creating a session; this prevents
SQLite row-ID reuse after delete/recreate from transferring a verified passkey
to a replacement account. It never resolves the user again by mutable username
after signature verification.

## Legacy JWT Policy

Legacy JWT cookies are no longer accepted by normal authentication or refresh.
The old tokens cannot be revoked safely because they contain no server-side
identifier or authentication version. Attempting to preserve them would leave
logout and password changes vulnerable to replay.

An upgrade therefore invalidates existing JWT cookies and requires one new
login. The JWT decoding helpers remain only for unrelated compatibility tests or
old code until a later cleanup; they are not in the request authentication path.

## Atomic User and Credential Mutations

Authentication application services own transaction boundaries. Repository
operations used in a multi-step mutation stage their changes with `flush` and
do not commit independently. The service commits once after all required
operations succeed and rolls back the whole unit on any error.

The following operations are single write transactions:

- password change plus revocation of every browser session;
- disabling a user plus session revocation;
- current-user credential update plus old-session revocation and creation of the
  replacement session;
- credential purge plus user deletion;
- setup-wizard replacement of the default administrator credentials.

For SQLite, mutations that enforce the final-enabled-user invariant acquire the
write transaction with adapter-level `BEGIN IMMEDIATE` before any SELECT. A
normal async SQLAlchemy `session.begin()` is insufficient because it remains a
deferred SQLite transaction. Early write acquisition serializes competing
disable/delete operations and prevents a stale check from leaving zero enabled
accounts or purging credentials before a later conflict.

Single-operation repository callers retain an explicit commit path so unrelated
database services do not silently change behavior.

Setup uses the same atomic credential-update application service. Completion
revokes every pre-setup session and intentionally leaves the caller signed out;
the user signs in with the newly selected credentials. The setup guard returns
the authenticated session user's ID (or the factory-default administrator's
ID), so completion never performs a second lookup by the mutable `admin` name.

Every authentication path that reads before writing acquires the SQLite write
snapshot before its first SELECT. Paths that only revoke or refresh use direct
conditional updates. This prevents WAL stale-snapshot upgrades from surfacing
as immediate `database is locked` errors even when a busy timeout is configured.

## Legacy API/MCP Token Migration

Generated tokens keep a short recognizable prefix because their fixed format and
high entropy ensure the prefix is not the complete secret. Imported legacy
tokens instead store an irreversible display fingerprint derived from the token
hash, such as `legacy_ab12cd34`; no raw substring is persisted.

Token uniqueness becomes `(token_hash, scope)`, allowing one legacy secret to
remain valid for both API and MCP when it was configured in both lists. Import
uses `INSERT ... ON CONFLICT(token_hash, scope) DO NOTHING`, so concurrent
startup workers are idempotent without a select-then-insert race.

The schema migration supports both fresh databases and databases that already
ran PR schema version 19. Because v19 has no reliable provenance marker, the v20
migration replaces the display prefix of every existing token row with a
hash-derived fingerprint; losing an old generated-token prefix is accepted to
guarantee that no short imported secret remains recoverable.

SQLite v20 transactionally rebuilds `api_token`: create the replacement table
without the table-level `UNIQUE(token_hash)` constraint, copy every row while
preserving ID, owner, scope, timestamps, expiry and revocation state, replace the
old table, and recreate foreign keys and indexes including a composite
`UNIQUE(token_hash, scope)`. SQLModel declares the same composite constraint.
The migration is guarded and rollback-tested against a real v19 schema.
Configuration token lists are cleared only after every requested
`(secret, scope)` entry is present.

## API-token Audit Writes

Authentication itself is read-only. After a token has been validated and its
database session is closed, the application performs a separate atomic
`last_used_at` update. Audit-update failures are logged and rolled back but do
not turn valid authentication into a 500 response.

Ending the read transaction before the update avoids SQLite's stale
read-snapshot upgrade failure. The direct update uses the configured busy
timeout; it does not re-read and then upgrade the same transaction.
Authentication returns the matched token row ID internally, and the audit write
updates that ID only. A secret present in both scopes must not update both rows.

## Frontend Behavior

The authentication client models login and refresh as cookie-session success;
it does not read or retain a session bearer token.

Token creation immediately separates the one-time secret from the public token
metadata. The store updates its list from the successful creation response and
returns the secret to the reveal dialog without making a second request first.
Any later list refresh is independent and cannot consume the only copy.

Closing, deactivating, or unmounting an access dialog clears password and
one-time-token refs. A lifecycle generation guard also discards a one-time token
whose create request resolves after the panel was closed or deactivated, so an
in-flight promise cannot restore scrubbed secret state. The access panel reloads
on KeepAlive activation, maps each token's `user_id` to an owner name, and
distinguishes active, expired, and revoked tokens using `expires_at` and
`revoked_at` rather than treating every unrevoked row as active.

The Axios error normalizer accepts the existing bilingual response envelope,
FastAPI string `detail`, and validation-error `detail[]`. Non-silent 401
responses always produce a useful localized fallback. Silent startup refreshes
still clear authentication state without showing a toast.

## Error Handling

- Invalid credentials and invalid cookies return 401 without revealing which
  credential component failed.
- API-token use on a session-only endpoint returns 403.
- Last-enabled-user and duplicate-username conflicts return 409.
- Audit metadata failures never fail an otherwise valid request.
- All multi-step mutations roll back on cancellation, database exceptions, or
  invariant conflicts.

## Testing Strategy

Regression tests are added before implementation for:

- login, refresh, and passkey responses containing no raw session token;
- current-user update containing no raw session token and the frontend Update
  type containing no `access_token`;
- Authorization rejecting a browser session token;
- logout clearing and revoking the cookie session;
- the actual logout response carrying the cookie-deletion `Set-Cookie` header;
- legacy JWT cookies being rejected after upgrade;
- password/setup updates rolling back or revoking every old session;
- failed deletion preserving the user's sessions, API tokens, and passkeys;
- concurrent final-user mutations preserving at least one enabled account;
- rollback at each flush, commit, exception, and cancellation point in every
  multi-step authentication mutation;
- short legacy secrets never appearing in `prefix`;
- one secret migrating successfully into both API and MCP scopes;
- a real v19 database upgrading to v20 without losing token IDs, owners,
  timestamps, expiry, revocation, or scope;
- concurrent multi-worker legacy imports remaining idempotent;
- concurrent token authentication not failing when audit writes contend;
- audit-write failure not failing authentication;
- audit updates changing only the authenticated row when one hash has two
  scopes;
- API principals receiving 403 and session principals succeeding across every
  session-only endpoint, including mixed header-plus-cookie requests;
- passkey verification issuing by immutable user ID during concurrent username
  rename/reuse;
- passkey session issuance revalidating credential ownership after SQLite user
  ID reuse;
- WAL concurrency between login/session writes and another writer;
- setup completion updating the authenticated stable user ID after admin rename;
- frontend token reveal surviving a subsequent refresh failure;
- frontend parsing FastAPI `detail` and showing a 401 fallback;
- frontend authentication types no longer containing `access_token`;
- sensitive access refs being scrubbed on close/deactivate/unmount;
- in-flight token creation not restoring a scrubbed one-time secret;
- KeepAlive activation reloading access data;
- token owner and active/expired/revoked state rendering.

After targeted red-green testing, run the complete backend suite, Ruff and Black
checks for changed Python files, frontend Vitest, Vue TypeScript checking, ESLint,
and the production frontend build.

## Compatibility and Rollout

This change intentionally logs out users once on upgrade and removes login-based
bearer sessions. Existing configured API/MCP tokens are migrated and remain the
supported automation mechanism. No user, passkey, application data, or scoped
API token is otherwise discarded.
