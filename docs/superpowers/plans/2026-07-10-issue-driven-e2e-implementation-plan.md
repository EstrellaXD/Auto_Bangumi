# Issue-Driven Hermetic E2E Implementation Plan

## Status

Ready for execution. This plan implements the approved
[`2026-07-10-issue-driven-e2e-test-design.md`](../specs/2026-07-10-issue-driven-e2e-test-design.md).

## Objective

Replace the ordered, stateful E2E workflow with deterministic runtime,
real-browser, real-qBittorrent, and packaged-image checks. Fix the two current
production regressions exposed by issues #1075 and #1072, make recent issue
fixes executable as acceptance tests, and add four parallel pull-request checks
whose p95 wall-clock time stays below 15 minutes.

## Guardrails

- Preserve unrelated working-tree files. In particular, never stage
  `backend/uv.lock`, `AGENTS.md`, or `PRODUCT.md` unless their owner explicitly
  asks for it.
- Commit the already-verified authentication implementation separately before
  beginning E2E work; do not mix it into issue or test-infrastructure commits.
- Do not add a production test-only endpoint. Tests use public APIs, mock
  service admin APIs, or a database fixture written before app startup.
- During test execution, AutoBangumi and qBittorrent run on a Docker internal
  network. Playwright additionally rejects requests outside the dynamically
  assigned local origins.
- No fixed host port, fixed container name, fixed Compose project name, fixed
  sleep, test retry, numbered test name, or cross-test state dictionary is
  allowed.
- A required test must have a positive or negative control so a broad
  suppression cannot make it pass accidentally.
- Each task uses a red/green cycle: add the narrow failing assertion, confirm
  the expected failure, implement the minimum behavior, then run the targeted
  and adjacent suites.

## Commit Sequence

1. Existing authentication review implementation.
2. `fix: preserve tmdb language and versioned episodes`.
3. `fix: make release classification deterministic`.
4. `test: add hermetic e2e support services`.
5. `test: replace ordered api e2e coverage`.
6. `test: add browser issue regressions`.
7. `test: exercise real qbittorrent and release images`.
8. `ci: run hermetic e2e checks`.

The sequence keeps production fixes, reusable infrastructure, scenarios, and
CI policy independently reviewable.

## Task 1: Stabilize the Existing Authentication Work

**Files**

- Existing modified files under `backend/src/module/{api,application,database,mcp,models,ports,security}`.
- Existing modified and new auth tests under `backend/src/test`.
- Existing modified files under `webui/src/{api,components,hooks,store,utils}` and `webui/types`.
- `docs/superpowers/specs/2026-07-10-auth-review-fixes-design.md`.

**Steps**

1. Re-run the focused backend auth, migration, and MCP suites and the focused
   WebUI auth/access suites against the current working tree.
2. Run backend Ruff, Black check, and mypy on the changed Python files.
3. Run WebUI type checking, ESLint, Prettier check, and the full Vitest suite.
4. Stage only the known authentication implementation, tests, and updated auth
   design. Explicitly inspect `git diff --cached --name-only` before commit.
5. Commit the authentication work without staging the three protected local
   files listed in Guardrails.

**Verification**

```bash
cd backend && uv run pytest \
  src/test/test_api_auth.py \
  src/test/test_api_passkey.py \
  src/test/test_api_users.py \
  src/test/test_auth.py \
  src/test/test_auth_persistence.py \
  src/test/test_auth_service_transactions.py \
  src/test/test_mcp_security.py \
  src/test/test_migrations_module.py \
  src/test/test_session_store.py \
  src/test/test_setup.py -q
cd backend && uv run pytest -q
cd backend && uv run ruff check src
cd backend && uv run mypy src
cd webui && pnpm test --run
cd webui && pnpm test:build
cd webui && pnpm lint
cd webui && pnpm format:check
```

## Task 2: Fix TMDB Search Localization (#1075)

**Files**

- Modify `backend/src/test/test_tmdb.py`.
- Modify `backend/src/module/parser/analyser/tmdb_parser.py`.

**Steps**

