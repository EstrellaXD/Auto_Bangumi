"""Access to the downloader-profile Compose stack owned by stack.py."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest

from test.e2e.support import REPO_ROOT, wait_until


@dataclass(frozen=True)
class DownloaderStack:
    environment: dict[str, str]

    @classmethod
    def from_environment(cls) -> "DownloaderStack":
        if not os.environ.get("AB_E2E_BASE_URL"):
            pytest.skip("requires e2e/scripts/stack.py --profile downloader")
        if os.environ.get("AB_E2E_PROFILE") != "downloader":
            pytest.skip("requires the real-qBittorrent downloader profile")
        required = (
            "AB_E2E_APP_IMAGE",
            "AB_E2E_BASE_URL",
            "AB_E2E_CONFIG_DIR",
            "AB_E2E_MOCK_INTERNAL_URL",
            "AB_E2E_PROJECT",
            "AB_E2E_QB_INTERNAL_URL",
            "AB_E2E_QB_URL",
            "AB_E2E_USERNAME",
            "AB_E2E_PASSWORD",
        )
        environment: dict[str, str] = {}
        for name in required:
            value = os.environ.get(name)
            if not value:
                pytest.fail(f"stack runner did not export {name}")
            environment[name] = value
        return cls(environment)

    @property
    def work_dir(self) -> Path:
        return Path(self.environment["AB_E2E_CONFIG_DIR"]).parent

    @property
    def base_url(self) -> str:
        return self.environment["AB_E2E_BASE_URL"]

    @property
    def qb_url(self) -> str:
        return self.environment["AB_E2E_QB_URL"]

    def run(self, *command: str) -> str:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        )
        return result.stdout.strip()

    def compose_command(self, *arguments: str) -> list[str]:
        return [
            "docker",
            "compose",
            "--project-name",
            self.environment["AB_E2E_PROJECT"],
            "--env-file",
            str(self.work_dir / "stack.env"),
            "--file",
            str(REPO_ROOT / "e2e/compose/browser.yml"),
            "--file",
            str(REPO_ROOT / "e2e/compose/downloader.yml"),
            *arguments,
        ]

    def compose_config(self) -> dict[str, Any]:
        return json.loads(self.run(*self.compose_command("config", "--format", "json")))

    def container_id(self, service: str) -> str:
        container_id = self.run(*self.compose_command("ps", "--quiet", service)).strip()
        assert container_id, f"Compose service is not running: {service}"
        return container_id

    def image_identity(self, service: str, image: str) -> tuple[str, str]:
        container_id = self.container_id(service)
        configured = self.run(
            "docker", "inspect", "--format={{.Config.Image}}", container_id
        )
        running_id = self.run("docker", "inspect", "--format={{.Image}}", container_id)
        local_id = self.run("docker", "image", "inspect", "--format={{.Id}}", image)
        assert configured == image
        assert running_id == local_id
        return container_id, running_id

    def restart_app(self) -> None:
        self.run(*self.compose_command("restart", "app"))

    def image_version(self, container_id: str) -> str:
        return self.run("docker", "exec", container_id, "cat", "/app/IMAGE_VERSION")

    def wait_for_health(self, client: httpx.Client) -> dict[str, Any]:
        def probe() -> dict[str, Any]:
            response = client.get("/health")
            return {
                "status_code": response.status_code,
                "payload": (
                    response.json() if response.status_code == 200 else response.text
                ),
            }

        state = wait_until(
            probe,
            lambda value: value["status_code"] == 200
            and value["payload"].get("db_ok") is True,
            timeout=45,
            description="downloader-profile app health after restart",
            interval=0.1,
        )
        return state["payload"]


@pytest.fixture(scope="session")
def downloader_stack() -> DownloaderStack:
    return DownloaderStack.from_environment()
