"""Hermetic HTTP upstream for AutoBangumi end-to-end tests.

The implementation intentionally uses only the Python standard library so the
same server can run directly from a checkout or in a tiny test container.
"""

from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

REDACTED = "[REDACTED]"
_SENSITIVE_NAMES = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "api_key",
    "api-key",
    "apikey",
    "access_token",
    "refresh_token",
    "token",
)
_TEXT_SECRET_RE = re.compile(
    r"(?i)(authorization|cookie|password|passwd|secret|api[_-]?key|"
    r"access[_-]?token|refresh[_-]?token|token)(\s*[=:]\s*)"
    r'([^&\s,;}"]+)'
)


def _is_sensitive(name: str) -> bool:
    lowered = name.lower()
    return any(part in lowered for part in _SENSITIVE_NAMES)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): REDACTED if _is_sensitive(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _redact_named_values(values: dict[str, Any]) -> dict[str, Any]:
    def redact_secret(value: Any) -> Any:
        if isinstance(value, list):
            return [REDACTED for _ in value]
        return REDACTED

    return {
        key: redact_secret(value) if _is_sensitive(key) else _redact(value)
        for key, value in values.items()
    }


def _content_type(path: Path, route_prefix: str) -> str:
    if route_prefix == "/rss/":
        return "application/rss+xml; charset=utf-8"
    if route_prefix == "/torrents/":
        return "application/x-bittorrent"
    if path.suffix.lower() == ".mkv":
        return "video/x-matroska"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _parse_range(value: str, size: int) -> tuple[int, int]:
    if size <= 0 or not value.startswith("bytes=") or "," in value:
        raise ValueError("unsupported byte range")
    spec = value[6:].strip()
    if "-" not in spec:
        raise ValueError("malformed byte range")
    start_text, end_text = spec.split("-", 1)
    try:
        if not start_text:
            suffix_length = int(end_text)
            if suffix_length <= 0:
                raise ValueError("empty suffix range")
            start = max(size - suffix_length, 0)
            end = size - 1
        else:
            start = int(start_text)
            if start < 0 or start >= size:
                raise ValueError("range starts outside resource")
            end = size - 1 if not end_text else min(int(end_text), size - 1)
            if end < start:
                raise ValueError("range end precedes start")
    except ValueError as exc:
        raise ValueError("malformed byte range") from exc
    return start, end


class _MockState:
    def __init__(self, fixture_root: Path):
        scenario_file = fixture_root / "tmdb" / "scenarios.json"
        scenario_data = json.loads(scenario_file.read_text(encoding="utf-8"))
        self.scenarios: dict[str, dict[str, Any]] = scenario_data["scenarios"]
        self.season: dict[str, Any] = scenario_data["season"]
        self.lock = threading.RLock()
        self.scenario_name: str | None = None
        self.requests: list[dict[str, Any]] = []
        self.notifications: list[dict[str, Any]] = []

    def reset(self) -> None:
        with self.lock:
            self.scenario_name = None
            self.requests.clear()
            self.notifications.clear()

    def activate(self, name: str) -> bool:
        with self.lock:
            if name not in self.scenarios:
                return False
            self.scenario_name = name
            return True

    def scenario(self) -> dict[str, Any] | None:
        with self.lock:
            if self.scenario_name is None:
                return None
            return copy.deepcopy(self.scenarios[self.scenario_name])

    def append_request(self, request: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self.requests.append(request)
        return request

    def set_response_status(self, request: dict[str, Any], status: int) -> None:
        with self.lock:
            request["response_status"] = status

    def append_notification(self, request: dict[str, Any]) -> None:
        notification = {
            key: copy.deepcopy(value)
            for key, value in request.items()
            if key != "response_status"
        }
        with self.lock:
            self.notifications.append(notification)

    def request_snapshot(self) -> list[dict[str, Any]]:
        with self.lock:
            return copy.deepcopy(self.requests)

    def state_snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "scenario": self.scenario_name,
                "notifications": copy.deepcopy(self.notifications),
                "request_count": len(self.requests),
            }


class _MockUpstreamServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], fixture_root: Path):
        super().__init__(address, _MockUpstreamHandler)
        self.fixture_root = fixture_root
        self.mock_state = _MockState(fixture_root)


