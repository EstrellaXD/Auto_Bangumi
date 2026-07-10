"""Contract tests for the host bridge around the internal E2E network."""

import runpy
import socketserver
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e

SERVER_PATH = Path(__file__).resolve().parents[5] / "e2e/port-proxy/server.py"
SERVER_MODULE = runpy.run_path(str(SERVER_PATH))
create_server = SERVER_MODULE["create_server"]
parse_forwards = SERVER_MODULE["parse_forwards"]


class _UpstreamHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args) -> None:
        return

    def do_GET(self) -> None:
        body = f"proxied:{self.path}".encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_parse_forwards_rejects_ambiguous_or_invalid_mappings():
    forwards = parse_forwards("17892=app:7892,18888=mock-upstream:18888")
    assert [
        (item.listen_port, item.target_host, item.target_port) for item in forwards
    ] == [
        (17892, "app", 7892),
        (18888, "mock-upstream", 18888),
    ]
    for invalid in ("", "not-a-mapping", "0=app:7892", "1=app:0", "1=a:2,1=b:3"):
        with pytest.raises(ValueError):
            parse_forwards(invalid)


def test_tcp_proxy_forwards_http_without_interpreting_the_protocol():
    upstream = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _UpstreamHandler)
    upstream.daemon_threads = True
    upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    upstream_thread.start()

    proxy = create_server(
        "127.0.0.1",
        0,
        "127.0.0.1",
        upstream.server_address[1],
    )
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()
    try:
        response = httpx.get(
            f"http://127.0.0.1:{proxy.server_address[1]}/health?through=proxy",
            timeout=5,
            trust_env=False,
        )
        assert response.status_code == 200
        assert response.text == "proxied:/health?through=proxy"
    finally:
        proxy.shutdown()
        proxy.server_close()
        upstream.shutdown()
        upstream.server_close()
        proxy_thread.join(timeout=5)
        upstream_thread.join(timeout=5)
        assert not proxy_thread.is_alive()
        assert not upstream_thread.is_alive()
