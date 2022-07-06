import logging

from parser.analyser import RawParser, DownloadParser, TMDBMatcher
from conf import settings

logger = logging.getLogger(__name__)


class TitleParser:
    def __init__(self):
        self._raw_parser = RawParser()
        self._download_parser = DownloadParser()

    def raw_parser(self, raw):
        return self._raw_parser.analyse(raw)

    def download_parser(self, download_raw, folder_name, season, method=settings.method):
        return self._download_parser.download_rename(download_raw, folder_name, season, method)

    def return_dict(self, raw):
        tmdb = TMDBMatcher()
        try:
            episode = self.raw_parser(raw)
            if settings.enable_tmdb:
                try:
                    tmdb_info = tmdb.tmdb_search(episode.title)
                    official_title = tmdb_info.title_zh if settings.title_language == "zh" else tmdb_info.title_jp
                    season = tmdb_info.last_season
                except Exception as e:
                    logger.debug(e)
                    logger.info("Not Match in TMDB")
                    official_title = episode.title
                    season = episode.season_info.number
            else:
                official_title = episode.title
                season = episode.season_info.number
            data = {
                "official_title": official_title,
                "title_raw": episode.title,
                "season": season,
                "season_raw": episode.season_info.raw,
                "group": episode.group,
                "dpi": episode.dpi,
                "source": episode.source,
                "subtitle": episode.subtitle,
                "added": False,
                "eps_collect": True if settings.eps_complete else False,
            }
            return data
        except Exception as e:
            logger.debug(e)


if __name__ == '__main__':
    import re
    T = TitleParser()
    raw = "[Lilith-Raws] 神渣☆偶像 / Kami Kuzu☆Idol - 01 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]"
    season = int(re.search(r"\d{1,2}", "S02").group())
    title = T.raw_parser(raw)
    print(season,title.title)