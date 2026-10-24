"""宿主 ORM 对象 → ``ab_sdk.ingest`` 只读快照的转换。

插件不接触数据库实例，钩子与 Provider 收到的都是这里构造的冻结副本。
"""

from ab_sdk.ingest import BangumiInfo, TorrentInfo
from module.models import Bangumi, Torrent


def torrent_info(torrent: Torrent) -> TorrentInfo:
    return TorrentInfo(
        name=torrent.name,
        url=torrent.url,
        homepage=torrent.homepage,
        rss_id=torrent.rss_id,
    )


def bangumi_info(bangumi: Bangumi) -> BangumiInfo:
    return BangumiInfo(
        id=bangumi.id,
        official_title=bangumi.official_title,
        title_raw=bangumi.title_raw,
        season=bangumi.season,
        group_name=bangumi.group_name,
        episode_type=bangumi.episode_type,
        rss_link=bangumi.rss_link or "",
        save_path=bangumi.save_path,
        filter=bangumi.filter or "",
    )