1. Add table-driven URL tests for TV and movie searches in `zh`, `jp`, and
   `en`. Parse the URL and assert exact `language`, `query`, `api_key`,
   `page=1`, and `include_adult=false` values rather than comparing an encoded
   string manually.
2. Add async tests proving both the whitespace-removal retry and the TV-to-movie
   fallback preserve the requested language.
3. Change `search_url` and `search_movie_url` to accept `language` and construct
   query strings through `urllib.parse.urlencode`.
4. Thread `language` through `_search_movie` and every initial, retry, and
   fallback call. Keep the existing language-bearing cache key.
5. Run TMDB, RSS analyser, searcher, and config-reload tests to catch signature
   and cache regressions.

**Verification**

```bash
cd backend && uv run pytest \
  src/test/test_tmdb.py \
  src/test/test_searcher.py \
  src/test/test_config.py -q
cd backend && uv run ruff check src/module/parser/analyser/tmdb_parser.py src/test/test_tmdb.py
cd backend && uv run black --check src/module/parser/analyser/tmdb_parser.py src/test/test_tmdb.py
```

## Task 3: Parse Versioned Episodes Before CRC Tokens (#1072)

**Files**

- Modify `backend/src/test/test_torrent_parser.py`.
- Modify `backend/src/test/test_offset_scanner.py`.
- Modify `backend/src/module/parser/analyser/raw_parser.py`.

**Steps**

1. Add the exact reported title as a parser regression:

   ```text
   [SubsPlease] Haibara-kun no Tsuyokute Seishun New Game - 06v2 (1080p) [E931DD98].mkv
   ```

   Assert season 1, episode 6, group `SubsPlease`, and episode type `episode`.
2. Add controls for plain `06`, bracketed `06v2`, `13v2` plus a CRC token,
   explicit `E13`, and a title with no episode signal.
3. Update the regular expression so an unbracketed numeric episode may carry a
   one- or two-digit `vN` suffix. The suffix belongs to the episode token and
   must be matched before a later `[Ehhhhhhhh]` CRC-like group.
4. Give explicit `E`/`EP` episode tokens an alphanumeric boundary so a CRC such
   as `E931DD98` cannot be accepted as an episode, while `E13` and `EP13`
   controls continue to parse.
5. Add scanner tests with a real temporary database for the exact E6/CRC title,
   a true-positive E13 against a 12-episode TMDB season, and an unparseable
   no-signal title. Assert both the boolean result and persisted review fields.
6. Run all parser, offset detector, offset scanner, and issue regression tests.

**Verification**

```bash
cd backend && uv run pytest \
  src/test/test_torrent_parser.py \
  src/test/test_title_parser.py \
  src/test/test_offset_detector.py \
  src/test/test_offset_scanner.py \
  src/test/test_issue_bugs.py -q
cd backend && uv run ruff check src/module/parser/analyser/raw_parser.py \
  src/test/test_torrent_parser.py src/test/test_offset_scanner.py
```

## Task 4: Extract and Test Release Classification (#1065)

**Files**

- Create `scripts/classify_release.py`.
- Create `backend/src/test/test_release_classification.py`.
- Modify `.github/workflows/build.yml`.

**Steps**

1. Put classification in a pure Python function accepting event name, ref
   type, ref name, head ref, PR title, and whether the tagged commit is on
   `main`. The PR title is accepted only to prove it has no effect on version
   selection.
2. Cover normal branch pushes, a PR titled/headed `Doc update`, tag
   `Doc-update`, a stable tag on and off `main`, and `X.Y.Z-beta.N`.
3. Make the CLI print `release`, `dev`, `build_test`, and `version` as GitHub
   output lines. A stable tag off `main` exits non-zero with a specific error.
4. Replace the embedded shell branching in `version-info` with the script while
   retaining the current job outputs and downstream job interface.
5. Confirm a non-SemVer PR title can never become `VERSION`.

**Verification**

```bash
cd backend && uv run pytest src/test/test_release_classification.py -q
cd backend && uv run ruff check ../scripts/classify_release.py \
  src/test/test_release_classification.py
python scripts/classify_release.py --event pull_request --ref-type branch \
  --ref-name main --head-ref Doc-update --on-main false
```

