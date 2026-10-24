"""搜索站点契约。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchSite:
    """一个返回 RSS 的搜索站点。

    ``url`` 中的 ``%s`` 会被替换为关键词（以 ``+`` 连接）。``parser`` 指定用哪个
    元数据源补全搜索结果：``mikan`` 或 ``tmdb``。用户在搜索设置里配置的同名
    站点优先于插件提供的站点。
    """

    url: str
    parser: str = "tmdb"
