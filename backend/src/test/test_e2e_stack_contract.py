"""Pure contract tests for the hermetic E2E stack infrastructure."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
E2E = ROOT / "e2e"
PYTHON_IMAGE = (
    "python:3.13.14-alpine3.23@sha256:"
    "9fdbf2e3e82628351513560b121e2ee6ce31cac212be9e070c5a5e2769fb5e76"
)
QB_IMAGE = (
    "linuxserver/qbittorrent:5.2.3@sha256:"
    "2e074403c7b72e6d89cee3d0d41a47f7b5708c6a9e5316f3958c90765cbe12ce"
)


def _load_script(name: str):
    path = E2E / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"e2e_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_compose_files_are_isolated_and_use_random_loopback_ports():
    browser = (E2E / "compose" / "browser.yml").read_text()
    downloader = (E2E / "compose" / "downloader.yml").read_text()

    assert "internal: true" in browser
    assert "container_name" not in browser + downloader
    assert ":latest" not in browser + downloader
    assert '"127.0.0.1::17892"' in browser
    assert '"127.0.0.1::18888"' in browser
    assert '"127.0.0.1::18080"' in browser
    assert '"127.0.0.1::28080"' in downloader
    assert not re.search(r"127\.0\.0\.1:(?!0:)\d+:\d+", browser + downloader)
    for setting in (
        "AB_DOWNLOADER_HOST",
        "AB_DOWNLOADER_USERNAME",
        "AB_DOWNLOADER_PASSWORD",
        "AB_DOWNLOAD_PATH",
        "AB_INTERVAL_TIME",
        "AB_RENAME_FREQ",
        "AB_DEBUG_MODE",
    ):
        assert setting not in browser + downloader
    assert QB_IMAGE in downloader


def test_support_service_images_are_pinned_and_dependency_free():
    for relative in (
        "mock-upstream/Dockerfile",
        "fake-qb/Dockerfile",
        "port-proxy/Dockerfile",
    ):
        dockerfile = (E2E / relative).read_text()
        assert f"FROM {PYTHON_IMAGE}" in dockerfile
        assert "pip install" not in dockerfile
        assert "apk add" not in dockerfile
        assert "server.py" in dockerfile


def test_qbittorrent_fixture_has_fixed_credentials_and_disables_peer_discovery():
    config = (E2E / "fixtures/qbittorrent/qBittorrent.conf").read_text()

    assert "WebUI\\Username=admin" in config
    assert (
        'WebUI\\Password_PBKDF2="@ByteArray('
        "ARQ77eY1NUZaQsuDHbIMCA==:"
        "0WMRkYTUWVT9wVvdDtHAjU9b3b7uB8NR1Gur2hmQCvCDpm39Q+PsJRJPaCU51dEiz+"
        'dTzh8qbPsL8WkFljQYFQ==)"'
    ) in config
    assert "DHTEnabled=false" in config
    assert "PeXEnabled=false" in config
    assert "LSDEnabled=false" in config
    assert "PortForwardingEnabled=false" in config
    assert "CheckForUpdates=false" in config


def test_build_context_stages_dist_and_version_without_touching_source(tmp_path):
    build = _load_script("build_test_image")
    repo = tmp_path / "repo"
    context = tmp_path / "context"
    dist = tmp_path / "dist"
    tracked = (
        Path(".dockerignore"),
        Path("Dockerfile"),
        Path("entrypoint.sh"),
        Path("backend/pyproject.toml"),
        Path("backend/uv.lock"),
        Path("backend/src/main.py"),
        Path("backend/src/module/example.py"),
    )
    for relative in tracked:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"fixture:{relative}\n")
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<main>e2e</main>")
    (dist / "assets/app.js").write_text("console.log('e2e')")

    build.prepare_context(
        repo,
        dist,
        context,
        version="3.3.999-e2e.1",
        tracked_files=tracked,
    )

    assert (context / "backend/src/dist/index.html").is_file()
    assert (context / "backend/src/dist/assets/app.js").is_file()
    assert (context / "backend/src/module/__version__.py").read_text() == (
        'VERSION = "3.3.999-e2e.1"\n'
    )
    assert not (repo / "backend/src/dist").exists()
    assert not (repo / "backend/src/module/__version__.py").exists()


def test_build_inputs_ignore_tracked_files_deleted_in_the_worktree(
    tmp_path,
    monkeypatch,
):
    build = _load_script("build_test_image")
    repo = tmp_path / "repo"
    (repo / "backend").mkdir(parents=True)
    (repo / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    class Result:
        stdout = b"Dockerfile\0backend/deleted.py\0"

    monkeypatch.setattr(build.subprocess, "run", lambda *_args, **_kwargs: Result())

    assert build.tracked_backend_files(repo) == (Path("Dockerfile"),)


def test_build_command_uses_only_the_temporary_context(tmp_path):
    build = _load_script("build_test_image")

    command = build.build_command(
        tmp_path / "context",
        image="auto-bangumi:e2e",
        version="3.3.999-e2e.1",
    )

    assert command[:2] == ["docker", "build"]
    assert ["--build-arg", "VERSION=3.3.999-e2e.1"] == command[2:4]
    assert ["--tag", "auto-bangumi:e2e"] == command[4:6]
    assert command[-1] == str(tmp_path / "context")


def test_stack_builds_unique_compose_commands_and_environment(tmp_path):
    stack_module = _load_script("stack")
    first_name = stack_module.unique_project_name("browser")
    second_name = stack_module.unique_project_name("browser")
    assert first_name != second_name
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", first_name)

    stack = stack_module.Stack(
        profile="downloader",
        repo_root=ROOT,
        work_dir=tmp_path / "work",
        project_name="ab-e2e-downloader-test",
    )
    command = stack.compose_command("config")

    assert command[:4] == [
        "docker",
        "compose",
        "--project-name",
        "ab-e2e-downloader-test",
    ]
    assert str(E2E / "compose/browser.yml") in command
    assert str(E2E / "compose/downloader.yml") in command
    assert command[-1] == "config"
    assert stack.environment["AB_E2E_CONFIG_DIR"] == str(
        (tmp_path / "work/config").resolve()
    )
    assert stack.environment["AB_E2E_WORK_DIR"] == str((tmp_path / "work").resolve())
    assert stack.environment["AB_E2E_DOWNLOAD_DIR"] == str(
        (tmp_path / "work/downloads").resolve()
    )
    assert stack.environment["AB_E2E_LOG_FILE"] == str(
        (tmp_path / "work/logs/log.txt").resolve()
    )
    assert stack.environment["AB_E2E_USERNAME"] == "testadmin"
    assert stack.environment["AB_E2E_PASSWORD"] == "testpassword123"
    stack._publish_urls(
        {"app": 40001, "mock-upstream": 40002, "fake-qb": 40003, "qbittorrent": 40004}
    )
    assert stack.environment["AB_E2E_REAL_QB_URL"] == "http://127.0.0.1:40004"
    assert stack.environment["AB_E2E_QB_URL"] == "http://127.0.0.1:40004"


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("127.0.0.1:49152", 49152),
        ("0.0.0.0:32768", 32768),
        ("[::1]:60000", 60000),
    ],
)
def test_stack_parses_dynamic_compose_ports(output, expected):
    stack_module = _load_script("stack")
    assert stack_module.parse_published_port(output) == expected


def test_qb_runtime_contract_checks_credentials_and_deterministic_preferences():
    stack_module = _load_script("stack")
    preferences = {
        "dht": False,
        "pex": False,
        "lsd": False,
        "upnp": False,
        "save_path": "/downloads/Bangumi",
        "rss_processing_enabled": False,
        "rss_auto_downloading_enabled": False,
    }

    stack_module.validate_qb_preferences(preferences)
    with pytest.raises(AssertionError, match="unsafe or non-deterministic"):
        stack_module.validate_qb_preferences({**preferences, "dht": True})


def test_qb_runtime_contract_accepts_login_204_and_checks_preferences(monkeypatch):
    stack_module = _load_script("stack")
    preferences = {
        "dht": False,
        "pex": False,
        "lsd": False,
        "upnp": False,
        "save_path": "/downloads/Bangumi",
        "rss_processing_enabled": False,
        "rss_auto_downloading_enabled": False,
    }

    class Response:
        def __init__(self, status, payload):
            self.status = status
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.payload

    class Opener:
        def __init__(self):
            self.calls = []

        def open(self, request, timeout):
            self.calls.append((request, timeout))
            if not isinstance(request, str):
                return Response(204, b"")
            return Response(200, __import__("json").dumps(preferences).encode())

    opener = Opener()
    monkeypatch.setattr(
        stack_module.urllib.request,
        "build_opener",
        lambda *_handlers: opener,
    )

    assert stack_module.verify_qb_runtime("http://127.0.0.1:12345") == preferences
    assert len(opener.calls) == 2


def test_run_with_stack_always_stops_after_command_failure():
    stack_module = _load_script("stack")

    class FakeStack:
        started = False
        stopped = False
        environment = {"AB_E2E_BASE_URL": "http://127.0.0.1:1"}

        def start(self):
            self.started = True

        def stop(self, *, collect=True):
            assert collect is True
            self.stopped = True

    fake = FakeStack()

    def fail(_command, _environment):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        stack_module.run_with_stack(fake, ["pytest"], runner=fail)

    assert fake.started is True
    assert fake.stopped is True


def test_run_with_stack_stops_after_start_failure():
    stack_module = _load_script("stack")

    class FakeStack:
        stopped = False
        environment = {}

        def start(self):
            raise RuntimeError("startup failed")

        def stop(self, *, collect=True):
            assert collect is True
            self.stopped = True

    fake = FakeStack()

    with pytest.raises(RuntimeError, match="startup failed"):
        stack_module.run_with_stack(fake, ["pytest"])

    assert fake.stopped is True


def test_partial_compose_start_collects_before_teardown(tmp_path, monkeypatch):
    stack_module = _load_script("stack")
    events = []

    def runner(command, **_kwargs):
        if "build" in command:
            events.append("build")
            return None
        if "up" in command:
            events.append("up")
            raise RuntimeError("compose health check failed")
        if "down" in command:
            events.append("down")
            return None
        raise AssertionError(f"Unexpected command: {command!r}")

    stack = stack_module.Stack(
        profile="browser",
        repo_root=ROOT,
        work_dir=tmp_path / "partial-start",
        project_name="ab-e2e-partial-start",
        runner=runner,
    )
    monkeypatch.setattr(stack, "collect", lambda: events.append("collect"))

    with pytest.raises(RuntimeError, match="compose health check failed"):
        stack_module.run_with_stack(stack, ["pytest"])

    assert events == ["build", "up", "collect", "down"]


def test_run_with_stack_handles_sigterm_and_restores_handlers(monkeypatch):
    stack_module = _load_script("stack")
    installed = {}
    signal_calls = []
    monkeypatch.setattr(
        stack_module.signal,
        "getsignal",
        lambda signum: f"previous-{signum}",
    )

    def install(signum, handler):
        installed[signum] = handler
        signal_calls.append((signum, handler))

    monkeypatch.setattr(stack_module.signal, "signal", install)

    class FakeStack:
        environment = {}

        def __init__(self):
            self.stop_count = 0

        def start(self):
            return None

        def stop(self, *, collect=True):
            assert collect is True
            self.stop_count += 1

    fake = FakeStack()

    def terminate(_command, _environment):
        installed[stack_module.signal.SIGTERM](stack_module.signal.SIGTERM, None)

    with pytest.raises(SystemExit):
        stack_module.run_with_stack(fake, ["pytest"], runner=terminate)

    assert fake.stop_count >= 1
    assert signal_calls[-2:] == [
        (
            stack_module.signal.SIGINT,
            f"previous-{stack_module.signal.SIGINT}",
        ),
        (
            stack_module.signal.SIGTERM,
            f"previous-{stack_module.signal.SIGTERM}",
        ),
    ]


def test_artifact_redaction_removes_credentials_and_tokens():
    artifacts = _load_script("collect_artifacts")
    raw = (
        "password=adminadmin Authorization: Bearer api-secret "
        "Cookie: SID=session-secret token=raw-token"
    )

    redacted = artifacts.redact_text(raw, secrets=("adminadmin",))

    for secret in ("adminadmin", "api-secret", "session-secret", "raw-token"):
        assert secret not in redacted
    assert redacted.count("[REDACTED]") >= 4


def test_static_audit_accepts_the_real_e2e_tree():
    audit = _load_script("audit_sources")
    assert audit.audit_repository(ROOT) == []


def test_static_audit_reports_fixed_ports_floating_images_and_blind_waits(tmp_path):
    audit = _load_script("audit_sources")
    (tmp_path / "e2e/compose").mkdir(parents=True)
    (tmp_path / "e2e/scripts").mkdir(parents=True)
    (tmp_path / "e2e/compose/bad.yml").write_text(
        "services:\n"
        "  bad:\n"
        "    container_name: fixed\n"
        "    image: example/tool:latest\n"
        '    ports: ["127.0.0.1:8080:8080"]\n'
    )
    (tmp_path / "e2e/scripts/bad.py").write_text("time.sleep(10)\n")

    messages = [finding.message for finding in audit.audit_repository(tmp_path)]

    assert any("container_name" in message for message in messages)
    assert any("floating image" in message for message in messages)
    assert any("fixed host port" in message for message in messages)
    assert any("blind sleep" in message for message in messages)
