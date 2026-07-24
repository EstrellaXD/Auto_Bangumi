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
    tmdb_parser,
    torrent_parser,
)
from module.parser.analyser.providers.base import AuthExpiredError
from module.parser.analyser.providers.credentials import auth_generation
from module.parser.analyser.selector import parse_configured_release_title_with_trace
from module.parser.analyser.tokenizer import (
    MediaType,
    ParsedRelease,
    ReleaseKind,
)
from module.parser.analyser.tokenizer.candidate import Claims
from module.parser.analyser.tokenizer.compat import to_legacy_episode
from module.parser.release_policy import (
    PersistenceTarget,
    bangumi_episode_type,
    has_release_evidence,
    is_weak_title_only,
    normalized_season,
    persistence_target,
)

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


def _llm_media_type(episode: Episode) -> MediaType:
    if episode.episode_type == "movie" or episode.is_movie:
        return MediaType.MOVIE
    if episode.episode_type == "special":
        return MediaType.SPECIAL
    return MediaType.EPISODE


def _project_classic_release(
    raw: str, release: ParsedRelease | None
) -> ParsedRelease | None:
    """Apply the pre-refactor compatibility contract to a Classic result."""
    if release is None:
        return None
    episode = to_legacy_episode(release)
    if episode is None:
        title_count = sum(
            bool(title)
            for title in (release.title_en, release.title_zh, release.title_jp)
        )
        if (
            title_count > 1
            and release.episode is None
            and release.media_type is MediaType.UNKNOWN
            and release.release_kind is ReleaseKind.SINGLE
            and has_release_evidence(release)
        ):
            return release
        return None
    return ParsedRelease(
        raw=raw,
        title_en=episode.title_en,
        title_zh=episode.title_zh,
        title_jp=episode.title_jp,
        group=episode.group,
        season=episode.season,
        season_raw=episode.season_raw,
        episode=episode.episode,
        media_type=_llm_media_type(episode),
        resolution=episode.resolution,
        source=episode.source,
        subtitle=episode.sub,
    )


def _has_structured_release_claims(claims: Claims) -> bool:
    """Whether a title-less parse still identified a concrete resource kind."""
    return any(
        value is not None
        for value in (
            claims.season,
            claims.episode,
            claims.episode_end,
            claims.media_type,
            claims.release_kind,
        )
    )


