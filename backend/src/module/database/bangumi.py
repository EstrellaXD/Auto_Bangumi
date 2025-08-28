import logging

from sqlmodel import Session, and_, delete, false, or_, select

from module.models import Bangumi

logger = logging.getLogger(__name__)


class BangumiDatabase:
    """
    TODO: 对 Bangumi 的一些新想法
    主键为 official_title, link, 季度
    判断一个 torrent name 是不是在 bangumi 里面
    先通过 name, link 来找一下, 然后看看季度有没有
    有一点问题是 现在有了一个 bangumi, 但是季度是改过的(如物语系列)
    当有俩个的时候, 一个已经加进去了, 另外一个没有,
    这时候会去解析, 由于季度不一样, 会被认为是多个 bangumi
    所以默认同一个 link 内的季度是一样的

    #FIXME :
    这就有了新问题, 在一个动漫连续多个季度的时候, 会被认为是同一个动漫
    一个暂时的解决方案是, 通过 season_raw 来判断, 如果当前存在一个季度更大的, 就不添加
    #ERROR : 这就会导致一个sb 的动漫是 S2 但是 TMDB 分到了 S1, 导致多加一个
    有大选大, 没有大再看看 mikan/tmdb 给的是什么
    """

    def __init__(self, session: Session):
        self.session:Session = session

    def add(self, data: Bangumi):
        """link 相同, official_title相同,就只补充,主要是为了
        一些会改名的
        """
        statement = select(Bangumi).where(
            data.official_title == Bangumi.official_title,
            data.rss_link == Bangumi.rss_link,
        )
        bangumi = self.session.exec(statement).first()
        if bangumi:
            if data.title_raw in bangumi.title_raw:
                logger.debug(f"[Database] {data.official_title} | {data.title_raw} has inserted into database.")
                return False
            bangumi.title_raw += f",{data.title_raw}"
            # TODO: 如果official_title 一致,将title_raw,group,更新
            if bangumi.group_name and data.group_name and data.group_name not in bangumi.group_name:
                bangumi.group_name += f"&{data.group_name}"
            data = bangumi

        self.session.add(data)
        self.session.commit()
        self.session.refresh(data)
        return True

    def update(self, data: Bangumi) -> bool:
        self.session.merge(data)
        self.session.commit()
        self.session.refresh(data)
        # logger.debug(f"[Database] Update {data.official_title}")
        return True

    def update_all(self, datas: list[Bangumi]) -> None:
        # 目前只在 refresh poster 的时候用到, 后面要用的话要注意会 detach
        self.session.add_all(datas)
        self.session.commit()
        # logger.debug(f"[Database] Update {len(datas)} bangumi.")

    def delete_one(self, _id: int):
        bangumi = self.session.get(Bangumi, _id)
        self.session.delete(bangumi)
        self.session.commit()
        # logger.debug(f"[Database] Delete bangumi id: {_id}.")

    def delete_all(self):
        # https://github.com/fastapi/sqlmodel/issues/909
        statement = delete(Bangumi)
        self.session.execute(statement)  # type: ignore
        self.session.commit()

    def search(self, title: str, season: int, rss_link: str) -> Bangumi | None:
        """
        根据官方标题、季节和 RSS 链接查找 Bangumi
        :param title: 官方标题
        :param season: 季节
        :param rss_link: RSS 链接
        :return: Bangumi 对象或 None
        """
        statement = select(Bangumi).where(
            and_(
                Bangumi.official_title == title,
                Bangumi.season == season,
                Bangumi.rss_link == rss_link,
            )
        )
        return self.session.exec(statement).first()

    def search_all(self) -> list[Bangumi]:
        statement = select(Bangumi)
        return list(self.session.exec(statement).all())

    def search_id(self, _id: int) -> Bangumi | None:
        bangumi = self.session.get(Bangumi, _id)
        if bangumi is None:
            return None
        return bangumi

    def search_official_title(self, official_title: str) -> Bangumi | None:
        statement = select(Bangumi).where(Bangumi.official_title == official_title)
        bangumi = self.session.exec(statement).first()
        if bangumi is None:
            return None
        return self.session.exec(statement).first()

    def not_complete(self) -> list[Bangumi]:
        # Find eps_complete = False
        # use `false()` to avoid E712 checking
        # see: https://docs.astral.sh/ruff/rules/true-false-comparison/
        condition = select(Bangumi).where(Bangumi.eps_collect == false(), Bangumi.deleted == false())
        datas = list(self.session.exec(condition).all())
        return datas
