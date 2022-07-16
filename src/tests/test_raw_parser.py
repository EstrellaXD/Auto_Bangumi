import unittest
from random import randrange

from parser.analyser import RawParser


class TestRawParser(unittest.TestCase):

    def test_raw_parser(self):
        parser = RawParser()
        content = "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】"
        info = parser.analyse(content)

        self.assertEqual(info.title_en, "Komi-san wa, Komyushou Desu.")
        self.assertEqual(info.resolution, "1920X1080")
        self.assertEqual(info.episode, 22)
        self.assertEqual(info.season, 2)

        content = "[百冬练习组&LoliHouse] BanG Dream! 少女乐团派对！☆PICO FEVER！ / Garupa Pico: Fever! - 26 [WebRip 1080p HEVC-10bit AAC][简繁内封字幕][END] [101.69 MB]"
        info = parser.analyse(content)

        self.assertEqual(info.group, "百冬练习组&LoliHouse")
        self.assertEqual(info.title_zh, "BanG Dream! 少女乐团派对！☆PICO FEVER！")
        self.assertEqual(info.resolution, "1080p")
        self.assertEqual(info.episode, 26)
        self.assertEqual(info.season, 1)

        content = "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译] [539.4 MB]"
        info = parser.analyse(content)
        self.assertEqual(info.group, "喵萌奶茶屋")
        self.assertEqual(info.title_en, "Summer Time Rendering")
        self.assertEqual(info.resolution, "1080p")
        self.assertEqual(info.episode, 11)
        self.assertEqual(info.season, 1)

        content = "【喵萌奶茶屋】★04月新番★夏日重现/Summer Time Rendering[11][1080p][繁日双语][招募翻译] [539.4 MB]"
        info = parser.analyse(content)
        self.assertEqual(info.title, "Summer Time Rendering")

    def test_pre_process(self):
        content = "【幻樱字幕组】【4月新番】"
        expected_content = "[幻樱字幕组][4月新番]"
        self.assertEqual(RawParser.pre_process(content), expected_content)

    def test_get_group(self):
        content = "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】"

        content = RawParser.pre_process(content)
        expected_content = "幻樱字幕组"

        self.assertEqual(RawParser.get_group(content), expected_content)

    def test_find_tags(self):
        cases = [
            ("[GB_MP4] [1920X1080] [bilibili]", ["GB", "1920X1080", "bilibili"]),
            ("[GB_MP4] [1920X1080]", ["GB", "1920X1080", None]),
            ("[简_MP4] [Bilibili]", ["简", None, "Bilibili"]),
            ("[简_MP4] [Bilibili] [Web]", ["简", None, "Web"]),
            ("dfkajflkdaj dfkadjlkfa [Web]", [None, None, "Web"]),
            ("dfkajflkdaj dfkadjlkfa [Web] [Web]", [None, None, "Web"]),
        ]

        for content, expected in cases:
            ret = RawParser.find_tags(content)
            self.assertEqual(len(ret), 3)
            for i in range(3):
                self.assertEqual(ret[i], expected[i])

    def test_episode(self):
        parser = RawParser()
        for epi in range(1, 100000, 100):
            content = f"【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第一季 Komi-san wa, Komyushou Desu. S01】【{epi}】【GB_MP4】【4K】"
            info = parser.analyse(content)
            self.assertEqual(info.episode, epi)

        for epi in range(1, 100000, 100):
            content = f"[Nekomoe kissaten][Summer Time Rendering - {epi} [1080p][JPTC].mp4"
            info = parser.analyse(content)
            self.assertEqual(info.episode, epi)

    def test_season(self):
        chinese_number_arr = ["一", "二", "三", "四",
                              "五", "六", "七", "八", "九", "十", "十一", "十二"]
        parser = RawParser()
        for i in range(1, 13):
            season = str(i).zfill(2)
            content = f"【幻樱字幕组】【古见同学有交流障碍症 第{chinese_number_arr[i - 1]}季 Komi-san wa, Komyushou Desu. S{season}】[1]"
            info = parser.analyse(content)
            self.assertEqual(info.season, i)
