import unittest

from parser.analyser import RawParser


class TestRawParser(unittest.TestCase):

    def test_raw_parser(self):
        parser = RawParser()
        content = "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第二季 Komi-san wa, Komyushou Desu. S02】【22】【GB_MP4】【1920X1080】"
        info = parser.analyse(content)

        self.assertEqual(info.title, "Komi-san wa, Komyushou Desu.")
        self.assertEqual(info.dpi, "1920X1080")
        self.assertEqual(info.ep_info.number, 22)
        self.assertEqual(info.season_info.number, 2)

        content = "【幻樱字幕组】【4月新番】【古见同学有交流障碍症 第一季 Komi-san wa, Komyushou Desu. S01】【23】【GB_MP4】【4K】"
        info = parser.analyse(content)

        self.assertEqual(info.title, "Komi-san wa, Komyushou Desu.")
        self.assertEqual(info.dpi, "4K")
        self.assertEqual(info.ep_info.number, 23)
        self.assertEqual(info.season_info.number, 1)

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