## Task 5: Build Deterministic Fixture Assets

**Files**

- Create `e2e/scripts/generate_fixtures.py`.
- Create generated `e2e/fixtures/files/tiny-media.mkv`.
- Create generated `e2e/fixtures/torrents/tiny-media.torrent`.
- Create RSS fixtures under `e2e/fixtures/rss`.
- Create TMDB response fixtures under `e2e/fixtures/tmdb`.
- Create a small local player document under `e2e/fixtures/player/index.html`.
- Create `backend/src/test/test_e2e_fixture_generation.py`.

**Steps**

1. Generate a deterministic 64 KiB payload from a fixed byte pattern; do not
   store random output.
2. Implement the small bencode encoder needed for a single-file torrent using
   only the Python standard library. Set piece length, SHA-1 pieces, filename,
   length, and `url-list` deterministically.
3. Use the internal URL
   `http://mock-upstream:18888/files/tiny-media.mkv` as the web seed and an RSS
   enclosure URL on the same service for the torrent metainfo.
4. Check in SHA-256 expectations for both generated files and make the unit
   test regenerate into a temporary directory and compare bytes.
5. Add RSS cases for normal download, duplicate refresh, #1072, and localized
   TV/movie searches. TMDB fixtures use `poster_path: null`, which proves the
   parser never reaches its hard-coded public image host during E2E. Fixtures
   contain no public URL.

**Verification**

```bash
python e2e/scripts/generate_fixtures.py --check
cd backend && uv run pytest src/test/test_e2e_fixture_generation.py -q
rg -n 'https?://' e2e/fixtures
```

The URL scan may match only the two approved internal service URLs and the
local player fixture's loopback placeholder.

## Task 6: Add Mock-Upstream and Fake-qB Services

**Files**

- Create `e2e/mock-upstream/server.py` and `e2e/mock-upstream/Dockerfile`.
- Create `e2e/fake-qb/server.py` and `e2e/fake-qb/Dockerfile`.
- Create `backend/src/test/e2e/runtime/test_support_services.py`.

**Steps**

1. Implement both services with the Python standard library so their images do
   not download packages at build time. Pin each Python base image with both a
   patch tag and immutable digest.
2. Mock-upstream serves `/health`, `/rss/*`, `/tmdb/*`, `/images/*`,
   `/notifications/*`, `/files/*`, `/torrents/*`, and `/player/*`.
3. File and torrent responses implement `HEAD` and single-byte-range `GET`,
   returning correct `Accept-Ranges`, `Content-Range`, `Content-Length`, 206,
   and 416 semantics. This is required by qBittorrent's web-seed client.
4. Its `/__admin/reset` selects a named scenario and clears the request journal;
   `/__admin/requests` and `/__admin/state` return recorded data. Unknown routes
   return 501 and remain in the journal.
5. Fake-qB implements the qB Web API subset AutoBangumi uses: login/logout,
   application preferences/version, torrent info, and torrent delete. Admin
   state selects Windows-path, neighbor-path, and forced-delete-failure cases.
6. Redact authorization, cookie, password, and token values before journaling.
7. Contract-test health, range requests, scenario reset, exact query/form
   capture, unknown-route failure, and redaction for both services.

**Verification**

```bash
cd backend && uv run pytest \
  src/test/e2e/runtime/test_support_services.py -m e2e -q
cd backend && uv run ruff check ../e2e/mock-upstream/server.py \
  ../e2e/fake-qb/server.py src/test/e2e/runtime/test_support_services.py
```

## Task 7: Add the Hermetic Stack and Test Controls

**Files**

- Create `e2e/compose/browser.yml`.
- Create `e2e/compose/downloader.yml`.
- Create `e2e/fixtures/qbittorrent/qBittorrent.conf`.
- Create `e2e/scripts/build_test_image.py`.
- Create `e2e/scripts/stack.py`.
- Create `e2e/scripts/collect_artifacts.py`.
- Create `e2e/scripts/audit_sources.py`.
- Create `backend/src/test/e2e/support/{client.py,database.py,poll.py,run_offset_scan.py,stack.py}`.
- Replace `backend/src/test/e2e/conftest.py` with isolated fixtures.

