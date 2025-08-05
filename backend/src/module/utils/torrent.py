import base64
import hashlib
from urllib.parse import quote
import logging

import bencodepy

logger = logging.getLogger(__name__)


def calculate_v2_hash(info_dict):
    """计算BitTorrent v2 hash"""
    # 检查是否为v2种子或混合种子
    if b"meta version" in info_dict and info_dict[b"meta version"] == 2:
        # 对于v2种子，使用SHA256
        encoded_info = bencodepy.encode(info_dict)
        return hashlib.sha256(encoded_info).digest()

    # 检查是否存在v2特有的字段
    if b"file tree" in info_dict:
        # 这是一个混合种子，计算v2 hash
        encoded_info = bencodepy.encode(info_dict)
        return hashlib.sha256(encoded_info).digest()

    return None


async def torrent_to_link(torrent_file):
    try:
        logger.debug(
            f"torrent_to_link: Processing torrent file, type: {type(torrent_file)}, size: {len(torrent_file) if hasattr(torrent_file, '__len__') else 'unknown'}"
        )

        torrent_info = bencodepy.decode(torrent_file)
        logger.debug(
            f"torrent_to_link: Successfully decoded torrent, keys: {list(torrent_info.keys())}"
        )

        # 获取 info 字段并进行 bencode 编码
        info = torrent_info[b"info"]
        encoded_info = bencodepy.encode(info)

        # 计算 info_hash (SHA1 hash of the encoded info dictionary)
        info_hash_v1 = hashlib.sha1(encoded_info).digest()
        info_hash_hex_v1 = base64.b16encode(info_hash_v1).decode("utf-8").lower()
        logger.debug(f"torrent_to_link: V1 hash calculated: {info_hash_hex_v1}")

        # 尝试计算v2 hash
        info_hash_v2 = calculate_v2_hash(info)

        # 如果是混合种子或v2种子，优先使用v2 hash
        if info_hash_v2:
            info_hash_hex_v2 = base64.b16encode(info_hash_v2).decode("utf-8").lower()
            # V2 hash 使用 btmh (BitTorrent Meta Hash) 格式，1220表示SHA256
            magnet_link = f"magnet:?xt=urn:btmh:1220{info_hash_hex_v2}"
            logger.debug(f"torrent_to_link: Using V2 hash: {info_hash_hex_v2}")
        else:
            # 使用v1 hash
            magnet_link = f"magnet:?xt=urn:btih:{info_hash_hex_v1}"
            logger.debug(f"torrent_to_link: Using V1 hash: {info_hash_hex_v1}")

        # # 获取文件名
        # name = torrent_info.get(b"info", {}).get(b"name", b"").decode("utf-8")
        # if name:
        #     magnet_link += f"&dn={quote(name)}"

        # 添加 trackers (可选)
        if b"announce" in torrent_info:
            tracker = torrent_info[b"announce"].decode("utf-8")
            magnet_link += f"&tr={quote(tracker)}"

        if b"announce-list" in torrent_info:
            for tracker_list in torrent_info[b"announce-list"]:
                tracker = tracker_list[0].decode("utf-8")
                magnet_link += f"&tr={quote(tracker)}"

        logger.debug(f"torrent_to_link: Generated magnet link: {magnet_link}")
        return magnet_link

    except Exception as e:
        logger.error(f"torrent_to_link: Error processing torrent file: {e}")
        logger.error(f"torrent_to_link: Torrent file type: {type(torrent_file)}")
        if hasattr(torrent_file, "__len__"):
            logger.error(f"torrent_to_link: Torrent file size: {len(torrent_file)}")
        if isinstance(torrent_file, bytes) and len(torrent_file) > 0:
            logger.error(f"torrent_to_link: First 50 bytes: {torrent_file[:50]}")
        return ""


async def get_torrent_hashes(torrent_file):
    """获取种子的所有可能hash (v1和v2)"""
    try:
        logger.debug(f"get_torrent_hashes: Processing torrent file")

        torrent_info = bencodepy.decode(torrent_file)
        info = torrent_info[b"info"]
        encoded_info = bencodepy.encode(info)

        # V1 hash (SHA1)
        v1_hash = hashlib.sha1(encoded_info).digest()
        v1_hash_hex = base64.b16encode(v1_hash).decode("utf-8").lower()
        logger.debug(f"get_torrent_hashes: V1 hash: {v1_hash_hex}")

        hashes = {"v1": v1_hash_hex}

        # V2 hash (SHA256)
        v2_hash = calculate_v2_hash(info)
        if v2_hash:
            v2_hash_hex = base64.b16encode(v2_hash).decode("utf-8").lower()
            hashes["v2"] = v2_hash_hex
            logger.debug(f"get_torrent_hashes: V2 hash: {v2_hash_hex}")
        else:
            logger.debug(
                "get_torrent_hashes: No V2 hash found, this is a V1-only torrent"
            )

        return hashes

    except Exception as e:
        logger.error(f"get_torrent_hashes: Error processing torrent file: {e}")
        return {"v1": ""}
