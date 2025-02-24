from abc import ABC, abstractmethod

from module.network import RequestContent


class WebPage(ABC):
    """
    Abstract class for anime info web page.
    """

    @abstractmethod
    async def get_content(self):
        pass


class BaseWebPage(WebPage):
    def __init__(self, url: str = "", content: str = None):
        # Url 和 content 是为了测试的时候用的
        self.url = url
        self.content = {}
        if content:
            self.content[url] = content

    async def get_content(self, url: str = ""):
        if not url:
            url = self.url
        if not url:
            return ""
        if self.content.get(url, None):
            return self.content.get(url)
        else:
            async with RequestContent() as req:
                content = await req.get_html(url)
                if content:
                    self.content[url] = content
                    return content
        return ""


class BaseAPI(ABC):
    @abstractmethod
    async def fetch_content(self, key_word: str) -> dict[str, str]:
        pass
