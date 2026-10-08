"""示例插件：NFO 写入。

订阅 ``torrent.organized``。对事件里每个正片 ``<名>.mkv``，在旁边写 ``<名>.nfo``
（Kodi / Jellyfin 的 ``episodedetails``）。季号、集数取自文件名中的 ``SxxEyy``
（内置重命名方式 pn / advance / template 的默认输出都含它），剧名取自
``Season N`` 的上一级目录。

- 事件里的路径是下载器视角：配置 ``path_from`` / ``path_to`` 换成 AutoBangumi
  看到的路径（两者都留空表示相同）。
- 投递为「至少一次」：``.nfo`` 已存在就跳过，所以重复事件和用户手改的文件都安全。
"""

import asyncio
import re
from pathlib import Path
from xml.sax.saxutils import escape

from pydantic import BaseModel, Field

from ab_sdk import Plugin, subscribe
from ab_sdk.events import TorrentOrganized

_EPISODE = re.compile(r"S(\d+)E(\d+(?:\.\d+)?)", re.IGNORECASE)


class Options(BaseModel):
    path_from: str = Field(
        "", title="下载器路径前缀", description="下载器看到的路径前缀；留空表示不映射"
    )
    path_to: str = Field(
        "", title="本地路径前缀", description="同一位置在 AutoBangumi 中的路径"
    )


def to_local(path: str, options: Options) -> Path:
    src = options.path_from.rstrip("/")
    if src and (path == src or path.startswith(src + "/")):
        return Path(options.path_to.rstrip("/") + path[len(src) :])
    return Path(path)


def nfo_xml(media: Path) -> str | None:
    """文件名里没有 SxxEyy 时返回 None（电影、特别篇等不写）。"""
    match = _EPISODE.search(media.stem)
    if match is None:
        return None
    show = media.parent.parent.name if media.parent.name.startswith("Season") else ""
    return (
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        "<episodedetails>\n"
        f"  <showtitle>{escape(show)}</showtitle>\n"
        f"  <season>{int(match.group(1))}</season>\n"
        f"  <episode>{match.group(2).lstrip('0') or '0'}</episode>\n"
        "</episodedetails>\n"
    )


def write_nfo(media: Path) -> bool:
    """已存在或不适用时返回 False。``x`` 模式保证不覆盖已有文件。"""
    content = nfo_xml(media)
    nfo = media.with_suffix(".nfo")
    if content is None or not media.parent.is_dir():
        return False
    try:
        with nfo.open("x", encoding="utf-8") as fh:
            fh.write(content)
    except FileExistsError:
        return False
    return True


class NfoWriter(Plugin[Options]):
    config_model = Options

    @subscribe(TorrentOrganized.kind)
    async def on_organized(self, event: TorrentOrganized) -> None:
        for file in event.files:
            if file.kind != "media":
                continue
            media = to_local(file.path, self.config)
            if await asyncio.to_thread(write_nfo, media):
                self.ctx.log.info("已写入 %s", media.with_suffix(".nfo"))
