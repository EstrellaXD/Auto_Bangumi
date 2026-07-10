#!/usr/bin/env python3
"""Lifecycle controller for isolated AutoBangumi E2E Compose stacks."""

from __future__ import annotations

import argparse
import http.cookiejar
import importlib.util
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Mapping, Sequence

PROFILES = {"browser", "downloader"}
DEFAULT_WAIT_SECONDS = 120
QB_EXPECTED_PREFERENCES = {
    "dht": False,
    "pex": False,
    "lsd": False,
    "upnp": False,
    "save_path": "/downloads/Bangumi",
    "rss_processing_enabled": False,
    "rss_auto_downloading_enabled": False,
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def unique_project_name(profile: str) -> str:
    if profile not in PROFILES:
        raise ValueError(f"Unknown E2E profile: {profile}")
    raw = f"ab-e2e-{profile}-{os.getpid()}-{secrets.token_hex(4)}".lower()
    normalized = re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")
    return normalized[:63].rstrip("-")


def parse_published_port(output: str) -> int:
    match = re.search(r":(\d+)\s*$", output.strip())
    if not match:
        raise ValueError(f"Cannot parse Docker Compose published port: {output!r}")
    port = int(match.group(1))
    if not 1 <= port <= 65535:
        raise ValueError(f"Published port is out of range: {port}")
    return port


def validate_qb_preferences(preferences: Mapping[str, object]) -> None:
    mismatches = {
        key: {"expected": expected, "actual": preferences.get(key)}
        for key, expected in QB_EXPECTED_PREFERENCES.items()
        if preferences.get(key) != expected
    }
    if mismatches:
        raise AssertionError(
            "qBittorrent E2E preferences are unsafe or non-deterministic: "
            f"{json.dumps(mismatches, sort_keys=True)}"
        )


def verify_qb_runtime(
    base_url: str,
    *,
    username: str = "admin",
    password: str = "adminadmin",
) -> dict[str, object]:
    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/v2/auth/login",
        data=urllib.parse.urlencode(
            {"username": username, "password": password}
        ).encode("utf-8"),
    )
    with opener.open(request, timeout=5) as response:
        body = response.read().decode("utf-8", errors="replace").strip()
        if response.status not in (200, 204) or (
            response.status == 200 and body.lower() != "ok."
        ):
            raise AssertionError(
                f"qBittorrent rejected fixed E2E credentials: "
                f"HTTP {response.status} {body!r}"
            )
    with opener.open(
        f"{base_url.rstrip('/')}/api/v2/app/preferences", timeout=5
    ) as response:
        preferences = json.loads(response.read().decode("utf-8"))
    if not isinstance(preferences, dict):
        raise AssertionError("qBittorrent preferences response is not an object")
    validate_qb_preferences(preferences)
    return preferences


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        values[key] = str(value)
    return values


