import base64
import hashlib
from urllib.parse import quote
import logging
import re

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


def base32_to_hex(base32_hash: str) -> str:
    """将Base32格式的hash转换为十六进制
    
    Args:
        base32_hash: 32字符的Base32编码hash
        
    Returns:
        40字符的小写十六进制hash，转换失败返回空字符串
    """
    try:
        # Base32解码
        decoded = base64.b32decode(base32_hash)
        return decoded.hex().lower()
    except Exception as e:
        logger.warning(f"Base32转换失败: {base32_hash}, error: {e}")
        return ""


def hex_to_base32(hex_hash: str) -> str:
    """将十六进制hash转换为Base32格式
    
    Args:
        hex_hash: 40字符的十六进制hash
        
    Returns:
        32字符的Base32编码hash，转换失败返回空字符串
    """
    try:
        # 十六进制转字节
        hex_bytes = bytes.fromhex(hex_hash)
        # 编码为Base32，去掉填充符
        return base64.b32encode(hex_bytes).decode().rstrip('=')
    except Exception as e:
        logger.warning(f"十六进制转Base32失败: {hex_hash}, error: {e}")
        return ""


def normalize_hash(hash_value: str) -> str:
    """标准化hash格式，统一转换为40字符小写十六进制
    
    Args:
        hash_value: 输入的hash值，可能是40字符十六进制或32字符Base32
        
    Returns:
        标准化的40字符小写十六进制hash
    """
    if not hash_value:
        return ""
    
    hash_value = hash_value.strip()
    
    # 40字符十六进制格式
    if len(hash_value) == 40 and re.match(r'^[a-fA-F0-9]{40}$', hash_value):
        return hash_value.lower()
    
    # 32字符Base32格式 (DMHY等站点常用)
    if len(hash_value) == 32 and re.match(r'^[A-Z0-9]{32}$', hash_value):
        hex_hash = base32_to_hex(hash_value)
        if hex_hash:
            logger.debug(f"将Base32 hash {hash_value} 转换为十六进制: {hex_hash}")
            return hex_hash
    
    # 其他情况，尝试转小写
    normalized = hash_value.lower()
    logger.debug(f"hash标准化: {hash_value} -> {normalized}")
    return normalized


def get_hash(torrent_url: str) -> str | None:
    """从torrent URL或magnet链接中提取hash
    
    Args:
        torrent_url: torrent文件URL或magnet链接
        
    Returns:
        提取的hash值，提取失败返回空字符串
    """
    hash_pattern_dict = {
        "magnet_hash_pattern": re.compile(r"\b([a-fA-F0-9]{40})\b"),
        # "torrent_hash_pattern": re.compile(r"/([a-fA-F0-9]{7,40})\.torrent"),
        "dmhy_hash_pattern": re.compile(r"urn:btih:([A-Z0-9]{32})"),
    }
    
    for pattern_name, hash_pattern in hash_pattern_dict.items():
        ans = re.search(hash_pattern, torrent_url)
        if ans:
            extracted_hash = ans[1]
            logger.debug(f"使用{pattern_name}提取hash: {extracted_hash}")
            # 使用normalize_hash标准化hash格式
            normalized_hash = normalize_hash(extracted_hash)
            if normalized_hash != extracted_hash:
                logger.debug(f"hash已标准化: {extracted_hash} -> {normalized_hash}")
            
            return normalized_hash
    
    logger.warning(f"[Utils] Cannot find hash in {torrent_url}")
    return ""
