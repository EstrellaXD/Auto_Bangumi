import asyncio
import logging

from module.conf import settings
from module.database import Database
from module.downloader import Client as download_client
from module.models import EpisodeFile, Message, SubtitleFile
from module.models.bangumi import Bangumi
from module.models.torrent import Torrent
from module.parser import TitleParser, TmdbParser
from module.parser.analyser.meta_parser import is_point_5, is_v1
from module.utils import (
    Event,
    EventType,
    check_file,
    event_bus,
    gen_save_path,
    path_to_bangumi,
)
from module.manager.template_renderer import TemplateRenderer

logger = logging.getLogger(__name__)

# 默认命名模板
DEFAULT_MEDIA_TEMPLATE = "{bangumi_name} S{season:02d}E{episode:02d}{suffix}"
DEFAULT_SUBTITLE_TEMPLATE = "{bangumi_name} S{season:02d}E{episode:02d}.{language}{suffix}"


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
        self._parser:TitleParser = TitleParser()
        self.tmdb_parser = TmdbParser()
        self.count:int = 0
        self._event_bus = event_bus


    @staticmethod
    def gen_path(
        file_info: EpisodeFile | SubtitleFile, bangumi_name,method: str
    ) -> str:
        render = TemplateRenderer()
        params = render.get_available_params(file_info,bangumi_name)


        default_method = "${torrent_name}"
        method_dict = {
            "subtitle_none": "${torrent_name}",
            "pn": "${title} S${season}E${episode}${suffix}",
            "advance": "${official_title} S${season}E${episode}${suffix}",
            "custom": "${official_title} S${season}E${episode} - ${group}${suffix}"
        }
        if isinstance(file_info, SubtitleFile):
            method_dict = {
                "subtitle_pn": "${title}.${language}${suffix}",
                "subtitle_advance": "${official_title} S${season}E${episode}.${language}${suffix}",
            }
        if method == "normal":
            logger.warning("[Renamer] Normal rename method is deprecated.")
        templete: str = method_dict.get(method, default_method)
        new_path = render.render_template(templete, params)
        logger.debug(f"[Renamer][gen_path] {new_path=}")
        return new_path

    async def rename_file(
        self,
        download_uid: str,
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

        logger.debug(f"[Renamer][rename_file] Start rename {download_uid}.")

        rename_method = settings.bangumi_manage.rename_method
        method = rename_method if file_type == "media" else "subtitle_" + rename_method

        # 主要是找集数, 当 season 是 0 时, 会从 file_path 中提取
        # torrent_parser 会对 file_path 进行处理, 所以不用担心太长的问题
        ep = self._parser.torrent_parser(file_path)
        if not ep:
            logger.debug(f"[Renamer][rename_file] {file_path} is not a valid file")
            return False

        # TODO: 后面支持剧场版的时个这要 改一下
        if ep and ep.episode == 0:
            logger.debug(f"[Renamer][rename_file] {ep.title} is parser episode failed")
            return True

        # .5 的也处理不了, 直接返回 True
        if is_point_5(ep.media_path):
            logger.debug(f"[Renamer][rename_file] {ep.title} is a point 5 file")
            # Notify = Notification()
            return True

        # v1 的没必要处理, 直接返回 True
        if is_v1(ep.media_path):
            logger.debug(f"[Renamer][rename_file] {ep.title} is a vd file")
            return True

        if bangumi is None:
            # 从save_path中提取番剧名称和season
            logger.debug(f"[Renamer][rename_file] bangumi is None, try to extract from save_path")
            bangumi_name, season = path_to_bangumi(save_path, settings.downloader.path)
            logger.debug(f"[Renamer][rename_file] {bangumi_name=}, {season=}")

            if season == 0:
                # 奇奇怪怪的路径, 不处理
                logger.warning(
                    f"[Renamer][rename_file] {save_path} is not a bangumi path"
                )
                return False
        else:
            bangumi_name = bangumi.official_title
            season = bangumi.season
            # 番剧偏移
            ep.episode += bangumi.offset if bangumi else 0

        ep.season = season

        file_type = "media" if "sub" not in method else "subtitle"
        # 当 episode 是 0 时, 不处理
        logger.debug(f"[Renamer][rename_file] {bangumi_name=}, {season=}, {file_type=}, {method=}")
        new_path = self.gen_path(ep, bangumi_name, method)
        old_path = file_path
        if new_path == old_path:
            logger.debug(f"[Renamer][rename_file] {old_path=} == {new_path=}")
            return True

        logger.debug(f"[Renamer][rename_file] {old_path=} ->{new_path=}")
        result = await download_client.rename_torrent_file(download_uid, old_path, new_path)
        logger.debug(f"[Renamer] {ep=} ")
        if result and file_type == "media":
            # 重命名成功, 发送通知
            notify_info = Message(
                title=bangumi_name,
                season=str(season),
                episode=str(ep.episode),
                poster_path=bangumi.poster_link if bangumi else "",
            )
            await self._publish_notification_request(notify_info)

        return result

    async def _publish_notification_request(self, notify_info: Message) -> None:
        """发布下载开始事件

        Args:
            torrent: 种子信息
            bangumi: 番剧信息
        """
        if not self._event_bus:
            logger.warning("[Download Controller] EventBus 未设置，无法发布事件")
            return

        try:
            event = Event(
                type=EventType.NOTIFICATION_REQUEST,
                data={"notify_info": notify_info},
            )

            asyncio.create_task(self._event_bus.publish(event))
            logger.debug(
                f"[Download Controller] 已发布通知请求事件: {notify_info.title}"
            )

        except Exception as e:
            logger.error(f"[Download Controller] 发布通知请求事件失败: {e}")

    async def rename_files(
        self,
        files_path: list[str],
        torrent: Torrent,
        bangumi: Bangumi,
    ) -> bool:
        """
        处理 一个种子, 多个文件的重命名
        """
        tasks = []
        dwonload_uid = torrent.download_uid
        if not dwonload_uid:
            logger.warning(f"[Renamer] {torrent.name} has no download uid, skip")
            return False
        save_path = gen_save_path(settings.downloader.path, bangumi)
        for file in files_path:
            task = self.rename_file(dwonload_uid, file, save_path, bangumi)
            logger.debug(f"[Renamer] rename_files {file} rename task added")
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results):
            logger.debug(f"[Renamer] Task {files_path[i]} returned: {result}")
            if result:
                # 处理成功的结果
                logger.debug(f"[Renamer] {files_path[i]} rename succeed")
                return result
            else:
                logger.warning(f"[Renamer] {files_path[i]} rename failed")
        return False

    async def rename_torrent(self, torrent: Torrent, bangumi: Bangumi | None = None):
        # 要torrent 的 download_uid,name
        files = []
        if not torrent.download_uid:
            logger.debug(f"[Renamer] {torrent.name} has no download uid, skip")
            return
        if bangumi is None:
            with Database() as db:
                #NOTE: 这里会更新一下 season 和 official_title
                # 可能是因为更新了番剧信息导致的
                bangumi = db.torrent_to_bangumi(torrent)
                if not bangumi:
                    bangumi = Bangumi(
                        official_title=torrent.bangumi_official_title,
                        season=torrent.bangumi_season,
                        rss_link=torrent.rss_link,
                    )
        files = await download_client.get_torrent_files(torrent.download_uid)
        if not files:
            logger.debug(f"[Renamer] {torrent.name} has no files, skip")
            return
        result = await self.rename_files(files, torrent, bangumi)
        logger.debug(f"[Renamer] {torrent.name} rename result: {result}")

        if result:
            logger.debug(f"[Renamer] {torrent.name} rename succeed")
            with Database() as db:
                torrent.renamed = True
                torrent.downloaded = True
                torrent.bangumi_official_title = bangumi.official_title
                torrent.bangumi_season = bangumi.season
                db.torrent.add(torrent)


if __name__ == "__main__":
    from module.conf import setup_logger


    setup_logger(level=logging.DEBUG, reset=True)
    title = "[LoliHouse] 2.5次元的诱惑  - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕].mkv"
    title = "[LoliHouse] 鬼人幻灯抄 / Kijin Gentoushou - 17 (幕末篇)[WebRip 1080p HEVC-10bit AAC][简繁内封字幕].mkv"
    bangumi_name = "鬼人幻灯抄"
    r = Renamer()
    file_info = TitleParser().torrent_parser(title)
    print(file_info)
    print(r.gen_path(file_info, bangumi_name,"advance"))
    # asyncio.run(Renamer().rename_torrent())
