# Hermetic E2E tests

The E2E suites run a production-built AutoBangumi image against local,
deterministic upstream services. Docker Compose publishes random loopback ports
and uses an internal network for service-to-service traffic. Tests must not use
public RSS, TMDB, image, player, or downloader endpoints.

## Prerequisites

- Docker Engine with Compose v2
- Python 3.13 and `uv`
- Node.js 20 and pnpm 9.11
- enough disk space for the AutoBangumi, Python, Playwright, and qBittorrent
  images

Install dependencies and browser binaries before starting a stack:

```bash
uv sync --directory backend --locked --group dev
pnpm --dir webui install --frozen-lockfile
pnpm --dir webui exec playwright install --with-deps chromium webkit firefox
```

## Build the production test image

The build helper places the compiled WebUI and generated version module in a
temporary Docker context. It does not write `dist` or
`module/__version__.py` into the source tree.

```bash
pnpm --dir webui run build
python3 e2e/scripts/build_test_image.py \
  --version 3.3.999-e2e.1 \
  --image auto-bangumi:e2e \
  --dist webui/dist
```

## Run a lane locally

Create a fresh project and work directory for every invocation. Reusing a work
directory also reuses setup state, which defeats first-run coverage.

```bash
export LANE=runtime
export AB_E2E_PROJECT="ab-e2e-local-$LANE-$$"
export AB_E2E_WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ab-e2e-$LANE.XXXXXX")"
export AB_E2E_APP_IMAGE=auto-bangumi:e2e
```

Runtime API and process coverage:

```bash
python3 e2e/scripts/stack.py run \
  --profile browser \
  --project-name "$AB_E2E_PROJECT" \
  --work-dir "$AB_E2E_WORK_DIR" \
  -- uv run --directory backend pytest src/test/e2e/runtime -m e2e -q
```

Chromium desktop:

```bash
python3 e2e/scripts/stack.py run \
  --profile browser \
  --project-name "$AB_E2E_PROJECT" \
  --work-dir "$AB_E2E_WORK_DIR" \
  -- pnpm --dir webui run test:e2e:chromium --retries=0
```

WebKit at the 390×844 mobile viewport:

```bash
python3 e2e/scripts/stack.py run \
  --profile browser \
  --project-name "$AB_E2E_PROJECT" \
  --work-dir "$AB_E2E_WORK_DIR" \
  -- pnpm --dir webui run test:e2e:webkit --retries=0
```

Real qBittorrent plus the packaged-image workflow:

```bash
python3 e2e/scripts/stack.py run \
  --profile downloader \
  --project-name "$AB_E2E_PROJECT" \
  --work-dir "$AB_E2E_WORK_DIR" \
  -- python3 e2e/scripts/run_downloader_lane.py
```

The downloader runner executes the focused Chromium download/rename spec and
`backend/src/test/e2e/downloader` inside that same fresh stack.

Firefox is a nightly, non-required lane:

```bash
python3 e2e/scripts/stack.py run \
  --profile browser \
  --project-name "$AB_E2E_PROJECT" \
  --work-dir "$AB_E2E_WORK_DIR" \
  -- pnpm --dir webui run test:e2e --project=firefox-nightly --retries=0
```

The nightly workflow runs browser and downloader twice as separate matrix
passes. Each pass receives a fresh project and work directory; locally, repeat
the corresponding command after recreating both variables above.

Useful lifecycle checks:

```bash
python3 e2e/scripts/stack.py validate --profile browser
python3 e2e/scripts/stack.py validate --profile downloader
python3 e2e/scripts/stack.py smoke --profile browser
python3 e2e/scripts/stack.py ports --profile browser \
  --project-name "$AB_E2E_PROJECT" --work-dir "$AB_E2E_WORK_DIR"
python3 e2e/scripts/stack.py env --profile browser \
  --project-name "$AB_E2E_PROJECT" --work-dir "$AB_E2E_WORK_DIR"
python3 e2e/scripts/stack.py restart --profile browser \
  --project-name "$AB_E2E_PROJECT" --work-dir "$AB_E2E_WORK_DIR" app
python3 e2e/scripts/stack.py stop --profile browser \
  --project-name "$AB_E2E_PROJECT" --work-dir "$AB_E2E_WORK_DIR"
```

## Duration and artifacts

The pull-request checks have a hard 15-minute limit. Typical targets are 5–8
minutes for runtime, 8–12 minutes for each browser, and 10–15 minutes for the
real-downloader/image lane.

`stack.py run` collects diagnostics before Compose teardown, including
Compose state and logs, mock-service request journals, qBittorrent state,
backend logs, and SQLite files. Local stack artifacts are written to
`$AB_E2E_WORK_DIR/artifacts`. Playwright writes screenshots and videos to
`webui/test-results`, with its HTML report in `webui/playwright-report`.
Raw Playwright traces are disabled because they serialize authenticated
storage state and response bodies; token-reveal tests also disable visual
recordings. Browser console errors and failed responses remain available in
the redacted `browser-diagnostics.json` attachment. CI uploads these paths
with `if: always()` and retains them for 14 days. Never print credentials or
session material from a test.

## Legacy workflow migration

The former numbered, session-scoped workflow and its fixed ports were removed.
Setup/auth/config/restart persistence now live in isolated runtime tests;
parser, offset-review, and Windows-path regressions have focused runtime and
browser scenarios; the real qB lane owns download, rename, idempotency, and
file deletion. Endpoint shape, validation, CRUD, empty-list, log, search, and
notification contracts remain in the faster `backend/src/test/test_api_*.py`
unit/integration suites. No test depends on state created by an earlier test.

## Add or change a mock scenario

1. Put static RSS, TMDB, player, torrent, image, or file data under
   `e2e/fixtures`. Fixture URLs must use only Compose service names or
   loopback addresses.
2. Add named TMDB behavior to
   `e2e/fixtures/tmdb/scenarios.json`.
3. Select or reset scenarios through `/__admin/scenario/<name>` and
   `/__admin/reset`; assert requests through
   `/__admin/requests` or `/__admin/state`.
4. Keep responses deterministic and add a contract test for any new endpoint,
   error mode, or request field.
5. Run `python3 e2e/scripts/audit_sources.py` before opening a PR.

Regenerate and verify the deterministic media and torrent assets with:

```bash
python3 e2e/scripts/generate_fixtures.py
python3 e2e/scripts/generate_fixtures.py --check
```

Commit the generated media, torrent, and checksum changes together.

## Update the qBittorrent image digest

The downloader overlay must retain both an exact patch tag and an immutable
manifest digest. To update it:

1. Choose the exact linuxserver/qbittorrent patch release and inspect its
   published manifest:

   ```bash
   docker buildx imagetools inspect linuxserver/qbittorrent:5.2.3
   ```

2. Replace only the tag and `sha256` digest in
   `e2e/compose/downloader.yml`. Never use `latest` or a
   moving major/minor tag.
3. Pull that exact reference, then run the downloader validation and smoke
   checks. Startup verifies the fixed `admin/adminadmin` credentials
   and rejects enabled DHT, PeX, LSD, UPnP, RSS processing, or a changed save
   path.
4. Run the downloader Playwright lane and inspect its artifacts before merging.
