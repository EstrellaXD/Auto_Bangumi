"""内置插件：种子过滤（``torrent.filter``）。

规则自带的「排除过滤」由宿主执行；本插件补充「包含过滤」：配置后，只有
名称匹配任一表达式的种子才会被下载。未配置时不过滤任何种子。
"""

import logging
import re

from pydantic import BaseModel, Field

from ab_sdk import Plugin, Verdict, hook, points
from ab_sdk.ingest import BangumiInfo, Release, TorrentInfo

logger = logging.getLogger(__name__)


class Options(BaseModel):
    include: list[str] = Field(
        default_factory=list,
        title="包含过滤",
        description=(
            "只下载名称匹配任一表达式的种子（正则，忽略大小写），"
            "例如 1080p、简体。留空表示不限制。对所有订阅生效。"
        ),
    )


def compile_terms(terms: list[str]) -> re.Pattern | None:
    """把多个表达式合并为一个模式；非法正则按字面匹配（与排除过滤一致）。"""
    cleaned = [t.strip() for t in terms if t.strip()]
    if not cleaned:
        return None
    try:
        return re.compile("|".join(cleaned), re.IGNORECASE)
    except re.error:
        logger.warning("包含过滤 %s 不是合法正则，按字面匹配", cleaned)
        return re.compile("|".join(re.escape(t) for t in cleaned), re.IGNORECASE)


class IngestFilters(Plugin[Options]):
    config_model = Options

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._include = compile_terms(self.config.include)

    @hook(points.TORRENT_FILTER, priority=50)
    def include_regex(
        self,
        torrent: TorrentInfo,
        release: Release | None,
        bangumi: BangumiInfo,
    ) -> Verdict:
        if self._include is None or self._include.search(torrent.name):
            return Verdict.ok()
        return Verdict.reject("不匹配包含过滤")
