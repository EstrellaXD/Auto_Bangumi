import re
import logging

from bs4 import BeautifulSoup

from conf import settings
from utils import json_config

logger = logging.getLogger(__name__)


class RSSFilter:
    def __init__(self):
        self.filter_rule = json_config.load(settings.filter_rule)

    def filter(self, item: BeautifulSoup):
        title = item.title.string
        torrent = item.find("enclosure")
        download = False
        for rule in self.filter_rule:
            if re.search(rule["include"], title):
                if not re.search(rule["exclude"], title):
                    download = True
                    logger.debug(f"{title} added")
        return download, torrent

