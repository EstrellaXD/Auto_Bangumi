from torrentool.bencode import Bencode
from torrentool.exceptions import BencodeDecodingError


def check_torrent(content: bytes) -> bool:
    try:
        if Bencode.decode(content):
            return True
        return False
    except BencodeDecodingError:
        return False
