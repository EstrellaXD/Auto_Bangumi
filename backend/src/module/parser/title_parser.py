import asyncio
import logging
import time

from module.conf import settings
from module.models import Bangumi, Movie
from module.models.bangumi import Episode
from module.models.config import LLM
from module.parser.analyser import (
    LLMParser,
    mikan_parser,
    raw_parser,
    tmdb_parser,
    torrent_parser,
)
from module.parser.analyser.providers.base import AuthExpiredError
from module.parser.analyser.providers.credentials import auth_generation
from module.parser.analyser.raw_parser import _detect_non_episodic_type

logger = logging.getLogger(__name__)


# 保留 fire-and-forget 通知任务的强引用，防止其在运行完成前被 GC。
_notify_tasks: set = set()


def _notify_auth_failure(provider_id: str, message: str) -> None:
    """凭据失效时向通知中心投递事件（fire-and-forget，不阻塞解析路径）。"""
    from module.notification import LLMAuthFailureEvent, NotificationManager

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    event = LLMAuthFailureEvent(provider_id=provider_id, message=message)
    task = loop.create_task(NotificationManager().send_event(event))
    _notify_tasks.add(task)
    task.add_done_callback(_notify_tasks.discard)


# Lazy singleton: building an LLMParser (and its underlying SDK client) is not
# free, so keep one around and only rebuild it when the relevant settings change.
# mode 不影响客户端构建（调用时读取），不参与缓存键。
_llm_parser: LLMParser | None = None
_llm_parser_kwargs: dict | None = None
_llm_cache: dict[tuple, tuple[float, Episode | None]] = {}
_llm_failure_count = 0
_llm_breaker_until = 0.0
_llm_semaphore: asyncio.Semaphore | None = None
_llm_semaphore_limit: int | None = None


def _get_llm_parser(kwargs: dict) -> LLMParser:
    global _llm_parser, _llm_parser_kwargs
    if _llm_parser is None or _llm_parser_kwargs != kwargs:
        # auth_gen 只参与"是否重建"的比较，不是构造参数
        ctor_kwargs = {k: v for k, v in kwargs.items() if k != "auth_gen"}
        _llm_parser = LLMParser(**ctor_kwargs)
        _llm_parser_kwargs = kwargs
    return _llm_parser


def reset_cache() -> None:
    """清空 LLM 解析器单例。配置重载后必须调用，否则会继续使用旧配置
    （如 provider/base_url/api_key）构建的客户端。"""
    global _llm_parser, _llm_parser_kwargs
    global _llm_cache, _llm_failure_count, _llm_breaker_until
    global _llm_semaphore, _llm_semaphore_limit
    parser = _llm_parser
    old_kwargs = _llm_parser_kwargs
    _llm_parser = None
    _llm_parser_kwargs = None
    _llm_cache = {}
    _llm_failure_count = 0
    _llm_breaker_until = 0.0
    _llm_semaphore = None
    _llm_semaphore_limit = None
    if parser is not None and hasattr(parser, "aclose"):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        # 不能立刻关：进行中的 _llm_parse 还握着这个共享 client，立即
        # aclose 会让它们全部报错、把 None 写进缓存并误触熔断。in-flight
        # 调用被 wait_for(timeout) 兜底，等一个超时周期后再关必然安全。
        grace = float((old_kwargs or {}).get("timeout") or 30) + 5.0

        async def _close_after_grace() -> None:
            await asyncio.sleep(grace)
            await parser.aclose()

        loop.create_task(_close_after_grace())


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
    global _llm_failure_count, _llm_breaker_until
    conf = _llm_config()
    now = time.monotonic()
    if _llm_breaker_until > now:
        logger.warning("LLM parser breaker is open; skipping '%s'", raw)
        return None
    api_key, model, base_url = conf.effective()
    parser_kwargs = {
        "provider": conf.provider,
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
        "timeout": conf.timeout,
        # 换号/断开时 bump → 单例重建；静默刷新不 bump（token 不进键）。
        "auth_gen": auth_generation(conf.provider),
    }
    cache_key = (tuple(sorted(parser_kwargs.items())), raw)
    if conf.cache_ttl > 0:
        cached = _llm_cache.get(cache_key)
        if cached is not None:
            expires_at, cached_episode = cached
            if expires_at > now:
                return cached_episode
            _llm_cache.pop(cache_key, None)
    try:
        try:
            llm = _get_llm_parser(parser_kwargs)
        except ValueError as e:
            # 未知 provider id（如配置里手改出拼写错误）：明确指出并熔断，
            # 避免每个标题都刷一行含糊的失败日志。
            logger.error(
                "Unknown LLM provider '%s' (%s); check settings.llm.provider",
                conf.provider,
                e,
            )
            _llm_breaker_until = time.monotonic() + conf.failure_backoff
            _cache_llm_result(cache_key, None, conf.cache_ttl)
            return None
        semaphore = _get_llm_semaphore(conf.max_concurrency)
        async with semaphore:
            episode_dict = await asyncio.wait_for(
                llm.parse(raw, asdict=True), timeout=conf.timeout
            )
        if not isinstance(episode_dict, dict):
            _record_llm_failure(conf)
            _cache_llm_result(cache_key, None, conf.cache_ttl)
            return None
        episode = Episode(**episode_dict)
        _llm_failure_count = 0
        _llm_breaker_until = 0.0
        _cache_llm_result(cache_key, episode, conf.cache_ttl)
        return episode
    except AuthExpiredError as e:
        # 刷新已失败，重试没有意义：跳过失败阈值直接熔断，等用户重连。
        logger.error(
            "LLM credentials for '%s' expired and refresh failed: %s",
            conf.provider,
            e,
        )
        _llm_breaker_until = time.monotonic() + conf.failure_backoff
        _cache_llm_result(cache_key, None, conf.cache_ttl)
        _notify_auth_failure(conf.provider, str(e))
        return None
    except Exception as e:
        logger.warning(f"LLM cannot parse '{raw}': {type(e).__name__}: {e}")
        _record_llm_failure(conf)
        _cache_llm_result(cache_key, None, conf.cache_ttl)
        return None


