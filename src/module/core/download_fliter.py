import re
import logging
import xml.etree.ElementTree
from typing import Tuple

from module.conf import settings
from module.utils import json_config

logger = logging.getLogger(__name__)


class RSSFilter:
    def __init__(self):
        self.filter_rule = json_config.load(settings.filter_rule)

    def filter(self, item: xml.etree.ElementTree.Element) -> Tuple[bool, str]:
        title = item.find("title").text
        torrent = item.find("enclosure").attrib["url"]
        download = False
        for rule in self.filter_rule:
            if re.search(rule["include"], title):
                if not re.search(rule["exclude"], title):
                    download = True
                    logger.debug(f"{title} added")
        return download, torrent
