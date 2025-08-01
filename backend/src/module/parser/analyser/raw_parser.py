import logging
import re
from typing import Any

from module.models import Episode
from module.parser.analyser import patterns as p

logger = logging.getLogger(__name__)

CHINESE_NUMBER_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
ROMAN_NUMBERS = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
}


class RawParser:
    """
    原始视频标题解析器

    用于解析动漫视频文件名，提取出剧集信息、季度、字幕组、分辨率等元数据。
    支持多种常见的动漫命名格式。
    """

    def __init__(self) -> None:
        self.raw_title = ""
        self.title = ""
        self.token = []

    def process_title(self) -> None:
        """预处理标题，统一格式"""
        self.title = self.title.replace("\n", " ")

        # 如果以【开头
        if self.title.startswith("【"):
            translation_table = str.maketrans("【】", "[]")
            self.title = self.title.translate(translation_table)
        self.title = self.title.strip()
        self.title += "_"

    def parser(self, title: str) -> Episode:
        self.raw_title = title
        self.title = title
        self.process_title()
        source_info = self.get_source_info()
        resolution_info = self.get_resolution_info()
        audio_info = self.get_audio_info()
        video_info = self.get_video_info()
        sub_info = self.get_sub_info()
        _ = self.get_unuseful_info()  # 清理无用信息，但不使用结果
        episode_info, episode_is_trusted, season_info, season_is_trusted = (
            self.get_episode_info()
        )

        if not season_info:
            season_info, season_is_trusted = self.get_season_info()
        episode = self.parser_episode(episode_info, episode_is_trusted)
        season, season_raw = self.parse_season(season_info, season_is_trusted)
        # 优化 token 处理逻辑
        temp_title = self.title
        if "/[]" in temp_title:
            parts = temp_title.split("/[]")
            if len(parts) > 1:
                temp_title = "[]".join(parts[:-1])
        self.token = re.split(r"[\[\]]", temp_title)
        (
            name_en,
            name_zh,
            name_jp,
        ) = self.name_process()

        group = self.get_group()
        source = source_info[0] if source_info else ""
        sub = sub_info[0] if sub_info else ""
        resolution = resolution_info[0] if resolution_info else ""

        return Episode(
            name_en,
            name_zh,
            name_jp,
            season,
            season_raw,
            episode,
            sub,
            group,
            resolution,
            source,
            audio_info,
            video_info,
        )

    def findall_sub_title(self, pattern: re.Pattern, sym: str = "[]") -> Any:
        """查找并替换标题中的模式"""
        ans = re.findall(pattern, self.title)
        if ans:
            self.title = re.sub(pattern, sym, self.title)
        else:
            ans = re.findall(pattern, self.raw_title)
        return ans

    def get_episode_info(self) -> tuple[Any, bool, Any, bool]:
        """获取剧集和季度信息"""
        episode_info = self.findall_sub_title(p.EPISODE_PATTERN, sym="/[]")
        episode_is_trusted = True
        season_info = self.findall_sub_title(p.SEASON_RE, sym="/[]")
        season_is_trusted = True
        if not episode_info:
            episode_info = self.findall_sub_title(p.EPISODE_RE_UNTRUSTED)
            episode_is_trusted = False
        return episode_info, episode_is_trusted, season_info, season_is_trusted

    def parser_episode(self, episode_info: Any, episode_is_trusted: bool) -> int:

        un_trusted_episode_list = []
        if not episode_info:
            # 实在没找到,返回0
            return 0
        if episode_is_trusted or len(episode_info) == 1:
            # 可信集数 or 长度为1
            # 秉持尽量返回的思想
            return self.episode_info_to_episode(episode_info[0])

        for un_trusted_episode in episode_info:
            un_trusted_episode_list.append(
                self.episode_info_to_episode(un_trusted_episode)
            )

        # 所有的集数一致
        if all(x == un_trusted_episode_list[0] for x in un_trusted_episode_list):
            return un_trusted_episode_list[0]

        if un_trusted_episode_list[1] not in [480, 720, 1080]:
            return un_trusted_episode_list[1]
        return un_trusted_episode_list[0]

    def parse_season(
        self, season_info: Any, season_is_trusted: bool
    ) -> tuple[int, str]:
        if season_info:
            season_list = [self.season_info_to_season(s) for s in season_info]
            if season_is_trusted:
                return season_list[0], season_info[0][0]
            # 如果是非可信季度信息，返回第一个有效的季度
            else:
                if len(season_info[0]) ==1 and season_list[0] > 1:
                    re.sub(p.SEASON_PATTERN_UNTRUSTED,"/[]" , self.title)
                    return season_list[0], season_info[0]

        return 1, ""

    def episode_info_to_episode(self, episode_info: Any) -> int:
        """从剧集信息元组中提取剧集号"""
        # 从元组中找到第一个非空字符串
        for episode in episode_info[1:]:  # 跳过第一个元素（完整匹配）
            if episode:
                try:
                    return int(episode)
                except ValueError:
                    logger.warning(f"无法解析剧集号: {episode}")
                    continue
        return 0

    def season_info_to_season(self, season_info: Any) -> int:
        """从季度信息元组中提取季度号"""
        # 从元组中找到第一个有效的季度数据
        for season in season_info:
            if("部分" in season):
                return 1
            if season and season.isdigit():
                try:
                    return int(season)
                except ValueError:
                    continue
            elif season in CHINESE_NUMBER_MAP:
                return CHINESE_NUMBER_MAP[season]
            elif season in ROMAN_NUMBERS:
                return ROMAN_NUMBERS[season]
        return 0

    def get_season_info(self) -> tuple[Any, bool]:
        """获取不可信的季度信息"""
        season_info = re.findall(p.SEASON_PATTERN_UNTRUSTED,self.title)
        is_trusted = False
        return season_info, is_trusted

    def name_process(self) -> tuple[str, str, str]:
        """处理标题，提取英文、中文和日文名称"""

        # 简化 token 过滤逻辑
        max_len = min(10, len(self.token))
        self.token = [token for token in self.token[:max_len] if len(token.strip()) > 1]

        self.token = self.token[:5]
        token_priority = [len(s) for s in self.token]
        if len(self.token) == 1:
            anime_title = self.token[0]

        elif len(self.token) == 2:
            anime_title = self.token[1]
        else:
            token_priority[1] += 4
            for token, idx in zip(self.token, range(3)):
                if "/" in token:
                    token_priority[idx] += 10
                if "&" in token:
                    token_priority[idx] -= 12
                if "字幕" in token:
                    token_priority[idx] -= 90
                if re.search(r"[a-zA-Z]{3,}", token):
                    token_priority[idx] += 2
                if re.search(r"[\u0800-\u4e00]{2,}", token):
                    token_priority[idx] += 2
                if re.search(r"[\u4e00-\u9fa5]{2,}", token):
                    token_priority[idx] += 2
            idx = token_priority.index(max(token_priority))
            anime_title = self.token[idx]
            anime_title = anime_title.strip()
        anime_title = re.sub(r"^\\|\\$", "", anime_title)
        anime_title = anime_title.strip()

        name_en, name_zh, name_jp = "", "", ""
        split = re.split(r"/|\s{2}|-\s{2}", anime_title)
        while "" in split:
            split.remove("")
        if len(split) == 1:
            if re.search("_{1}", anime_title) is not None:
                split = re.split("_", anime_title)
            elif re.search(" - {1}", anime_title) is not None:
                split = re.split("-", anime_title)
        if len(split) == 1:
            # 主要的思想就是从头或者尾部找出一个中文名
            chinese_chars = len(p.CHINESE_PATTERN.findall(split[0]))
            chinese_ratio = chinese_chars / len(split[0]) if len(split[0]) > 0 else 0
            # 移除调试 print 语句
            if chinese_ratio <= 0.7:
                split_space = split[0].split(" ")

                for idx in [0, -1]:
                    if re.search(r"^[\u4e00-\u9fa5]{2,}", split_space[idx]) is not None:
                        chs = split_space[idx]
                        split_space.remove(chs)
                        split = [chs, " ".join(split_space)]
                        break
        for token in split:
            if re.search(r"[\u0800-\u4e00]{2,}", token) and not name_jp:
                name_jp = token.strip()
            elif re.search(r"[\u4e00-\u9fa5]{2,}", token) and not name_zh:
                name_zh = token.strip()
            elif re.search(r"[a-zA-Z]{3,}", token) and not name_en:
                name_en = token.strip()
        return name_en, name_zh, name_jp

    def get_group(self) -> str:
        """获取字幕组信息"""
        for group in self.token:
            if group := group.strip():
                # 修复字符串操作 - replace 不会就地修改
                group = group.replace("/", "").strip()
                return group
        return ""

    def get_video_info(self) -> Any:
        """获取视频格式信息"""
        return self.findall_sub_title(p.VIDEO_TYPE_PATTERN)

    def get_resolution_info(self) -> Any:
        """获取分辨率信息"""
        return self.findall_sub_title(p.RESOLUTION_RE)

    def get_source_info(self) -> Any:
        """获取视频来源信息"""
        return self.findall_sub_title(p.SOURCE_RE)

    def get_unuseful_info(self) -> Any:
        """获取无用信息"""
        return self.findall_sub_title(p.UNUSEFUL_RE)

    def get_sub_info(self) -> Any:
        """获取字幕信息"""
        return self.findall_sub_title(p.SUB_RE)

    def get_audio_info(self) -> Any:
        """获取音频信息"""
        return self.findall_sub_title(p.AUDIO_INFO)


