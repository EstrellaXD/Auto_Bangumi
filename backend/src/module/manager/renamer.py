import asyncio
import logging
import re

from module.conf import settings
from module.database import Database
from module.downloader import DownloadClient
from module.downloader.path import TorrentPath
from module.models import EpisodeFile, Notification, SubtitleFile
from module.models.torrent import RenamerInfo
from module.notification import PostNotification
from module.parser import TitleParser
from module.utils.bangumi_data import get_hash

logger = logging.getLogger(__name__)


def torrent_to_bangumi(id):
    if id:
        with Database() as database:
            torrent_bangumi = database.bangumi.search_id(id)
            return torrent_bangumi


class Renamer:
    def __init__(self):
        self._path_parser = TorrentPath()
        self._parser = TitleParser()
        self._check_pool = {}
        self.count = 0

    @staticmethod
    def print_result(torrent_count, rename_count):
        if rename_count != 0:
            logger.info(
                f"Finished checking {torrent_count} files' name, renamed {rename_count} files."
            )
        logger.debug(f"Checked {torrent_count} files")

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
        return method_dict.get(method, method_dict.get("none"))

    async def rename_file(
        self,
        renamer_info: RenamerInfo,
        file: str,
        method: str,
        bangumi_name: str,
        client: DownloadClient,
    ):
        logger.debug(f"[Renamer] Start rename {renamer_info.torrent.name}.")
        # 对路径和filename简单的提取出season,title
        # 主要还是拿到集数,其他的并不重要,advance用不到
        if "sub" not in method:
            ep = self._parser.torrent_parser(renamer_info.save_path, file)
        else:
            ep = self._parser.torrent_parser(
                renamer_info.save_path, file, file_type="subtitle"
            )
        if ep and renamer_info.bangumi and renamer_info.bangumi.offset:
            # logging.info(f"[debug] {ep.episode=} {renamer_info.bangumi.offset}")
            ep.episode += renamer_info.bangumi.offset


        bangumi_name = bangumi_name

        new_path = self.gen_path(ep, bangumi_name, method)
        old_path = file

        result = await client.rename_torrent_file(renamer_info.hash, old_path, new_path)

        logger.debug(f"[Renamer] {ep=} ")
        post_path = None
        if renamer_info.bangumi and renamer_info.bangumi.poster_link:
            post_path = renamer_info.bangumi.poster_link
        if ep and renamer_info.torrent.id:
            notification_info = Notification(
                title=bangumi_name,
                season=ep.season,
                episode=ep.episode,
                poster_path=post_path,
            )
            asyncio.create_task(PostNotification().send(notify=notification_info))
        self.count += 1
        # logger.info(f"[Renamer] {old_path} -> {new_path}")
        return result

    async def rename_files(
        self,
        renamer_info: RenamerInfo,
        media_list: list[str],
        method: str,
        bangumi_name: str,
        client: DownloadClient,
    ):

        logger.debug(f"[Renamer] Start rename {renamer_info.torrent.name}.")
        tasks = []
        for file in media_list:
            task = self.rename_file(renamer_info, file, method, bangumi_name, client)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.warning(f"[Renamer] {media_list[i]} rename failed")
                return result
            else:
                # 处理成功的结果
                logger.debug(f"[Renamer] Task {media_list[i]} returned: {result}")
                logger.debug(f"[Renamer] {media_list[i]} rename succeed")
        # TODO: remove bad torrent
        return renamer_info.torrent

    async def gen_renamer_info(
        self,
        client: DownloadClient,
        torrent_hash: str,
        bangumi,
        torrent_item,
        save_path,
    ):
        torrent_contents: list[str] = await client.get_torrent_files(torrent_hash)
        if torrent_contents:
            # 获取最浅一层的文件,若一层无文件才会到下一层,并只会穿一层
            torrent_content_len = [
                self._path_parser._file_depth(f) for f in torrent_contents
            ]
            torrent_contents = [
                f
                for f, f_len in zip(torrent_contents, torrent_content_len)
                if f_len == min(torrent_content_len)
            ]

        return RenamerInfo(
            torrent=torrent_item,
            bangumi=bangumi,
            hash=torrent_hash,
            save_path=save_path,
            content=torrent_contents,
        )

    async def rename_by_info(self, client, renamer_info: RenamerInfo):
        rename_method = settings.bangumi_manage.rename_method

        # 从save_path和settings.download.path 对比拿到 bangumi_name,season
        bangumi_name, _ = self._path_parser.path_to_bangumi(renamer_info.save_path)
        media_list, subtitle_list = self._path_parser.check_files(renamer_info.content)
        torrent_item = await self.rename_files(
            renamer_info,
            media_list,
            rename_method,
            bangumi_name,
            client,
        )
        await self.rename_files(
            renamer_info,
            subtitle_list,
            f"subtitle_{rename_method}",
            bangumi_name,
            client,
        )
        if not isinstance(torrent_item, BaseException) and torrent_item and torrent_item.id:
            with Database() as db:
                torrent_item = db.torrent.search(torrent_item.id)
                torrent_item.downloaded = True
                db.torrent.update(torrent_item)

    async def rename(self):
        """
        每个 RenamerInfo 对应一个种子,包含种子,对应的bangumi, save_path,hash,content
        """
        # 从数据库中获取downloaded=0的种子,也就不在管理非AB下载的种子
        # 与其管理非AB下载的种子,不如AB提供下载的方法
        # 现有的管理效果也并不好,所以放弃
        logger.debug("[Renamer] Start rename process.")
        async with DownloadClient() as client:
            # 获取AB 下载的种子详细信息,主要是获取下载进度和save_path
            bangumi_torrent_infos: list[dict] = await client.get_torrent_info(limit=50)
            with Database() as database:
                torrent_items = database.torrent.search_all_unrenamed()
                hash_list = [get_hash(link_hash.url) for link_hash in torrent_items]
                name_list = [torrent_item.name for torrent_item in torrent_items]

            renamer_info_list: list[RenamerInfo] = []

            for bangumi_torrent_info in bangumi_torrent_infos:
                torrent_hash = bangumi_torrent_info["hash"]
                torrent_name = bangumi_torrent_info["name"]
                # 部份torrent 的hash与mikan不一致
                if torrent_hash in hash_list: 
                    torrent_idx = hash_list.index(torrent_hash)
                elif torrent_name in name_list:
                    torrent_idx = name_list.index(torrent_name)
                else:
                    continue
                torrent_item = torrent_items[torrent_idx]
                bangumi = torrent_to_bangumi(torrent_item.bangumi_id)

                renamer_info = await self.gen_renamer_info(
                    client,
                    torrent_hash,
                    bangumi,
                    torrent_item,
                    save_path=bangumi_torrent_info["save_path"],
                )

                renamer_info_list.append(renamer_info)

            renamer_task = []
            for renamer_info in renamer_info_list:
                # 从save_path和settings.download.path 对比拿到 bangumi_name,season
                renamer_task.append(self.rename_by_info(client,renamer_info))
            torrents = await asyncio.gather(*renamer_task, return_exceptions=True)
            logging.info(f"[Renamer] have renamed {self.count}")

    async def compare_ep_version(
        self, torrent_name: str, torrent_hash: str, client: DownloadClient
    ):
        if re.search(r"v\d.", torrent_name):
            pass
        else:
            await client.delete_torrent(hashes=torrent_hash)


if __name__ == "__main__":

    from module.conf import setup_logger

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    settings.log.debug_enable = True
    setup_logger()
    asyncio.run(Renamer().rename())
