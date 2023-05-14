from module.network import RequestContent
from module.conf import settings


class RSSSearcher(RequestContent):

    def __search_url(self, keywords: str) -> str:
        keywords.replace(" ", "+")
        url = f"{settings.rss_parser.custom_url}/RSS/Search?keyword={keywords}"
        return url

    def search_keywords(self, keywords: str) -> list[dict]:
        url = self.__search_url(keywords)
        torrents = self.get_torrents(url)
        return torrents
