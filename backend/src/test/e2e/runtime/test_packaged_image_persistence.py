"""Packaged-image version identity and bind-mounted config persistence."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest

from test.e2e.support import REPO_ROOT, wait_until

pytestmark = pytest.mark.e2e

_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$")


def _stack_environment() -> dict[str, str]:
    base_url = os.environ.get("AB_E2E_BASE_URL")
    if not base_url:
        pytest.skip("requires an app started by e2e/scripts/stack.py")
    if shutil.which("docker") is None:
        pytest.skip("Docker CLI is required for packaged-image identity checks")

    required = (
        "AB_E2E_PROJECT",
        "AB_E2E_APP_IMAGE",
        "AB_E2E_CONFIG_DIR",
        "AB_E2E_FAKE_QB_INTERNAL_URL",
        "AB_E2E_MOCK_INTERNAL_URL",
        "AB_E2E_USERNAME",
        "AB_E2E_PASSWORD",
    )
    environment = {"AB_E2E_BASE_URL": base_url}
    for name in required:
        value = os.environ.get(name)
        if not value:
            pytest.fail(f"stack runner did not export {name}")
        environment[name] = value
    return environment


def _run(*command: str) -> str:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout.strip()


def _compose_command(environment: dict[str, str], *arguments: str) -> list[str]:
    work_dir = Path(environment["AB_E2E_CONFIG_DIR"]).parent
    return [
        "docker",
        "compose",
        "--project-name",
        environment["AB_E2E_PROJECT"],
        "--env-file",
        str(work_dir / "stack.env"),
        "--file",
        str(REPO_ROOT / "e2e/compose/browser.yml"),
        *arguments,
    ]


def _container_identity(environment: dict[str, str]) -> tuple[str, str, str]:
    container_id = _run(*_compose_command(environment, "ps", "--quiet", "app"))
    assert container_id, "Compose app container is not running"
    configured_image = _run(
        "docker", "inspect", "--format={{.Config.Image}}", container_id
    )
    running_image_id = _run("docker", "inspect", "--format={{.Image}}", container_id)
    local_image_id = _run(
        "docker",
        "image",
        "inspect",
        "--format={{.Id}}",
        environment["AB_E2E_APP_IMAGE"],
    )
    assert configured_image == environment["AB_E2E_APP_IMAGE"]
    assert not configured_image.endswith(":latest")
    assert running_image_id == local_image_id
    return container_id, running_image_id, configured_image


def _image_version(container_id: str) -> str:
    return _run("docker", "exec", container_id, "cat", "/app/IMAGE_VERSION")


def _wait_for_health(client: httpx.Client) -> dict[str, Any]:
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
        description="packaged app health and SQLite readiness after restart",
        interval=0.1,
    )
    return state["payload"]


def test_packaged_image_version_and_config_survive_container_restart():
    environment = _stack_environment()
    with httpx.Client(
        base_url=environment["AB_E2E_BASE_URL"],
        timeout=10,
        trust_env=False,
    ) as client:
        initial_health = _wait_for_health(client)
        compose_contract = json.loads(
            _run(*_compose_command(environment, "config", "--format", "json"))
        )
        assert compose_contract["services"]["app"]["pull_policy"] == "never"
        assert (
            compose_contract["services"]["app"]["image"]
            == environment["AB_E2E_APP_IMAGE"]
        )
        container_id, image_id, _configured_image = _container_identity(environment)
        image_version = _image_version(container_id)

        assert _SEMVER.fullmatch(image_version)
        assert initial_health == {
            "status": "ok",
            "version": image_version,
            "db_ok": True,
        }
        expected_version = os.environ.get("E2E_VERSION")
        if expected_version:
            assert image_version == expected_version

        setup_status = client.get("/api/v1/setup/status")
        assert setup_status.status_code == 200
        assert setup_status.json()["need_setup"] is True
        assert setup_status.json()["version"] == image_version
        setup = client.post(
            "/api/v1/setup/complete",
            json={
                "username": environment["AB_E2E_USERNAME"],
                "password": environment["AB_E2E_PASSWORD"],
                "downloader_type": "qbittorrent",
                "downloader_host": environment["AB_E2E_FAKE_QB_INTERNAL_URL"],
                "downloader_username": "admin",
                "downloader_password": "adminadmin",
                "downloader_path": "/downloads/Bangumi",
                "downloader_ssl": False,
                "rss_url": "",
                "rss_name": "",
                "notification_enable": False,
            },
        )
        assert setup.status_code == 200
        assert setup.json()["status"] is True
        login = client.post(
            "/api/v1/auth/login",
            data={
                "username": environment["AB_E2E_USERNAME"],
                "password": environment["AB_E2E_PASSWORD"],
            },
        )
        assert login.status_code == 200
        assert login.json() == {"authenticated": True}
        assert client.post("/api/v1/stop").status_code in {200, 406}

        config_response = client.get("/api/v1/config/get")
        assert config_response.status_code == 200
        config = config_response.json()
        config["program"]["rss_time"] = 4321
        config["program"]["rename_time"] = 77
        config["rss_parser"]["enable"] = False
        config["rss_parser"]["language"] = "jp"
        config["bangumi_manage"]["enable"] = False
        config["network"][
            "tmdb_base_url"
        ] = f"{environment['AB_E2E_MOCK_INTERNAL_URL']}/tmdb"
        config["network"][
            "bgm_base_url"
        ] = f"{environment['AB_E2E_MOCK_INTERNAL_URL']}/bgm"
        config["update"]["auto_check"] = False
        updated = client.patch("/api/v1/config/update", json=config)
        assert updated.status_code == 200

        _run(*_compose_command(environment, "restart", "app"))
        restarted_health = _wait_for_health(client)
        restarted_container, restarted_image_id, _ = _container_identity(environment)

        assert restarted_image_id == image_id
        assert _image_version(restarted_container) == image_version
        assert restarted_health == initial_health
        program_status = client.get("/api/v1/status")
        assert program_status.status_code == 200
        assert program_status.json()["version"] == image_version

        persisted_response = client.get("/api/v1/config/get")
        assert persisted_response.status_code == 200
        persisted = persisted_response.json()
        assert persisted["program"]["rss_time"] == 4321
        assert persisted["program"]["rename_time"] == 77
        assert persisted["rss_parser"]["enable"] is False
        assert persisted["rss_parser"]["language"] == "jp"
        assert persisted["bangumi_manage"]["enable"] is False
        assert persisted["network"]["tmdb_base_url"] == (
            f"{environment['AB_E2E_MOCK_INTERNAL_URL']}/tmdb"
        )
        assert persisted["network"]["bgm_base_url"] == (
            f"{environment['AB_E2E_MOCK_INTERNAL_URL']}/bgm"
        )
        assert persisted["update"]["auto_check"] is False
