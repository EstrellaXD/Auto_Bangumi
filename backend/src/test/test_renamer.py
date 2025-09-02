import pytest
from module.manager.renamer import Renamer
from module.parser import TitleParser


class TestRenamer:
    """测试 Renamer 类的 gen_path 方法"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.renamer = Renamer()
        self.title_parser = TitleParser()

    def test_gen_path_pn_method_episode(self):
        """测试 pn 方法生成媒体文件路径"""
        torrent_name = "[LoliHouse] 我的青春恋爱物语果然有问题 - 05 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕].mkv"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        file_info.season = 1
        bangumi_name = "我的青春恋爱物语果然有问题"
        method = "pn"

        result = self.renamer.gen_path(file_info, bangumi_name, method)
        expected = "我的青春恋爱物语果然有问题 S01E05.mkv"
        assert result == expected

    def test_gen_path_advance_method_episode(self):
        """测试 advance 方法生成媒体文件路径"""
        torrent_name = "[ANi] 进击的巨人 最终季 - 12 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4].mp4"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        file_info.season = 4
        bangumi_name = "进击的巨人 最终季"
        method = "advance"

        result = self.renamer.gen_path(file_info, bangumi_name, method)
        expected = "进击的巨人 最终季 S04E12.mp4"
        assert result == expected

    def test_gen_path_custom_method_episode(self):
        """测试 custom 方法生成媒体文件路径（包含字幕组）"""
        torrent_name = "[LoliHouse] 鬼灭之刃 游郭篇 - 08 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕].mkv"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        file_info.season = 2
        bangumi_name = "鬼灭之刃 游郭篇"
        method = "custom"

        result = self.renamer.gen_path(file_info, bangumi_name, method)
        expected = "鬼灭之刃 游郭篇 S02E08 - LoliHouse.mkv"
        assert result == expected

    def test_gen_path_torrent_name_method(self):
        """测试使用原种子名方法"""
        torrent_name = "[LoliHouse] 2.5次元的诱惑 - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕].mkv"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        bangumi_name = "2.5次元的诱惑"
        method = "default"  # 会使用默认的 torrent_name 方法

        result = self.renamer.gen_path(file_info, bangumi_name, method)
        expected = "[LoliHouse] 2.5次元的诱惑 - 01 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕].mkv"
        assert result == expected

    def test_gen_path_episode_zero_padding(self):
        """测试集数的零填充格式"""
        torrent_name = "[字幕组] 东京食尸鬼 - 03.mp4"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        file_info.season = 1
        bangumi_name = "东京食尸鬼"
        method = "pn"

        result = self.renamer.gen_path(file_info, bangumi_name, method)
        expected = "东京食尸鬼 S01E03.mp4"
        assert result == expected

    def test_gen_path_with_mp4_suffix(self):
        """测试 MP4 格式文件"""
        torrent_name = "[ANi] 一拳超人 第二季 - 10 [1080P][Baha][WEB-DL][AAC AVC][CHT][MP4].mp4"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        file_info.season = 2
        bangumi_name = "一拳超人 第二季"
        method = "advance"

        result = self.renamer.gen_path(file_info, bangumi_name, method)
        expected = "一拳超人 第二季 S02E10.mp4"
        assert result == expected

    def test_gen_path_unknown_method_fallback(self):
        """测试未知方法回退到默认方法"""
        torrent_name = "[测试] 测试番剧 - 01.mkv"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        bangumi_name = "测试番剧"
        method = "unknown_method"

        result = self.renamer.gen_path(file_info, bangumi_name, method)
        expected = "[测试] 测试番剧 - 01.mkv"
        assert result == expected

    def test_gen_path_long_title(self):
        """测试长标题处理"""
        torrent_name = "[LoliHouse] 关于我转生变成史莱姆这档事 第二季 第二部分 - 18.mkv"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        file_info.season = 2
        long_title = "关于我转生变成史莱姆这档事 第二季 第二部分"
        method = "advance"

        result = self.renamer.gen_path(file_info, long_title, method)
        expected = f"{long_title} S02E18.mkv"
        assert result == expected

    def test_gen_path_edge_case_episode_zero(self):
        """测试集数为0的边界情况"""
        torrent_name = "[测试] 测试番剧 - 00.mkv"
        file_info = self.title_parser.torrent_parser(torrent_name)
        assert file_info is not None
        file_info.season = 1
        file_info.episode = 0  # 确保集数为0
        bangumi_name = "测试番剧"
        method = "pn"

        result = self.renamer.gen_path(file_info, bangumi_name, method)
        expected = "测试番剧 S01E00.mkv"
        assert result == expected

    

    

