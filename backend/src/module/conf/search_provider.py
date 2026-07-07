from pathlib import Path
from typing import TypedDict

from module.utils import json_config


class ProviderConfig(TypedDict):
    """单个搜索源配置：URL 模板与解析该源结果所用的解析器。"""

    url: str
    parser: str


def _default_parser(site: str) -> str:
    """旧配置没有 parser 字段时的默认规则：mikan 站点用 mikan 解析器，其余用 tmdb。"""
    return "mikan" if site == "mikan" else "tmdb"


DEFAULT_PROVIDER: dict[str, ProviderConfig] = {
    "mikan": {"url": "https://mikanani.me/RSS/Search?searchstr=%s", "parser": "mikan"},
    "nyaa": {"url": "https://nyaa.si/?page=rss&q=%s&c=0_0&f=0", "parser": "tmdb"},
    "dmhy": {"url": "http://dmhy.org/topics/rss/rss.xml?keyword=%s", "parser": "tmdb"},
}

PROVIDER_PATH = Path("config/search_provider.json")


def _normalize(raw: dict) -> dict[str, ProviderConfig]:
    """兼容旧版本仅存储 URL 字符串的配置格式：{"site": "url"} -> {"site": {"url", "parser"}}。"""
    normalized: dict[str, ProviderConfig] = {}
    for site, value in raw.items():
        if isinstance(value, str):
            normalized[site] = {"url": value, "parser": _default_parser(site)}
        else:
            normalized[site] = {
                "url": value.get("url", ""),
                "parser": value.get("parser") or _default_parser(site),
            }
    return normalized


def load_provider() -> dict[str, ProviderConfig]:
    if PROVIDER_PATH.exists():
        return _normalize(json_config.load(PROVIDER_PATH))
    else:
        PROVIDER_PATH.parent.mkdir(parents=True, exist_ok=True)
        json_config.save(PROVIDER_PATH, DEFAULT_PROVIDER)
        return DEFAULT_PROVIDER


def save_provider(providers: dict) -> None:
    """Save search providers to config file and update SEARCH_CONFIG.

    Accepts either the legacy {site: url} shape or the {site: {url, parser}}
    shape. When only a URL is supplied for a site that already has a saved
    parser choice, that parser choice is preserved instead of being reset to
    the default.
    """
    global SEARCH_CONFIG
    normalized = _normalize(providers)
    for site, config in normalized.items():
        if isinstance(providers.get(site), str) and site in SEARCH_CONFIG:
            config["parser"] = SEARCH_CONFIG[site]["parser"]
    json_config.save(PROVIDER_PATH, normalized)
    SEARCH_CONFIG = normalized


def get_provider() -> dict[str, ProviderConfig]:
    """Get current search providers config."""
    return SEARCH_CONFIG


SEARCH_CONFIG = load_provider()
