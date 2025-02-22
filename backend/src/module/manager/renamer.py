import asyncio
import logging
import re

from module.conf import settings
from module.database import Database
from module.downloader import Client as download_client
from module.downloader.path import TorrentPath
from module.models import EpisodeFile, Notification, SubtitleFile
from module.models.bangumi import Bangumi
from module.models.rss import RSSItem
from module.models.torrent import Torrent
from module.notification import PostNotification
from module.parser import TitleParser, TmdbParser
from module.parser.analyser.raw_parser import is_point_5, is_vd
from module.rss import RSSAnalyser

logger = logging.getLogger(__name__)


class Renamer:
    """
    重命名模块
    renamer 有俩个地方用,一个是日常的循环,一个是 bangumi 更新后
    1. 日常循环中, 需要对下载的种子进行重命名, 重命名后需要更新 database
    2. bangumi 更新后, 需要对 bangumi 关联的种子进行重命名, 无需更新 database
    命名要的数据
    1. hash 这是唯一标识
    2. 文件名,这是声名要改的文件
    3. save_path 这是最终路径
    4. content 这是文件列表
    rename的步骤
    1. 从 download 获取种子的文件列表, 包含 种子的 hash, 文件名, 保存路径,会默认取前100个
    2. 从数据库中判断是否已经重命名 , 将所有未重命名的种子文件列表传入
    3. 从 save_path 中提取番剧名称和 season, 对于不是标准路径, 会进行一次tmdb解析
    4. 去bangumi中找到对应的番剧, 用于 poster 和 offset
    5. 对种子名进行解析, 提取 集数
    6. 重命名文件, 重命名成功后, 发送通知
    """

    def __init__(self):
        self._path_parser = TorrentPath()
        self._parser = TitleParser()
        self._check_pool = {}
        self.count = 0
        self.notify_dict = {}
        self.bangumi_cache = {}

    async def send_notification(self):
        """
        发送通知
        """
        for notify_info in self.notify_dict.values():
            await PostNotification().send(notify_info)

    @staticmethod
    async def get_torrent_files(
        torrent_hash: str,
    ) -> list[str]:
        """
        update 的时候会用这个
        获取种子文件列表
        文件夹举例
        LKSUB][Make Heroine ga Oosugiru!][01-12][720P]/[LKSUB][Make Heroine ga Oosugiru!][01][720P].mp4
        """
        async with download_client as client:
            torrent_contents: list[str] = await client.get_torrent_files(torrent_hash)
        return torrent_contents

    @staticmethod
    def gen_path(
        file_info: EpisodeFile | SubtitleFile, bangumi_name: str, method: str
    ) -> str:
        season = f"{file_info.season:02d}"
        episode = f"{file_info.episode:02d}"
        method_dict = {
            "none": f"{file_info.media_path}",
            "subtitle_none": file_info.media_path,
            "pn": f"{file_info.title} S{season}E{episode}{file_info.suffix}",
            "advance": f"{bangumi_name} S{season}E{episode}{file_info.suffix}",
            "normal": file_info.media_path,
        }
        if isinstance(file_info, SubtitleFile):
            method_dict = {
                "subtitle_pn": f"{file_info.title} S{season}E{episode}.{file_info.language}{file_info.suffix}",
                "subtitle_advance": f"{bangumi_name} S{season}E{episode}.{file_info.language}{file_info.suffix}",
            }
        if method == "normal":
            logger.warning("[Renamer] Normal rename method is deprecated.")
        new_path = method_dict.get(method, method_dict.get("none"))
        logger.debug(f"[Renamer][gen_path] {new_path=}")
        return new_path

    async def rename_file(
        self,
        hash: str,
        file_path: str,
        save_path: str,
        bangumi: Bangumi | None = None,
        method: str | None = None,
    ):
        """
        重命名文件
        当是 update 导致的更新时,有 无torrent,无需更新
        当有 hash, file_path, save_path 时, 足够重命名
        bangumi 主要是用于 poster 和 offset
        对于.5 文件, 感觉还是不要重命名了, 直接发送一个通知
        Args:
            hash (str): 种子hash
            file_path (str): 文件路径
            save_path (str): 保存路径 与 file path 相比,是 file path 更长
            method (str): 重命名方法
            bangumi_name (str): 番剧名称
            torrent (Torrent | None, optional): 种子. Defaults to None.
            bangumi (Bangumi | None, optional): 番剧. Defaults to None.
        Returns:
            bool: 重命名是否成功
        """
        # 检查文件类型
        # 当文件类型不是 media 或 subtitle 时, 返回 False
        file_type = self._path_parser.check_file(file_path)
        if not file_type:
            logger.debug(f"[Renamer] {file_path} is not a media or subtitle")
            return True

        logger.debug(f"[Renamer][rename_file] Start rename {hash}.")

        rename_method = settings.bangumi_manage.rename_method
        if method is None:
            method = (
                rename_method if file_type == "media" else "subtitle_" + rename_method
            )
        # 从save_path中提取番剧名称和season
        bangumi_name, season = self._path_parser.path_to_bangumi(save_path)

        if season == 0:
            # 奇奇怪怪的路径, 不处理
            logger.warning(f"[Renamer][rename_file] {save_path} is not a bangumi path")
            return True

        file_type = "media" if "sub" not in method else "subtitle"
        # 主要是找集数, 当 season 是 0 时, 会从 file_path 中提取
        # torrent_parser 会对 file_path 进行处理, 所以不用担心太长的问题
        ep = self._parser.torrent_parser(
            file_path,
            file_type=file_type,
        )
        ep.season = season
        # 番剧偏移
        ep.episode += bangumi.offset if bangumi else 0
        # TODO: 对.5 文件进行处理
        new_path = self.gen_path(ep, bangumi_name, method)
        old_path = file_path
        if new_path == old_path:
            logger.debug(f"[Renamer][rename_file] {old_path=} == {new_path=}")
            logging.debug(f"[Renamer][rename_file] have renamed {old_path}")
            return True

        logger.debug(f"[Renamer][rename_file] {old_path=} ->{new_path=}")
        async with download_client as client:
            result = await client.rename_torrent_file(hash, old_path, new_path)
        logger.debug(f"[Renamer] {ep=} ")
        # 以下为通知用
        if result:
            notify_info = self.notify_dict.get(bangumi_name, None)
            # 当有相同的动漫时, 将集数进行累加
            if notify_info:
                notify_info.episode += "," + str(ep.episode)
            else:
                notify_info = Notification(
                    title=bangumi_name,
                    season=ep.season,
                    episode=str(ep.episode),
                    poster_path=bangumi.poster_link if bangumi else None,
                )
            self.notify_dict[bangumi_name] = notify_info

            self.count += 1
        return result

    async def rename_files(
        self,
        hash: str,
        files_path: list[str],
        save_path: str,
        bangumi: Bangumi | None = None,
        method: str | None = None,
    ) -> bool:
        """
        处理 一个种子, 多个文件的重命名
        """
        tasks = []
        for file in files_path:
            task = self.rename_file(hash, file, save_path, bangumi, method)
            logger.debug(f"[Renamer] rename_files {file} rename task added")
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results):
            if result:
                # 处理成功的结果
                logger.debug(f"[Renamer] Task {files_path[i]} returned: {result}")
                logger.debug(f"[Renamer] {files_path[i]} rename succeed")
                return result
            else:
                logger.warning(f"[Renamer] {files_path[i]} rename failed")
        return False

    async def rename_by_info(
        self,
        hash: str,
        files_path: list[str],
        save_path: str,
        torrent: Torrent,
        bangumi: Bangumi | None = None,
    ):
        # 这里的 torrent 不允许为 None, 困为这个要更新
        result = await self.rename_files(hash, files_path, save_path, bangumi)
        logger.debug(f"[Renamer] {torrent.name} rename result: {result}")
        if result and torrent.id:
            logger.debug(f"[Renamer] {torrent.name} rename succeed")
            with Database() as db:
                torrent_item = db.torrent.search(torrent.id)
                torrent_item.downloaded = True
                db.torrent.update(torrent_item)

    async def rename(self):
        """ """
        logger.debug("[Renamer] Start rename process.")
        async with download_client as client:
            # 获取AB 下载的种子详细信息,主要是获取 save_path
            # save_path 以 download 查询的为准
            bangumi_torrent_infos: list[dict] = await client.get_torrent_info(limit=100)
        renamer_info_list: list[tuple[Torrent, Bangumi, list[str]]] = []

        for bangumi_torrent_info in bangumi_torrent_infos:
            torrent_hash = bangumi_torrent_info["hash"]
            torrent_name = bangumi_torrent_info["name"]
            with Database() as database:
                if not (torrent_item := database.torrent.search_torrent(torrent_hash)):
                    # 如果没有在数据库中,则添加
                    torrent_item = Torrent(name=torrent_name, url=torrent_hash)
                    database.torrent.add(torrent_item)
                if not torrent_item.downloaded:
                    # 找 Bangumi , 主要用 offset 和 poster_link
                    bangumi = None
                    bangumi_name, season = self._path_parser.path_to_bangumi(
                        bangumi_torrent_info["save_path"]
                    )
                    if torrent_item.bangumi_id:
                        bangumi = database.bangumi.search_id(torrent_item.bangumi_id)
                        # torrent_item.bangumi_id 不可靠
                        if bangumi and bangumi.official_title != bangumi_name:
                            logger.debug(
                                f"[Renamer] {torrent_name} bangumi_id is {torrent_item.bangumi_id}, but official_title is {bangumi_name}"
                            )
                            bangumi = database.bangumi.search_official_title(
                                bangumi_name
                            )
                    if not bangumi:
                        # TODO: 这个的请求还是太多了, 需要优化
                        if season != 0:
                            # 是一个 AB 下载的,如 collect,或其他原因没有记录的
                            logger.debug(
                                f"[Renamer] start rename collection {bangumi_name}"
                            )
                            # 抓一个 poster
                            bangumi = Bangumi(
                                official_title=bangumi_name,
                            )
                            if self.bangumi_cache.get(bangumi_name):
                                bangumi = self.bangumi_cache[bangumi_name]
                            else:
                                if await TmdbParser().poster_parser(bangumi):
                                    self.bangumi_cache[bangumi_name] = bangumi
                        else:
                            # 不是AB 下载的,但是想要重命名
                            logger.debug(
                                f"[Renamer] start rename {torrent_name} not downloaded by AutoBangumi"
                            )
                            if self.bangumi_cache.get(torrent_name):
                                bangumi = self.bangumi_cache[torrent_name]
                            else:
                                bangumi = await RSSAnalyser().torrent_to_data(
                                    torrent=Torrent(name=torrent_name),
                                    rss=RSSItem(parser="tmdb"),
                                )
                                self.bangumi_cache[torrent_name] = bangumi

                            save_path = self._path_parser.gen_save_path(bangumi)
                            async with download_client as client:
                                await client.move_torrent(
                                    hashes=torrent_hash,
                                    location=save_path,
                                )
                                logger.debug(
                                    [
                                        f"[Renamer][rename] {torrent_name} moved to {save_path}"
                                    ]
                                )
                            bangumi_torrent_info["save_path"] = save_path

                    # 拿到种子对应的文件列表

                    async with download_client as client:
                        torrent_contents: list[str] = await client.get_torrent_files(
                            torrent_hash
                        )
                    renamer_info_list.append(
                        (
                            torrent_hash,
                            torrent_contents,
                            bangumi_torrent_info["save_path"],
                            torrent_item,
                            bangumi,
                        )
                    )

        renamer_task = []
        for renamer_info in renamer_info_list:
            renamer_task.append(self.rename_by_info(*renamer_info))
        logging.debug("[Renamer] Start rename task.")
        await asyncio.gather(*renamer_task)
        await self.send_notification()
        if self.count:
            logging.info(f"[Renamer] have renamed {self.count}")
        else:
            logging.debug("[Renamer] No files need to be renamed.")


if __name__ == "__main__":

    from module.conf import setup_logger

    setup_logger("DEBUG", reset=True)

    asyncio.run(Renamer().rename())