def _merge_llm_release(
    raw: str,
    episode: Episode,
    deterministic: ParsedRelease | None,
) -> ParsedRelease:
    """Convert an LLM result without mutating the cached legacy object.

    LLM titles keep their primary-mode semantics.  When deterministic parsing
    found a structural bundle, its media/cardinality/season/episode/version
    fields stay atomic so an LLM cannot create hybrids such as RANGE 7-12 or
    turn a movie/PV into a weekly episode.
    """

    media_type = _llm_media_type(episode)
    release_kind = ReleaseKind.SINGLE
    use_deterministic_structure = False
    if deterministic is not None:
        if (
            deterministic.media_type is not MediaType.UNKNOWN
            or deterministic.is_mixed_collection
        ):
            media_type = deterministic.media_type
        release_kind = deterministic.release_kind
        use_deterministic_structure = bool(
            deterministic.media_type is not MediaType.UNKNOWN
            or deterministic.release_kind is not ReleaseKind.SINGLE
            or deterministic.season is not None
            or deterministic.episode is not None
            or deterministic.episode_end is not None
        )

    season: int | None = episode.season
    season_raw: str | None = episode.season_raw
    episode_number: int | float | None = episode.episode
    episode_end: int | float | None = None
    episode_title: str | None = None
    version: int | None = None
    if deterministic is not None and use_deterministic_structure:
        season = deterministic.season
        season_raw = deterministic.season_raw
        episode_number = deterministic.episode
        episode_end = deterministic.episode_end
        episode_title = deterministic.episode_title
        version = deterministic.version

    return ParsedRelease(
        raw=raw,
        title_en=episode.title_en
        or (deterministic.title_en if deterministic else None),
        title_zh=episode.title_zh
        or (deterministic.title_zh if deterministic else None),
        title_jp=episode.title_jp
        or (deterministic.title_jp if deterministic else None),
        group=episode.group or (deterministic.group if deterministic else None),
        season=season,
        season_raw=season_raw,
        episode=episode_number,
        episode_end=episode_end,
        episode_title=episode_title,
        media_type=media_type,
        release_kind=release_kind,
        resolution=episode.resolution
        or (deterministic.resolution if deterministic else None),
        source=episode.source or (deterministic.source if deterministic else None),
        subtitle=episode.sub or (deterministic.subtitle if deterministic else None),
        codecs=deterministic.codecs if deterministic else (),
        audio=deterministic.audio if deterministic else (),
        container=deterministic.container if deterministic else None,
        version=version,
        year=deterministic.year if deterministic else None,
        tags=deterministic.tags if deterministic else (),
        evidence=deterministic.evidence if deterministic else (),
    )


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
    def _resolve_titles(release: ParsedRelease) -> tuple[str | None, str | None]:
        """Extract official_title and title_raw from a generic release."""
        language = settings.rss_parser.language
        titles = {
            "zh": release.title_zh,
            "en": release.title_en,
            "jp": release.title_jp,
        }
        title_raw = release.title_en or release.title_zh or release.title_jp
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
    def _release_to_bangumi(
        release: ParsedRelease, official_title: str, title_raw: str
    ) -> Bangumi:
        episode = release.episode
        return Bangumi(
            official_title=official_title,
            title_raw=title_raw,
            year=str(release.year) if release.year is not None else None,
            season=normalized_season(release),
            season_raw=release.season_raw,
            group_name=release.group or "",
            dpi=release.resolution,
            source=release.source,
            subtitle=release.subtitle,
            eps_collect=episode is None or episode <= 1,
            episode_offset=0,
            filter=",".join(settings.rss_parser.filter),
            episode_type=bangumi_episode_type(release),
        )

    @staticmethod
    def _release_to_movie(
        release: ParsedRelease, official_title: str, title_raw: str
    ) -> Movie:
        return Movie(
            official_title=official_title,
            title_raw=title_raw,
            year=release.year,
            group_name=release.group or "",
            dpi=release.resolution,
            source=release.source,
            subtitle=release.subtitle,
            filter=",".join(settings.rss_parser.filter),
        )

    @staticmethod
    async def raw_parser(raw: str) -> Bangumi | Movie | None:
        try:
            llm_conf = _llm_config()
            parse_outcome = parse_configured_release_title_with_trace(raw)
            logger.debug(
                "Parsing resource with %s engine: %s", parse_outcome.engine, raw
            )
            deterministic = parse_outcome.result
            if parse_outcome.engine == "classic":
                deterministic = _project_classic_release(raw, deterministic)
            if (
                deterministic is None
                and parse_outcome.trace is not None
                and _has_structured_release_claims(parse_outcome.trace.claims)
            ):
                logger.debug("Structured resource has no usable title: %s", raw)
                return None
            if deterministic is not None and not deterministic.primary_title:
                logger.debug("Structured resource has no usable title: %s", raw)
                return None
            release: ParsedRelease | None = None

            # primary 模式保留 LLM 标题语义，但确定性结构提示仍参与合并，
            # 避免关键词误判并确保 range/PV 等准入策略无法被绕过。
            if llm_conf.enable and llm_conf.mode == "primary":
                episode = await _llm_parse(raw)
                if episode is not None:
                    release = _merge_llm_release(raw, episode, deterministic)

            if release is None:
                release = deterministic

            # fallback 只处理“解析失败/只有弱标题”的输入。明确识别出的
            # PV、range、batch、collection 直接遵守业务拒绝策略。
            should_fallback = deterministic is None or is_weak_title_only(deterministic)
            if llm_conf.enable and llm_conf.mode == "fallback" and should_fallback:
                episode = await _llm_parse(raw)
                if episode is not None:
                    release = _merge_llm_release(raw, episode, deterministic)

            if release is None:
                return None
            target = persistence_target(release)
            if target is None:
                logger.debug("Parsed but did not admit resource: %s", raw)
                return None

            official_title, title_raw = TitleParser._resolve_titles(release)
            if not title_raw:
                logger.warning("Cannot extract title_raw from '%s', skipping", raw)
                return None
            if not official_title:
                logger.warning("Cannot extract official_title from '%s', skipping", raw)
                return None
            logger.debug("RAW:%s >> %s", raw, title_raw)

            if target is PersistenceTarget.MOVIE:
                return TitleParser._release_to_movie(release, official_title, title_raw)
            return TitleParser._release_to_bangumi(release, official_title, title_raw)
        except (ValueError, AttributeError, TypeError) as e:
            logger.warning(f"Cannot parse '{raw}': {type(e).__name__}: {e}")
            return None

    @staticmethod
    async def mikan_parser(homepage: str) -> tuple[str, str]:
        return await mikan_parser(homepage)
