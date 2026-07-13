"""Exact-digest qBittorrent image and runtime safety contract."""

from __future__ import annotations

import re

import httpx
import pytest

pytestmark = pytest.mark.e2e

QB_IMAGE = (
    "linuxserver/qbittorrent:5.2.3@sha256:"
    "2e074403c7b72e6d89cee3d0d41a47f7b5708c6a9e5316f3958c90765cbe12ce"
)


def test_exact_digest_qb_image_uses_only_local_webseed_capabilities(
    downloader_stack,
):
    assert re.fullmatch(
        r"linuxserver/qbittorrent:\d+\.\d+\.\d+@sha256:[0-9a-f]{64}",
        QB_IMAGE,
    )
    compose = downloader_stack.compose_config()
    assert compose["services"]["qbittorrent"]["image"] == QB_IMAGE
    downloader_stack.image_identity("qbittorrent", QB_IMAGE)

    with httpx.Client(
        base_url=downloader_stack.qb_url,
        timeout=10,
        trust_env=False,
    ) as qb:
        login = qb.post(
            "/api/v2/auth/login",
            data={"username": "admin", "password": "adminadmin"},
        )
        assert login.status_code in {200, 204}
        if login.status_code == 200:
            assert login.text.strip() == "Ok."

        version = qb.get("/api/v2/app/version")
        assert version.status_code == 200
        assert version.text.strip() == "v5.2.3"
        preferences = qb.get("/api/v2/app/preferences")
        assert preferences.status_code == 200
        expected_preferences = {
            "dht": False,
            "pex": False,
            "lsd": False,
            "upnp": False,
            "rss_processing_enabled": False,
            "rss_auto_downloading_enabled": False,
            "save_path": "/downloads/Bangumi",
        }
        actual_preferences = preferences.json()
        assert {
            key: actual_preferences.get(key) for key in expected_preferences
        } == expected_preferences

        torrents = qb.get("/api/v2/torrents/info")
        assert torrents.status_code == 200
        assert torrents.json() == []
