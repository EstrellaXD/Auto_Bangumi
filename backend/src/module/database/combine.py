import logging

from sqlmodel import Session, SQLModel, and_, false, select, text

from models import Bangumi, RSSItem, Torrent, User

from .bangumi import BangumiDatabase
from .engine import engine as e
from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .user import UserDatabase

logger = logging.getLogger(__name__)


class Database(Session):
    """
    要提供几个交插的方法
    """

    def __init__(self, engine=e):
        self.engine = engine
        super().__init__(engine)
        self.rss: RSSDatabase = RSSDatabase(self)
        self.torrent: TorrentDatabase = TorrentDatabase(self)
        self.bangumi: BangumiDatabase = BangumiDatabase(self)
        self.user: UserDatabase = UserDatabase(self)

    def bangumi_to_rss(self, bangumi: Bangumi) -> RSSItem | None:
        return self.rss.search_url(bangumi.rss_link)

    def add_bangumi(self, bangumi: Bangumi):
        pass

    def torrent_to_bangumi(self, torrent: Torrent) -> Bangumi | None:
        """根据 Torrent 查找相关的 Bangumi"""
        "依据 official_title, seasion, rss_link"
        return self.bangumi.search(torrent.bangumi_official_title, torrent.bangumi_season, torrent.rss_link)

    def find_torrent_by_bangumi(self, bangumi: Bangumi) -> list[Torrent]:
        """根据 Bangumi 查找相关的 Torrent"""
        "依据 official_title, seasion, rss_link"
        return self.torrent.filter_by_bangumi(bangumi.official_title, bangumi.season, bangumi.rss_link)

    def create_table(self):
        SQLModel.metadata.create_all(self.engine)

    def drop_table(self):
        SQLModel.metadata.drop_all(self.engine)

    def _get_table_columns(self, table_name: str) -> list[str]:
        """获取表的所有列名"""
        result = self.exec(text(f"PRAGMA table_info({table_name})")).all()
        return [row[1] for row in result]  # row[1] is column name

    def get_unrenamed_torrents(self) -> list[Torrent]:
        """获取所有未重命名的种子"""
        return self.torrent.search_all_unrenamed()

    def find_bangumi_by_name(self, name: str, rss_link: str, aggrated: bool) -> Bangumi | None:
        # 现在是一个更新过的种子, 各种原因要查找 bangumi
        # 对于聚合而言, link, title_raw一致可认为是一个bangumi
        # 对于非聚合, link 一致就可认为是一个
        # 对于一个种子要找 bangumi, 主要是在 刷新 rss 的时候,
        if aggrated:
            statement = select(Bangumi).where(Bangumi.title_raw.contains(name))
            bangumi = self.exec(
                statement
                # select(Bangumi).where(Bangumi.deleted == false())
            ).first()
            return bangumi
        else:
            statement = select(Bangumi).where(
                and_(
                    (Bangumi.rss_link == rss_link),
                    # use `false()` to avoid E712 checking
                    # see: https://docs.astral.sh/ruff/rules/true-false-comparison/
                    Bangumi.deleted == false(),
                )
            )
            return self.exec(statement).first()



if __name__ == "__main__":
    url = "https://mikanani.me/Download/20250531/fb338d0c51c01c2494a9fb1642dd97769416b5c2.torrent"
    with Database() as db:
        ans = db.find_bangumi_by_name(
            name="Spice and Wolf",
            rss_link="https://mikanani.me/rss/12345",
            aggrated=True,
        )
        print(ans)
    #     db.migrate()
    # torrent = db.torrent.search_by_url(url)
    # if torrent:
    #     print(type(torrent))
    # else:
    #     print("未找到种子")
