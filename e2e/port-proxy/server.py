#!/usr/bin/env python3
"""Small TCP forwarder exposing an otherwise-internal E2E network to the host."""

from __future__ import annotations

import os
import select
import socket
import socketserver
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class Forward:
    listen_port: int
    target_host: str
    target_port: int


def parse_forwards(value: str) -> tuple[Forward, ...]:
    forwards: list[Forward] = []
    for raw_entry in value.split(","):
        entry = raw_entry.strip()
        if not entry:
            continue
        try:
            listen_text, target = entry.split("=", 1)
            target_host, target_text = target.rsplit(":", 1)
            listen_port = int(listen_text)
            target_port = int(target_text)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid forward mapping: {entry!r}") from exc
        if not target_host or not 1 <= listen_port <= 65535:
            raise ValueError(f"Invalid forward mapping: {entry!r}")
        if not 1 <= target_port <= 65535:
            raise ValueError(f"Invalid forward mapping: {entry!r}")
        forwards.append(Forward(listen_port, target_host, target_port))
    if not forwards:
        raise ValueError("At least one forward mapping is required")
    if len({item.listen_port for item in forwards}) != len(forwards):
        raise ValueError("Forward listen ports must be unique")
    return tuple(forwards)


class ForwardingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        target: tuple[str, int],
    ) -> None:
        self.target = target
        super().__init__(address, ForwardingHandler)


class ForwardingHandler(socketserver.BaseRequestHandler):
    server: ForwardingServer

    def handle(self) -> None:
        try:
            upstream = socket.create_connection(self.server.target, timeout=5)
        except OSError:
            return
        with upstream:
            upstream.settimeout(None)
            self.request.settimeout(None)
            peers = (self.request, upstream)
            while True:
                readable, _, _ = select.select(peers, (), (), 30)
                if not readable:
                    continue
                for source in readable:
                    try:
                        data = source.recv(65_536)
                    except OSError:
                        return
                    if not data:
                        return
                    destination = upstream if source is self.request else self.request
                    try:
                        destination.sendall(data)
                    except OSError:
                        return


def create_server(
    host: str,
    port: int,
    target_host: str,
    target_port: int,
) -> ForwardingServer:
    return ForwardingServer((host, port), (target_host, target_port))


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    forwards = parse_forwards(
        os.environ.get(
            "FORWARDS",
            "17892=app:7892,18888=mock-upstream:18888,18080=fake-qb:8080,"
            "28080=qbittorrent:8080",
        )
    )
    servers = [
        create_server(host, item.listen_port, item.target_host, item.target_port)
        for item in forwards
    ]
    threads = [
        threading.Thread(target=server.serve_forever, daemon=True)
        for server in servers[1:]
    ]
    for thread in threads:
        thread.start()
    try:
        servers[0].serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
