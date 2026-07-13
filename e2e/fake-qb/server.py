#!/usr/bin/env python3
"""Small hermetic qBittorrent Web API fake used by end-to-end tests."""

from __future__ import annotations

import copy
import json
import os
import secrets
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

MATCHING_HASH = "a" * 40
NEIGHBOUR_HASH = "b" * 40
DELETE_FAILURE_HASH = "f" * 40
REDACTED = "[REDACTED]"

_SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "auth",
    "cookie",
    "sid",
)

_PRESET_TORRENTS = (
    {
        "hash": MATCHING_HASH,
        "name": "Target Anime - 01",
        "save_path": "D:\\Downloads\\Bangumi\\Test Anime (2024)\\Season 1\\",
        "category": "Bangumi",
        "tags": "ab:1",
        "state": "pausedUP",
        "progress": 1.0,
        "size": 65_536,
    },
    {
        "hash": NEIGHBOUR_HASH,
        "name": "Nearby Anime - 10",
        "save_path": "D:\\Downloads\\Bangumi\\Test Anime (2024)\\Season 10",
        "category": "Bangumi",
        "tags": "ab:10",
        "state": "pausedUP",
        "progress": 1.0,
        "size": 65_536,
    },
    {
        "hash": DELETE_FAILURE_HASH,
        "name": "Forced Delete Failure",
        "save_path": "D:\\Downloads\\Bangumi\\Delete Failure\\Season 1",
        "category": "Bangumi",
        "tags": "ab:failure",
        "state": "pausedUP",
        "progress": 1.0,
        "size": 65_536,
    },
)

_PRESET_PREFERENCES = {
    "save_path": "D:\\Downloads\\Bangumi",
    "temp_path_enabled": False,
    "web_ui_port": 8080,
    "dht": False,
    "pex": False,
    "lsd": False,
    "upnp": False,
}


def _is_sensitive(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(fragment in normalized for fragment in _SENSITIVE_FRAGMENTS)


def _redact_object(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive(str(key)) else _redact_object(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_object(item) for item in value]
    return value


def _redact_values(name: str, values: list[str]) -> list[str]:
    if _is_sensitive(name):
        return [REDACTED for _ in values]
    if name.lower() == "json":
        sanitized: list[str] = []
        for value in values:
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                sanitized.append(value)
            else:
                sanitized.append(
                    json.dumps(_redact_object(parsed), separators=(",", ":"))
                )
        return sanitized
    return list(values)


def _redact_mapping(values: dict[str, list[str]]) -> dict[str, list[str]]:
    return {key: _redact_values(key, items) for key, items in values.items()}


class FakeQbState:
    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.lock = threading.RLock()
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.torrents = {
                torrent["hash"]: copy.deepcopy(torrent) for torrent in _PRESET_TORRENTS
            }
            self.preferences = copy.deepcopy(_PRESET_PREFERENCES)
            self.sessions: set[str] = set()
            self.requests: list[dict[str, Any]] = []

    def record(
        self,
        *,
        method: str,
        path: str,
        query: dict[str, list[str]],
        form: dict[str, list[str]],
        headers: dict[str, str],
    ) -> None:
        sanitized_headers = {
            key: REDACTED if _is_sensitive(key) else value
            for key, value in headers.items()
        }
        request = {
            "method": method,
            "path": path,
            "query": _redact_mapping(query),
            "form": _redact_mapping(form),
            "headers": sanitized_headers,
        }
        with self.lock:
            self.requests.append(request)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "torrents": copy.deepcopy(list(self.torrents.values())),
                "preferences": _redact_object(copy.deepcopy(self.preferences)),
                "session_count": len(self.sessions),
            }


class FakeQbServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        username: str,
        password: str,
    ) -> None:
        self.state = FakeQbState(username, password)
        super().__init__(address, FakeQbHandler)


