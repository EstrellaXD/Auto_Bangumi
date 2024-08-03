import logging
import re

logger = logging.getLogger(__name__)

def get_hash(torrent_url: str) -> str | None:
    hash_pattern_dict = {
        "magnet_hash_pattern": re.compile(r"urn:btih:([a-fA-F0-9]{40})"),
        "torrent_hash_pattern": re.compile(r"/([a-fA-F0-9]{40})\.torrent"),
    }
    for hash_pattern in hash_pattern_dict.values():
        ans = re.search(hash_pattern, torrent_url)
        if ans:
            return ans[1]

