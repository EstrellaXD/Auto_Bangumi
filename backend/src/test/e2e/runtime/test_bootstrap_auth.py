"""First-run setup and browser-session authentication through the public API."""

import pytest

from test.e2e.support.runtime import E2E_PASSWORD, E2E_USERNAME

pytestmark = pytest.mark.e2e


def test_first_run_setup_requires_an_explicit_login(backend_factory):
    backend = backend_factory()

    setup_status = backend.client.get("/api/v1/setup/status")
    assert setup_status.status_code == 200
    assert setup_status.json() == {
        "need_setup": True,
        "version": "DEV_VERSION",
    }
    assert backend.client.get("/api/v1/status").status_code == 401

    setup = backend.setup()
    assert setup.status_code == 200
    assert setup.json()["status"] is True
    assert "token" not in backend.client.cookies
    assert backend.client.get("/api/v1/status").status_code == 401
    assert backend.client.get("/api/v1/setup/status").json()["need_setup"] is False

    repeated = backend.setup()
    assert repeated.status_code == 403


def test_login_refresh_and_logout_manage_a_persisted_cookie(backend_factory):
    backend = backend_factory()
    setup = backend.setup()
    assert setup.status_code == 200
    assert setup.json()["status"] is True

    wrong_password = backend.login(password="definitely-wrong")
    assert wrong_password.status_code == 401
    assert "token" not in backend.client.cookies

    login = backend.login()
    assert login.status_code == 200
    assert login.json() == {"authenticated": True}
    set_cookie = login.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=strict" in set_cookie
    assert "token" in backend.client.cookies

    me = backend.client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == E2E_USERNAME
    assert backend.client.get("/api/v1/status").status_code == 200

    refresh = backend.client.post("/api/v1/auth/refresh_token")
    assert refresh.status_code == 200
    assert refresh.json() == {"authenticated": True}

    logout = backend.client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert "token" not in backend.client.cookies
    assert backend.client.get("/api/v1/status").status_code == 401

    fresh_login = backend.login(username=E2E_USERNAME, password=E2E_PASSWORD)
    assert fresh_login.status_code == 200
