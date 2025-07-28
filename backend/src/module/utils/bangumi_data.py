import logging
import re

logger = logging.getLogger(__name__)


def get_hash(torrent_url: str) -> str | None:
    hash_pattern_dict = {
        "magnet_hash_pattern": re.compile(r"\b([a-fA-F0-9]{40})\b"),
        "torrent_hash_pattern": re.compile(r"/([a-fA-F0-9]{7,40})\.torrent"),
        "dmhy_hash_pattern": re.compile(r"urn:btih:([A-Z0-9]{32})"),
    }
    for hash_pattern in hash_pattern_dict.values():
        ans = re.search(hash_pattern, torrent_url)
        if ans:
            return ans[1]
    logger.warning(f"[Utils] Cannot find hash in {torrent_url}")
    return ""


if __name__ == "__main__":
    test_url = r"https://nyaa.land/download/1864806.torrent"
    test_url = "magnet:?xt=urn:btih:R5NMZKCR2GYMZJRYO6AUGPKZPTQPAFDM"
    test_url = "2d01b04fe5c32a6b7db2d50fe67882af564c50e8"
    print(get_hash(test_url))
