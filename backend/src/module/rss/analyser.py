import logging
import re

import httpx

from models import Bangumi, RSSItem, Torrent
from module.exceptions import ParserError
from module.parser import MikanParser, RawParser, parser_config, tmdb_parser

logger = logging.getLogger(__name__)

# 模块级别的 parser 实例
_mikan_parser: MikanParser | None = None


def _get_mikan_parser() -> MikanParser:
    global _mikan_parser
    if _mikan_parser is None:
        _mikan_parser = MikanParser()
    return _mikan_parser


def filter_torrent(torrent: Torrent, bangumi: Bangumi) -> bool:
    """
    filter torrent by bangumi
    """
    exclude_filter = bangumi.exclude_filter.replace(",", "|") if bangumi.exclude_filter else ""
    include_filter = bangumi.include_filter.replace(",", "|") if bangumi.include_filter else ""
    if exclude_filter and re.search(exclude_filter, torrent.name):
        logger.debug(
            f"[RSS Filter] Exclude torrent {torrent.name} for {bangumi.official_title},regex: {exclude_filter}"
        )
        return False

    # Check include filter first (if set, torrent must match)
    if include_filter and not re.search(include_filter, torrent.name):
        logger.debug(f"[RSS Filter] Include filter not matched for {torrent.name}, regex: {include_filter}")
        return False
    logger.debug(
        f"[RSS Filter] Torrent {torrent.name} passed filters for {bangumi.official_title}. include_filter: {include_filter}, exclude_filter: {exclude_filter}"
    )
    return True


async def official_title_parser(bangumi: Bangumi, parser: str, torrent: Torrent) -> Bangumi:
    """解析官方标题

    根据 parser 类型使用 MikanParser 或 TmdbParser 解析官方标题
    """
    # MikanParser 要是没有homepage, 降级为 TmdbParser
    if torrent.homepage:
        try:
            parsered_bangumi = await MikanParser().parser(torrent.homepage)
            if parsered_bangumi is None:
                logger.debug("[Parser] 种子界面未找到对应的主页")
            else:
                bangumi.poster_link = parsered_bangumi.poster_link
                bangumi.official_title = parsered_bangumi.official_title
                bangumi.mikan_id = parsered_bangumi.id
        except httpx.RequestError:
            logger.warning("[Parser] Mikan parser request error, fallback to TMDB parser.")
        except ParserError as e:
            logger.warning(f"[Parser] Mikan parser error: {e}, fallback to TMDB parser.")
    try:
        parsered_bangumi = await tmdb_parser(bangumi.official_title, parser_config.language)
    except httpx.RequestError as e:
        logger.warning(f"[Parser] TMDB parser request error {e}.")
        if bangumi.mikan_id:
            # 这说明 Mikan 解析成功了，直接返回
            return bangumi
        else:
            # tmdb 和 mikan 都失败，抛出异常
            raise
    if parsered_bangumi is None:
        # 这说明 TMDB 上没有找到对应的番剧
        return bangumi
    # FIXME: 如果解析出来的属性是默认值，则不更新
    bangumi.official_title = parsered_bangumi.title
    bangumi.year = parsered_bangumi.year
    bangumi.season = parsered_bangumi.season
    bangumi.poster_link = parsered_bangumi.poster_link
    bangumi.tmdb_id = str(parsered_bangumi.id)
    # 一些非法的字符名称替换掉
    bangumi.official_title = re.sub(r"[/:.\\]", " ", bangumi.official_title)
    return bangumi


async def torrent_to_bangumi(torrent: Torrent, rss: RSSItem) -> Bangumi | None:
    """解析 torrent 名称为 bangumi

    filter 在 RawParser 中设置
    如果只有 rawparser, 则返回 None
    # 如果是网络导致的解析失败, 等待下次再试
    # 如果只解析出来了 tmdb, 也可认为解析成功
    # 如果 tmdb 和 mikan 都没有解析出来, 返回 RawParser 解析结果
    """
    if (bangumi := RawParser().parser(title=torrent.name)) and bangumi.official_title != "official_title":
        try:
            res = await official_title_parser(bangumi, rss.parser, torrent)
        except httpx.RequestError:
            logger.debug(f"[RSS analyser] Fail to parse official title for {torrent.name} due to request error.")
            return None
        # if not :
        #     logger.debug(f"[RSS analyser] Fail to parse official title for {torrent.name}.")
        #     return None
        # 这里是最早加入 bangumi.rss_link, bangumi.parser 的地方
        bangumi.rss_link = rss.url
        bangumi.parser = rss.parser
        logger.debug(f"[RSS analyser] Parsed bangumi: {bangumi.official_title} from torrent {torrent.name}")
        return bangumi
    return None
