"""HTTP 层性能头：gzip 压缩与 SPA 静态文件的缓存策略。"""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import main
from module.api.deps import get_context
from module.security.api import get_current_user

HTML = {"accept": "text/html"}
GZIP = {"accept-encoding": "gzip"}
IMMUTABLE = "public, max-age=31536000, immutable"


@pytest.fixture
def app(tmp_path):
    dist = tmp_path / "dist"
    for sub in ("assets", "fonts", "images"):
        (dist / sub).mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa</html>")
    (dist / "theme-init.js").write_text("// theme")
    (dist / "assets" / "app-abc.js").write_text("export const x = 1;\n" * 200)
    (dist / "fonts" / "a.woff2").write_text("font")
    (dist / "images" / "a.svg").write_text("<svg/>")
    app = main.create_app()
    main.mount_webui(app, dist)
    return app


class TestSpaCacheControl:
    @pytest.mark.parametrize("root_path", ["", "/ab"])
    @pytest.mark.parametrize(
        ("path", "cache_control"),
        [
            ("assets/app-abc.js", IMMUTABLE),
            ("", "no-cache"),
            ("index.html", "no-cache"),
            # 前端路由深链接回落到 index.html
            ("bangumi", "no-cache"),
            ("bangumi/detail/3", "no-cache"),
            # assets/ 下不存在的路径同样回落到 index.html，不能永久缓存
            ("assets/missing", "no-cache"),
            ("fonts/a.woff2", None),
            ("images/a.svg", None),
            ("theme-init.js", None),
        ],
    )
    def test_cache_control_by_path(self, app, root_path, path, cache_control):
        resp = TestClient(app, root_path=root_path).get(
            f"{root_path}/{path}", headers=HTML
        )
        assert resp.status_code == 200
        assert resp.headers.get("cache-control") == cache_control


class TestGzip:
    def test_large_static_asset_is_gzipped(self, app):
        resp = TestClient(app).get("/assets/app-abc.js", headers=GZIP)
        assert resp.headers["content-encoding"] == "gzip"

    def test_small_response_is_not_gzipped(self, app):
        resp = TestClient(app).get("/", headers={**HTML, **GZIP})
        assert "content-encoding" not in resp.headers

    def test_event_stream_is_not_gzipped(self, app):
        app.dependency_overrides[get_current_user] = lambda: "user"
        app.dependency_overrides[get_context] = lambda: MagicMock(
            is_running=True, first_run=False
        )
        started: dict = {}

        async def drive() -> None:
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/api/v1/events/stream",
                "raw_path": b"/api/v1/events/stream",
                "query_string": b"",
                "headers": [(b"accept-encoding", b"gzip")],
                "scheme": "http",
                "server": ("test", 80),
                "client": ("test", 1),
                "http_version": "1.1",
                "root_path": "",
            }

            async def receive() -> dict:
                await asyncio.Event().wait()  # 客户端保持连接，不发 disconnect
                return {}

            async def send(message: dict) -> None:
                if message["type"] == "http.response.start":
                    started.update(message)
                    raise asyncio.CancelledError  # 只取响应头，随后断开

            try:
                await app(scope, receive, send)
            except asyncio.CancelledError:
                pass

        asyncio.run(drive())
        headers = {k.decode(): v.decode() for k, v in started["headers"]}
        assert headers["content-type"].startswith("text/event-stream")
        assert "content-encoding" not in headers
