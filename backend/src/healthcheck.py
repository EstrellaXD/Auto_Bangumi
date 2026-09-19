"""Docker HEALTHCHECK：探测 /health，退出码 0 表示健康。

端口取自 config.json（WebUI 可改，AB_WEBUI_PORT 只在首次启动时写入），
不能写死 7892。先连 IPv4 回环再连 IPv6：busybox wget 把 localhost 解析成
::1，而默认只监听 0.0.0.0（#1106）；IPV6/HOST=::1 时只有 ::1 可达。
只用标准库，避免每 30 秒导入整个应用。
"""

import json
import sys
import urllib.request
from pathlib import Path

CONFIG_PATH = Path("config/config.json")
DEFAULT_PORT = 7892


def webui_port(config_path: Path = CONFIG_PATH) -> int:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        return int(config["program"]["webui_port"])
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULT_PORT


def main() -> int:
    port = webui_port()
    # 忽略 HTTP_PROXY 等环境变量：回环探测不能走代理
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for host in ("127.0.0.1", "[::1]"):
        try:
            with opener.open(f"http://{host}:{port}/health", timeout=2):
                return 0
        except OSError:
            continue
    return 1


if __name__ == "__main__":
    sys.exit(main())