def _get_llm_semaphore(limit: int) -> asyncio.Semaphore:
    global _llm_semaphore, _llm_semaphore_limit
    if _llm_semaphore is None or _llm_semaphore_limit != limit:
        _llm_semaphore = asyncio.Semaphore(limit)
        _llm_semaphore_limit = limit
    return _llm_semaphore


def _cache_llm_result(
    cache_key: tuple, episode: Episode | None, cache_ttl: int
) -> None:
    if cache_ttl <= 0:
        return
    _llm_cache[cache_key] = (time.monotonic() + cache_ttl, episode)


def _record_llm_failure(conf: LLM) -> None:
    global _llm_failure_count, _llm_breaker_until
    _llm_failure_count += 1
    if _llm_failure_count >= conf.failure_threshold:
        _llm_breaker_until = time.monotonic() + conf.failure_backoff


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
    def _resolve_titles(episode: Episode) -> tuple[str | None, str | None]:
        """Extract official_title and title_raw from an Episode."""
        language = settings.rss_parser.language
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
        return official_title, title_raw

    @staticmethod
    def _episode_to_bangumi(
        episode: Episode, official_title: str, title_raw: str
    ) -> Bangumi:
        return Bangumi(
            official_title=official_title,
            title_raw=title_raw,
            season=episode.season,
            season_raw=episode.season_raw,
            group_name=episode.group,
            dpi=episode.resolution,
            source=episode.source,
            subtitle=episode.sub,
            eps_collect=False if episode.episode > 1 else True,
            episode_offset=0,
            filter=",".join(settings.rss_parser.filter),
            episode_type=episode.episode_type,
        )

    @staticmethod
    def _episode_to_movie(
        episode: Episode, official_title: str, title_raw: str
    ) -> Movie:
        return Movie(
            official_title=official_title,
            title_raw=title_raw,
            group_name=episode.group,
            dpi=episode.resolution,
            source=episode.source,
            subtitle=episode.sub,
            filter=",".join(settings.rss_parser.filter),
        )

    @staticmethod
    async def raw_parser(raw: str) -> Bangumi | Movie | None:
        try:
            llm_conf = _llm_config()
            episode = None
            from_llm = False
            # primary 模式：LLM 优先解析每个标题；失败时用正则兜底，保证不丢标题
            if llm_conf.enable and llm_conf.mode == "primary":
                episode = await _llm_parse(raw)
                from_llm = episode is not None
            if episode is None:
                episode = raw_parser(raw)
            # fallback 模式（默认）：正则优先，仅当正则失败时才请求 LLM 兜底
            if episode is None and llm_conf.enable and llm_conf.mode == "fallback":
                episode = await _llm_parse(raw)
                from_llm = episode is not None
            if episode is None:
                return None
            # 正则路径已在剥离字幕组名后的标题上判定过 episode_type，这里只
            # 给缺少该能力的 LLM 结果补分类；对完整 raw 判定会把组名/标签里
            # 撞词（如 "[Movie-Fan]"）的普通周更集误判成剧场版/特别篇。
            if from_llm:
                detected_episode_type = _detect_non_episodic_type(raw)
                if detected_episode_type is not None:
                    episode.episode_type = detected_episode_type

            official_title, title_raw = TitleParser._resolve_titles(episode)
            if not title_raw:
                logger.warning("Cannot extract title_raw from '%s', skipping", raw)
                return None
            if not official_title:
                logger.warning("Cannot extract official_title from '%s', skipping", raw)
                return None
            logger.debug("RAW:%s >> %s", raw, title_raw)

            # The upstream LLM path exposes its inferred non-episodic type on a
            # Bangumi.  Keep that contract while routing deterministically parsed
            # movie markers into the dedicated local Movie table.
            if episode.episode_type == "movie" and not from_llm:
                return TitleParser._episode_to_movie(episode, official_title, title_raw)
            return TitleParser._episode_to_bangumi(episode, official_title, title_raw)
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Cannot parse '{raw}': {type(e).__name__}: {e}")
            return None

    @staticmethod
    async def mikan_parser(homepage: str) -> tuple[str, str]:
        return await mikan_parser(homepage)
