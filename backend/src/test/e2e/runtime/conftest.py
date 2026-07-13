"""Function-scoped fixtures for independently runnable runtime E2E tests."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from test.e2e.support import (
    E2E_FIXTURES,
    REPO_ROOT,
    BackendSandbox,
    HttpService,
    load_script,
)


@pytest.fixture
def backend_factory(
    tmp_path: Path,
) -> Generator[Callable[..., BackendSandbox], None, None]:
    sandboxes: list[BackendSandbox] = []

    def create() -> BackendSandbox:
        sandbox = BackendSandbox(tmp_path / f"backend-{len(sandboxes) + 1}")
        sandboxes.append(sandbox)
        sandbox.start()
        return sandbox

    yield create

    for sandbox in reversed(sandboxes):
        sandbox.close()


@pytest.fixture
def mock_upstream() -> Generator[HttpService, None, None]:
    namespace = load_script(REPO_ROOT / "e2e" / "mock-upstream" / "server.py")
    server = namespace["create_server"]("127.0.0.1", 0, E2E_FIXTURES)
    service = HttpService(server).start()
    try:
        yield service
    finally:
        service.close()


@pytest.fixture
def twelve_episode_upstream(
    tmp_path: Path,
) -> Generator[HttpService, None, None]:
    """Mock TMDB whose single season has twelve already-aired episodes."""

    fixture_root = tmp_path / "twelve-episode-fixtures"
    shutil.copytree(E2E_FIXTURES, fixture_root)
    scenario_path = fixture_root / "tmdb" / "scenarios.json"
    scenarios = json.loads(scenario_path.read_text(encoding="utf-8"))
    scenarios["season"]["episodes"] = [
        {"episode_number": episode, "air_date": f"2026-06-{episode:02d}"}
        for episode in range(1, 13)
    ]
    scenario_path.write_text(
        json.dumps(scenarios, ensure_ascii=False),
        encoding="utf-8",
    )

    namespace = load_script(REPO_ROOT / "e2e" / "mock-upstream" / "server.py")
    server = namespace["create_server"]("127.0.0.1", 0, fixture_root)
    service = HttpService(server).start()
    try:
        yield service
    finally:
        service.close()


@pytest.fixture
def fake_qb() -> Generator[HttpService, None, None]:
    namespace = load_script(REPO_ROOT / "e2e" / "fake-qb" / "server.py")
    server = namespace["create_server"]("127.0.0.1", 0)
    service = HttpService(server, ready_path="/__admin/state").start()
    try:
        yield service
    finally:
        service.close()
