from sqlmodel import Session, SQLModel, and_, delete, false, or_, select, text

from module.database.bangumi import BangumiDatabase
from module.database.engine import engine as e
from module.database.rss import RSSDatabase
from module.database.torrent import TorrentDatabase
from module.database.user import UserDatabase
from module.database.database_version import VersionDatabase
from module.models import Bangumi, User
from module.models import RSSItem
from module.models import Torrent
import logging

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
        self.databaseversion: VersionDatabase = VersionDatabase(self)

    def bangumi_to_rss(self, bangumi: Bangumi) -> RSSItem | None:
        return self.rss.search_url(bangumi.rss_link)

    def add_bangumi(self, bangumi: Bangumi):
        pass

    def torrent_to_bangumi(self, torrent: Torrent) -> Bangumi | None:
        """根据 Torrent 查找相关的 Bangumi"""
        "依据 official_title, seasion, rss_link"
        return self.bangumi.search(
            torrent.bangumi_official_title, torrent.bangumi_season, torrent.rss_link
        )

    def find_torrent_by_bangumi(self, bangumi: Bangumi) -> list[Torrent]:
        """根据 Bangumi 查找相关的 Torrent"""
        "依据 official_title, seasion, rss_link"
        return self.torrent.filter_by_bangumi(
            bangumi.official_title, bangumi.season, bangumi.rss_link
        )

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

    def find_bangumi_by_name(
        self, name: str, rss_link: str, aggrated: bool
    ) -> Bangumi | None:
        # 现在是一个更新过的种子, 各种原因要查找 bangumi
        # 对于聚合而言, link, title_raw一致可认为是一个bangumi
        # 对于非聚合, link 一致就可认为是一个
        # 对于一个种子要找 bangumi, 主要是在 刷新 rss 的时候,
        if aggrated:
            logger.debug(f"[Database Combine] 查找聚合 Bangumi: {name}, {rss_link}")
            statement = select(Bangumi).where(Bangumi.title_raw.contains(name))
            bangumi = self.exec(
                statement
                # select(Bangumi).where(Bangumi.deleted == false())
            ).first()
            logger.debug(f"[Database Combine] 找到聚合 Bangumi: {bangumi.official_title if bangumi else 'None'}")
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

    def _migrate_table_data(self, table_name: str, model_class, existing_data: list):
        """通用的表数据迁移方法"""
        if not existing_data:
            return []

        migrated_data = []

        # 获取新模型的字段名
        model_fields = set(model_class.__fields__.keys())

        for item in existing_data:
            try:
                # 如果已经是字典格式
                if isinstance(item, dict):
                    item_dict = item
                elif hasattr(item, "model_dump"):
                    # 如果是 SQLModel 对象
                    item_dict = item.model_dump()
                elif hasattr(item, "_mapping"):
                    # 如果是数据库行对象
                    item_dict = dict(item._mapping)
                else:
                    # 如果是原始行数据，需要先获取列名
                    existing_columns = self._get_table_columns(table_name)
                    item_dict = {
                        existing_columns[i]: item[i]
                        for i in range(min(len(existing_columns), len(item)))
                    }

                # 只保留模型中存在的字段，为新字段设置默认值
                migrated_dict = {}
                for field_name in model_fields:
                    if field_name == "id":
                        # 保留原有ID，如果没有则让数据库自动生成
                        if (
                            field_name in item_dict
                            and item_dict[field_name] is not None
                        ):
                            migrated_dict[field_name] = item_dict[field_name]
                        continue
                    elif field_name in item_dict:
                        migrated_dict[field_name] = item_dict[field_name]
                    else:
                        # 为新字段设置默认值
                        field_info = model_class.__fields__[field_name]
                        if (
                            hasattr(field_info, "default")
                            and field_info.default is not None
                        ):
                            migrated_dict[field_name] = field_info.default
                        else:
                            # 根据类型设置默认值
                            field_type = field_info.annotation
                            if field_type == str or field_type == str | None:
                                migrated_dict[field_name] = (
                                    "" if "str | None" not in str(field_type) else None
                                )
                            elif field_type == bool:
                                migrated_dict[field_name] = False
                            elif field_type == int or field_type == int | None:
                                migrated_dict[field_name] = (
                                    0 if "int | None" not in str(field_type) else None
                                )
                            else:
                                migrated_dict[field_name] = None

                migrated_data.append(model_class(**migrated_dict))
            except Exception as e:
                print(f"Error migrating {table_name} record: {e}")
                print(f"Problematic data: {item}")
                continue

        return migrated_data

    def migrate(self):
        """自动识别和迁移数据库结构"""
        print("开始数据库迁移...")

        # 获取现有数据并立即转换为字典，避免对象引用问题
        tables_data = {}

        # 尝试获取各表数据
        for table_name, model_class in [
            ("bangumi", Bangumi),
            ("torrent", Torrent),
            ("rssitem", RSSItem),
            ("user", User),
        ]:
            try:
                # 检查表是否存在
                table_exists = self.exec(
                    text(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                    )
                ).first()
                if not table_exists:
                    print(f"表 {table_name} 不存在，跳过")
                    tables_data[table_name] = []
                    continue

                # 尝试用模型查询并立即转换为字典
                raw_data = []
                if table_name == "bangumi":
                    orm_data = self.bangumi.search_all()
                    raw_data = [
                        item.model_dump() if hasattr(item, "model_dump") else item
                        for item in orm_data
                    ]
                elif table_name == "torrent":
                    orm_data = self.torrent.search_all()
                    raw_data = [
                        item.model_dump() if hasattr(item, "model_dump") else item
                        for item in orm_data
                    ]
                elif table_name == "rssitem":
                    orm_data = self.rss.search_all()
                    raw_data = [
                        item.model_dump() if hasattr(item, "model_dump") else item
                        for item in orm_data
                    ]
                elif table_name == "user":
                    orm_data = self.exec(text(f"SELECT * FROM {table_name}")).all()
                    raw_data = [
                        dict(row._mapping) if hasattr(row, "_mapping") else row
                        for row in orm_data
                    ]

                tables_data[table_name] = raw_data
                print(f"成功获取 {table_name} 表数据: {len(raw_data)} 条记录")

            except Exception as e:
                print(f"获取 {table_name} 表数据失败，使用原始SQL查询: {e}")
                try:
                    orm_data = self.exec(text(f"SELECT * FROM {table_name}")).all()
                    raw_data = [
                        dict(row._mapping) if hasattr(row, "_mapping") else row
                        for row in orm_data
                    ]
                    tables_data[table_name] = raw_data
                    print(
                        f"使用原始SQL获取 {table_name} 表数据: {len(raw_data)} 条记录"
                    )
                except Exception as e2:
                    print(f"完全无法获取 {table_name} 表数据: {e2}")
                    tables_data[table_name] = []

        # 迁移数据
        migrated_data = {}
        for table_name, model_class in [
            ("bangumi", Bangumi),
            ("torrent", Torrent),
            ("rssitem", RSSItem),
        ]:
            migrated_data[table_name] = self._migrate_table_data(
                table_name, model_class, tables_data[table_name]
            )
            print(f"迁移 {table_name} 数据: {len(migrated_data[table_name])} 条记录")

        # 特殊处理 user 表（原始数据）
        user_data = tables_data.get("user", [])

        # 重建表结构
        print("重建表结构...")
        self.drop_table()
        self.create_table()
        self.commit()

        # 重新插入数据
        print("重新插入数据...")
        try:
            for table_name in ["bangumi", "torrent", "rssitem"]:
                data = migrated_data[table_name]
                if data:
                    try:
                        if table_name == "bangumi":
                            for item in data:
                                self.merge(item)
                        elif table_name == "torrent":
                            for item in data:
                                self.merge(item)
                        elif table_name == "rssitem":
                            for item in data:
                                self.merge(item)
                        self.commit()
                        print(f"插入 {table_name} 数据: {len(data)} 条记录")
                    except Exception as e:
                        print(f"插入 {table_name} 数据失败: {e}")
                        self.rollback()
                        continue

            # 处理 user 数据
            if user_data:
                try:
                    for user_item in user_data:
                        if isinstance(user_item, dict):
                            user_dict = user_item
                        elif hasattr(user_item, "__len__") and len(user_item) >= 3:
                            # 原始行数据
                            user_dict = {
                                "username": user_item[1],
                                "password": user_item[2],
                            }
                        else:
                            continue

                        self.merge(User(**user_dict))
                    self.commit()
                    print(f"插入 user 数据: {len(user_data)} 条记录")
                except Exception as e:
                    print(f"插入 user 数据失败: {e}")
                    self.rollback()

            print("数据库迁移完成!")
        except Exception as e:
            print(f"数据迁移过程中发生错误: {e}")
            self.rollback()
            raise


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
