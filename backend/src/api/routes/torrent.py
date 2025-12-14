import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.util.concurrency import asyncio

from module.database import Database, engine
from module.manager import BangumiManager, TorrentManager
from models import APIResponse, Bangumi, ResponseModel, Torrent
from module.security.api import get_current_user

from .response import u_response

router = APIRouter(prefix="/torrent", tags=["torrent"])
logger = logging.getLogger(__name__)


@router.get(
    "/get_all",
    response_model=list[Torrent],
    dependencies=[Depends(get_current_user)],
)
async def manage_bangumi(_id: int):
    """
    管理对应 Bangumi 的规则
    """
    try:
        resp = await TorrentManager().fetch_all_bangumi_torrents(_id)
        return resp
    except Exception as e:
        logger.error(f"[Bangumi] Error managing bangumi: {e}")
        return []


@router.post(
    "/delete",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_torrent(url: str):
    """
    删除对应的种子
    """
    try:
        resp = await TorrentManager().delete_torrent(url)
        if resp:
            resp = ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Delete torrent for {url}",
                msg_zh=f"删除 {url} 的种子",
            )
        else:
            resp = ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find torrent with url {url}",
                msg_zh=f"无法找到 url 为 {url} 的种子",
            )
        return resp
    except Exception as e:
        logger.error(f"[Bangumi] Error deleting torrent: {e}")
        return ResponseModel(
            status_code=500,
            status=False,
            msg_en="Internal server error",
            msg_zh="服务器内部错误",
        )


@router.post("/disable", response_model=APIResponse, dependencies=[Depends(get_current_user)])
async def disable_torrent(url: str, name, _id: int):
    """
    禁用对应的种子
    """
    try:
        await TorrentManager().disable_torrent(url, name, _id)
        return ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Successfully disabled torrent with url {url}",
            msg_zh=f"成功禁用 url 为 {url} 的种子",
        )
    except Exception as e:
        logger.error(f"[Bangumi] Error disabling torrent: {e}")
        return ResponseModel(
            status_code=500,
            status=False,
            msg_en="Internal server error",
            msg_zh="服务器内部错误",
        )


@router.post(
    "/download",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def download_bangumi(_id: int, torrent: Torrent):
    """
    手动下载对应 Bangumi 的种子
    """
    try:
        resp = TorrentManager().download_torrent(_id, torrent)
        if resp:
            resp = ResponseModel(
                status_code=200,
                status=True,
                msg_en=f"Download torrent for {_id}",
                msg_zh=f"下载 {_id} 的种子",
            )
        else:
            resp = ResponseModel(
                status_code=406,
                status=False,
                msg_en=f"Can't find id {_id}",
                msg_zh=f"无法找到 id {_id}",
            )
        return resp
    except Exception as e:
        logger.error(f"[Bangumi] Error downloading bangumi: {e}")
        return ResponseModel(
            status_code=500,
            status=False,
            msg_en="Internal server error",
            msg_zh="服务器内部错误",
        )
