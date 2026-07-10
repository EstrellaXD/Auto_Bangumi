"""Pure contracts for source-process E2E isolation and startup recovery."""

import pytest

from test.e2e.support import runtime as runtime_support


def test_runtime_sandbox_drops_inherited_autobangumi_settings(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("AB_HTTP_PROXY", "http" + "://proxy.invalid:8080")
    monkeypatch.setenv("AB_SOCKS", "socks5" + "://proxy.invalid:1080")
    monkeypatch.setenv("AB_DOWNLOADER_PASSWORD", "production-secret")
    monkeypatch.setenv("AB_DEV_NO_AUTH", "1")

    sandbox = runtime_support.BackendSandbox(tmp_path / "sandbox")
    try:
        for name in (
            "AB_HTTP_PROXY",
            "AB_SOCKS",
            "AB_DOWNLOADER_PASSWORD",
            "AB_DEV_NO_AUTH",
        ):
            assert name not in sandbox.env
        assert sandbox.env["AB_WEBUI_PORT"] == str(sandbox.port)
    finally:
        sandbox.close()


def test_runtime_sandbox_retries_a_loopback_bind_collision(tmp_path, monkeypatch):
    ports = iter((41001, 41002))
    monkeypatch.setattr(runtime_support, "_unused_loopback_port", lambda: next(ports))
    sandbox = runtime_support.BackendSandbox(tmp_path / "sandbox")
    spawned_ports = []

    class FakeProcess:
        pid = 1234

        def __init__(self, *, exited: bool):
            self.exited = exited

        def poll(self):
            return 1 if self.exited else None

        def terminate(self):
            self.exited = True

        def wait(self, timeout):
            return 0

        def kill(self):
            self.exited = True

    def popen(_command, *, env, stdout, **_kwargs):
        spawned_ports.append(env["AB_WEBUI_PORT"])
        exited = len(spawned_ports) == 1
        if exited:
            stdout.write(b"ERROR address already in use\n")
        return FakeProcess(exited=exited)

    wait_calls = 0

    def wait(probe, _predicate, **_kwargs):
        nonlocal wait_calls
        wait_calls += 1
        if wait_calls == 1:
            probe()
        return {"status_code": 200}

    monkeypatch.setattr(runtime_support.subprocess, "Popen", popen)
    monkeypatch.setattr(runtime_support, "wait_until", wait)
    try:
        sandbox.start()
        assert spawned_ports == ["41001", "41002"]
        assert sandbox.port == 41002
        assert sandbox.base_url == "http://127.0.0.1:41002"
    finally:
        sandbox.close()


def test_runtime_sandbox_does_not_retry_a_later_non_bind_failure(
    tmp_path,
    monkeypatch,
):
    ports = iter((42001, 42002, 42003))
    monkeypatch.setattr(runtime_support, "_unused_loopback_port", lambda: next(ports))
    sandbox = runtime_support.BackendSandbox(tmp_path / "sandbox")
    spawned_ports = []

    class FailedProcess:
        pid = 4321

        def poll(self):
            return 1

    def popen(_command, *, env, stdout, **_kwargs):
        spawned_ports.append(env["AB_WEBUI_PORT"])
        message = (
            b"ERROR address already in use\n"
            if len(spawned_ports) == 1
            else b"ERROR invalid runtime configuration\n"
        )
        stdout.write(message)
        return FailedProcess()

    def wait(probe, _predicate, **_kwargs):
        probe()
        raise AssertionError("unreachable")

    monkeypatch.setattr(runtime_support.subprocess, "Popen", popen)
    monkeypatch.setattr(runtime_support, "wait_until", wait)
    try:
        with pytest.raises(
            runtime_support._FatalProbeError,
            match="invalid runtime configuration",
        ):
            sandbox.start()
        assert spawned_ports == ["42001", "42002"]
    finally:
        sandbox.close()
