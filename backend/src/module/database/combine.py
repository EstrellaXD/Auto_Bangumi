from sqlmodel import Session, SQLModel, text

from module.models import Bangumi, User
from module.models.rss import RSSItem
from module.models.torrent import Torrent

from .bangumi import BangumiDatabase
from .engine import engine as e
from .rss import RSSDatabase
from .torrent import TorrentDatabase
from .user import UserDatabase


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

    def _migrate_table_data(self, table_name: str, model_class, existing_data: list):
        """通用的表数据迁移方法"""
        if not existing_data:
            return []

        # 获取当前表的列名
        existing_columns = self._get_table_columns(table_name)

        # 获取新模型的字段名
        model_fields = set(model_class.__fields__.keys())

        # 找出共同的字段
        common_fields = set(existing_columns) & model_fields

        migrated_data = []
        for item in existing_data:
            if hasattr(item, "model_dump"):
                # 如果是 SQLModel 对象
                item_dict = item.model_dump()
            else:
                # 如果是原始行数据，转换为字典
                item_dict = {
                    existing_columns[i]: item[i] for i in range(len(existing_columns))
                }

            # 只保留共同字段，为新字段设置默认值
            migrated_dict = {}
            for field_name in model_fields:
                if field_name == "id":
                    continue  # 跳过主键，让数据库自动生成
                elif field_name in common_fields:
                    migrated_dict[field_name] = item_dict.get(field_name)
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

            try:
                migrated_data.append(model_class(**migrated_dict))
            except Exception as e:
                print(f"Error migrating {table_name} record: {e}")
                continue

        return migrated_data

    def migrate(self):
        """自动识别和迁移数据库结构"""
        print("开始数据库迁移...")

        # 获取现有数据
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

                # 尝试用模型查询
                if table_name == "bangumi":
                    raw_data = self.bangumi.search_all()
                elif table_name == "torrent":
                    raw_data = self.torrent.search_all()
                elif table_name == "rssitem":
                    raw_data = self.rss.search_all()
                elif table_name == "user":
                    raw_data = self.exec(text(f"SELECT * FROM {table_name}")).all()

                tables_data[table_name] = raw_data
                print(f"成功获取 {table_name} 表数据: {len(raw_data)} 条记录")

            except Exception as e:
                print(f"获取 {table_name} 表数据失败，使用原始SQL查询: {e}")
                try:
                    raw_data = self.exec(text(f"SELECT * FROM {table_name}")).all()
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
        for table_name in ["bangumi", "torrent", "rssitem"]:
            data = migrated_data[table_name]
            if data:
                if table_name == "bangumi":
                    self.bangumi.add_all(data)
                elif table_name == "torrent":
                    self.torrent.add_all(data)
                elif table_name == "rssitem":
                    self.rss.add_all(data)
                print(f"插入 {table_name} 数据: {len(data)} 条记录")

        # 处理 user 数据
        if user_data:
            if hasattr(user_data[0], "__len__") and len(user_data[0]) >= 3:
                # 原始行数据
                user_row = user_data[0]
                user_dict = {"username": user_row[1], "password": user_row[2]}
                self.add(User(**user_dict))
                print("插入 user 数据: 1 条记录")

        self.commit()
        print("数据库迁移完成!")
