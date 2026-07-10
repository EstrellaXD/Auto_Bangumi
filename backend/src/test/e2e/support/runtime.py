"""Process and HTTP helpers for hermetic AutoBangumi runtime tests.

Every backend instance owns a temporary working directory, SQLite database,
configuration, HTTP port, cookie jar, and log.  Nothing here reaches into the
running application: tests configure and inspect it through public APIs, while
the worker module is used only while the process is stopped to prepare an
offline database fixture or invoke the same production offset scanner.
"""

from __future__ import annotations

import json
import os
import runpy
import socket
import subprocess
import sys
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from time import monotonic
from typing import Any, TypeVar

import httpx

REPO_ROOT = Path(__file__).resolve().parents[5]
BACKEND_SRC = REPO_ROOT / "backend" / "src"
E2E_FIXTURES = REPO_ROOT / "e2e" / "fixtures"
WORKER_PATH = Path(__file__).with_name("worker.py")

E2E_USERNAME = "testadmin"
E2E_PASSWORD = "testpassword123"

T = TypeVar("T")
_POLL_EVENT = threading.Event()
_MAX_BIND_ATTEMPTS = 3
_BIND_FAILURE_MARKERS = (
    "address already in use",
    "errno 48",
    "errno 98",
)


class _FatalProbeError(RuntimeError):
    """Readiness failure that cannot become healthy without a restart."""


def wait_until(
    probe: Callable[[], T],
    predicate: Callable[[T], bool],
    *,
    timeout: float,
    description: str,
    interval: float = 0.05,
) -> T:
    """Poll until ``predicate`` succeeds, reporting deadline and last state.

    ``Event.wait`` provides an interruptible polling interval without fixed
    sleeps.  Every caller must provide a finite timeout and a useful operation
    description so a CI failure explains what it observed last.
    """

    deadline = monotonic() + timeout
    last_state: object = "<probe not run>"
    while True:
        try:
            value = probe()
            last_state = value
            if predicate(value):
                return value
        except _FatalProbeError:
            raise
        except Exception as exc:  # readiness probes intentionally tolerate races
            last_state = f"{type(exc).__name__}: {exc}"

        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Deadline exceeded while waiting for {description}; "
                f"last state: {last_state!r}"
            )
        _POLL_EVENT.wait(min(interval, remaining))


def load_script(path: Path) -> dict[str, Any]:
    """Load a standalone E2E server script without requiring a package name."""

    return runpy.run_path(str(path))


def _unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class HttpService:
    """Own a standard-library threaded HTTP server and an admin client."""

    def __init__(self, server: Any, *, ready_path: str = "/health") -> None:
        self.server = server
        host, port = server.server_address[:2]
        connect_host = "127.0.0.1" if host in {"", "0.0.0.0", "::"} else host
        self.base_url = f"http://{connect_host}:{port}"
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=5.0,
            trust_env=False,
        )
        self.ready_path = ready_path
        self.thread = threading.Thread(
            target=server.serve_forever,
            name=f"e2e-http-{port}",
            daemon=True,
        )
        self._started = False

    def start(self, *, timeout: float = 5.0) -> "HttpService":
        self.thread.start()
        self._started = True

        def probe() -> dict[str, Any]:
            response = self.client.get(self.ready_path)
            return {
                "status_code": response.status_code,
                "body": response.text[:500],
            }

        wait_until(
            probe,
            lambda state: state["status_code"] == 200,
            timeout=timeout,
            description=f"HTTP service {self.base_url}{self.ready_path}",
        )
        return self

    def close(self) -> None:
        self.client.close()
        if not self._started:
            self.server.server_close()
            return
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5.0)
        if self.thread.is_alive():
            raise RuntimeError(f"HTTP service thread did not stop: {self.base_url}")


