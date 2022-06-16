import re
import logging

from network import RequestContent
from parser import TitleParser

from conf import settings

from core import DownloadClient

logger = logging.getLogger(__name__)


class RSSAnalyser:
    def __init__(self):
        self._title_analyser = TitleParser()
        self._request = RequestContent()

    def rss_to_datas(self, bangumi_info: list):
        rss_titles = self._request.get_titles(settings.rss_link)
        self._request.close_session()
        for raw_title in rss_titles:
            logger.debug(raw_title)
            extra_add = True
            for d in bangumi_info:
                if re.search(d["title_raw"], raw_title) is not None:
                    extra_add = False
                    break
            if extra_add:
                data = self._title_analyser.return_dict(raw_title)
                if data["official_title"] not in bangumi_info:
                    bangumi_info.append(data)

    def rss_to_data(self, url):
        rss_title = self._request.get_title(url)
        self._request.close_session()
        data = self._title_analyser.return_dict(rss_title)
        return data

    def run(self, bangumi_info: list, download_client: DownloadClient):
        self.rss_to_datas(bangumi_info)
        download_client.add_rules(bangumi_info, rss_link=settings.rss_link)


if __name__ == "__main__":
    from conf.const_dev import DEV_SETTINGS
    settings.init(DEV_SETTINGS)
    print(settings.host_ip)
    client = DownloadClient()
    ra = RSSAnalyser()
    data = [{'official_title': '勇者辞职不干了', 'title_raw': 'Yuusha, Yamemasu', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': False, 'eps_collect': False},
            {'official_title': '朋友游戏', 'title_raw': 'Tomodachi Game', 'season': 1, 'season_raw': '', 'group': '离谱Sub', 'dpi': '1080p', 'source': None, 'subtitle': '简体内嵌', 'added': True, 'eps_collect': False},
            {'official_title': '街角魔族', 'title_raw': 'Machikado Mazoku: 2-choume', 'season': 2, 'season_raw': '', 'group': '桜都字幕组', 'dpi': '1080P', 'source': None, 'subtitle': '简繁内封', 'added': True, 'eps_collect': False},
            {'official_title': '杜鹃的婚约', 'title_raw': 'Kakkou no Iinazuke', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': '间谍过家家', 'title_raw': 'SPYxFAMILY', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': 'Love Live！虹咲学园 学园偶像同好会', 'title_raw': 'Love Live！虹咲学园 学园偶像同好会', 'season': 2, 'season_raw': 'S02', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': '指名！', 'title_raw': 'CUE!', 'season': 1, 'season_raw': '', 'group': '喵萌Production', 'dpi': '1080p', 'source': None, 'subtitle': '简日双语', 'added': True, 'eps_collect': False},
            {'official_title': '辉夜大小姐想让我告白', 'title_raw': 'Kaguya-sama wa Kokurasetai', 'season': None, 'season_raw': 'S03', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': '处刑少女的生存之道', 'title_raw': 'Shokei Shoujo no Virgin Road', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': 'Kakkou no Iikagen', 'title_raw': 'Kakkou no Iikagen', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': '古见同学有交流障碍症。', 'title_raw': 'Komi-san wa, Komyushou Desu.', 'season': 2, 'season_raw': '', 'group': '幻樱字幕组', 'dpi': '1920X1080', 'source': None, 'subtitle': 'GB', 'added': True, 'eps_collect': False},
            {'official_title': '夏日重现', 'title_raw': 'Summer Time Rendering', 'season': 1, 'season_raw': '', 'group': '喵萌奶茶屋', 'dpi': '1080p', 'source': None, 'subtitle': '简日双语', 'added': True, 'eps_collect': False},
            {'official_title': '魔法使黎明期', 'title_raw': 'Mahoutsukai Reimeiki', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': '派对浪客诸葛孔明', 'title_raw': 'Paripi Koumei', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': None, 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': '相合之物', 'title_raw': 'Deaimon', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': '盾之勇者成名录', 'title_raw': 'Tate no Yuusha no Nariagari', 'season': 2, 'season_raw': 'S02', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False},
            {'official_title': '史上最强大魔王转生为村民A', 'title_raw': 'Shijou Saikyou no Daimaou', 'season': 1, 'season_raw': '', 'group': 'Lilith-Raws', 'dpi': '1080p', 'source': 'Baha', 'subtitle': 'CHT', 'added': True, 'eps_collect': False}]
    ra.run(data, client)
    for d in data:
        print(d)