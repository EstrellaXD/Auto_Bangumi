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

    def test_pre_process(self):
        content = "【幻樱字幕组】【4月新番】"
        expected_content = "[幻樱字幕组][4月新番]"
        self.assertEqual(RawParser.pre_process(content), expected_content)
