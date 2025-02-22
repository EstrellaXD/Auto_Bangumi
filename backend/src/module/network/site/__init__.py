from .mikan import rss_parser

# 抽象出来是为了可以模拟一下,不用真的去请求网站

__all__ = ["rss_parser"]
