import logging

from module.conf import settings
from module.models import Bangumi
from module.models.bangumi import Episode
from module.models.config import LLM
from module.parser.analyser import (
    LLMParser,
    mikan_parser,
    raw_parser,
    tmdb_parser,
    torrent_parser,
)

logger = logging.getLogger(__name__)

# Lazy singleton: building an LLMParser (and its underlying SDK client) is not
# free, so keep one around and only rebuild it when the relevant settings change.
# mode 不影响客户端构建（调用时读取），不参与缓存键。
_llm_parser: LLMParser | None = None
_llm_parser_kwargs: dict | None = None


def _get_llm_parser(kwargs: dict) -> LLMParser:
    global _llm_parser, _llm_parser_kwargs
    if _llm_parser is None or _llm_parser_kwargs != kwargs:
        _llm_parser = LLMParser(**kwargs)
        _llm_parser_kwargs = kwargs
    return _llm_parser


def reset_cache() -> None:
    """清空 LLM 解析器单例。配置重载后必须调用，否则会继续使用旧配置
    （如 provider/base_url/api_key）构建的客户端。"""
    global _llm_parser, _llm_parser_kwargs
    _llm_parser = None
    _llm_parser_kwargs = None


def _llm_config() -> LLM:
    """读取 LLM 配置段；llm 段缺失时回退读取旧的 experimental_openai
    （与 conf/config.py 的自动迁移互为保险）。"""
    llm = getattr(settings, "llm", None)
    if llm is not None:
        return llm
    legacy = settings.experimental_openai
    return LLM(
        enable=legacy.enable,
        provider="openai",
        api_key=legacy.api_key,
        model=legacy.model,
        base_url=legacy.api_base,
        # 旧配置的语义是 LLM 优先
        mode="primary",
    )


async def _llm_parse(raw: str) -> Episode | None:
    """用 LLM 解析标题，返回 Episode；任何失败（API 错误、拒答、
    输出不可用）都返回 None，由调用方决定是否回退。"""
    conf = _llm_config()
    try:
        llm = _get_llm_parser(
            {
                "provider": conf.provider,
                "api_key": conf.api_key,
                "model": conf.model,
                "base_url": conf.base_url,
            }
        )
        episode_dict = await llm.parse(raw, asdict=True)
        if not isinstance(episode_dict, dict):
            return None
        return Episode(**episode_dict)
    except Exception as e:
        logger.warning(f"LLM cannot parse '{raw}': {type(e).__name__}: {e}")
        return None


class TitleParser:
    def __init__(self):
        pass

    @staticmethod
    def torrent_parser(
        torrent_path: str,
        torrent_name: str | None = None,
        season: int | None = None,
        file_type: str = "media",
        episode_type: str = "episode",
    ):
        try:
            return torrent_parser(
                torrent_path, torrent_name, season, file_type, episode_type
            )
        except Exception as e:
            logger.warning(f"Cannot parse {torrent_path} with error {e}")

    @staticmethod
    async def tmdb_parser(
        title: str, season: int, language: str, episode_type: str = "episode"
    ):
        tmdb_info = await tmdb_parser(title, language, is_movie=episode_type == "movie")
        if tmdb_info:
            logger.debug("TMDB Matched, official title is %s", tmdb_info.title)
            tmdb_season = tmdb_info.last_season if tmdb_info.last_season else season
            return tmdb_info.title, tmdb_season, tmdb_info.year, tmdb_info.poster_link
        else:
            logger.warning(f"Cannot match {title} in TMDB. Use raw title instead.")
            logger.warning("Please change bangumi info manually.")
            return title, season, None, None

    @staticmethod
    async def tmdb_poster_parser(bangumi: Bangumi):
        tmdb_info = await tmdb_parser(
            bangumi.official_title, settings.rss_parser.language
        )
        if tmdb_info:
            logger.debug("TMDB Matched, official title is %s", tmdb_info.title)
            bangumi.poster_link = tmdb_info.poster_link
        else:
            logger.warning(
                f"Cannot match {bangumi.official_title} in TMDB. Use raw title instead."
            )
            logger.warning("Please change bangumi info manually.")

    @staticmethod
    async def raw_parser(raw: str) -> Bangumi | None:
        language = settings.rss_parser.language
        try:
            llm_conf = _llm_config()
            episode = None
            # primary 模式：LLM 优先解析每个标题；失败时用正则兜底，保证不丢标题
            if llm_conf.enable and llm_conf.mode == "primary":
                episode = await _llm_parse(raw)
            if episode is None:
                episode = raw_parser(raw)
            # fallback 模式（默认）：正则优先，仅当正则失败时才请求 LLM 兜底
            if episode is None and llm_conf.enable and llm_conf.mode == "fallback":
                episode = await _llm_parse(raw)
            if episode is None:
                return None

            titles = {
                "zh": episode.title_zh,
                "en": episode.title_en,
                "jp": episode.title_jp,
            }
            title_raw = episode.title_en or episode.title_zh or episode.title_jp
            if titles[language]:
                official_title = titles[language]
            elif titles["zh"]:
                official_title = titles["zh"]
            elif titles["en"]:
                official_title = titles["en"]
            elif titles["jp"]:
                official_title = titles["jp"]
            else:
                official_title = title_raw
            if not title_raw:
                logger.warning("Cannot extract title_raw from '%s', skipping", raw)
                return None
            _season = episode.season
            logger.debug("RAW:%s >> %s", raw, title_raw)
            return Bangumi(
                official_title=official_title,
                title_raw=title_raw,
                season=_season,
                season_raw=episode.season_raw,
                group_name=episode.group,
                dpi=episode.resolution,
                source=episode.source,
                subtitle=episode.sub,
                eps_collect=False if episode.episode > 1 else True,
                offset=0,
                filter=",".join(settings.rss_parser.filter),
                episode_type=episode.episode_type,
            )
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Cannot parse '{raw}': {type(e).__name__}: {e}")
            return None

    @staticmethod
    async def mikan_parser(homepage: str) -> tuple[str, str]:
        return await mikan_parser(homepage)