class FakeQbHandler(BaseHTTPRequestHandler):
    server: FakeQbServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_bytes(
        self,
        status: int,
        payload: bytes,
        content_type: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, status: int, body: Any) -> None:
        payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self._send_bytes(status, payload, "application/json; charset=utf-8")

    def _send_text(
        self,
        status: int,
        body: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self._send_bytes(
            status,
            body.encode("utf-8"),
            "text/plain; charset=utf-8",
            headers,
        )

    def _read_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        payload = self.rfile.read(length) if length else b""
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("application/x-www-form-urlencoded"):
            return {}
        return parse_qs(payload.decode("utf-8"), keep_blank_values=True)

    def _record(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        form: dict[str, list[str]],
    ) -> None:
        self.server.state.record(
            method=method,
            path=path,
            query=query,
            form=form,
            headers=dict(self.headers.items()),
        )

    def _session_id(self) -> str | None:
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        cookies = SimpleCookie()
        try:
            cookies.load(cookie_header)
        except Exception:
            return None
        sid = cookies.get("SID")
        return sid.value if sid else None

    def _authenticated(self) -> bool:
        session_id = self._session_id()
        with self.server.state.lock:
            return session_id is not None and session_id in self.server.state.sessions

    def _require_auth(self) -> bool:
        if self._authenticated():
            return True
        self._send_text(403, "Forbidden")
        return False

    @staticmethod
    def _one(form: dict[str, list[str]], key: str, default: str = "") -> str:
        values = form.get(key)
        return values[0] if values else default

    def do_GET(self) -> None:
        target = urlsplit(self.path)
        query = parse_qs(target.query, keep_blank_values=True)

        if target.path == "/__admin/state":
            self._send_json(200, self.server.state.snapshot())
            return
        if target.path == "/__admin/requests":
            with self.server.state.lock:
                requests = copy.deepcopy(self.server.state.requests)
            self._send_json(200, {"requests": requests})
            return

        self._record("GET", target.path, query, {})
        if target.path.startswith("/api/v2/") and not self._require_auth():
            return

        if target.path == "/api/v2/app/version":
            self._send_text(200, "v5.2.3")
            return
        if target.path == "/api/v2/app/preferences":
            with self.server.state.lock:
                preferences = copy.deepcopy(self.server.state.preferences)
            self._send_json(200, preferences)
            return
        if target.path == "/api/v2/torrents/info":
            self._send_json(200, self._filtered_torrents(query))
            return

        self._send_json(
            501,
            {"error": "unsupported endpoint", "method": "GET", "path": target.path},
        )

    def _filtered_torrents(self, query: dict[str, list[str]]) -> list[dict[str, Any]]:
        with self.server.state.lock:
            torrents = copy.deepcopy(list(self.server.state.torrents.values()))

        hashes = query.get("hashes", [""])[0]
        if hashes:
            selected_hashes = set(hashes.split("|"))
            torrents = [item for item in torrents if item["hash"] in selected_hashes]
        category = query.get("category", [""])[0]
        if category:
            torrents = [item for item in torrents if item["category"] == category]
        tag = query.get("tag", [""])[0]
        if tag:
            torrents = [
                item
                for item in torrents
                if tag in {value.strip() for value in item["tags"].split(",")}
            ]
        status_filter = query.get("filter", [""])[0]
        if status_filter == "completed":
            torrents = [item for item in torrents if item["progress"] >= 1]
        return torrents

    def do_POST(self) -> None:
        target = urlsplit(self.path)
        query = parse_qs(target.query, keep_blank_values=True)
        form = self._read_form()

        if target.path == "/__admin/reset":
            self.server.state.reset()
            self._send_json(200, {"ok": True})
            return

        self._record("POST", target.path, query, form)

        if target.path == "/api/v2/auth/login":
            self._login(form)
            return
        if target.path.startswith("/api/v2/") and not self._require_auth():
            return
        if target.path == "/api/v2/auth/logout":
            self._logout()
            return
        if target.path == "/api/v2/app/setPreferences":
            self._set_preferences(form)
            return
        if target.path == "/api/v2/torrents/delete":
            self._delete_torrents(form)
            return

        self._send_json(
            501,
            {"error": "unsupported endpoint", "method": "POST", "path": target.path},
        )

    def _login(self, form: dict[str, list[str]]) -> None:
        username = self._one(form, "username")
        password = self._one(form, "password")
        if (
            username != self.server.state.username
            or password != self.server.state.password
        ):
            self._send_text(200, "Fails.")
            return
        session_id = secrets.token_hex(16)
        with self.server.state.lock:
            self.server.state.sessions.add(session_id)
        self._send_text(
            200,
            "Ok.",
            {"Set-Cookie": f"SID={session_id}; HttpOnly; SameSite=Strict; Path=/"},
        )

    def _logout(self) -> None:
        session_id = self._session_id()
        if session_id:
            with self.server.state.lock:
                self.server.state.sessions.discard(session_id)
        self._send_text(
            200,
            "Ok.",
            {"Set-Cookie": "SID=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/"},
        )

    def _set_preferences(self, form: dict[str, list[str]]) -> None:
        try:
            preferences = json.loads(self._one(form, "json"))
        except (TypeError, ValueError):
            self._send_text(400, "Invalid preferences")
            return
        if not isinstance(preferences, dict):
            self._send_text(400, "Invalid preferences")
            return
        with self.server.state.lock:
            self.server.state.preferences.update(preferences)
        self._send_text(200)

    def _delete_torrents(self, form: dict[str, list[str]]) -> None:
        hashes_value = self._one(form, "hashes")
        if not hashes_value:
            self._send_text(400, "Missing hashes")
            return
        with self.server.state.lock:
            hashes = (
                set(self.server.state.torrents)
                if hashes_value == "all"
                else set(hashes_value.split("|"))
            )
            if DELETE_FAILURE_HASH in hashes:
                self._send_text(500, "Forced delete failure")
                return
            for torrent_hash in hashes:
                self.server.state.torrents.pop(torrent_hash, None)
        self._send_text(200)


def create_server(
    host: str = "127.0.0.1",
    port: int = 0,
    *,
    username: str = "admin",
    password: str = "adminadmin",
) -> FakeQbServer:
    """Create an unstarted server; callers own ``serve_forever`` and shutdown."""
    return FakeQbServer((host, port), username, password)


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    username = os.environ.get("QB_USERNAME", "admin")
    password = os.environ.get("QB_PASSWORD", "adminadmin")
    server = create_server(host, port, username=username, password=password)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