**Steps**

1. Build the WebUI, then assemble a temporary Docker build context containing
   the tracked backend plus the built `dist` and a generated
   `module/__version__.py` set to `3.3.999-e2e.1`. Do not write either generated
   artifact into the working tree. Build the native app image and assert
   `/app/IMAGE_VERSION` and the Python version module use the same value.
2. `browser.yml` starts the app, mock-upstream, and fake-qB on one internal
   network. Publish app and admin ports dynamically on `127.0.0.1`.
   `stack.py` creates temporary bind-mounted config, data, download, and log
   directories so tests can seed a database before startup and retain failure
   state after containers stop.
3. `downloader.yml` overlays real qBittorrent and shared download volumes. The
   image reference contains a patch tag and immutable `sha256` digest; a stack
   validation command rejects floating references.
4. Mount a fixed, test-only qB configuration. Disable DHT, PeX, LSD, UPnP, NAT
   traversal, RSS, and update checks.
5. `stack.py` creates a unique project name, starts services with health waits,
   discovers published ports, emits an environment file, restarts one service,
   and tears down volumes in `finally`/signal handlers.
6. `collect_artifacts.py` records Compose status/logs, service journals, qB
   state, backend logs, and a copy of the failed SQLite database with secret
   values redacted where output is textual.
7. Support polling helpers accept a deadline and include the last observed
   state in assertion messages. They never sleep without rechecking a bounded
   condition.
8. The pytest fixtures consume `AB_E2E_BASE_URL`, mock/fake admin URLs, Compose
   files, project name, and artifact directory. The environment file exposes
   separate internal-service and dynamically published loopback mock URLs so
   the backend and browser never need to resolve the other's address. Fixtures
   create unique resource prefixes and an idempotent baseline administrator
   without relying on test definition order.
9. Provide two app fixture types: a dedicated fresh stack for first-run and
   pre-start database scenarios, and one baseline stack for independent CRUD
   scenarios. A bootstrap test never shares its config/data directory with a
   baseline test.
   A database-seeded scenario first completes Setup with the mock downloader,
   stops the app, writes fixtures into the bind-mounted current-schema SQLite
   database, runs any one-shot service operation, and restarts the app. It never
   pre-creates the database before the initial Setup boot.
10. `audit_sources.py` enforces the public-host allowlist, immutable image
    references, absence of fixed ports/container names and Playwright retries,
    and absence of blind waits outside the bounded polling helpers.

**Verification**

```bash
python e2e/scripts/build_test_image.py --version 3.3.999-e2e.1
python e2e/scripts/stack.py validate --profile browser
python e2e/scripts/stack.py validate --profile downloader
python e2e/scripts/stack.py smoke --profile browser
```

## Task 8: Replace the Ordered Runtime E2E Suite

**Files**

- Create `backend/src/test/e2e/runtime/test_bootstrap_auth.py`.
- Create `backend/src/test/e2e/runtime/test_session_access.py`.
- Create `backend/src/test/e2e/runtime/test_restart_persistence.py`.
- Create `backend/src/test/e2e/runtime/test_tmdb_language.py`.
- Create `backend/src/test/e2e/runtime/test_offset_review.py`.
- Create `backend/src/test/e2e/runtime/test_windows_path_delete.py`.
- Modify `backend/pyproject.toml` marker declarations if lane-specific markers
  are introduced.

**Steps**

1. Bootstrap/auth runs on its dedicated fresh stack and verifies first-run
   setup, exact
   `{ "authenticated": true }` bodies, absence of token material, HttpOnly and
   SameSite session cookie attributes, POST refresh, wrong-password failure,
   logout, and deterministic 401 responses without development bypass.
2. Session/access creates a secondary user so primary fixture credentials do
   not mutate. Use two cookie jars, update credentials, and prove old sessions
   and password fail while the replacement session works.