class _MockUpstreamHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: _MockUpstreamServer

    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def do_GET(self) -> None:
        self._handle_request(head_only=False)

    def do_HEAD(self) -> None:
        self._handle_request(head_only=True)

    def do_POST(self) -> None:
        self._handle_request(head_only=False)

    def do_PUT(self) -> None:
        self._handle_request(head_only=False)

    def _read_body(self) -> Any:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return None

        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if content_type == "application/json":
            try:
                return _redact(json.loads(raw.decode("utf-8")))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return "<invalid JSON>"
        if content_type == "application/x-www-form-urlencoded":
            try:
                form = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
            except UnicodeDecodeError:
                return f"<{len(raw)} bytes>"
            return _redact_named_values(form)
        if content_type.startswith("text/"):
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                return f"<{len(raw)} bytes>"
            return _TEXT_SECRET_RE.sub(rf"\1\2{REDACTED}", text)
        return f"<{len(raw)} bytes>"

    def _journal(self, parsed, body: Any) -> dict[str, Any]:
        query = parse_qs(parsed.query, keep_blank_values=True)
        headers = {key.lower(): value for key, value in self.headers.items()}
        request = {
            "method": self.command,
            "path": unquote(parsed.path),
            "query": _redact_named_values(query),
            "headers": _redact_named_values(headers),
            "body": body,
            "response_status": None,
        }
        return self.server.mock_state.append_request(request)

    def _handle_request(self, *, head_only: bool) -> None:
        parsed = urlsplit(self.path)
        body = self._read_body()
        if self._handle_admin(parsed, body, head_only=head_only):
            return

        journal = self._journal(parsed, body)
        path = unquote(parsed.path)
        if path == "/health":
            if self.command not in {"GET", "HEAD"}:
                self._send_method_not_allowed(journal, "GET, HEAD", head_only)
            else:
                self._send_json(journal, 200, {"status": "ok"}, head_only)
            return

        if path.startswith("/tmdb/"):
            if self.command not in {"GET", "HEAD"}:
                self._send_method_not_allowed(journal, "GET, HEAD", head_only)
            else:
                self._handle_tmdb(parsed, journal, head_only=head_only)
            return

        static_route = self._static_route(path)
        if static_route is not None:
            if self.command not in {"GET", "HEAD"}:
                self._send_method_not_allowed(journal, "GET, HEAD", head_only)
            else:
                route_prefix, directory, relative = static_route
                self._send_static(
                    journal,
                    route_prefix,
                    directory,
                    relative,
                    head_only=head_only,
                )
            return

        if path.startswith("/notifications/"):
            if self.command != "POST":
                self._send_method_not_allowed(journal, "POST", head_only)
            else:
                self.server.mock_state.append_notification(journal)
                self._send_empty(journal, 204)
            return

        self._send_json(
            journal,
            501,
            {"detail": f"Unexpected mock-upstream request: {self.command} {path}"},
            head_only,
        )

    def _handle_admin(self, parsed, body: Any, *, head_only: bool) -> bool:
        path = unquote(parsed.path)
        state = self.server.mock_state
        if path == "/__admin/reset":
            if self.command != "POST":
                self._send_unjournaled_json(405, {"detail": "Method not allowed"})
            else:
                state.reset()
                self._send_unjournaled_json(200, {"ok": True})
            return True
        if path == "/__admin/requests":
            if self.command not in {"GET", "HEAD"}:
                self._send_unjournaled_json(405, {"detail": "Method not allowed"})
            else:
                self._send_unjournaled_json(
                    200, {"requests": state.request_snapshot()}, head_only=head_only
                )
            return True
        if path == "/__admin/state":
            if self.command not in {"GET", "HEAD"}:
                self._send_unjournaled_json(405, {"detail": "Method not allowed"})
            else:
                self._send_unjournaled_json(
                    200, state.state_snapshot(), head_only=head_only
                )
            return True

        scenario_match = re.fullmatch(r"/__admin/scenario/([^/]+)", path)
        if scenario_match:
            if self.command not in {"PUT", "POST"}:
                self._send_unjournaled_json(405, {"detail": "Method not allowed"})
            else:
                name = scenario_match.group(1)
                if state.activate(name):
                    self._send_unjournaled_json(200, {"scenario": name})
                else:
                    self._send_unjournaled_json(
                        404, {"detail": f"Unknown scenario: {name}"}
                    )
            return True
        if path == "/__admin/scenario" and self.command in {"PUT", "POST"}:
            name = body.get("name") if isinstance(body, dict) else None
            if isinstance(name, str) and state.activate(name):
                self._send_unjournaled_json(200, {"scenario": name})
            else:
                self._send_unjournaled_json(
                    404, {"detail": f"Unknown scenario: {name}"}
                )
            return True
        return False

    def _handle_tmdb(self, parsed, journal: dict[str, Any], *, head_only: bool) -> None:
        scenario = self.server.mock_state.scenario()
        if scenario is None:
            self._send_json(
                journal, 409, {"detail": "No active TMDB scenario"}, head_only
            )
            return

        path = unquote(parsed.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        search_match = re.fullmatch(r"/tmdb/3/search/(tv|movie)", path)
        if search_match:
            expected = scenario.get("search", {})
            kind = search_match.group(1)
            supplied_query = (query.get("query") or [""])[0]
            supplied_language = (query.get("language") or [""])[0]
            expected_query = expected.get("query")
            initial_query = expected.get("initial_query")
            matches = (
                expected.get("kind") == kind
                and supplied_language == expected.get("language")
                and supplied_query == expected_query
            )
            if supplied_query == initial_query:
                matches = False
            results = expected.get("results", []) if matches else []
            self._send_json(journal, 200, {"results": results}, head_only)
            return

        season_match = re.fullmatch(r"/tmdb/3/tv/(\d+)/season/(\d+)", path)
        if season_match:
            detail = scenario.get("detail")
            if not self._detail_matches(
                detail,
                query,
                int(season_match.group(1)),
                scenario.get("search", {}).get("language"),
            ):
                self._send_json(
                    journal, 404, {"detail": "TV season not found"}, head_only
                )
                return
            season_number = int(season_match.group(2))
            known_seasons = {
                item.get("season_number") for item in detail.get("seasons", [])
            }
            if season_number not in known_seasons:
                self._send_json(
                    journal, 404, {"detail": "TV season not found"}, head_only
                )
                return
            self._send_json(journal, 200, self.server.mock_state.season, head_only)
            return

        detail_match = re.fullmatch(r"/tmdb/3/tv/(\d+)", path)
        if detail_match:
            detail = scenario.get("detail")
            if not self._detail_matches(
                detail,
                query,
                int(detail_match.group(1)),
                scenario.get("search", {}).get("language"),
            ):
                self._send_json(
                    journal, 404, {"detail": "TV show not found"}, head_only
                )
                return
            self._send_json(journal, 200, detail, head_only)
            return

        self._send_json(
            journal,
            501,
            {"detail": f"Unexpected TMDB request: {path}"},
            head_only,
        )

    @staticmethod
    def _detail_matches(
        detail: dict[str, Any] | None,
        query: dict[str, list[str]],
        requested_id: int,
        expected_language: str | None,
    ) -> bool:
        if detail is None or detail.get("id") != requested_id:
            return False
        supplied_language = (query.get("language") or [""])[0]
        return bool(expected_language) and supplied_language == expected_language

    def _static_route(self, path: str) -> tuple[str, Path, str] | None:
        root = self.server.fixture_root
        for route_prefix, directory_name in (
            ("/rss/", "rss"),
            ("/images/", "images"),
            ("/files/", "files"),
            ("/torrents/", "torrents"),
        ):
            if path.startswith(route_prefix):
                return route_prefix, root / directory_name, path[len(route_prefix) :]
        if path in {"/player", "/player/"}:
            return "/player/", root / "player", "index.html"
        if path.startswith("/player/"):
            return "/player/", root / "player", path[len("/player/") :]
        return None

    def _send_static(
        self,
        journal: dict[str, Any],
        route_prefix: str,
        directory: Path,
        relative: str,
        *,
        head_only: bool,
    ) -> None:
        base = directory.resolve()
        candidate = (base / relative).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            self._send_json(journal, 404, {"detail": "File not found"}, head_only)
            return
        if not candidate.is_file():
            self._send_json(journal, 404, {"detail": "File not found"}, head_only)
            return

        size = candidate.stat().st_size
        range_header = self.headers.get("Range")
        headers = {"Accept-Ranges": "bytes"}
        status = 200
        start = 0
        end = max(size - 1, 0)
        if range_header:
            try:
                start, end = _parse_range(range_header, size)
            except ValueError:
                headers["Content-Range"] = f"bytes */{size}"
                self._send_bytes(
                    journal,
                    416,
                    b"",
                    "application/octet-stream",
                    head_only=head_only,
                    headers=headers,
                )
                return
            status = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"

        length = end - start + 1 if size else 0
        if head_only:
            data = b""
        else:
            with candidate.open("rb") as file:
                file.seek(start)
                data = file.read(length)
        self._send_bytes(
            journal,
            status,
            data,
            _content_type(candidate, route_prefix),
            head_only=head_only,
            headers=headers,
            content_length=length,
        )

    def _send_method_not_allowed(
        self, journal: dict[str, Any], allow: str, head_only: bool
    ) -> None:
        self._send_json(
            journal,
            405,
            {"detail": "Method not allowed"},
            head_only,
            headers={"Allow": allow},
        )

    def _send_json(
        self,
        journal: dict[str, Any],
        status: int,
        payload: Any,
        head_only: bool,
        headers: dict[str, str] | None = None,
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self._send_bytes(
            journal,
            status,
            data,
            "application/json; charset=utf-8",
            head_only=head_only,
            headers=headers,
        )

    def _send_empty(self, journal: dict[str, Any], status: int) -> None:
        self._send_bytes(
            journal,
            status,
            b"",
            "application/octet-stream",
            head_only=True,
        )

    def _send_bytes(
        self,
        journal: dict[str, Any],
        status: int,
        data: bytes,
        content_type: str,
        *,
        head_only: bool,
        headers: dict[str, str] | None = None,
        content_length: int | None = None,
    ) -> None:
        self.server.mock_state.set_response_status(journal, status)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header(
            "Content-Length",
            str(len(data) if content_length is None else content_length),
        )
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if not head_only and data:
            self.wfile.write(data)

    def _send_unjournaled_json(
        self, status: int, payload: Any, *, head_only: bool = False
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only and data:
            self.wfile.write(data)


def create_server(
    host: str, port: int, fixture_root: str | os.PathLike[str]
) -> ThreadingHTTPServer:
    """Create a configured server without starting its serve loop."""

    root = Path(fixture_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Fixture root does not exist: {root}")
    return _MockUpstreamServer((host, port), root)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "18888"))
    )
    parser.add_argument(
        "--fixture-root",
        default=os.environ.get("FIXTURES_ROOT", "/fixtures"),
    )
    args = parser.parse_args()
    server = create_server(args.host, args.port, args.fixture_root)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
