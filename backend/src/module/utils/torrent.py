import base64
import hashlib
from urllib.parse import quote

import bencodepy


async def torrent_to_link(torrent_file):
    torrent_info = bencodepy.decode(torrent_file)

    # 获取 info 字段并进行 bencode 编码
    info = torrent_info[b"info"]
    encoded_info = bencodepy.encode(info)

    # 计算 info_hash (SHA1 hash of the encoded info dictionary)
    info_hash = hashlib.sha1(encoded_info).digest()

    # 将 hash 转换为磁力链接格式
    info_hash_hex = base64.b16encode(info_hash).decode("utf-8").lower()

    # # 获取文件名
    # name = torrent_info.get(b"info", {}).get(b"name", b"").decode("utf-8")

    # 构建磁力链接
    magnet_link = f"magnet:?xt=urn:btih:{info_hash_hex}"
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
    return magnet_link
