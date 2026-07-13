"""Native packaged-image version and persistent-volume restart smoke test."""

from __future__ import annotations

import os
import re

import httpx
import pytest

pytestmark = pytest.mark.e2e

_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$")


def _ensure_setup(client: httpx.Client, downloader_stack) -> None:
    status = client.get("/api/v1/setup/status")
    assert status.status_code == 200
    if not status.json()["need_setup"]:
        return
    setup = client.post(
        "/api/v1/setup/complete",
        json={
            "username": downloader_stack.environment["AB_E2E_USERNAME"],
            "password": downloader_stack.environment["AB_E2E_PASSWORD"],
            "downloader_type": "qbittorrent",
            "downloader_host": downloader_stack.environment["AB_E2E_QB_INTERNAL_URL"],
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


def test_native_image_version_and_config_survive_restart(downloader_stack):
    compose = downloader_stack.compose_config()
    app_service = compose["services"]["app"]
    app_image = downloader_stack.environment["AB_E2E_APP_IMAGE"]
    assert app_service["image"] == app_image
    assert app_service["pull_policy"] == "never"
    assert not app_image.endswith(":latest")

    with httpx.Client(
        base_url=downloader_stack.base_url,
        timeout=10,
        trust_env=False,
    ) as client:
        initial_health = downloader_stack.wait_for_health(client)
        app_container, image_id = downloader_stack.image_identity("app", app_image)
        image_version = downloader_stack.image_version(app_container)
        assert _SEMVER.fullmatch(image_version)
        assert initial_health == {
            "status": "ok",
            "version": image_version,
            "db_ok": True,
        }
        expected_version = os.environ.get("E2E_VERSION")
        if expected_version:
            assert image_version == expected_version

        _ensure_setup(client, downloader_stack)
        login = client.post(
            "/api/v1/auth/login",
            data={
                "username": downloader_stack.environment["AB_E2E_USERNAME"],
                "password": downloader_stack.environment["AB_E2E_PASSWORD"],
            },
        )
        assert login.status_code == 200
        assert login.json() == {"authenticated": True}
        assert client.post("/api/v1/stop").status_code in {200, 406}

        config_response = client.get("/api/v1/config/get")
        assert config_response.status_code == 200
        config = config_response.json()
        config["program"]["rss_time"] = 2468
        config["program"]["rename_time"] = 37
        config["rss_parser"]["enable"] = False
        config["rss_parser"]["language"] = "jp"
        config["bangumi_manage"]["enable"] = False
        config["network"][
            "tmdb_base_url"
        ] = f"{downloader_stack.environment['AB_E2E_MOCK_INTERNAL_URL']}/tmdb"
        config["network"][
            "bgm_base_url"
        ] = f"{downloader_stack.environment['AB_E2E_MOCK_INTERNAL_URL']}/bgm"
        config["update"]["auto_check"] = False
        updated = client.patch("/api/v1/config/update", json=config)
        assert updated.status_code == 200

        downloader_stack.restart_app()
        restarted_health = downloader_stack.wait_for_health(client)
        restarted_container, restarted_image_id = downloader_stack.image_identity(
            "app", app_image
        )
        assert restarted_image_id == image_id
        assert downloader_stack.image_version(restarted_container) == image_version
        assert restarted_health == initial_health

        program_status = client.get("/api/v1/status")
        assert program_status.status_code == 200
        assert program_status.json()["version"] == image_version
        persisted_response = client.get("/api/v1/config/get")
        assert persisted_response.status_code == 200
        persisted = persisted_response.json()
        assert persisted["program"]["rss_time"] == 2468
        assert persisted["program"]["rename_time"] == 37
        assert persisted["rss_parser"]["enable"] is False
        assert persisted["rss_parser"]["language"] == "jp"
        assert persisted["bangumi_manage"]["enable"] is False
        assert (
            persisted["downloader"]["host"]
            == downloader_stack.environment["AB_E2E_QB_INTERNAL_URL"]
        )
        assert persisted["network"]["tmdb_base_url"] == (
            f"{downloader_stack.environment['AB_E2E_MOCK_INTERNAL_URL']}/tmdb"
        )
        assert persisted["network"]["bgm_base_url"] == (
            f"{downloader_stack.environment['AB_E2E_MOCK_INTERNAL_URL']}/bgm"
        )
        assert persisted["update"]["auto_check"] is False
