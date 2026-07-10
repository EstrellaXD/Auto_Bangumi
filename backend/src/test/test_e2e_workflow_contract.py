"""Pure source contracts for the hermetic E2E GitHub workflows."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PR_WORKFLOW = REPO_ROOT / ".github/workflows/e2e.yml"
NIGHTLY_WORKFLOW = REPO_ROOT / ".github/workflows/e2e-nightly.yml"
BUILD_WORKFLOW = REPO_ROOT / ".github/workflows/build.yml"
PLAYWRIGHT_CONFIG = REPO_ROOT / "webui/playwright.config.ts"
DOWNLOADER_RUNNER = REPO_ROOT / "e2e/scripts/run_downloader_lane.py"
E2E_README = REPO_ROOT / "e2e/README.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _workflow_header(source: str) -> str:
    header, separator, _ = source.partition("\njobs:\n")
    assert separator, "workflow must contain a top-level jobs mapping"
    return header


def _job(source: str, job_id: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(job_id)}:\n"
        rf"(?P<body>.*?)(?=^  [a-z0-9][a-z0-9-]*:\n|\Z)",
        source,
    )
    assert match, f"missing workflow job: {job_id}"
    return match.group("body")


def test_pr_workflow_runs_for_every_pull_request() -> None:
    source = _read(PR_WORKFLOW)
    header = _workflow_header(source)

    assert re.search(r"(?m)^  pull_request: \{\}$", header)
    assert "schedule:" not in header
    assert not re.search(
        r"(?m)^\s+(?:branches|branches-ignore|paths|paths-ignore):",
        header,
    )


def test_pr_workflow_expands_to_four_stable_fifteen_minute_checks() -> None:
    source = _read(PR_WORKFLOW)
    runtime = _job(source, "e2e-runtime")
    browser = _job(source, "e2e-browser")
    downloader = _job(source, "e2e-downloader-image")

    assert "name: e2e-runtime" in runtime
    assert "name: e2e-browser (${{ matrix.project }})" in browser
    assert "project: chromium" in browser
    assert "project: webkit-mobile" in browser
    assert "name: e2e-downloader-image" in downloader

    for job in (runtime, browser, downloader):
        assert "timeout-minutes: 15" in job
        assert not re.search(r"(?m)^    continue-on-error:", job)


def test_pr_jobs_use_unique_stack_and_work_directory_names() -> None:
    source = _read(PR_WORKFLOW)

    for job_id in ("e2e-runtime", "e2e-browser", "e2e-downloader-image"):
        job = _job(source, job_id)
        assert "AB_E2E_PROJECT:" in job
        assert "AB_E2E_WORK_DIR" in job
        assert "github.run_id" in job
        assert "github.run_attempt" in job
        assert "RUNNER_TEMP" in job
        assert '--project-name "$AB_E2E_PROJECT"' in job
        assert '--work-dir "$AB_E2E_WORK_DIR"' in job
        assert "Ensure stack teardown" in job
        assert "if: always()" in job

    browser = _job(source, "e2e-browser")
    assert "matrix.project" in browser


def test_pr_commands_match_the_repository_entry_points() -> None:
    source = _read(PR_WORKFLOW)
    runtime = _job(source, "e2e-runtime")
    browser = _job(source, "e2e-browser")
    downloader = _job(source, "e2e-downloader-image")

    for job in (runtime, browser, downloader):
        assert "e2e/scripts/build_test_image.py" in job
        assert "e2e/scripts/stack.py run" in job
        assert "e2e/scripts/collect_artifacts.py" in job

    assert "uv run --directory backend pytest src/test/e2e/runtime -m e2e" in runtime
    assert "script: test:e2e:chromium" in browser
    assert "script: test:e2e:webkit" in browser
    assert 'pnpm --dir webui run "${{ matrix.script }}"' in browser
    assert "--profile downloader" in downloader
    assert "python3 e2e/scripts/run_downloader_lane.py" in downloader

    runner = _read(DOWNLOADER_RUNNER)
    assert '"rss-download-rename.spec.ts"' in runner
    assert '"--project=chromium-desktop"' in runner
    assert '"src/test/e2e/downloader"' in runner
    assert '"--junitxml=' in runner


def test_pr_dependencies_and_generated_outputs_are_cached() -> None:
    source = _read(PR_WORKFLOW)
    runtime = _job(source, "e2e-runtime")
    browser = _job(source, "e2e-browser")
    downloader = _job(source, "e2e-downloader-image")

    for job in (runtime, downloader):
        assert "astral-sh/setup-uv@v4" in job
        assert "enable-cache: true" in job
        assert "cache-dependency-glob: backend/uv.lock" in job
        assert "uv sync --directory backend --locked --group dev" in job

    for job in (runtime, browser, downloader):
        assert "pnpm/action-setup@v4" in job
        assert "cache: pnpm" in job
        assert "cache-dependency-path: webui/pnpm-lock.yaml" in job
        assert "pnpm --dir webui install --frozen-lockfile" in job
        assert "path: webui/dist" in job
        assert "AB_E2E_IMAGE_ARCHIVE" in job
        assert "backend/src/**" in job
        assert "webui/src/**" in job

    for job in (browser, downloader):
        assert "PLAYWRIGHT_BROWSERS_PATH" in job
        assert "playwright install --with-deps" in job
        assert "hashFiles('webui/pnpm-lock.yaml')" in job


def test_pr_browser_runs_have_zero_retries_and_fourteen_day_artifacts() -> None:
    source = _read(PR_WORKFLOW)
    browser = _job(source, "e2e-browser")
    downloader = _job(source, "e2e-downloader-image")
    downloader_runner = _read(DOWNLOADER_RUNNER)

    assert source.count("--retries=0") == 1
    assert downloader_runner.count('"--retries=0"') == 1
    for command_source in (source, downloader_runner):
        assert "-- --retries" not in command_source
        assert not re.search(r"--retries(?:=|\s+)[1-9][0-9]*", command_source)
    for job in (_job(source, "e2e-runtime"), browser, downloader):
        assert "uses: actions/upload-artifact@v4" in job
        assert "retention-days: 14" in job
        assert "if-no-files-found: warn" in job
        assert "if: always()" in job

    playwright = _read(PLAYWRIGHT_CONFIG)
    assert re.search(r"\bretries:\s*0\b", playwright)
    assert re.search(r"\bworkers:\s*1\b", playwright)


def test_nightly_is_non_pr_non_blocking_and_repeats_fresh_stacks() -> None:
    source = _read(NIGHTLY_WORKFLOW)
    header = _workflow_header(source)
    job = _job(source, "e2e-nightly")

    assert "pull_request:" not in header
    assert "schedule:" in header
    assert "workflow_dispatch:" in header
    assert "continue-on-error: true" in job
    assert "timeout-minutes: 15" in job
    assert job.count("lane: firefox") == 1
    assert job.count("lane: browser") == 2
    assert job.count("lane: downloader") == 2
    assert job.count("pass: 2") == 2
    assert "playwright-project: firefox-nightly" in job
    assert "playwright-project: chromium-desktop" in job
    assert "--retries=0" in job
    assert "run test:e2e -- --project" not in job
    assert "AB_E2E_PROJECT:" in job
    assert "matrix.lane" in job
    assert "matrix.pass" in job
    assert "github.run_id" in job
    assert "github.run_attempt" in job
    assert "retention-days: 14" in job
    assert "if: always()" in job
    assert not re.search(r"--retries(?:=|\s+)[1-9][0-9]*", source)


def test_normal_backend_workflow_excludes_e2e_tests() -> None:
    source = _read(BUILD_WORKFLOW)
    assert re.search(
        r'uv run pytest src/test -v -m ["\']not e2e["\']',
        source,
    )


def test_readme_documents_local_operation_and_maintenance() -> None:
    source = _read(E2E_README)

    for command in (
        "e2e/scripts/build_test_image.py",
        "e2e/scripts/stack.py run",
        "pytest src/test/e2e/runtime -m e2e",
        "test:e2e:chromium",
        "test:e2e:webkit",
        "--project=firefox-nightly",
        "e2e/scripts/generate_fixtures.py --check",
        "e2e/scripts/audit_sources.py",
        "docker buildx imagetools inspect",
    ):
        assert command in source

    assert "$AB_E2E_WORK_DIR/artifacts" in source
    assert "webui/playwright-report" in source
    assert "14 days" in source
    assert "15-minute" in source
    assert "sha256" in source
    assert "admin/adminadmin" in source
