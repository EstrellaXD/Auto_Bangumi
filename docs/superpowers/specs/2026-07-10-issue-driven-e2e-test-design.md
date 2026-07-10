# Issue-Driven Hermetic E2E Test Design

## Status

User-approved design. The written specification is pending final user review
before an implementation plan is created.

## Context

AutoBangumi already has 67 tests marked as end-to-end under
`backend/src/test/e2e`, but they are one ordered, stateful workflow. The suite
starts a real backend process and Docker services, yet AutoBangumi itself uses
the mock downloader, the RSS fixture is never refreshed through the full
pipeline, and the real qBittorrent container is only contacted directly by the
test. The normal GitHub Actions test command does not select `-m e2e`, so the
entire suite is skipped in CI.

The suite has also drifted from the current authentication contract. It still
expects login, refresh, and credential-update responses to expose
`access_token`, uses the deprecated GET refresh endpoint, and allows protected
requests to return either 200 or 401. Browser coverage is currently limited to
Vitest and Happy DOM; there is no real-browser test runner.

Recent GitHub issues expose gaps that unit tests alone have not prevented:

- [#1075](https://github.com/EstrellaXD/Auto_Bangumi/issues/1075): TMDB TV and
  movie search URLs omit the configured localization parameter.
- [#1072](https://github.com/EstrellaXD/Auto_Bangumi/issues/1072): a release
  title containing `06v2` and CRC `[E931DD98]` is parsed as episode 931, causing
  a false offset warning.
- [#1069](https://github.com/EstrellaXD/Auto_Bangumi/issues/1069): the mobile
  rule editor moves with the virtual keyboard and makes title editing
  impractical.
- [#1068](https://github.com/EstrellaXD/Auto_Bangumi/issues/1068): Windows and
  POSIX save-path separators previously prevented torrent deletion. The code
  fix is merged but lacks an API-to-downloader regression.
- [#1067](https://github.com/EstrellaXD/Auto_Bangumi/issues/1067): parser
  language and localized search-result caching regressed before being fixed.
- [#1065](https://github.com/EstrellaXD/Auto_Bangumi/issues/1065): a PR title
  became a non-SemVer image version and broke container startup.
- [#1062](https://github.com/EstrellaXD/Auto_Bangumi/issues/1062): local player
  settings were mistaken for server configuration, and mixed-content behavior
  was unclear.

This design turns those reports into deterministic acceptance tests while also
rehabilitating the existing E2E suite.

## Confirmed Decisions

- Every pull request runs the full E2E gate without path filtering.
- The pull-request browser matrix is Chromium desktop plus WebKit mobile.
- Firefox runs nightly rather than on every pull request.
- The total wall-clock budget is 15 minutes; independent lanes run in parallel.
- Test execution is hermetic. TMDB, RSS, images, notifications, and media files
  come from local fixtures. Public services are never used by the PR tests.
- A real, pinned qBittorrent container downloads a tiny local torrent from a
  local web seed and participates in the complete RSS-to-file workflow.
- Public-network validation is limited to a separate, non-blocking post-release
  monitor.

## Goals

- Make browser, backend, database, downloader, filesystem, and packaged-image
  boundaries observable in CI.
- Convert recent bugs into deterministic positive and negative controls.
- Exercise production-built WebUI assets against a real backend rather than a
  Vite development server.
- Make each failure independently diagnosable from uploaded artifacts.
- Remove order dependence and mutable cross-test state.
- Keep the required gate at or below 15 minutes at p95.

## Non-Goals

- PR tests do not call real TMDB, Mikan, Nyaa, Bangumi, image, notification, or
  tracker services.
- Desktop Playwright cannot reliably open an Android or iOS native soft
  keyboard. Mobile tests emulate the observable viewport contraction instead.
- Multi-architecture image emulation remains in the release pipeline. PR image
  smoke tests build only the runner's native architecture.
- Unimplemented feature requests such as #1071, #1073, and #1058 are retained
  as future acceptance scenarios, not installed as currently failing gates.
- Third-party iframe `X-Frame-Options`, CSP, and real HTTPS mixed-content policy
  are not reproduced in the PR gate.

## Architecture

The gate has three independent lanes. The browser lane is a two-entry matrix,
so GitHub exposes four required check instances in total.

```text
local fixtures ──> real AutoBangumi (production WebUI + backend + SQLite)
      │                         │
      │                         ├── e2e-runtime (pytest + HTTP)
      │                         ├── e2e-browser / Chromium
      │                         ├── e2e-browser / WebKit mobile
      └── real qBittorrent <────└── e2e-downloader-image
```

| Lane | Responsibilities | Target |
| --- | --- | --- |
| `e2e-runtime` | Real backend, SQLite, mock upstream, API, scheduler, migration, restart persistence | 4–6 minutes |
| `e2e-browser` | Production WebUI against a real backend; Chromium desktop and WebKit mobile matrix | 8–12 minutes |
| `e2e-downloader-image` | Real qBittorrent, tiny download, rename/delete workflow, packaged-image startup | 10–15 minutes |

The lanes run concurrently. Each lane receives a unique Compose project name,
temporary config/data directories, and dynamically allocated host ports.
Container names and host ports are never fixed, which permits concurrent CI
runs and local development.

## Repository Layout

The cross-stack assets live at the repository root rather than under the Python
test package:

```text
e2e/
├── compose/
│   ├── browser.yml
│   └── downloader.yml
├── fixtures/
│   ├── files/tiny-media.mkv
│   ├── rss/
│   ├── tmdb/
│   └── torrents/tiny-media.torrent
├── mock-upstream/
├── fake-qb/
└── scripts/

backend/src/test/e2e/
├── runtime/
├── downloader/
└── support/

webui/e2e/
├── fixtures/
└── specs/

webui/playwright.config.ts
.github/workflows/e2e.yml
```

The existing E2E fixtures move into this structure as they are replaced. There
is no second permanent fixture implementation.

## Test Components

### Mock Upstream

One small HTTP service provides:

- `/rss/*` for deterministic RSS documents;
- `/tmdb/*` for TV search, movie search, detail, season, and image metadata;
- `/images/*` for local poster content;
- `/notifications/*` for webhook capture;
- `/files/tiny-media.mkv` as the qBittorrent web seed;
- `/__admin/reset`, `/__admin/requests`, and `/__admin/state` for scenario
  control and request inspection.

Each test loads a named scenario. An unrecognized request returns HTTP 501 and
is recorded in the request journal. This makes an accidental external contract
change visible instead of returning an overly permissive fixture.

### Fake qBittorrent

A separate fake-qB service is used only where a real Linux qBittorrent cannot
produce the required protocol condition, notably Windows-style paths and
forced delete failures for #1068. It records form bodies and returns explicit
scenario responses. The core downloader workflow always uses real qBittorrent.

### Real qBittorrent and Tiny Torrent

The qBittorrent image reference includes both a patch-version tag and an
immutable `sha256` digest; floating tags are rejected by a CI assertion. The
digest is recorded in the Compose file and updated only through an intentional
dependency change. A mounted test configuration provides fixed test-only
credentials. The pre-generated torrent contains a roughly 64 KiB media payload
and a web-seed URL resolving to the mock-upstream service name on the internal
Compose network.

The full workflow is:

1. Complete Setup with the real qBittorrent endpoint.
2. Add the local RSS through the public API or WebUI.
3. Trigger `POST /api/v1/rss/refresh/{rss_id}`.
4. Poll the qBittorrent task until completion.
5. Poll AutoBangumi's database/API and the shared filesystem for rename and
   organization completion.
6. Refresh the RSS again and prove no duplicate task is added.
7. Delete with files enabled and prove both qBittorrent state and the file are
   removed.

No DHT, tracker, magnet discovery, or public peer is needed.

### Production WebUI

The WebUI is built once and served by the real backend, matching the packaged
application. The Iconify simple-icons data is installed or vendored locally so
the build does not fetch `esm.sh`. Playwright disables Service Workers during
tests to prevent PWA cache state from crossing cases.

## Browser Isolation

Chromium and WebKit run as separate matrix jobs, each with an independent
backend and database. Within a job:

- the first-run Setup spec owns a fresh environment;
- authenticated specs create a baseline account through public endpoints and
  generate a Playwright `storageState` bound to that database;
- every spec creates a fresh browser context and uses a unique resource prefix;
- tests clean up only resources they own;
- the project runs with one Playwright worker against its backend, avoiding
  shared-server races while the two browser jobs remain parallel.

Tests use roles and accessible names. Stable `data-testid` attributes are added
only where the UI exposes no semantic locator. No production test-only API is
introduced. Data that cannot be established through public APIs is placed into
an offline fixture database before the process starts.

## Issue-Driven Test Matrix

| Spec | Coverage | Required assertions | Layer |
| --- | --- | --- | --- |
| `bootstrap-auth.spec.ts` | Current authentication work | Setup; exact non-secret login response; HttpOnly/SameSite cookie; reload/refresh; wrong password; logout and back navigation | Chromium + WebKit |
| `session-access.spec.ts` | Current authentication work | Two contexts; password change invalidates old session/password; API/MCP scope isolation; Bearer cannot perform account-control operations | Browser + runtime |
| `token-secret.spec.ts` | Current authentication work | Secret appears once; list contains prefix only; close, navigation, unmount, and late response never restore it | Chromium + WebKit |
| `tmdb-language.spec.ts` | #1075, #1067 | `zh`/`jp` reach TV, movie, and retry searches; same keyword after language change does not reuse localized cache | Browser + mock TMDB |
| `offset-review.spec.ts` | #1072 | `06v2 ... [E931DD98]` parses as episode 6 and does not flag; episode 13 of a 12-episode season does flag; no parse signal does not write review state | Runtime + browser smoke |
| `mobile-rule-editor.spec.ts` | #1069 | 390×844 full-screen editor; viewport contraction does not translate panel; title remains visible, editable, and persists | WebKit mobile |
| `windows-path-delete.spec.py` | #1068 | POSIX DB path matches backslash/trailing-slash fake-qB path; only exact torrent is deleted; disable preserves Bangumi; qB failure is not reported as success | Runtime + fake qB |
| `player-local-settings.spec.ts` | #1062 | Player type/URL immediately enter localStorage; no backend config request; reload persists; new context starts at defaults; iframe URL is unchanged | Chromium + WebKit |
| `rss-download-rename.spec.ts` | Core workflow | RSS to qB to tiny completed file to rename/organization; UI reflects completion; second refresh is idempotent; delete removes state/file | Chromium + real qB |
| `release-image-smoke.spec.py` | #1065 | Non-SemVer/PR title cannot release; valid injected version starts; health, API version, and image version agree | Docker |
| `restart-persistence.spec.py` | 3.3 persistence | Users, sessions, API tokens, RSS, and Bangumi survive restart; revoked credentials do not revive | Runtime |

The #1072 fixture uses the exact reported title:

```text
[SubsPlease] Haibara-kun no Tsuyokute Seishun New Game - 06v2 (1080p) [E931DD98].mkv
```

The negative regression always runs beside a true-positive episode-overflow
control. This prevents a parser fix from merely suppressing all versioned or
CRC-bearing titles.

For #1075, the mock TV and movie search endpoints return the expected result
only when the correct `language` query is present. The whitespace-removal retry
also requires the same language. Tests inspect the upstream request journal as
well as the user-visible localized result.

## Existing E2E Rehabilitation

The current ordered workflow is split by bounded responsibility. Before adding
new scenarios, its stale authentication expectations are corrected:

- login, refresh, and credential update must equal
  `{ "authenticated": true }` and contain no raw session token;
- refresh uses POST;
- unauthenticated protected requests must be 401, never `(200, 401)`;
- development authentication bypass is not enabled;
- tests no longer use numbered method names or a shared `e2e_state` dictionary;
- subprocess output goes to log files instead of unconsumed pipes;
- RSS coverage triggers real analysis, refresh, persistence, and downloader
  effects rather than only storing a URL;
- no-op and error-path assertions remain only when they validate a documented
  contract.

## Release Classification and Image Smoke

The release-trigger classification currently embedded in the workflow is moved
to a small script with a table-driven contract. It must classify:

- normal branch push: no release;
- PR titled `Doc update`: no release;
- tag `Doc-update`: no release;
- stable `X.Y.Z` tag on a main ancestor: stable release;
- stable tag off main: explicit failure;
- `X.Y.Z-beta.N`: prerelease without changing stable `latest`.

The PR smoke image uses a legal test SemVer such as `3.3.999-e2e.1`, starts on
the runner's native architecture, and must report healthy. The status API,
runtime version, and `/app/IMAGE_VERSION` must agree. Public registry `latest`
is never pulled in the required PR gate.

## CI Workflow

`.github/workflows/e2e.yml` runs on every pull request with no path filters. Its
required checks are:

- `e2e-runtime`;
- `e2e-browser (chromium)`;
- `e2e-browser (webkit-mobile)`;
- `e2e-downloader-image`.

Each job has `timeout-minutes: 15`. Dependency stores, Playwright browser
binaries, frontend build output, and Buildx layers are cached using lockfile and
source-sensitive keys. Test execution occurs on an internal Compose network;
dependency installation and existing package-manager access happen before that
network is entered.

PR runs use zero test retries. A nightly workflow runs Firefox and repeats the
browser and downloader suites to expose intermittent failures. It does not
change the required PR checks.

The checks initially run in shadow mode for ten representative PR executions.
They become required only after all ten pass and p95 wall-clock time is below 15
minutes. This rollout validates the budget without weakening the final policy.

## Waiting and Timeouts

Fixed sleeps are forbidden. Tests wait for one of the following bounded
conditions:

- a health or API response;
- a Playwright locator state;
- a recorded upstream request;
- a qBittorrent task state;
- a database/API state transition;
- a filesystem path state.

Every poll includes its last observed state in the failure message. Individual
actions default to 10 seconds and full specs to 60 seconds unless the downloader
completion spec documents a longer bound within the 15-minute job limit.

## Failure Handling and Artifacts

An unexpected mock request returns 501 and remains in the request journal. A
stack startup failure prints every health status and recent service log before
exiting. GitHub Actions uses `if: always()` to upload:

- Playwright trace, screenshots, video, and HTML report;
- browser console errors and failed network requests;
- backend logs;
- mock-upstream request journal;
- qBittorrent logs and torrent state, with credentials redacted;
- Compose service status and logs;
- the failed test SQLite database, which contains test-only credentials.

Artifacts use the lane, browser project, commit, and run attempt in their names.
They are retained for 14 days.

## Flake Policy

Required checks do not retry tests. A flaky result is a defect. Temporary
quarantine requires a linked issue, an owner, and a removal date no more than
seven days away; the quarantined behavior must still run as a visible
non-blocking check. Nightly repetition provides the evidence needed to identify
timing and isolation problems.

## Acceptance Criteria

- All four check instances are required on every pull request.
- p95 end-to-end gate wall-clock time is below 15 minutes after ten shadow runs.
- Test execution performs no public upstream requests.
- Chromium desktop and WebKit mobile both run against production-built assets.
- The real-qB test downloads, renames/organizes, deduplicates, and deletes the
  tiny fixture without public peers.
- Every listed recent issue has at least one deterministic regression and an
  appropriate positive or negative control.
- No E2E test depends on definition order or shared mutable state from another
  test.
- A failed check can be diagnosed from uploaded artifacts without rerunning it
  interactively.
