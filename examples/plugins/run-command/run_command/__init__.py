"""示例插件：整理完成后运行外部命令。

订阅全部事件（``@subscribe("*")``），只对配置里列出的 ``torrent.organized`` /
``file.renamed`` 运行 ``command``。命令是参数列表，直接 ``exec``，不经过 shell，
所以参数里的空格、``$``、``;`` 都按字面传给程序。

事件字段以 ``AB_*`` 环境变量传给命令。整个参数恰好是 ``{字段}`` 时替换为字段值
（``{files}`` 展开为每个文件一个参数）；参数里夹带的占位符不替换，以免文件名被拼进
``sh -c`` 之类的脚本文本：

- 两个事件都有：``AB_EVENT``、``AB_BANGUMI_ID``（旧种子可能为空）、``AB_DOWNLOADER_ID``
- ``torrent.organized``：``AB_TORRENT_HASH``、``AB_FILES``（正片与字幕的路径，每行一个）
- ``file.renamed``：``AB_OLD_PATH``、``AB_NEW_PATH``、``AB_FILE_KIND``

路径是下载器视角。命令超时被杀掉；退出码非 0 时记录 stderr 末尾。命令的失败只记日志，
不抛给宿主：外部脚本出错不应让插件被熔断。
"""

import asyncio
import os
import re
import tempfile
from subprocess import DEVNULL

from pydantic import BaseModel, Field

from ab_sdk import Event, Plugin, subscribe
from ab_sdk.events import FileRenamed, TorrentOrganized

MAX_TIMEOUT = 3600
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class Options(BaseModel):
    command: list[str] = Field(
        default_factory=list,
        title="命令",
        description=(
            "程序及其参数，每项一个，如 /config/scripts/link.sh、{files}；不经过 shell，"
            "只替换整项为占位符的参数"
        ),
    )
    events: list[str] = Field(
        default_factory=lambda: [TorrentOrganized.kind],
        title="事件",
        description="在哪些事件后运行：torrent.organized、file.renamed",
    )
    timeout: int = Field(
        300, ge=1, le=MAX_TIMEOUT, title="超时（秒）", description="超时后杀掉命令"
    )


def event_fields(event: Event) -> dict[str, str] | None:
    """事件 → 字段（键为小写，不带 ``AB_`` 前缀）；不支持的事件返回 None。"""
    match event:
        case TorrentOrganized():
            specific = {
                "torrent_hash": event.torrent_hash,
                "files": "\n".join(f.path for f in event.files),
            }
        case FileRenamed():
            specific = {
                "old_path": event.old_path,
                "new_path": event.new_path,
                "file_kind": event.file_kind,
            }
        case _:
            return None
    bangumi_id = "" if event.bangumi_id is None else str(event.bangumi_id)
    return {
        "event": event.kind,
        "bangumi_id": bangumi_id,
        "downloader_id": event.downloader_id,
        **specific,
    }


def build_argv(command: list[str], fields: dict[str, str]) -> list[str]:
    """整项为 ``{字段}`` 的参数替换为字段值，``{files}`` 展开为每个文件一个参数。

    部分包含占位符的参数与未知的占位符原样保留。
    """
    argv: list[str] = []
    for arg in command:
        m = _PLACEHOLDER.fullmatch(arg)
        if m is None or m[1] not in fields:
            argv.append(arg)
        elif m[1] == "files":
            argv.extend(fields["files"].splitlines())
        else:
            argv.append(fields[m[1]])
    return argv


def build_env(fields: dict[str, str]) -> dict[str, str]:
    """继承宿主环境（否则子进程没有 PATH），再加上 ``AB_*``。

    宿主自己的 ``AB_*``（如 ``AB_DOWNLOADER_PASSWORD``）不传给命令。
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("AB_")}
    return {**env, **{f"AB_{k.upper()}": v for k, v in fields.items()}}


class RunCommand(Plugin[Options]):
    config_model = Options

    @subscribe("*", timeout=MAX_TIMEOUT + 10)
    async def on_event(self, event: Event) -> None:
        cfg = self.config
        if not cfg.command or event.kind not in cfg.events:
            return
        fields = event_fields(event)
        if fields is None:
            return
        argv = build_argv(cfg.command, fields)
        # stderr 写进临时文件而不是管道：命令留在后台的子进程继承 stderr 时，
        # 读管道要等到它们退出，命令本身早已结束也会被当成超时
        with tempfile.TemporaryFile() as err:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    stdin=DEVNULL,
                    stdout=DEVNULL,
                    stderr=err,
                    env=build_env(fields),
                )
            except OSError as e:
                self.ctx.log.warning("无法启动命令 %s：%s", argv[0], e)
                return
            try:
                async with asyncio.timeout(cfg.timeout):
                    await proc.wait()
            except TimeoutError:
                self.ctx.log.warning("命令 %s 超过 %s 秒，已终止", argv[0], cfg.timeout)
                return
            finally:
                # 超时或宿主取消处理时，不留下孤儿进程
                # ponytail: 只杀直接子进程；命令自己再派生的进程需由脚本负责
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
            err.seek(max(0, err.seek(0, os.SEEK_END) - 2000))
            tail = err.read().decode(errors="replace").strip()
        if proc.returncode:
            self.ctx.log.warning(
                "命令 %s 退出码 %s：%s", argv[0], proc.returncode, tail
            )
        else:
            self.ctx.log.info("命令 %s 已完成（%s）", argv[0], event.kind)
