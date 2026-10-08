"""新规则入库前的元数据补全（``metadata_provider`` 扩展点）。

RSS 订阅的 ``parser`` 字段选择元数据源：内置的 ``mikan``（解析 Mikan 番剧
页面的海报与官方标题）与 ``tmdb`` 以 ``core`` 身份登记，插件可登记新的 id。
未登记的取值（如 ``none``）不做任何补全。
"""

import logging
from dataclasses import replace

from ab_sdk import points
from ab_sdk.ingest import Metadata, MetadataProvider, MetadataRequest
from module.conf import settings
from module.models import Bangumi, Movie, RSSItem, Torrent
from module.parser import TitleParser
from module.plugin import host as plugin_host
from module.plugin.views import torrent_info

logger = logging.getLogger(__name__)


class MikanMetadata:
    """从 Mikan 番剧页面读取海报与官方标题。"""

    async def enrich(self, request: MetadataRequest) -> Metadata | None:
        homepage = request.torrent.homepage
        if not homepage:
            if request.kind == "movie":
                logger.warning("Mikan movie torrent has no homepage info.")
            else:
                logger.warning("Mikan torrent has no homepage info.")
            return None
        try:
            poster_link, official_title = await TitleParser.mikan_parser(homepage)
        except AttributeError as e:
            logger.warning(f"Failed to parse Mikan homepage {homepage}: {e}")
            return None
        return replace(
            request.current,
            poster_link=poster_link,
            official_title=official_title or request.current.official_title,
        )


class TmdbMetadata:
    """按标题搜索 TMDB；未命中时沿用原标题，年份与海报置空（与 3.x 一致）。"""

    async def enrich(self, request: MetadataRequest) -> Metadata | None:
        current = request.current
        title, season, year, poster_link = await TitleParser.tmdb_parser(
            current.official_title,
            current.season,
            request.language,
            episode_type=request.episode_type,
        )
        if request.kind == "movie":
            season = current.season
        return Metadata(
            official_title=title, season=season, year=year, poster_link=poster_link
        )


CORE_PROVIDERS: dict[str, MetadataProvider] = {
    "mikan": MikanMetadata(),
    "tmdb": TmdbMetadata(),
}


def _valid_metadata(result: Metadata) -> bool:
    """字段会直接写入新规则；标题为空、季度非整数等结果按失败处理。"""
    return (
        isinstance(result, Metadata)
        and isinstance(result.official_title, str)
        and result.official_title != ""
        and isinstance(result.season, int)
        and isinstance(result.year, (str, type(None)))
        and isinstance(result.poster_link, (str, type(None)))
    )


async def _resolve(parser_id: str, request: MetadataRequest) -> Metadata | None:
    entry = (
        plugin_host.get_registry().providers(points.METADATA_PROVIDER).get(parser_id)
    )
    if entry is None:
        return None
    if entry.plugin_id == plugin_host.CORE:
        # 内置源的异常照旧向上抛出，保持 3.x 行为
        return await entry.factory().enrich(request)

    async def call() -> Metadata | None:
        return await entry.factory().enrich(request)

    runner = plugin_host.get_runner()
    if runner is not None:
        ok, result = await runner.call_provider(
            entry.plugin_id, points.METADATA_PROVIDER, call, check=_valid_metadata
        )
        if not ok:
            return None
    else:
        try:
            result = await call()
        except Exception as e:
            logger.warning("[Plugin:%s] 元数据源失败：%s", entry.plugin_id, e)
            return None
    if result is not None and not _valid_metadata(result):
        logger.warning(
            "[Plugin:%s] 元数据源返回了无效结果 %s，已忽略",
            entry.plugin_id,
            type(result).__name__,
        )
        return None
    return result


async def enrich_bangumi(bangumi: Bangumi, rss: RSSItem, torrent: Torrent) -> None:
    request = MetadataRequest(
        kind="bangumi",
        torrent=torrent_info(torrent),
        language=settings.rss_parser.language,
        episode_type=bangumi.episode_type,
        current=Metadata(
            official_title=bangumi.official_title,
            season=bangumi.season,
            year=bangumi.year,
            poster_link=bangumi.poster_link,
        ),
    )
    result = await _resolve(rss.parser, request)
    if result is None:
        return
    bangumi.official_title = result.official_title
    bangumi.season = result.season
    bangumi.year = result.year
    bangumi.poster_link = result.poster_link


async def enrich_movie(movie: Movie, rss: RSSItem, torrent: Torrent) -> None:
    request = MetadataRequest(
        kind="movie",
        torrent=torrent_info(torrent),
        language=settings.rss_parser.language,
        episode_type="movie",
        current=Metadata(
            official_title=movie.official_title,
            season=1,
            year=str(movie.year) if movie.year is not None else None,
            poster_link=movie.poster_link,
        ),
    )
    result = await _resolve(rss.parser, request)
    if result is None:
        return
    movie.official_title = result.official_title
    if result.year:
        try:
            movie.year = int(result.year)
        except (ValueError, TypeError):
            pass
    movie.poster_link = result.poster_link