class BackendSandbox:
    """Run one source checkout backend against an isolated working directory."""

    def __init__(
        self,
        work_dir: Path,
    ) -> None:
        self.work_dir = work_dir.resolve()
        self.work_dir.mkdir(parents=True, exist_ok=False)
        for directory in ("config", "data", "dist", "dist/assets", "dist/images"):
            (self.work_dir / directory).mkdir(parents=True, exist_ok=True)
        (self.work_dir / "dist" / "index.html").write_text(
            "<html><body>runtime e2e</body></html>",
            encoding="utf-8",
        )

        self.log_path = self.work_dir / "backend.log"
        self.process: subprocess.Popen[bytes] | None = None
        self._log_handle: Any = None
        self.port = 0
        self.base_url = ""
        self.client: httpx.Client
        self._assign_unused_port()
        self.env = self._build_env()

    def _build_env(self) -> dict[str, str]:
        # Never inherit a developer or production AutoBangumi configuration.
        # In particular, AB_HTTP_PROXY/AB_SOCKS can exfiltrate local fixture
        # traffic and proxy credentials from an otherwise hermetic test.
        env = {
            key: value for key, value in os.environ.items() if not key.startswith("AB_")
        }
        for proxy_name in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        ):
            env.pop(proxy_name, None)
        env.update(
            {
                "HOST": "127.0.0.1",
                "NO_PROXY": "127.0.0.1,localhost",
                "no_proxy": "127.0.0.1,localhost",
                "PYTHONPATH": str(BACKEND_SRC),
                "AB_WEBUI_PORT": str(self.port),
                "AB_RSS_COLLECTOR": "false",
                "AB_RENAME": "false",
                "AB_INTERVAL_TIME": "3600",
                "AB_RENAME_FREQ": "3600",
                "AB_LANGUAGE": "zh",
            }
        )
        return env

    def _assign_unused_port(self) -> None:
        existing_client = getattr(self, "client", None)
        if existing_client is not None:
            existing_client.close()
        self.port = _unused_loopback_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.client = self.new_client()
        if hasattr(self, "env"):
            self.env["AB_WEBUI_PORT"] = str(self.port)

    def _bind_failed(self, *, since: int) -> bool:
        if not self.log_path.exists():
            return False
        with self.log_path.open("rb") as log:
            log.seek(since)
            attempt_log = log.read().decode("utf-8", errors="replace").lower()
        return any(marker in attempt_log for marker in _BIND_FAILURE_MARKERS)

    def new_client(
        self,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=10.0,
            trust_env=False,
        )

    def start(self, *, timeout: float = 25.0) -> "BackendSandbox":
        if self.process is not None:
            raise RuntimeError("Backend process is already started")
        for attempt in range(_MAX_BIND_ATTEMPTS):
            attempt_log_offset = (
                self.log_path.stat().st_size if self.log_path.exists() else 0
            )
            self._log_handle = self.log_path.open("ab", buffering=0)
            self.process = subprocess.Popen(
                [sys.executable, str(BACKEND_SRC / "main.py")],
                cwd=self.work_dir,
                env=self.env,
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
            )

            def probe() -> dict[str, Any]:
                assert self.process is not None
                return_code = self.process.poll()
                if return_code is not None:
                    raise _FatalProbeError(
                        f"backend exited with {return_code}; "
                        f"log tail: {self.log_tail()}"
                    )
                response = self.client.get("/health")
                return {
                    "status_code": response.status_code,
                    "body": response.text[:500],
                    "pid": self.process.pid,
                }

            try:
                wait_until(
                    probe,
                    lambda state: state["status_code"] == 200,
                    timeout=timeout,
                    description=f"AutoBangumi health at {self.base_url}/health",
                )
                return self
            except Exception:
                bind_failed = self._bind_failed(since=attempt_log_offset)
                self.stop()
                if bind_failed and attempt + 1 < _MAX_BIND_ATTEMPTS:
                    self._assign_unused_port()
                    continue
                raise
        raise AssertionError("unreachable")

    def stop(self, *, timeout: float = 10.0) -> None:
        process = self.process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)
        self.process = None
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def restart(self) -> "BackendSandbox":
        self.stop()
        return self.start()

    def close(self) -> None:
        self.stop()
        self.client.close()

    def log_tail(self, *, limit: int = 4_000) -> str:
        if not self.log_path.exists():
            return "<no backend log>"
        return self.log_path.read_text(encoding="utf-8", errors="replace")[-limit:]

    def _run_worker(self, command: str, *args: str) -> Any:
        result = subprocess.run(
            [sys.executable, str(WORKER_PATH), command, str(self.work_dir), *args],
            cwd=self.work_dir,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30.0,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"E2E worker {command!r} failed with {result.returncode}; "
                f"stdout={result.stdout[-2000:]!r}; stderr={result.stderr[-4000:]!r}"
            )
        for line in reversed(result.stdout.splitlines()):
            if line.startswith("E2E_RESULT="):
                return json.loads(line.removeprefix("E2E_RESULT="))
        raise RuntimeError(
            f"E2E worker {command!r} returned no result marker; "
            f"stdout={result.stdout[-2000:]!r}"
        )

    def seed_database(self, payload: Mapping[str, Any]) -> None:
        if self.process is not None:
            raise RuntimeError("Database fixtures may only be seeded while stopped")
        if not (self.work_dir / "data" / "data.db").is_file():
            raise RuntimeError(
                "Database fixtures require a completed initial backend startup"
            )
        payload_path = self.work_dir / "seed.json"
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        result = self._run_worker("seed", str(payload_path))
        if result.get("seeded") is not True:
            raise RuntimeError(f"Unexpected seed result: {result!r}")

    def run_offset_scan(self, bangumi_id: int) -> bool:
        if self.process is not None:
            raise RuntimeError("Offset fixture scan requires the backend to be stopped")
        result = self._run_worker("offset", str(bangumi_id))
        return bool(result["flagged"])

    def setup(
        self,
        *,
        downloader_type: str = "mock",
        downloader_host: str = "mock",
        downloader_username: str = "",
        downloader_password: str = "",
        downloader_path: str = "/downloads/Bangumi",
    ) -> httpx.Response:
        return self.client.post(
            "/api/v1/setup/complete",
            json={
                "username": E2E_USERNAME,
                "password": E2E_PASSWORD,
                "downloader_type": downloader_type,
                "downloader_host": downloader_host,
                "downloader_username": downloader_username,
                "downloader_password": downloader_password,
                "downloader_path": downloader_path,
                "downloader_ssl": False,
                "rss_url": "",
                "rss_name": "",
                "notification_enable": False,
            },
        )

    def login(
        self,
        *,
        username: str = E2E_USERNAME,
        password: str = E2E_PASSWORD,
        client: httpx.Client | None = None,
    ) -> httpx.Response:
        target = client or self.client
        return target.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
        )

    def setup_and_login(self, **setup_kwargs: str) -> None:
        setup = self.setup(**setup_kwargs)
        if setup.status_code != 200 or setup.json().get("status") is not True:
            raise AssertionError(
                f"setup failed: status={setup.status_code}, body={setup.text}; "
                f"log tail={self.log_tail()}"
            )
        login = self.login()
        if login.status_code != 200:
            raise AssertionError(
                f"login failed: status={login.status_code}, body={login.text}; "
                f"log tail={self.log_tail()}"
            )
        self.stop_tasks()

    def stop_tasks(self) -> None:
        """Stop the scheduler so a focused runtime test cannot reach the network."""

        response = self.client.post("/api/v1/stop")
        if response.status_code not in {200, 406}:
            raise AssertionError(
                f"scheduler stop failed: {response.status_code} {response.text}"
            )

    def update_config(self, mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        current = self.client.get("/api/v1/config/get")
        if current.status_code != 200:
            raise AssertionError(
                f"config read failed: {current.status_code} {current.text}"
            )
        payload = current.json()
        mutate(payload)
        response = self.client.patch("/api/v1/config/update", json=payload)
        if response.status_code != 200:
            raise AssertionError(
                f"config update failed: {response.status_code} {response.text}"
            )
        return payload
