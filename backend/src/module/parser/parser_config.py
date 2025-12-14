from models.config import RSSParser

TMDB_URL = "https://api.themoviedb.org"
TMDB_IMG_URL = "https://image.tmdb.org/t/p/w780"

_parser_config: RSSParser | None = None


def get_parser_config() -> RSSParser:
    """获取解析器配置，如果未初始化则返回默认配置"""
    if _parser_config is None:
        return RSSParser()
    return _parser_config


def set_parser_config(config: RSSParser):
    """设置解析器配置"""
    global _parser_config
    _parser_config = config


# Default TMDB API key, replace with your own key if needed
# Note: Using a public key is not recommended for production use.
# It is better to set your own key in the configuration.
t = "291237f90b24267380d6176c98f7619f"

LANGUAGE = {"zh": "zh-CN", "jp": "ja-JP", "en": "en-US"}
def get_api_key():
    """Get the TMDB API key from settings."""
    return get_parser_config().tmdb_api_key or t


def search_url(keyword: str) -> str:
    """Generate TMDB search URL for TV shows."""
    return f"{TMDB_URL}/3/search/tv?api_key={get_api_key()}&page=1&query={keyword}&include_adult=false"


def info_url(show_id: str, language: str) -> str:
    """Generate TMDB info URL for a specific TV show."""
    return f"{TMDB_URL}/3/tv/{show_id}?api_key={get_api_key()}&language={LANGUAGE[language]}"
