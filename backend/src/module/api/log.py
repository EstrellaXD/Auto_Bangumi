import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

from module.conf import LOG_PATH
from module.models import APIResponse
from module.security.api import get_current_user

router = APIRouter(
    prefix="/log", tags=["log"], dependencies=[Depends(get_current_user)]
)


_TAIL_BYTES = 512 * 1024  # 512 KB


def _read_file_tail(path: Path, budget: int) -> tuple[bytes, bool, int]:
    """同步读取单个文件的最后 budget 字节（掐掉开头的半行）。

    返回 (数据, 是否截断, 读到的文件末尾偏移)。末尾偏移供 SSE 作为增量读取的
    起点。文件在 stat 与 open 之间被轮转改名时按空文件处理——抛异常会炸掉
    GET /log 与整条 SSE 流。
    """
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size > budget:
                f.seek(-budget, 2)
                data = f.read()
                end = f.tell()
                # Drop first partial line
                idx = data.find(b"\n")
                if idx != -1:
                    data = data[idx + 1 :]
                return data, True, end
            f.seek(0)
            data = f.read()
            return data, False, f.tell()
    except FileNotFoundError:
        return b"", False, 0


def _read_log_tail() -> tuple[bytes, int]:
    """读取日志尾部，供 asyncio.to_thread 在线程池中执行。

    轮转（RotatingFileHandler / 启动轮转）刚发生后 log.txt 近乎为空；
    仅当 log.txt 完整读入（未截断）且预算有剩时，把 log.txt.1 的尾部
    拼在前面，UI 不出现"日志突然清空"的断崖。截断读取时绝不拼接：
    中间内容已缺失，再贴更旧的备份会造成时间倒跳的假象。

    返回 (数据, log.txt 读到的末尾偏移)。
    """
    data, truncated, end = _read_file_tail(LOG_PATH, _TAIL_BYTES)
    if truncated:
        return data, end
    remaining = _TAIL_BYTES - len(data)
    if remaining > 0:
        backup_data, _, _ = _read_file_tail(
            LOG_PATH.with_name(f"{LOG_PATH.name}.1"), remaining
        )
        data = backup_data + data
    return data, end


@router.get("", response_model=str)
async def get_log():
    if LOG_PATH.exists():
        # Up to 512 KB of sync file I/O; keep it off the event loop.
        data, _ = await asyncio.to_thread(_read_log_tail)
        return Response(data, media_type="text/plain")
    else:
        return Response("Log file not found", status_code=404)


# 日志清空次数。原地截断后若在 SSE 下次读取前又长过旧偏移，大小比较发现不了；
# SSE 的读取游标比对这个计数，变化时重推整段
_clear_generation = 0


def _clear_log_files() -> None:
    """清空日志并删除轮转备份，否则拼接读取会把旧内容带回来。"""
    global _clear_generation
    LOG_PATH.write_text("")
    for backup in LOG_PATH.parent.glob(f"{LOG_PATH.name}.*"):
        backup.unlink(missing_ok=True)
    _clear_generation += 1


@router.post("/clear", response_model=APIResponse)
async def clear_log():
    if LOG_PATH.exists():
        # 截断 + 删除备份都是文件 I/O，与 get_log 一样放线程池执行
        await asyncio.to_thread(_clear_log_files)
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Log cleared successfully.", "msg_zh": "日志清除成功。"},
        )
    else:
        return JSONResponse(
            status_code=404,
            content={"msg_en": "Log file not found.", "msg_zh": "日志文件未找到。"},
        )