def get_raw():
    import json
    import random

    with open("./data.jsonl", "r", encoding="utf-8") as file:
        lines = file.readlines()
        line = random.choice(lines).strip()
    raw_name = json.loads(line).get("raw")
    return raw_name


def raw_parser(raw: str) -> Episode | None:
    """解析原始视频标题，提取剧集信息"""
    try:
        parser = RawParser()
        return parser.parser(raw)
    except Exception as e:
        logger.error(f"解析标题失败: {raw}, 错误: {e}")
        return None


def is_v1(title: str) -> bool:
    """
    判断是否是 v1 番剧
    """
    if p.V1_RE.findall(title):
        return True
    return False


def is_point_5(title: str) -> bool:
    """
    判断是否是 .5 番剧
    """
    if p.POINT_5_RE.findall(title):
        return True
    return False


if __name__ == "__main__":

    # title = get_raw()
    # title = "赛马娘 (2018) S03E13.mp4"
    # title = "[SweetSub][鹿乃子大摇大摆虎视眈眈][Shikanoko Nokonoko Koshitantan][04][WebRip][1080P][AVC 8bit][繁日双语][462.01 MB]"
    # title = "[ANi] Make Heroine ga Oosugiru /  败北女角太多了！ - 01 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4]"
    # title = "[极影字幕社]★4月新番 天国大魔境 Tengoku Daimakyou 第05话 GB 720P MP4（字幕社招人内详）"
    # title = "hello[2023.1.2]hell"
    # title = "海盗战记 (2019) S01E01.mp4"
    # title = "[SBSUB][CONAN][1082][V2][1080P][AVC_AAC][CHS_JP](C1E4E331).mp4"
    # title = "前辈是男孩子 (2024) S01E02.mp4"
    # title = "[SBSUB][CONAN][1082][V2][1080P][AVC_AAC][CHS_JP](C1E4E331).mp4"
    # title = "海盗战记 S01E01.zh-tw.ass"
    title = "[百冬练习组&LoliHouse] BanG Dream! 少女乐团派对！☆PICO FEVER！ / Garupa Pico: Fever! - 26 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][END] [101.69 MB]"
    # title ="【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
    # title = "【失眠搬运组】放学后失眠的你-Kimi wa Houkago Insomnia - 06 [bilibili - 1080p AVC1 CHS-JP].mp4"
    # title = "[KitaujiSub] Shikanoko Nokonoko Koshitantan [01Pre][WebRip][HEVC_AAC][CHS_JP].mp4"
    # title = "[Doomdos] - 白色闪电 - 第02话 - [1080P].mp4"
    # title = "Doomdos] -凡人修仙传-第107话-[1080P].mp"
    # title = "[豌豆字幕组&风之圣殿字幕组】★04月新番[鬼灭之刃 柱训练篇 / Kimetsu_no_Yaiba-Hashira_Geiko_Hen][02(57)][简体][1080P][MP4]"
    # title = "迷宮飯 08/[TOC] Delicious in Dungeon [08][1080P][AVC AAC][CHT][MP4].mp4"
    # title = "[喵萌奶茶屋&LoliHouse] 葬送的芙莉莲 / Sousou no Frieren - 06 [WebRip 1080p HEVC-10bit AAC][简繁日内封字幕]"
    # title = "[LoliHouse] Ore wa Subete wo Parry suru - 05 [WebRip 1080p HEVC-10bit AAC SRTx2]"
    # title = " [LoliHouse] 我要【招架】一切 ～反误解的世界最强想成为冒险者～ / Ore wa Subete wo Parry suru - 05 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕] [复制磁连]"
    # title = "北宇治字幕组] 夜晚的水母不会游泳 / Yoru no Kurage wa Oyogenai [01-12 修正合集][WebRip][HEVC_AAC][简繁日内封] [复制磁连]"
    # title = "[北宇治字组&霜庭云花Sub&氢气烤肉架]【我推的孩子】/【Oshi no Ko】[18][WebRip][HEVC_AAC][繁日内嵌]"
    # # print(re.findall(RESOLUTION_RE,title))
    title = (
        "[织梦字幕组][尼尔：机械纪元 NieR Automata Ver1.1a][02集][1080P][AVC][简日双语]"
    )
    # title = "[ANi] Bakemonogatari / 物语系列 第外季＆第怪季 - 06.5 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4][ANi] Bakemonogatari / 物语系列 第外季＆第怪季 - 06.5 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4][217.2 MB]"
    # title = "ANi] 我獨自升級 - 07.5 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"
    # title = "[NEO·QSW]古莲泰沙U グレンダイザーU Grendizer U 02[WEBRIP AVC 1080P]（搜索用：巨灵神/克雷飞天神）"
    # title ="地下城里的人们 (2024) S02E10005.mp4"
    # title = (
    #     "[ANi] 物語系列 第外季＆第怪季 - 06.5 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4 "
    # )
    # title = "物语系列 S05E06.5.mp4 "
    # title = " 【幻月字幕组】【24年日剧】【直到破坏了丈夫的家庭】【第7话】【1080P】【中日双语】.mp4"
    # title = "[LoliHouse] 2.5次元的诱惑 / 2.5-jigen no Ririsa - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][LoliHouse] 2.5次元的诱惑 / 2.5-jigen no Ririsa - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][609.59 MB]"
    # title = "[ANi] Re：从零开始的异世界生活 第三季 - 01 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4] [复制磁连]"
    # title = "[AnimeRep] 蓝箱 / 青之箱 / Blue Box / Ao no Hako- 02 [1080p][简中内嵌]"
    # title = "[ANi] Kekkon Surutte Hontou desu ka /  听说你们要结婚！？ - 03 [1080P][baha][WEB-DL][AAC AVC][CHT][MP4]"
    # title = "[DBD-Raws][败犬女主太多了！/Make Heroine ga Oosugiru!/负けヒロインが多すぎる!][07-08TV+特典映像][BOX4][1080P][BDRip][HEVC-10bit][FLACx2][MKV] [复制磁连]"
    # title = "[漫猫字幕组&猫恋汉化组] 败犬女主太多了/Make Heroine ga Oosugiru (01-12Fin WEBRIP 1080p AVC AAC MP4 2024年7月 简中) [复制磁连]"
    # title = "[北宇治字幕组&LoliHouse] 地。-关于地球的运动- / Chi. Chikyuu no Undou ni Tsuite 03 [WebRip 1080p HEVC-10bit AAC ASSx2][简繁日内封字幕] [复制磁连]"
    # title = "[Lilith-Raws] Boku no Kokoro no Yabai Yatsu - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4"
    # title = "[LoliHouse] 关于我转生变成史莱姆这档事 第三季 / Tensei Shitara Slime Datta Ken 3rd Season - 17.5(65.5) [WebRip 1080p HEVC-10bit AAC][简繁内封字幕] [复制磁连]"
    # title = "水星的魔女(2022) S00E19.mp4"
    # title = "[Billion Meta Lab] 终末列车寻往何方 Shuumatsu Torein Dokoe Iku [12][1080][HEVC 10bit][简繁日内封][END]"
    # title = " 幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】"
    # title = "【1月】超超超超超喜欢你的100个女朋友 第二季 07.mp4"
    # print(is_vd(title))
    # print(is_point_5(title))
    # title = "[云歌字幕组][Re:从零开始的异世界生活 第三季 袭击篇][01][HEVC][x265 10bit][1080p][简日双语][招募校对] [复制磁连]"
    # title = "NEO·QSW]想星的阿克艾利昂 情感神话 想星のアクエリオン Aquarion: Myth of Emotions 02[WEBRIP AVC 1080P]（搜索用：想星的大天使）"
    # title = "[SBSUBJ[CONAN][1155][WEBRIP][1080P1[AVC_AAC][CHT_JP](8D4F664C).mp4"
    # title = "[TOC] 最弱技能《果实大师》 ～关于能无限食用技能果实（吃了就会死）这件事～ 09 [1080P][AVC AAC][CHT][MP4] [复制磁连]"
    # title = "[ANi] 离开 A 级队伍的我，和从前的弟子往迷宫深处迈进 - 08 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4] [复制磁连]"
    # title = "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
    # title = "海盗战记 (2019) S01E01.mp4"
    # print(title)
    # print(re.findall(EPISODE_PATTERN, title))
    # print(re.findall(SEASON_RE, title))
    # print(re.findall(EPISODE_RE_UNTRUSTED, title))
    # title = (
    #     "[梦蓝字幕组]New Doraemon 哆啦A梦新番[747][2023.02.25][AVC][1080P][GB_JP][MP4]"
    # )
    # # #
    # title = "碧蓝之海 第二季.mp4"
    # title = "坂本日常 第2部分"
    # title = "[ANi] Grand Blue Dreaming /  GRAND BLUE 碧蓝之海 2 - 04 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4]"
    title =  "[Lilith-Raws] Boku no Kokoro no Yabai Yatsu - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT].mp4"
    title = "【极影字幕社】★4月新番 天国大魔境 Tengoku Daimakyou 第05话 GB 720P MP4（字幕社招人内详）"
    res = raw_parser(title)
    for k, v in res.__dict__.items():
        print(f"{k}: {v}")
    # print(ret.token)
    # print(raw_parser(title))