3. Create API and MCP tokens; prove one-time secret display, prefix-only list
   responses, scope isolation, Authorization precedence, account-control denial
   for Bearer credentials, and immediate revocation.
4. Restart persistence records user, session, tokens, RSS, and Bangumi IDs,
   restarts only the app service, and checks that valid data remains while
   revoked credentials stay revoked.
5. TMDB language selects mock scenarios and exercises real analysis for TV,
   movie, whitespace retry, and same-keyword language changes. Assert both the
   user-facing result and upstream journal.
6. Offset review completes Setup on a dedicated fresh stack, stops the app,
   seeds the real database, runs `run_offset_scan.py` against that work
   directory, and restarts the app. It covers E6/CRC false-positive, E13
   true-positive, and no-signal control cases.
7. Windows delete points the configured downloader at fake-qB. Exercise both
   delete and disable through the public API, assert exact selected hash and
   `deleteFiles`, check database outcomes, and make forced qB failure visible.
8. Every test establishes its own preconditions and uses unique resource names;
   test order can be reversed without changing results.

**Verification**

```bash
python e2e/scripts/stack.py run --profile browser -- \
  uv run --directory backend pytest src/test/e2e/runtime -m e2e -q
```

As an isolation audit, run every collected runtime node ID once by itself and
run modules in reverse order through the stack runner. Do not add a random-order
dependency solely for this check.

## Task 9: Install and Configure Playwright for Hermetic Test Runtime

**Files**

- Modify `webui/package.json` and `webui/pnpm-lock.yaml`.
- Modify `webui/unocss.config.ts`.
- Create `webui/playwright.config.ts`.
- Create `webui/tsconfig.e2e.json`.
- Create `webui/e2e/fixtures/{api.ts,auth.ts,network.ts,test.ts}`.
- Create `webui/e2e/setup/{bootstrap-chromium.setup.ts,bootstrap-webkit.setup.ts}`.
- Create `webui/e2e/specs/production-smoke.spec.ts`.
- Modify `.gitignore` for Playwright output directories.

**Steps**

1. Use `pnpm add -D --save-exact` for `@playwright/test` and
   `@iconify-json/simple-icons`, recording exact versions in both package and
   lock files.
2. Remove the UnoCSS `https://esm.sh/` CDN fallback and load simple-icons from
   the installed JSON package. Prove `pnpm build` succeeds with outbound access
   blocked.
3. Define separate `setup-chromium`/`chromium-desktop` and
   `setup-webkit`/`webkit-mobile` dependency pairs plus `firefox-nightly`.
   WebKit uses a 390×844 iPhone-sized viewport. PR jobs select one pair;
   nightly selects Firefox. Set locale to `en-US`, one worker, zero retries,
   `serviceWorkers: 'block'`, trace/video/screenshot on failure, and a base URL
   supplied by `AB_E2E_BASE_URL`.
   Use `AB_E2E_PROFILE` and spec tags so normal browser jobs exclude the
   `@downloader` scenario, the downloader job selects it explicitly, and
   desktop projects exclude the `@mobile` geometry scenario.
4. Each setup project completes the real wizard through accessible UI controls,
   validates the response contract and cookie flags, then writes its own
   browser-specific storage state. Chromium and WebKit never share one auth
   file. The browser profile configures fake-qB; the downloader profile uses the
   real internal qB endpoint. The auth path includes both browser and stack
   profile, so a downloader invocation never reuses browser-profile state.
5. API fixtures create secondary users and unique resources through public
   endpoints. Network fixtures allow only the app, mock admin, and fake-qB
   origins; an unexpected request fails the test with method and URL.
6. Capture browser console errors and failed responses into per-test artifact
   files. Redact secrets before writing logs.
7. Add a production smoke that checks `/health`, `/#/setup`, and hashed static
   assets before any feature spec runs. This catches a missing version module or
   `dist` staging error directly.

**Verification**

