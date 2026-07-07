"""Tests for the unauthenticated /health liveness probe."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from module.api.health import router as health_router

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """App with only the health router mounted, at the root (no /api prefix)."""
    app = FastAPI()
    app.include_router(health_router)
    return app


@pytest.fixture
def client(app):
    """Plain TestClient — no auth override, matching the probe's real usage."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_no_auth_required_returns_200(self, client):
        """GET /health succeeds without any auth dependency/header."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_reports_version_and_db_ok(self, client):
        """GET /health returns status/version/db_ok, DB reachable -> db_ok True."""
        with patch("module.api.health.VERSION", "3.3.0-test"):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "3.3.0-test"
        assert data["db_ok"] is True

    def test_health_db_failure_reports_db_ok_false(self, client):
        """A DB query failure is caught: still 200, but db_ok is False."""
        with patch("module.api.health.Database", side_effect=RuntimeError("db down")):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db_ok"] is False