def _write_env_file(path: Path, values: Mapping[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in sorted(values.items()):
        if "\n" in value or "\r" in value:
            raise ValueError(f"Environment value for {key} contains a newline")
        lines.append(f"{key}={json.dumps(value)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_artifact_module(repo_root: Path):
    path = repo_root / "e2e/scripts/collect_artifacts.py"
    spec = importlib.util.spec_from_file_location("ab_e2e_collect_artifacts", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load artifact collector: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Stack:
    """One Compose project with isolated bind mounts and dynamic host ports."""

    def __init__(
        self,
        *,
        profile: str,
        repo_root: Path | None = None,
        work_dir: Path | None = None,
        project_name: str | None = None,
        runner=subprocess.run,
    ) -> None:
        if profile not in PROFILES:
            raise ValueError(f"Unknown E2E profile: {profile}")
        self.profile = profile
        self.repo_root = (repo_root or repository_root()).resolve()
        self.project_name = project_name or unique_project_name(profile)
        self.work_dir = (
            work_dir.resolve()
            if work_dir is not None
            else Path(tempfile.mkdtemp(prefix=f"{self.project_name}-")).resolve()
        )
        self.config_dir = self.work_dir / "config"
        self.data_dir = self.work_dir / "data"
        self.download_dir = self.work_dir / "downloads"
        self.log_dir = self.work_dir / "logs"
        self.log_file = self.log_dir / "log.txt"
        self.qb_config_dir = self.work_dir / "qb-config"
        self.artifact_dir = self.work_dir / "artifacts"
        self.env_file = self.work_dir / "stack.env"
        self._runner = runner
        self._started = False

        for directory in (
            self.config_dir,
            self.data_dir,
            self.download_dir,
            self.log_dir,
            self.qb_config_dir,
            self.artifact_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        self.log_file.touch(exist_ok=True)
        self._install_qb_config()

        existing = _read_env_file(self.env_file)
        self.environment: dict[str, str] = {
            "AB_E2E_PROFILE": self.profile,
            "AB_E2E_PROJECT": self.project_name,
            "AB_E2E_CONFIG_DIR": str(self.config_dir),
            "AB_E2E_DATA_DIR": str(self.data_dir),
            "AB_E2E_DOWNLOAD_DIR": str(self.download_dir),
            "AB_E2E_LOG_FILE": str(self.log_file),
            "AB_E2E_QB_CONFIG_DIR": str(self.qb_config_dir),
            "AB_E2E_FIXTURES_DIR": str(self.repo_root / "e2e/fixtures"),
            "AB_E2E_ARTIFACT_DIR": str(self.artifact_dir),
            "AB_E2E_USERNAME": "testadmin",
            "AB_E2E_PASSWORD": "testpassword123",
            "AB_E2E_APP_IMAGE": os.environ.get("AB_E2E_APP_IMAGE", "auto-bangumi:e2e"),
            "AB_E2E_MOCK_IMAGE": os.environ.get(
                "AB_E2E_MOCK_IMAGE", f"{self.project_name}/mock-upstream:local"
            ),
            "AB_E2E_FAKE_QB_IMAGE": os.environ.get(
                "AB_E2E_FAKE_QB_IMAGE", f"{self.project_name}/fake-qb:local"
            ),
            "AB_E2E_PUID": str(getattr(os, "getuid", lambda: 1000)()),
            "AB_E2E_PGID": str(getattr(os, "getgid", lambda: 1000)()),
            "AB_E2E_MOCK_INTERNAL_URL": "http://mock-upstream:18888",
            "AB_E2E_FAKE_QB_INTERNAL_URL": "http://fake-qb:8080",
            "AB_E2E_QB_INTERNAL_URL": "http://qbittorrent:8080",
            **existing,
        }
        self.write_environment()

    @property
    def compose_files(self) -> tuple[Path, ...]:
        files = (self.repo_root / "e2e/compose/browser.yml",)
        if self.profile == "downloader":
            files += (self.repo_root / "e2e/compose/downloader.yml",)
        return files

    @property
    def process_environment(self) -> dict[str, str]:
        return {**os.environ, **self.environment}

    def _install_qb_config(self) -> None:
        source = self.repo_root / "e2e/fixtures/qbittorrent/qBittorrent.conf"
        destination = self.qb_config_dir / "qBittorrent/qBittorrent.conf"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copy2(source, destination)

    def write_environment(self) -> Path:
        _write_env_file(self.env_file, self.environment)
        return self.env_file

    def compose_command(self, *arguments: str) -> list[str]:
        command = [
            "docker",
            "compose",
            "--project-name",
            self.project_name,
            "--env-file",
            str(self.env_file),
        ]
        for compose_file in self.compose_files:
            command.extend(("--file", str(compose_file)))
        command.extend(arguments)
        return command

    def _run_compose(
        self,
        *arguments: str,
        check: bool = True,
        capture_output: bool = False,
    ):
        return self._runner(
            self.compose_command(*arguments),
            cwd=self.repo_root,
            env=self.process_environment,
            check=check,
            capture_output=capture_output,
            text=capture_output,
        )

    def validate(self) -> None:
        self._run_compose("config", capture_output=True)

    def _published_port(self, service: str, container_port: int) -> int:
        result = self._run_compose(
            "port",
            "--index",
            "1",
            service,
            str(container_port),
            capture_output=True,
        )
        return parse_published_port(result.stdout)

    def ports(self) -> dict[str, int]:
        ports = {
            "app": self._published_port("app", 7892),
            "mock-upstream": self._published_port("mock-upstream", 18888),
            "fake-qb": self._published_port("fake-qb", 8080),
        }
        if self.profile == "downloader":
            ports["qbittorrent"] = self._published_port("qbittorrent", 8080)
        return ports

    def _publish_urls(self, ports: Mapping[str, int]) -> None:
        self.environment.update(
            {
                "AB_E2E_BASE_URL": f"http://127.0.0.1:{ports['app']}",
                "AB_E2E_MOCK_URL": (f"http://127.0.0.1:{ports['mock-upstream']}"),
                "AB_E2E_FAKE_QB_URL": f"http://127.0.0.1:{ports['fake-qb']}",
            }
        )
        if "qbittorrent" in ports:
            real_qb_url = f"http://127.0.0.1:{ports['qbittorrent']}"
            self.environment["AB_E2E_REAL_QB_URL"] = real_qb_url
            self.environment["AB_E2E_QB_URL"] = real_qb_url
        self.write_environment()

    def start(self) -> dict[str, int]:
        if self.profile == "downloader":
            self._run_compose("pull", "qbittorrent")
        self._run_compose("build", "mock-upstream", "fake-qb")
        self._run_compose(
            "up",
            "--detach",
            "--wait",
            "--wait-timeout",
            str(DEFAULT_WAIT_SECONDS),
        )
        self._started = True
        published = self.ports()
        self._publish_urls(published)
        if self.profile == "downloader":
            verify_qb_runtime(self.environment["AB_E2E_REAL_QB_URL"])
        return published

    def _wait_for_health(self, timeout: float = 30) -> None:
        url = f"{self.environment['AB_E2E_BASE_URL'].rstrip('/')}/health"
        deadline = time.monotonic() + timeout
        last_error = "no request attempted"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return
                    last_error = f"HTTP {response.status}"
            except (OSError, urllib.error.URLError) as exc:
                last_error = repr(exc)
            time.sleep(0.2)
        raise TimeoutError(f"App did not become healthy at {url}: {last_error}")

    def restart(self, service: str = "app") -> None:
        self._run_compose("restart", service)
        if service == "app" and "AB_E2E_BASE_URL" in self.environment:
            self._wait_for_health()
        else:
            self._run_compose(
                "up",
                "--detach",
                "--wait",
                "--wait-timeout",
                str(DEFAULT_WAIT_SECONDS),
                service,
            )

    def collect(self) -> None:
        collector = _load_artifact_module(self.repo_root)
        admin_urls = {}
        if "AB_E2E_MOCK_URL" in self.environment:
            admin_urls["mock-upstream"] = self.environment["AB_E2E_MOCK_URL"]
        if "AB_E2E_FAKE_QB_URL" in self.environment:
            admin_urls["fake-qb"] = self.environment["AB_E2E_FAKE_QB_URL"]
        collector.collect_artifacts(
            compose_command=self.compose_command(),
            artifact_dir=self.artifact_dir,
            data_dir=self.data_dir,
            log_file=self.log_file,
            admin_urls=admin_urls,
            qb_url=self.environment.get("AB_E2E_REAL_QB_URL"),
            environment=self.process_environment,
            secrets=(
                self.environment.get("AB_E2E_SESSION_TOKEN", ""),
                self.environment.get("AB_E2E_API_TOKEN", ""),
            ),
        )

    def stop(self, *, collect: bool = True) -> None:
        try:
            if collect and self._started:
                self.collect()
        finally:
            self._run_compose(
                "down",
                "--volumes",
                "--remove-orphans",
                check=False,
            )
            self._started = False


CommandRunner = Callable[[Sequence[str], Mapping[str, str]], object]


def _default_command_runner(
    command: Sequence[str], environment: Mapping[str, str]
) -> int:
    return subprocess.run(list(command), env=dict(environment), check=False).returncode


@contextmanager
def scoped_signal_cleanup(stack):
    """Ensure SIGINT/SIGTERM tear down this stack, then restore prior handlers."""
    previous: dict[int, object] = {}
    cleaning = False

    def handle(signum, _frame):
        nonlocal cleaning
        if not cleaning:
            cleaning = True
            stack.stop(collect=True)
        raise SystemExit(128 + signum)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, handle)
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def run_with_stack(
    stack,
    command: Sequence[str],
    *,
    runner: CommandRunner = _default_command_runner,
):
    with scoped_signal_cleanup(stack):
        stack.start()
        try:
            return runner(list(command), {**os.environ, **stack.environment})
        finally:
            stack.stop(collect=True)


def _add_stack_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", choices=sorted(PROFILES), default="browser")
    parser.add_argument("--repo-root", type=Path, default=repository_root())
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--project-name")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("validate", "start", "stop", "ports", "env", "smoke"):
        subparser = subparsers.add_parser(action)
        _add_stack_arguments(subparser)
    restart = subparsers.add_parser("restart")
    _add_stack_arguments(restart)
    restart.add_argument("service", nargs="?", default="app")
    run = subparsers.add_parser("run")
    _add_stack_arguments(run)
    run.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def _stack_from_args(args) -> Stack:
    return Stack(
        profile=args.profile,
        repo_root=args.repo_root,
        work_dir=args.work_dir,
        project_name=args.project_name,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    stack = _stack_from_args(args)
    if args.action == "validate":
        stack.validate()
        return 0
    if args.action == "start":
        print(json.dumps(stack.start(), sort_keys=True))
        print(stack.env_file)
        return 0
    if args.action == "stop":
        stack.stop(collect=True)
        return 0
    if args.action == "ports":
        ports = stack.ports()
        stack._publish_urls(ports)
        print(json.dumps(ports, sort_keys=True))
        return 0
    if args.action == "env":
        print(stack.env_file.read_text(encoding="utf-8"), end="")
        return 0
    if args.action == "restart":
        stack.restart(args.service)
        return 0
    if args.action == "smoke":
        with scoped_signal_cleanup(stack):
            stack.start()
            try:
                stack._wait_for_health()
            finally:
                stack.stop(collect=True)
        return 0
    if args.action == "run":
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        if not command:
            raise SystemExit("A command is required after --")
        result = run_with_stack(stack, command)
        return int(result) if isinstance(result, int) else 0
    raise AssertionError(f"Unhandled action: {args.action}")


if __name__ == "__main__":
    raise SystemExit(main())
