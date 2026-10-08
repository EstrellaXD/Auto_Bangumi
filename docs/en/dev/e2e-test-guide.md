# E2E Test Guide

The end-to-end tests run a production-built AutoBangumi image against local, deterministic upstream services (mock RSS, TMDB, player and qBittorrent). The tests do not use public services. Docker Compose publishes random ports on the loopback address. The services talk to each other on an internal network.

The full guide (all test lanes, diagnostic artifacts, how to add a mock scenario, how to update the qBittorrent image digest) is [`e2e/README.md`](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/e2e/README.md) in the repository. This page gives only the shortest path to run the tests locally.

## Prerequisites

- Docker Engine with Compose v2
- Python 3.13 and `uv`
- Node.js 20 and pnpm 9.11

```bash
uv sync --directory backend --locked --group dev
pnpm --dir webui install --frozen-lockfile
pnpm --dir webui exec playwright install --with-deps chromium webkit firefox
```

## Build the test image

```bash
pnpm --dir webui run build
python3 e2e/scripts/build_test_image.py \
  --version 3.3.999-e2e.1 \
  --image auto-bangumi:e2e \
  --dist webui/dist
```

The build script puts the WebUI build and the generated version module in a temporary Docker context. It does not write them into the source tree.

## Run

Use a new project name and a new work directory for each run. If you use a work directory again, you also use its setup state again, and the first-run coverage is lost.

```bash
export LANE=runtime
export AB_E2E_PROJECT="ab-e2e-local-$LANE-$$"
export AB_E2E_WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ab-e2e-$LANE.XXXXXX")"
export AB_E2E_APP_IMAGE=auto-bangumi:e2e

# Runtime API and process tests
python3 e2e/scripts/stack.py run \
  --profile browser \
  --project-name "$AB_E2E_PROJECT" \
  --work-dir "$AB_E2E_WORK_DIR" \
  -- uv run --directory backend pytest src/test/e2e/runtime -m e2e -q
```

| Lane | Command after `--` | `--profile` |
| --- | --- | --- |
| Runtime | `uv run --directory backend pytest src/test/e2e/runtime -m e2e -q` | `browser` |
| Chromium desktop | `pnpm --dir webui run test:e2e:chromium --retries=0` | `browser` |
| WebKit mobile | `pnpm --dir webui run test:e2e:webkit --retries=0` | `browser` |
| Real qBittorrent and packaged image | `python3 e2e/scripts/run_downloader_lane.py` | `downloader` |

- A normal `pytest` run skips the E2E tests. You must give `-m e2e`.
- `stack.py run` collects diagnostics before it removes the Compose stack. It writes them to `$AB_E2E_WORK_DIR/artifacts`. Playwright writes screenshots and videos to `webui/test-results`, and the HTML report to `webui/playwright-report`.
- To stop a stack: `python3 e2e/scripts/stack.py stop --profile browser --project-name "$AB_E2E_PROJECT" --work-dir "$AB_E2E_WORK_DIR"`.

## CI

`.github/workflows/e2e.yml` runs the runtime lane, the browser lanes (Chromium, WebKit mobile) and the real-downloader lane on each PR. `e2e-nightly.yml` runs the Firefox lane each night. It also runs the browser lane and the downloader lane two times each, as separate passes. The faster contract tests for endpoint structure and validation stay in `backend/src/test/test_api_*.py`.
