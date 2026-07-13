# AutoBangumi Architecture and Authentication Modernization

## Context

AutoBangumi has strong behavior-level test coverage, but its nominal modules form a
single tightly coupled dependency graph. REST routes, MCP handlers, background jobs,
database sessions, downloader clients, and configuration are connected through
module-level singletons and inheritance. The frontend uses modern Vue syntax, while
feature state and presentation logic are duplicated across stores and large route or
modal components.

This design modernizes the architecture without forcing an immediate breaking API or
configuration migration. Existing endpoints and configuration files remain readable
during a compatibility window while new internal boundaries become authoritative.

## Compatibility Strategy

The migration uses a compatibility shell around a new application core:

- Existing REST paths continue to work. Mutating GET endpoints gain POST replacements
  and emit deprecation headers.
- Existing configuration files are migrated in place. Secrets are never returned by
  read APIs and unchanged secrets are omitted from update requests.
- Existing JWT cookies are accepted for one compatibility period and exchanged for a
  database-backed session. New JWTs are not issued.
- Existing manager and engine classes remain as thin facades while callers migrate to
  application services.
- Database migrations preserve current users, passkeys, API tokens, and application
  data.

## Authentication and Multi-user Model

All authenticated users have equal permissions. Public registration is disabled.
Any authenticated user may manage accounts, with invariants preventing the system
from losing its final enabled account. The first-run wizard creates the first user.

The user table contains a unique username, password hash, enabled flag, and audit
timestamps. An `auth_session` table stores a random session token hash, user ID,
expiry, last activity, and creation metadata. The browser receives the raw token only
in an HttpOnly cookie. Login, logout, password changes, user disabling, and user
deletion create or revoke persisted sessions transactionally. Sessions remain valid
across process restarts and across Uvicorn workers.

Passkeys continue to reference `user_id`. Registration operates on the authenticated
user and authentication creates the same persisted session as password login.

Configured login and MCP bearer tokens move into a hashed database token table.
Plaintext is displayed only once at creation. Existing configuration tokens are
imported during migration. Disabled users and revoked tokens fail immediately.

## Backend Architecture

The backend is divided into four dependency directions:

1. `domain`: domain values and rules without FastAPI, SQLModel sessions, or clients.
2. `application`: use cases and typed application errors.
3. `ports`: repository, unit-of-work, downloader, HTTP, notification, session, token,
   configuration, scheduler lease, and clock protocols.
4. `adapters`: FastAPI, MCP, SQLite/SQLModel, downloader implementations, HTTPX,
   notification providers, and file-backed configuration.

REST, MCP, and jobs call the same application use cases. They do not import each
other. A composition root in application startup constructs concrete adapters and
injects them into services. Existing `RSSEngine`, `TorrentManager`, and related public
classes delegate to these services during the compatibility period.

Database transactions are owned by a unit of work. Sync SQLModel access runs behind
one explicit thread boundary while async callers are migrated; no async route or job
performs incidental synchronous database work. Shared HTTP clients are created and
closed by application lifespan. Mutable module-level ORM caches are removed.

## Program Lifecycle and Multi-worker Scheduling

Program becomes a supervisor composed of independent job objects rather than a
multiple-inheritance hierarchy. Startup loads configuration and completes database
migrations before the API accepts traffic. Start, stop, and restart are serialized by
one lifecycle lock and implemented as idempotent state transitions. Every task is
stored, supervised, and awaited during shutdown.

A SQLite scheduler lease elects one worker as background-job leader. The owner renews
the lease periodically. Losing the lease stops jobs before another worker takes over.
Only the leader runs RSS refresh, rename, offset scan, and calendar refresh. API and
MCP requests remain available in every worker.

## Configuration and Secret Handling

Configuration paths derive from an explicit application root or environment
variable, never the process working directory. Importing configuration performs no
file creation or mutation. Writes use a temporary file, fsync, and atomic replace.
Readers detect file mtime changes so workers converge after updates.

Read and write DTOs are separate. Secret values are represented as configured/not
configured on reads. Update DTOs use omission to mean unchanged, a new value to mean
replace, and an explicit clear operation to remove a secret. Recursive sanitization
remains defense in depth and handles mappings and sequences.

## Frontend Component Map

Search is organized as a feature:

- `SearchModal`: orchestration and subscription flow.
- `SearchToolbar`: query/provider inputs; emits search and value updates.
- `SearchFilterPanel`: filter options and selected filters; emits
  `update:filters`.
- `SearchResultGroups`: renders grouped results; emits `select`.
- `SearchConfirmDialog`: accepts one bangumi; emits `confirm` and `cancel`.
- `useSearchStream`: owns EventSource lifecycle and cancellation.
- `useSearchFilters`: owns normalization, options, filtering, and counts.

Bangumi and calendar share `useBangumiGroups` and `BangumiRulePicker`.
`CalendarBoard` owns drag/drop rendering and emits assignment or unpin operations.
Route pages remain composition surfaces.

Project API, store, hook, and utility modules use explicit imports. Only framework
APIs remain eligible for automatic import. OpenAPI-generated DTOs describe transport
contracts; feature mappers convert DTOs into UI models.

## Dependency Modernization

Frontend dependencies are upgraded in three verified batches:

1. Vite, TypeScript, Vitest, Vue compiler plugins, and vue-tsc.
2. Axios, Pinia, VueUse, vue-i18n, and related runtime packages.
3. UnoCSS, Storybook, ESLint, Prettier, and their configuration formats.

Each batch must pass install, production build, type checking, unit tests, and lint
before the next batch begins. Python dependencies remain lockfile driven; application
boundaries and dependency constraints are corrected before optional version bumps.

## Error Handling and API Contracts

Application services raise typed errors such as not found, conflict, validation,
authentication, external-service failure, and unavailable. REST maps these errors to
one response envelope and MCP maps them to structured tool errors. Domain and
application code do not construct HTTP responses.

OpenAPI is the source of truth for frontend transport types. Legacy response shapes
are adapted at the REST boundary until deprecated paths are removed.

## Verification and Delivery

Required checks are:

- Backend unit and integration tests, Ruff, and migration tests.
- Frontend type check, unit/component tests, ESLint, and production build.
- Authentication tests covering multiple users, session persistence, revocation,
  passkeys, token hashing, and last-user invariants.
- Concurrency tests covering idempotent lifecycle transitions and scheduler lease
  takeover.
- Architecture tests preventing forbidden package imports.
- A separate Docker-backed E2E CI job instead of silently skipping E2E coverage.

Implementation is delivered in small compatibility-preserving commits, with security
and lifecycle fixes preceding structural and dependency changes.