```bash
cd webui && pnpm install --frozen-lockfile
cd webui && pnpm build
cd webui && pnpm exec playwright test --list
cd webui && pnpm test:e2e:typecheck
cd webui && pnpm test:build
cd webui && pnpm lint
cd webui && pnpm format:check
```

## Task 10: Add Browser Authentication and Secret-Lifetime Scenarios

**Files**

- Create `webui/e2e/specs/bootstrap-auth.spec.ts`.
- Create `webui/e2e/specs/session-access.spec.ts`.
- Create `webui/e2e/specs/token-secret.spec.ts`.
- Add accessible labels only where needed in
  `webui/src/components/setup/wizard-container.vue`,
  `webui/src/components/setup/wizard-step-*.vue`,
  `webui/src/components/setting/config-access.vue`.

**Steps**

1. The browser-specific setup project is the sole owner of first-run Setup.
   `bootstrap-auth.spec.ts` starts from its resulting account and covers login
   response secrecy, cookie persistence across reload, wrong password, logout,
   and browser-back protection. It never attempts Setup a second time.
2. Session access uses two independent contexts and a secondary user to prove
   credential updates invalidate prior sessions without destabilizing the
   baseline admin.
3. Token secret creates a token in the Access panel and confirms the full value
   appears only in the reveal modal while the list exposes only its prefix.
4. Close the reveal, navigate away, unmount the component, and return; the
   secret must never reappear.
5. Delay the real create-token response with Playwright routing, navigate away,
   then continue the request. Assert the late promise does not restore secret
   UI or sensitive component state.
6. Setup fields, account/token rows, and dialogs use roles, labels, and
   accessible names; no test ID is added for these flows.

**Verification**

```bash
python e2e/scripts/stack.py run --profile browser -- \
  pnpm --dir webui exec playwright test \
  bootstrap-auth.spec.ts session-access.spec.ts token-secret.spec.ts \
  --project=chromium-desktop
python e2e/scripts/stack.py run --profile browser -- \
  pnpm --dir webui exec playwright test \
  bootstrap-auth.spec.ts token-secret.spec.ts --project=webkit-mobile
```

## Task 11: Add Browser Regressions for Recent UI and Parser Issues

**Files**

- Create `webui/e2e/specs/tmdb-language.spec.ts`.
- Create `webui/e2e/specs/offset-review.spec.ts`.
- Create `webui/e2e/specs/mobile-rule-editor.spec.ts`.
- Create `webui/e2e/specs/player-local-settings.spec.ts`.
- Modify `webui/src/components/basic/ab-bottom-sheet.vue`.
- Modify `webui/src/components/bangumi-preview.vue`.
- Modify `webui/src/components/ab-edit-rule.vue`,
  `webui/src/components/ab-add-rss.vue`,
  `webui/src/components/basic/ab-search.vue`,
  `webui/src/components/search/ab-search-modal.vue`,
  `webui/src/components/setting/config-player.vue`,
  `webui/src/pages/index/config.vue`, and
  `webui/src/pages/index/player.vue`.

**Steps**

1. TMDB language changes parser language from `zh` to `jp`, searches the same
   keyword, and proves TV, movie, and whitespace retry calls use the expected
   language without cross-language cache reuse.
2. Offset review creates two Bangumi through the real analysis/subscribe APIs,
   then PATCHes their complete public update payloads so the E13 rule is marked
   for review and the exact `06v2`/`E931` rule is not. The UI displays a warning
   only for the true mismatch; runtime tests remain responsible for proving how
   those persisted states are calculated.
3. Mobile rule editor runs at 390×844 in WebKit. Assert full-screen panel
   geometry, focus the title, contract viewport height, and prove the panel is
   not translated. Edit, save, reload, and assert persistence.
4. Player settings assert immediate localStorage writes, no config-update or
   restart request, same-context reload persistence, new-context defaults, and
   an unchanged iframe URL loading the dynamically published loopback
   `/player/index.html` fixture marker. Give the iframe a localized accessible
   `title`.
5. Name the bottom-sheet dialog/title and add the single geometry-only
   `data-testid="bottom-sheet-panel"`. Add accessible labels to Bangumi and RSS
   fields, named regions to config sections, a named search dialog/textbox/list,
   and a localized iframe title. Correct any control whose explicit ARIA role
   masks its native button semantics. All other locators use roles, labels, and
   visible names.

