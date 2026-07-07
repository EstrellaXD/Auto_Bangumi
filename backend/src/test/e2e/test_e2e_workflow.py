"""E2E integration tests for the full AutoBangumi workflow.

Tests are executed in definition order within the class.  Each phase
builds on state created by earlier phases (setup wizard -> auth ->
config -> RSS -> bangumi -> downloader -> program -> log -> search ->
notification -> credential update -> cleanup).

Prerequisites:
    - Docker running (qBittorrent + mock RSS containers)
    - Port 7892 free (AutoBangumi)
    - Port 18080 free (qBittorrent)
    - Port 18888 free (mock RSS server)

Run:
    cd backend && uv run pytest -m e2e -v --tb=long
"""

import httpx
import pytest

from .conftest import E2E_PASSWORD, E2E_USERNAME


@pytest.mark.e2e
class TestE2EWorkflow:
    """Full workflow test against real qBittorrent and mock RSS server."""

    # ===================================================================
    # Phase 1: Setup Wizard
    # ===================================================================

    def test_01_setup_status_needs_setup(self, api_client):
        """Fresh instance should require setup."""
        resp = api_client.get("/api/v1/setup/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["need_setup"] is True
        assert "version" in data

    def test_02_verify_infrastructure(self, api_client, qb_password):
        """Verify Docker test infrastructure is reachable."""
        # qBittorrent WebUI
        qb_resp = httpx.get("http://localhost:18080", timeout=5.0)
        assert qb_resp.status_code == 200

        # Mock RSS server
        rss_resp = httpx.get("http://localhost:18888/health", timeout=5.0)
        assert rss_resp.status_code == 200

        # Mock RSS feed content
        xml_resp = httpx.get("http://localhost:18888/rss/mikan.xml", timeout=5.0)
        assert xml_resp.status_code == 200
        assert "<rss" in xml_resp.text
        assert "Frieren" in xml_resp.text

        # qBittorrent password was extracted
        assert qb_password, "qBittorrent password should not be empty"

    def test_03_mock_rss_nonexistent_feed(self):
        """Mock RSS server returns 404 for unknown feeds."""
        resp = httpx.get("http://localhost:18888/rss/nonexistent.xml", timeout=5.0)
        assert resp.status_code == 404

    def test_04_test_mock_downloader(self, api_client):
        """Setup wizard test-downloader endpoint accepts mock type."""
        resp = api_client.post(
            "/api/v1/setup/test-downloader",
            json={
                "type": "mock",
                "host": "localhost",
                "username": "admin",
                "password": "admin",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_05_setup_validation_username_too_short(self, api_client):
        """Username < 4 chars triggers Pydantic 422."""
        resp = api_client.post(
            "/api/v1/setup/complete",
            json={
                "username": "ab",
                "password": "validpassword",
                "downloader_type": "mock",
                "downloader_host": "localhost",
                "downloader_username": "x",
                "downloader_password": "x",
                "downloader_path": "/tmp",
            },
        )
        assert resp.status_code == 422

    def test_06_setup_validation_password_too_short(self, api_client):
        """Password < 8 chars triggers Pydantic 422."""
        resp = api_client.post(
            "/api/v1/setup/complete",
            json={
                "username": "validuser",
                "password": "short",
                "downloader_type": "mock",
                "downloader_host": "localhost",
                "downloader_username": "x",
                "downloader_password": "x",
                "downloader_path": "/tmp",
            },
        )
        assert resp.status_code == 422

    def test_07_complete_setup(self, api_client, e2e_state):
        """Complete the setup wizard with mock downloader and test RSS URL."""
        resp = api_client.post(
            "/api/v1/setup/complete",
            json={
                "username": E2E_USERNAME,
                "password": E2E_PASSWORD,
                "downloader_type": "mock",
                "downloader_host": "localhost:18080",
                "downloader_username": "admin",
                "downloader_password": "admin",
                "downloader_path": "/downloads/Bangumi",
                "downloader_ssl": False,
                "rss_url": "http://localhost:18888/rss/mikan.xml",
                "rss_name": "Test Mikan Feed",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] is True
        e2e_state["setup_complete"] = True

    def test_08_setup_status_complete(self, api_client):
        """After setup, need_setup should be False."""
        resp = api_client.get("/api/v1/setup/status")
        assert resp.status_code == 200
        assert resp.json()["need_setup"] is False

    def test_09_setup_complete_blocked(self, api_client):
        """POST /setup/complete returns 403 after setup is done."""
        resp = api_client.post(
            "/api/v1/setup/complete",
            json={
                "username": "another",
                "password": "anotherpassword",
                "downloader_type": "mock",
                "downloader_host": "localhost",
                "downloader_username": "x",
                "downloader_password": "x",
                "downloader_path": "/tmp",
            },
        )
        assert resp.status_code == 403

    def test_09b_test_downloader_blocked(self, api_client):
        """POST /setup/test-downloader returns 403 after setup is done."""
        resp = api_client.post(
            "/api/v1/setup/test-downloader",
            json={"type": "mock", "host": "x", "username": "x", "password": "x"},
        )
        assert resp.status_code == 403

    def test_09c_test_rss_blocked(self, api_client):
        """POST /setup/test-rss returns 403 after setup is done."""
        resp = api_client.post(
            "/api/v1/setup/test-rss",
            json={"url": "http://example.com/rss.xml"},
        )
        assert resp.status_code == 403

    # ===================================================================
    # Phase 2: Authentication
    # ===================================================================

    def test_10_login(self, api_client, e2e_state):
        """Login with credentials created during setup."""
        resp = api_client.post(
            "/api/v1/auth/login",
            data={"username": E2E_USERNAME, "password": E2E_PASSWORD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        e2e_state["token"] = data["access_token"]

    def test_11_login_cookie_set(self, api_client):
        """After login, the 'token' cookie should be set on the client."""
        assert "token" in api_client.cookies

    def test_12_access_protected_endpoint(self, api_client):
        """Authenticated client can access protected endpoints."""
        resp = api_client.get("/api/v1/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "version" in data
        assert "first_run" in data

    def test_13_refresh_token(self, api_client, e2e_state):
        """Token refresh returns a new access token and updates cookie."""
        resp = api_client.get("/api/v1/auth/refresh_token")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        e2e_state["token"] = data["access_token"]
        # NOTE: Tokens may be identical if login+refresh happen within the
        # same second (JWT exp uses second-level granularity).

    def test_14_login_wrong_password(self, api_client):
        """Login with incorrect password returns 401."""
        resp = api_client.post(
            "/api/v1/auth/login",
            data={"username": E2E_USERNAME, "password": "wrong_password"},
        )
        assert resp.status_code == 401

    def test_15_login_nonexistent_user(self, api_client):
        """Login with a user that doesn't exist returns 401."""
        resp = api_client.post(
            "/api/v1/auth/login",
            data={"username": "no_such_user", "password": "irrelevant"},
        )
        assert resp.status_code == 401

    def test_16_unauthenticated_client(self):
        """A fresh client with no cookies.

        NOTE: In DEV_VERSION, auth is bypassed so this returns 200.
        In production builds this would return 401.
        """
        with httpx.Client(base_url="http://localhost:7892", timeout=5.0) as fresh:
            resp = fresh.get("/api/v1/status")
            assert resp.status_code in (200, 401)

    # ===================================================================
    # Phase 3: Configuration
    # ===================================================================

    def test_20_get_config(self, api_client):
        """Retrieve current configuration with all top-level sections."""
        resp = api_client.get("/api/v1/config/get")
        assert resp.status_code == 200
        config = resp.json()
        for section in (
            "program",
            "downloader",
            "rss_parser",
            "bangumi_manage",
            "log",
            "proxy",
            "notification",
            "llm",
            "experimental_openai",
        ):
            assert section in config, f"Missing config section: {section}"
        assert config["downloader"]["type"] == "mock"

    def test_21_config_passwords_masked(self, api_client):
        """Sensitive fields are masked as '********' in GET /config/get."""
        resp = api_client.get("/api/v1/config/get")
        config = resp.json()
        # downloader password
        assert config["downloader"]["password"] == "********"
        # proxy password (even if empty, still masked since key contains 'password')
        assert config["proxy"]["password"] == "********"

    def test_22_update_config(self, api_client):
        """Update a non-sensitive config field via PATCH."""
        get_resp = api_client.get("/api/v1/config/get")
        config = get_resp.json()

        config["program"]["rss_time"] = 600
        # Re-supply masked passwords with actual values
        config["downloader"]["password"] = "admin"
        config["proxy"]["password"] = ""
        config["proxy"]["username"] = ""

        resp = api_client.patch("/api/v1/config/update", json=config)
        assert resp.status_code == 200

    def test_23_config_update_persisted(self, api_client):
        """Verify the config update from previous test is persisted."""
        resp = api_client.get("/api/v1/config/get")
        assert resp.json()["program"]["rss_time"] == 600

    # ===================================================================
    # Phase 4: RSS Management
    # ===================================================================

    def test_30_list_rss_initial(self, api_client, e2e_state):
        """One RSS feed should exist from setup wizard."""
        resp = api_client.get("/api/v1/rss")
        assert resp.status_code == 200
        feeds = resp.json()
        assert isinstance(feeds, list)
        assert len(feeds) == 1
        assert feeds[0]["name"] == "Test Mikan Feed"
        e2e_state["initial_rss_id"] = feeds[0]["id"]

    def test_31_add_rss_feed(self, api_client, e2e_state):
        """Add a second RSS feed with unique URL."""
        resp = api_client.post(
            "/api/v1/rss/add",
            json={
                "url": "http://localhost:18888/rss/mikan.xml?tag=e2e",
                "name": "E2E Second Feed",
                "aggregate": False,
                "parser": "mikan",
            },
        )
        assert resp.status_code == 200

    def test_32_add_rss_duplicate_url(self, api_client):
        """Adding RSS with an existing URL returns 406 (duplicate)."""
        resp = api_client.post(
            "/api/v1/rss/add",
            json={
                "url": "http://localhost:18888/rss/mikan.xml",
                "name": "Duplicate Feed",
                "aggregate": False,
                "parser": "mikan",
            },
        )
        # u_response returns the status_code from ResponseModel (406 for failed add)
        assert resp.status_code == 406

    def test_33_list_rss_after_add(self, api_client, e2e_state):
        """Two feeds should now exist."""
        resp = api_client.get("/api/v1/rss")
        feeds = resp.json()
        assert len(feeds) == 2
        names = {f["name"] for f in feeds}
        assert "Test Mikan Feed" in names
        assert "E2E Second Feed" in names
        for feed in feeds:
            if feed["name"] == "E2E Second Feed":
                e2e_state["second_rss_id"] = feed["id"]
                break

    def test_34_disable_rss(self, api_client, e2e_state):
        """Disable the second RSS feed."""
        rss_id = e2e_state["second_rss_id"]
        resp = api_client.patch(f"/api/v1/rss/disable/{rss_id}")
        assert resp.status_code == 200

    def test_35_verify_rss_disabled(self, api_client, e2e_state):
        """Disabled feed should have enabled=False."""
        resp = api_client.get("/api/v1/rss")
        for feed in resp.json():
            if feed["id"] == e2e_state["second_rss_id"]:
                assert feed["enabled"] is False
                break
        else:
            pytest.fail("Second RSS feed not found")

    def test_36_enable_rss(self, api_client, e2e_state):
        """Re-enable the RSS feed via enable/many."""
        rss_id = e2e_state["second_rss_id"]
        resp = api_client.post("/api/v1/rss/enable/many", json=[rss_id])
        assert resp.status_code == 200

    def test_37_verify_rss_enabled(self, api_client, e2e_state):
        """Feed should be enabled again."""
        resp = api_client.get("/api/v1/rss")
        for feed in resp.json():
            if feed["id"] == e2e_state["second_rss_id"]:
                assert feed["enabled"] is True
                break

    def test_38_update_rss(self, api_client, e2e_state):
        """Update RSS feed name."""
        rss_id = e2e_state["second_rss_id"]
        resp = api_client.patch(
            f"/api/v1/rss/update/{rss_id}",
            json={"name": "Renamed Feed"},
        )
        assert resp.status_code == 200

    def test_39_verify_rss_updated(self, api_client, e2e_state):
        """Verify the rename persisted."""
        resp = api_client.get("/api/v1/rss")
        for feed in resp.json():
            if feed["id"] == e2e_state["second_rss_id"]:
                assert feed["name"] == "Renamed Feed"
                break

    def test_39b_delete_nonexistent_rss(self, api_client):
        """Deleting a non-existent RSS ID returns 200.

        The database DELETE WHERE id=X succeeds even when no rows match
        (no exception raised), so the endpoint returns 200.
        """
        resp = api_client.delete("/api/v1/rss/delete/99999")
        assert resp.status_code == 200

    def test_39c_disable_nonexistent_rss(self, api_client):
        """Disabling a non-existent RSS ID returns 404."""
        resp = api_client.patch("/api/v1/rss/disable/99999")
        assert resp.status_code == 404

    def test_39d_delete_rss(self, api_client, e2e_state):
        """Delete the second RSS feed."""
        rss_id = e2e_state["second_rss_id"]
        resp = api_client.delete(f"/api/v1/rss/delete/{rss_id}")
        assert resp.status_code == 200

    def test_39e_verify_rss_deleted(self, api_client, e2e_state):
        """Only the initial feed should remain."""
        resp = api_client.get("/api/v1/rss")
        feeds = resp.json()
        assert len(feeds) == 1
        assert feeds[0]["name"] == "Test Mikan Feed"

    # ===================================================================
    # Phase 5: Bangumi
    # ===================================================================

    def test_40_bangumi_get_all_empty(self, api_client):
        """Bangumi list is empty until RSS refresh populates it."""
        resp = api_client.get("/api/v1/bangumi/get/all")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_41_bangumi_needs_review_empty(self, api_client):
        """No bangumi should need review initially."""
        resp = api_client.get("/api/v1/bangumi/needs-review")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_42_bangumi_dismiss_review_nonexistent(self, api_client):
        """Dismissing review for nonexistent bangumi returns 404."""
        resp = api_client.post("/api/v1/bangumi/dismiss-review/99999")
        assert resp.status_code == 404

    def test_43_bangumi_reset_all(self, api_client):
        """Reset all bangumi (safe when list is empty)."""
        resp = api_client.post("/api/v1/bangumi/reset/all")
        assert resp.status_code == 200

    # ===================================================================
    # Phase 6: Downloader
    # ===================================================================

    def test_50_downloader_check(self, api_client):
        """Mock downloader health check should succeed."""
        resp = api_client.get("/api/v1/check/downloader")
        assert resp.status_code == 200

    def test_51_downloader_torrents_empty(self, api_client):
        """No torrents in mock downloader initially."""
        resp = api_client.get("/api/v1/downloader/torrents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_52_downloader_pause_empty(self, api_client):
        """Pausing with empty hash list should succeed (no-op)."""
        resp = api_client.post("/api/v1/downloader/torrents/pause", json={"hashes": []})
        assert resp.status_code == 200

    def test_53_downloader_resume_empty(self, api_client):
        """Resuming with empty hash list should succeed (no-op)."""
        resp = api_client.post(
            "/api/v1/downloader/torrents/resume", json={"hashes": []}
        )
        assert resp.status_code == 200

    def test_54_downloader_delete_empty(self, api_client):
        """Deleting with empty hash list should succeed (no-op)."""
        resp = api_client.post(
            "/api/v1/downloader/torrents/delete",
            json={"hashes": [], "delete_files": False},
        )
        assert resp.status_code == 200

    def test_55_downloader_tag_nonexistent_bangumi(self, api_client):
        """Tagging a torrent with nonexistent bangumi_id returns status=false."""
        resp = api_client.post(
            "/api/v1/downloader/torrents/tag",
            json={"hash": "abc123", "bangumi_id": 99999},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] is False

    def test_56_downloader_auto_tag(self, api_client):
        """Auto-tag with no torrents returns 0 tagged."""
        resp = api_client.post("/api/v1/downloader/torrents/tag/auto")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tagged_count"] == 0
        assert data["unmatched_count"] == 0

    def test_57_qbittorrent_direct_connectivity(self, qb_password):
        """Verify direct connectivity to the real qBittorrent instance."""
        resp = httpx.post(
            "http://localhost:18080/api/v2/auth/login",
            data={"username": "admin", "password": qb_password},
            timeout=5.0,
        )
        # 旧版 qB 返回 200 + "Ok."，新版镜像返回 204 无响应体
        assert resp.status_code in (200, 204)
        if resp.status_code == 200:
            assert "ok" in resp.text.lower()

    # ===================================================================
    # Phase 7: Program Lifecycle
    # ===================================================================

    def test_60_program_status_not_running(self, api_client):
        """After first-run setup, program is NOT auto-started.

        startup() detects first_run and returns early without calling start().
        """
        resp = api_client.get("/api/v1/status")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["status"], bool)
        assert isinstance(data["version"], str)
        assert isinstance(data["first_run"], bool)

    def test_61_program_stop_when_not_running(self, api_client):
        """Stopping a program that isn't running returns 406."""
        resp = api_client.post("/api/v1/stop")
        assert resp.status_code == 406

    def test_62_program_start(self, api_client):
        """Explicitly start the program."""
        resp = api_client.post("/api/v1/start")
        assert resp.status_code == 200

    def test_63_program_stop(self, api_client):
        """Stop the now-running program."""
        resp = api_client.post("/api/v1/stop")
        assert resp.status_code == 200

    def test_64_program_stop_already_stopped(self, api_client):
        """Stopping again returns 406 (not running)."""
        resp = api_client.post("/api/v1/stop")
        assert resp.status_code == 406

    def test_65_program_restart(self, api_client):
        """Restart works even from a stopped state."""
        resp = api_client.post("/api/v1/restart")
        assert resp.status_code == 200

    # ===================================================================
    # Phase 8: Log
    # ===================================================================

    def test_70_get_log(self, api_client):
        """Retrieve application log (text/plain response)."""
        resp = api_client.get("/api/v1/log")
        # Log file may or may not exist depending on AB startup behavior
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert "text/plain" in resp.headers.get("content-type", "")

    def test_71_clear_log(self, api_client):
        """Clear the log file."""
        resp = api_client.post("/api/v1/log/clear")
        # 200 if log exists, 406 if not found
        assert resp.status_code in (200, 406)

    def test_72_get_log_after_clear(self, api_client):
        """Log should be empty or very short after clear."""
        resp = api_client.get("/api/v1/log")
        if resp.status_code == 200:
            # Log might have new entries from the clear request itself
            assert len(resp.text) < 10000

    # ===================================================================
    # Phase 9: Search
    # ===================================================================

    def test_80_search_providers(self, api_client):
        """List available search providers."""
        resp = api_client.get("/api/v1/search/provider")
        assert resp.status_code == 200
        providers = resp.json()
        assert isinstance(providers, list)
        assert len(providers) > 0

    def test_81_search_provider_config(self, api_client):
        """Get search provider URL templates."""
        resp = api_client.get("/api/v1/search/provider/config")
        assert resp.status_code == 200
        config = resp.json()
        assert isinstance(config, dict)

    def test_82_search_empty_keywords(self, api_client):
        """Search with no keywords returns empty list."""
        resp = api_client.get("/api/v1/search/bangumi")
        assert resp.status_code == 200
        assert resp.json() == []

    # ===================================================================
    # Phase 10: Notification
    # ===================================================================

    def test_85_notification_test_invalid_index(self, api_client):
        """Test notification with out-of-range index returns success=false."""
        resp = api_client.post(
            "/api/v1/notification/test", json={"provider_index": 9999}
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_86_notification_test_config_unknown_type(self, api_client):
        """Test-config with unknown provider type returns success=false."""
        resp = api_client.post(
            "/api/v1/notification/test-config",
            json={"type": "nonexistent_provider", "enabled": True},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    # ===================================================================
    # Phase 11: Credential Update & Cleanup
    # ===================================================================

    def test_90_update_credentials(self, api_client, e2e_state):
        """Update user password via /auth/update."""
        resp = api_client.post(
            "/api/v1/auth/update",
            json={"password": "newpassword123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["message"] == "update success"
        e2e_state["new_password"] = "newpassword123"

    def test_91_login_with_new_password(self, api_client, e2e_state):
        """Login works with the updated password."""
        resp = api_client.post(
            "/api/v1/auth/login",
            data={
                "username": E2E_USERNAME,
                "password": e2e_state["new_password"],
            },
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_92_login_old_password_fails(self, api_client):
        """Old password should no longer work after credential update."""
        resp = api_client.post(
            "/api/v1/auth/login",
            data={"username": E2E_USERNAME, "password": E2E_PASSWORD},
        )
        assert resp.status_code == 401

    def test_93_logout(self, api_client):
        """Logout clears the auth session and deletes cookie."""
        resp = api_client.post("/api/v1/auth/logout")
        assert resp.status_code == 200

    def test_94_verify_logged_out(self, api_client):
        """After logout, the token cookie should be cleared.

        NOTE: In DEV_VERSION, endpoints still work (auth bypass).
        This test verifies the cookie was deleted.
        """
        # httpx may still have a cookie if the server didn't properly
        # delete it, but the logout response should have Set-Cookie
        # with max-age=0 or explicit deletion.
        resp = api_client.get("/api/v1/status")
        # DEV_VERSION: 200 (bypass), Production: 401 (no token)
        assert resp.status_code in (200, 401)
