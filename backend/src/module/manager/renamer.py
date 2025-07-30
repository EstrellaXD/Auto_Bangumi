import asyncio

import logging

from module.conf import settings
from module.database import Database
from module.downloader import Client as download_client
from module.models import EpisodeFile, Notification, SubtitleFile
from module.models.bangumi import Bangumi
from module.models.torrent import Torrent
from module.notification import PostNotification
from module.parser import TitleParser, TmdbParser
from module.parser.analyser.raw_parser import is_point_5, is_v1
from module.utils import check_file, path_to_bangumi

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
        self._parser = TitleParser()
        self._check_pool = {}
        self.count = 0
        self.notify_dict = {}
        self.bangumi_cache = {}
        self.tmdb_parser = TmdbParser()

    async def send_notification(self):
        """
        发送通知
        """
        for notify_info in self.notify_dict.values():
            await PostNotification().send(notify_info)

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
        new_path: str = method_dict.get(method, method_dict.get("none", ""))
        logger.debug(f"[Renamer][gen_path] {new_path=}")
        return new_path

    async def rename_file(
        self,
        hash: str,
        file_path: str,
        save_path: str,
        bangumi: Bangumi | None = None,
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
        file_type = check_file(file_path)
        if not file_type:
            logger.debug(f"[Renamer] {file_path} is not a media or subtitle")
            return False

        logger.debug(f"[Renamer][rename_file] Start rename {hash}.")

        rename_method = settings.bangumi_manage.rename_method
        method = (
            rename_method if file_type == "media" else "subtitle_" + rename_method
        )

        # 主要是找集数, 当 season 是 0 时, 会从 file_path 中提取
        # torrent_parser 会对 file_path 进行处理, 所以不用担心太长的问题
        ep = self._parser.torrent_parser(file_path)
        if not ep:
            logger.debug(f"[Renamer][rename_file] {file_path} is not a valid file")
            return False

        #TODO: 后面支持剧场版的时个这要 改一下
        if ep and ep.episode == 0:
            logger.debug(f"[Renamer][rename_file] {ep.title} is parser episode failed")
            return True

        # .5 的也处理不了, 直接返回 True
        if is_point_5(ep.title):
            logger.debug(f"[Renamer][rename_file] {ep.title} is a point 5 file")
            # Notify = Notification()
            return True

        # v1 的没必要处理, 直接返回 True
        if is_v1(ep.title):
            logger.debug(f"[Renamer][rename_file] {ep.title} is a vd file")
            return True

        if bangumi is None:
            # 从save_path中提取番剧名称和season
            bangumi_name, season = path_to_bangumi(save_path, settings.downloader.path)


            if season == 0:
                # 奇奇怪怪的路径, 不处理
                logger.warning(f"[Renamer][rename_file] {save_path} is not a bangumi path")
                return False
        else:
            bangumi_name = bangumi.official_title
            season = bangumi.season
            # 番剧偏移
            ep.episode += bangumi.offset if bangumi else 0

        ep.season = season

        file_type = "media" if "sub" not in method else "subtitle"
        # 当 episode 是 0 时, 不处理
        new_path = self.gen_path(ep, bangumi_name, method)
        old_path = file_path
        if new_path == old_path:
            logger.debug(f"[Renamer][rename_file] {old_path=} == {new_path=}")
            logging.debug(f"[Renamer][rename_file] have renamed {old_path}")
            return True

        logger.debug(f"[Renamer][rename_file] {old_path=} ->{new_path=}")
        result = await download_client.rename_torrent_file(hash, old_path, new_path)
        logger.debug(f"[Renamer] {ep=} ")
        return result

    async def rename_files(
        self,
        files_path: list[str],
        torrent: Torrent,
        bangumi: Bangumi | None = None,
    ) -> bool:
        """
        处理 一个种子, 多个文件的重命名
        """
        tasks = []
        hash = torrent.download_guid
        if not hash:
            logger.warning(f"[Renamer] {torrent.name} has no download guid, skip")
            return False
        save_path = torrent.save_path
        for file in files_path:
            task = self.rename_file(hash, file, save_path, bangumi)
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

    async def rename_torrent(self, torrent: Torrent, bangumi: Bangumi):
        # 要torrent 的 save_path,download_guid,name
        files = []
        if not torrent.download_guid:
            logger.debug(f"[Renamer] {torrent.name} has no download guid, skip")
            return
        files = await download_client.get_torrent_files(torrent.download_guid)
        if not files:
            logger.debug(f"[Renamer] {torrent.name} has no files, skip")
            return
        result = await self.rename_files(files, torrent, bangumi)
        logger.debug(f"[Renamer] {torrent.name} rename result: {result}")

        if result:
            logger.debug(f"[Renamer] {torrent.name} rename succeed")
            with Database() as db:
                torrent.renamed = True
                torrent.save_path = bangumi.save_path  # 更新保存路径
                torrent.downloaded = True
                db.torrent.add(torrent)





if __name__ == "__main__":

    from module.conf import setup_logger

    setup_logger("DEBUG", reset=True)

    torrent = Torrent()
    bangumi = Bangumi()
    asyncio.run(Renamer().rename_torrent())
