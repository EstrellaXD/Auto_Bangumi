"""示例插件：STRM 写入。

订阅 ``torrent.organized``。对事件里每个正片，去掉路径前缀 ``media_root`` 得到
相对路径 ``rel``，写 ``<strm_root>/<rel 换成 .strm>``，内容为 ``url_prefix + rel``。
Emby / Jellyfin 播放 ``.strm`` 时直接读取这个地址，媒体文件可以放在网盘或对象存储里。

- ``media_root`` 与事件路径同为下载器视角，所以不需要路径映射；``strm_root`` 是
  AutoBangumi 看到的本地目录。
- ``url_prefix`` 含 ``://`` 时按 URL 处理，路径的每一段做百分号编码；否则
  （本地路径）原样拼接。
- 投递为「至少一次」：内容相同就不重写；``url_prefix`` 改了会在下次事件时更新。
"""

import asyncio
import posixpath
from pathlib import Path
from urllib.parse import quote

from pydantic import BaseModel, Field

from ab_sdk import Plugin, subscribe
from ab_sdk.events import TorrentOrganized


class Options(BaseModel):
    strm_root: str = Field(
        "", title="STRM 目录", description="写入 .strm 的目录（AutoBangumi 中的路径）"
    )
    url_prefix: str = Field(
        "",
        title="地址前缀",
        description="拼在相对路径前，如 http://nas:8096/media/ 或本地路径 /mnt/cloud/",
    )
    media_root: str = Field(
        "",
        title="媒体根目录",
        description="下载器中要去掉的路径前缀，如 /downloads/Bangumi；其下的目录结构原样映射",
    )


def relative(path: str, media_root: str) -> str | None:
    """``path`` 不在 ``media_root`` 下（或就是 ``media_root`` 本身）时返回 None。"""
    root = media_root.rstrip("/")
    if not root or not path.startswith(root + "/"):
        return None
    rel = posixpath.normpath(path[len(root) + 1 :])
    # "." 会写出 <strm_root>.strm，落在 strm_root 之外
    if rel in (".", "..") or rel.startswith("../"):
        return None
    return rel


def strm_target(rel: str, options: Options) -> tuple[Path, str]:
    """(.strm 路径, 文件内容)。"""
    link = quote(rel, safe="/") if "://" in options.url_prefix else rel
    strm = Path(options.strm_root, *rel.split("/")).with_suffix(".strm")
    return strm, options.url_prefix + link


def write_strm(strm: Path, content: str) -> bool:
    """内容相同时不重写，返回 False。"""
    if strm.is_file() and strm.read_text(encoding="utf-8") == content:
        return False
    strm.parent.mkdir(parents=True, exist_ok=True)
    strm.write_text(content, encoding="utf-8")
    return True


class StrmWriter(Plugin[Options]):
    config_model = Options

    @subscribe(TorrentOrganized.kind)
    async def on_organized(self, event: TorrentOrganized) -> None:
        cfg = self.config
        if not cfg.strm_root or not cfg.url_prefix:
            return
        for file in event.files:
            if file.kind != "media":
                continue
            rel = relative(file.path, cfg.media_root)
            if rel is None:
                self.ctx.log.warning(
                    "%s 不在媒体根目录 %s 下", file.path, cfg.media_root
                )
                continue
            strm, content = strm_target(rel, cfg)
            if await asyncio.to_thread(write_strm, strm, content):
                self.ctx.log.info("已写入 %s", strm)
