import logging

import httpx
from models.config import Proxy


logger = logging.getLogger(__name__)

_proxy_config: Proxy | None = None


def get_proxy_config() -> Proxy:
    """获取代理配置，如果未初始化则返回默认配置"""
    if _proxy_config is None:
        return Proxy()
    return _proxy_config


def set_proxy_config(config: Proxy):
    """设置代理配置"""
    global _proxy_config
    _proxy_config = config


def set_proxy() -> str | None:
    config = get_proxy_config()
    if not config.enable:
        return None
    auth = ""
    host = config.host
    if host.startswith("http://"):
        host = host[7:]
    if config.username:
        auth = f"{config.username}:{config.password}@"
    if config.type in ["http", "socks5"]:
        return f"{config.type}://{auth}{host}:{config.port}"
    else:
        logger.error(f"[Network] Unsupported proxy type: {config.type}")
        return None


def test_proxy() -> bool:
    config = get_proxy_config()
    with httpx.Client(proxy=set_proxy()) as client:
        try:
            client.get("https://www.baidu.com")
            return True
        except httpx.ProxyError:
            logger.error(
                f"[Network] Cannot connect to proxy, please check your proxy username {config.username} and password {config.password}"
            )
            return False
        except httpx.ConnectError:
            logger.error(f"host is down, please check your proxy host {config.host}")
            return False
        except httpx.ConnectTimeout:
            logger.error(f"[Network] Cannot connect to proxy {config.host}:{config.port}")
            return False


if __name__ == "__main__":
    print(set_proxy())
    with httpx.Client(proxy=set_proxy()) as client:
        client.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
        )
        res = client.get("https://www.baidu.com")
        print(res.content)
        print(res)
