import base64
import hashlib
from urllib.parse import quote
import logging
import re

import bencodepy

logger = logging.getLogger(__name__)


def process_title(title:str) -> str:
    """预处理标题，统一格式"""
    # title 里面可能有"\n"
    title = title.replace("\n", " ")
    # 如果以【开头
    #
    if title.startswith("【"):
        translation_table = str.maketrans("【】", "[]")
        title = title.translate(translation_table)
    title = title.strip()
    # 末尾加一个 / 处理边界
    title += "/"
    return title


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


def torrent_to_link(torrent_file)-> list[str]:
    """将种子文件转换为磁力链接

    Returns:
        list[str]: 包含 v1 和 v2 (如果存在) 磁力链接的列表
    """
    try:
        logger.debug(
            f"torrent_to_link: Processing torrent file, type: {type(torrent_file)}, size: {len(torrent_file) if hasattr(torrent_file, '__len__') else 'unknown'}"
        )

        torrent_info = bencodepy.decode(torrent_file)
        logger.debug(f"torrent_to_link: Successfully decoded torrent, keys: {list(torrent_info.keys())}")

        # 获取 info 字段并进行 bencode 编码
        info = torrent_info[b"info"]
        encoded_info = bencodepy.encode(info)

        # 计算 info_hash (SHA1 hash of the encoded info dictionary)
        info_hash_v1 = hashlib.sha1(encoded_info).digest()
        info_hash_hex_v1 = base64.b16encode(info_hash_v1).decode("utf-8").lower()
        logger.debug(f"torrent_to_link: V1 hash calculated: {info_hash_hex_v1}")

        # 构建tracker列表
        tracker_params = ""
        if b"announce" in torrent_info:
            tracker = torrent_info[b"announce"].decode("utf-8")
            tracker_params += f"&tr={quote(tracker)}"

        if b"announce-list" in torrent_info:
            for tracker_list in torrent_info[b"announce-list"]:
                tracker = tracker_list[0].decode("utf-8")
                tracker_params += f"&tr={quote(tracker)}"

        # 构建 v1 magnet 链接
        magnet_link_v1 = f"magnet:?xt=urn:btih:{info_hash_hex_v1}{tracker_params}"
        logger.debug(f"torrent_to_link: Generated V1 magnet link: {magnet_link_v1}")

        magnet_links = [magnet_link_v1]

        # 尝试计算v2 hash
        info_hash_v2 = calculate_v2_hash(info)
        if info_hash_v2:
            info_hash_hex_v2 = base64.b16encode(info_hash_v2).decode("utf-8").lower()
            # V2 hash 使用 btmh (BitTorrent Meta Hash) 格式，1220表示SHA256
            magnet_link_v2 = f"magnet:?xt=urn:btmh:1220{info_hash_hex_v2}{tracker_params}"
            logger.debug(f"torrent_to_link: Generated V2 magnet link: {magnet_link_v2}")
            magnet_links.append(magnet_link_v2)
        else:
            logger.debug(f"torrent_to_link: No V2 hash available, returning V1 only")

        return magnet_links

    except Exception as e:
        logger.error(f"torrent_to_link: Error processing torrent file: {e}")
        logger.error(f"torrent_to_link: Torrent file type: {type(torrent_file)}")
        if hasattr(torrent_file, "__len__"):
            logger.error(f"torrent_to_link: Torrent file size: {len(torrent_file)}")
        if isinstance(torrent_file, bytes) and len(torrent_file) > 0:
            logger.error(f"torrent_to_link: First 50 bytes: {torrent_file[:50]}")
        return []


def get_torrent_hashes(torrent_file)-> list[str]:
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

        hashes = [v1_hash_hex]

        # V2 hash (SHA256)
        v2_hash = calculate_v2_hash(info)
        if v2_hash:
            v2_hash_hex = base64.b16encode(v2_hash).decode("utf-8").lower()
            hashes.append(v2_hash_hex)
            logger.debug(f"get_torrent_hashes: V2 hash: {v2_hash_hex}")
        else:
            logger.debug("get_torrent_hashes: No V2 hash found, this is a V1-only torrent")

        return hashes

    except Exception as e:
        logger.error(f"[get_torrent_hashes]: Error processing torrent file: {e}")
        return []


def get_hash(torrent_url: str) -> str:
    """从torrent URL或magnet链接中提取hash (支持v1和v2)

    Args:
        torrent_url: torrent文件URL或magnet链接

    Returns:
        提取的hash值，优先返回v1，如果没有v1则返回v2，提取失败返回空字符串
    """
    hash_pattern_dict = {
        # V1 hash pattern: urn:btih: + 40字符十六进制
        "magnet_v1_hex": re.compile(r"urn:btih:([a-fA-F0-9]{40})"),
        # V2 hash pattern: urn:btmh:1220 + 64字符十六进制SHA256
        "magnet_v2": re.compile(r"urn:btmh:1220([a-fA-F0-9]{64})"),
    }

    for pattern_name, hash_pattern in hash_pattern_dict.items():
        ans = re.search(hash_pattern, torrent_url)
        if ans:
            extracted_hash = ans[1]
            logger.debug(f"使用{pattern_name}提取hash: {extracted_hash}")
            # 直接返回小写十六进制
            return extracted_hash.lower()

    logger.warning(f"[Utils] Cannot find hash in {torrent_url}")
    return ""
