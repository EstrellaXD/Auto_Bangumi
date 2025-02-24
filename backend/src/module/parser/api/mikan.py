from .baseapi import BaseWebPage


class RemoteMikan(BaseWebPage):
    def __init__(self, url: str = "", content: str = None):
        super().__init__(url, content)


class LocalMikan(BaseWebPage):
    # 直接收一个本地文件内容
    def __init__(self, url: str = None, content: str = None):
        super().__init__(url, content)
