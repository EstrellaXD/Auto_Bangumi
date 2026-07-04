"""Shared fixtures for E2E integration tests.

These tests require Docker (qBittorrent + mock RSS server) and run
AutoBangumi as a real subprocess with isolated config/data directories.

Run with:  cd backend && uv run pytest -m e2e -v
"""

import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

# ---------------------------------------------------------------------------
# Auto-skip E2E tests unless explicitly selected
# ---------------------------------------------------------------------------

E2E_DIR = Path(__file__).parent


def pytest_collection_modifyitems(config, items):
    """Skip E2E tests unless -m e2e is specified."""
    marker_expr = config.getoption("-m", default="")
    if "e2e" in marker_expr:
        return
    skip = pytest.mark.skip(reason="E2E tests require: pytest -m e2e")
    for item in items:
        if "e2e" in item.keywords:
            item.add_marker(skip)


# ---------------------------------------------------------------------------
# Test credentials (used in setup and login)
# ---------------------------------------------------------------------------

E2E_USERNAME = "testadmin"
E2E_PASSWORD = "testpassword123"

# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_tmpdir(tmp_path_factory):
    """Session-scoped temp directory for AB config/data isolation."""
    return tmp_path_factory.mktemp("e2e")


@pytest.fixture(scope="session")
def docker_services():
    """Start and stop Docker Compose test infrastructure."""
    compose_file = E2E_DIR / "docker-compose.test.yml"

    # Build mock RSS image
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "build"],
        check=True,
        capture_output=True,
    )

    # Start services and wait for health checks
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d", "--wait"],
        check=True,
        timeout=120,
    )

    yield

    # Teardown
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "down", "-v"],
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="session")
def qb_password(docker_services):
    """Extract the auto-generated password from qBittorrent container logs."""
    for _ in range(30):
        result = subprocess.run(
            ["docker", "logs", "ab-test-qbittorrent"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines() + result.stderr.splitlines():
            if "temporary password" in line.lower():
                return line.split(":")[-1].strip()
        time.sleep(2)
    pytest.fail("Could not extract qBittorrent temporary password from Docker logs")


@pytest.fixture(scope="session")
def ab_process(e2e_tmpdir, docker_services):
    """Start AutoBangumi as a subprocess with isolated config/data dirs.

    Uses CWD-based isolation: main.py resolves config/ and data/ relative
    to the working directory, so we create those dirs in a temp location
    and run the process from there.
    """
    work_dir = e2e_tmpdir / "ab_workdir"
    work_dir.mkdir()
    (work_dir / "config").mkdir()
    (work_dir / "data").mkdir()

    # main.py mounts StaticFiles for dist/assets and dist/images when
    # VERSION != "DEV_VERSION".  Create dummy dirs so the mounts succeed
    # (the E2E tests only exercise the API, not the frontend).
    dist_dir = work_dir / "dist"
    dist_dir.mkdir()
    (dist_dir / "assets").mkdir()
    (dist_dir / "images").mkdir()
    # Jinja2Templates requires at least one template file
    (dist_dir / "index.html").write_text("<html><body>e2e stub</body></html>")

    # backend/src/ is the directory containing main.py and module/
    src_dir = Path(__file__).resolve().parents[2]

    proc = subprocess.Popen(
        [sys.executable, str(src_dir / "main.py")],
        cwd=str(work_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for AutoBangumi to be ready (poll setup status endpoint)
    ready = False
    for _ in range(30):
        try:
            resp = httpx.get("http://localhost:7892/api/v1/setup/status", timeout=3.0)
            if resp.status_code == 200:
                ready = True
                break
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(1)

    if not ready:
        proc.terminate()
        stdout, stderr = proc.communicate(timeout=5)
        pytest.fail(
            f"AutoBangumi did not start within 30s.\n"
            f"stdout: {stdout.decode(errors='replace')[-2000:]}\n"
            f"stderr: {stderr.decode(errors='replace')[-2000:]}"
        )

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


@pytest.fixture(scope="session")
def api_client(ab_process):
    """HTTP client pointing at the running AutoBangumi instance.

    Maintains cookies across requests so that the auth token (set via
    Set-Cookie on login) is automatically included in subsequent calls.
    """
    with httpx.Client(base_url="http://localhost:7892", timeout=10.0) as client:
        yield client


@pytest.fixture(scope="session")
def e2e_state():
    """Mutable dict for sharing state across ordered E2E tests."""
    return {}