**Verification**

```bash
python e2e/scripts/stack.py run --profile browser -- \
  pnpm --dir webui exec playwright test \
  tmdb-language.spec.ts offset-review.spec.ts player-local-settings.spec.ts \
  --project=chromium-desktop
python e2e/scripts/stack.py run --profile browser -- \
  pnpm --dir webui exec playwright test \
  mobile-rule-editor.spec.ts player-local-settings.spec.ts \
  --project=webkit-mobile
```

## Task 12: Exercise Real qBittorrent and Packaged Images

**Files**

- Create `webui/e2e/specs/rss-download-rename.spec.ts`.
- Create `backend/src/test/e2e/downloader/test_release_image_smoke.py`.
- Create `backend/src/test/e2e/downloader/test_qb_image_contract.py`.
- Modify `e2e/fixtures/qbittorrent/qBittorrent.conf`.
- Modify `e2e/fixtures/rss/tiny-download.xml`.

**Steps**

1. Validate the pinned qB image starts with the mounted credentials and all
   peer-discovery/update features disabled. Resolve one supported LinuxServer
   image once, record the complete `<patch-tag>@sha256:<digest>` reference in
   Compose, and make the image-contract test compare that exact shape.
2. Complete Setup with the internal qB endpoint and shared download path.
   This occurs in the downloader invocation's dedicated setup project and fresh
   stack; the feature spec consumes its profile-specific storage state and does
   not run Setup again.
3. Add the local RSS, call the real refresh endpoint, and poll qB until the
   web-seed torrent is complete. No tracker, DHT, or public peer may appear in
   qB state.
4. Poll AutoBangumi API/database/filesystem until the media file is renamed and
   organized. Assert the expected season and episode in both API and path.
5. Refresh the same RSS again and prove the torrent/task count does not grow.
6. Open the WebUI and prove completed state is visible, then delete with files
   enabled and verify qB state, AutoBangumi state, and the shared file are gone.
7. Build the native AutoBangumi image with `3.3.999-e2e.1`, start it with fresh
   volumes, and assert `/health` remains healthy, `db_ok=true`, and the health
   version equals `docker exec ... cat /app/IMAGE_VERSION`.
8. The image test must inspect the locally built image ID and fail if Docker
   attempts to pull `latest` or any public AutoBangumi image.

**Verification**

```bash
python e2e/scripts/stack.py run --profile downloader -- \
  pnpm --dir webui exec playwright test rss-download-rename.spec.ts \
  --project=chromium-desktop
python e2e/scripts/stack.py run --profile downloader -- \
  uv run --directory backend pytest src/test/e2e/downloader -m e2e -q
```

## Task 13: Add Pull-Request and Nightly Workflows

**Files**

- Create `.github/workflows/e2e.yml`.
- Create `.github/workflows/e2e-nightly.yml`.
- Modify `.github/workflows/build.yml`.
- Create `e2e/README.md`.

**Steps**

1. Add `e2e-runtime`, `e2e-browser (chromium)`,
   `e2e-browser (webkit-mobile)`, and `e2e-downloader-image` jobs on every pull
   request without branch or path filters. Set `timeout-minutes: 15` on each
   job.
2. Change the existing backend unit-test job to run
   `pytest -m "not e2e"`. Keep the nested E2E skip guard as defense in depth so
   a normal `pytest` invocation cannot start Docker unexpectedly.
3. Cache uv, pnpm, Playwright browser binaries, frontend output, and Buildx
   layers with lockfile/source-sensitive keys. Install dependencies before
   starting the internal test network.
4. Give every job a unique Compose project and artifact directory derived from
   workflow, job, run ID, attempt, and matrix project.
5. Wrap execution so stack logs and failure artifacts upload with `if: always()`
   even when setup or tests fail. Use 14-day retention.
6. Run zero PR retries. The nightly workflow runs Firefox and repeated browser
   and downloader passes, uploads the same artifacts, and remains non-blocking.
