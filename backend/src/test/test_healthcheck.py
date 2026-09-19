"""Docker HEALTHCHECK 端口解析（#1106）。"""

import json
from pathlib import Path

import healthcheck


def test_webui_port_reads_configured_port(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"program": {"webui_port": 8080}}))

    assert healthcheck.webui_port(config) == 8080


def test_webui_port_defaults_when_config_missing(tmp_path: Path) -> None:
    assert healthcheck.webui_port(tmp_path / "config.json") == 7892