7. Document exact local commands, prerequisites, expected duration, artifact
   locations, mock scenario authoring, fixture regeneration, and qB digest
   update procedure.
8. Keep branch protection unchanged during ten shadow PR runs. Record run URLs,
   result, and wall-clock duration; after 10/10 passes and p95 below 15 minutes,
   make the four named checks required in repository settings.

**Verification**

```bash
rg -n 'timeout-minutes: 15|retention-days: 14' \
  .github/workflows/e2e.yml .github/workflows/e2e-nightly.yml
ruby -e "require 'yaml'; YAML.load_file('.github/workflows/e2e.yml')"
ruby -e "require 'yaml'; YAML.load_file('.github/workflows/e2e-nightly.yml')"
```

## Task 14: Remove the Legacy Workflow and Run the Full Gate

**Files**

- Delete `backend/src/test/e2e/test_e2e_workflow.py`.
- Delete `backend/src/test/e2e/docker-compose.test.yml`.
- Delete `backend/src/test/e2e/mock_rss_server.py`.
- Delete `backend/src/test/e2e/Dockerfile.mock-rss`.
- Delete migrated files under `backend/src/test/e2e/fixtures` after confirming
  their only replacement is under root `e2e/fixtures`.
- Update `backend/src/test/e2e/__init__.py` to describe the new lane split.
- Update `e2e/README.md` with the final command names and artifact paths.

**Steps**

1. Map every meaningful old assertion to a unit, runtime, browser, downloader,
   or image test. Preserve documented compatibility assertions; discard only
   order checks, permissive `(200, 401)` checks, and no-op assertions that do
   not describe a contract.
2. Remove the old session-scoped process, fixed ports/container names,
   `e2e_state`, and numbered methods.
3. Run `audit_sources.py` against the new tree for blind sleeps, public upstream
   hosts, floating image tags, raw secret logging, fixed ports/container names,
   and Playwright retries.
4. Intentionally trigger one mock 501, one browser assertion failure, and one qB
   timeout locally. Confirm the artifact bundle identifies the last observed
   state without an interactive rerun, then restore the assertions.
5. Run backend unit/runtime/downloader suites, WebUI unit/type/lint/build suites,
   both PR browser projects, and the native image smoke.
6. Ask a subagent to review the final diff for correctness, isolation, secret
   handling, flake sources, and divergence from the approved design. Fix every
   actionable finding and rerun the affected lanes.

**Verification**

```bash
python e2e/scripts/audit_sources.py
cd backend && uv run pytest -q
cd backend && uv run ruff check src ../e2e ../scripts/classify_release.py
cd backend && uv run mypy src
cd webui && pnpm test --run
cd webui && pnpm test:build
cd webui && pnpm lint
cd webui && pnpm format:check
python e2e/scripts/stack.py run --profile browser -- \
  uv run --directory backend pytest src/test/e2e/runtime -m e2e -q
python e2e/scripts/stack.py run --profile browser -- \
  pnpm --dir webui exec playwright test --project=chromium-desktop
python e2e/scripts/stack.py run --profile browser -- \
  pnpm --dir webui exec playwright test --project=webkit-mobile
python e2e/scripts/stack.py run --profile downloader -- \
  pnpm --dir webui exec playwright test rss-download-rename.spec.ts \
  --project=chromium-desktop
python e2e/scripts/stack.py run --profile downloader -- \
  uv run --directory backend pytest src/test/e2e/downloader -m e2e -q
```

## Completion Criteria

- #1075 and #1072 are fixed with focused unit/integration regressions.
- #1069, #1068, #1067, #1065, and #1062 have deterministic acceptance tests.
- The old ordered E2E workflow and duplicate fixtures are gone.
- Runtime, Chromium, WebKit mobile, real-qB, and image tests pass locally.
- Test execution produces no public request and uses no floating container tag.
- Failure artifacts contain enough state to diagnose injected failures.
- The four PR jobs complete within 15 minutes and enter the ten-run shadow
  period before branch-protection enforcement.
