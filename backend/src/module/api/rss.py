from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .response import u_response

from module.models import RSSItem, RSSUpdate, Torrent
from module.rss import RSSEngine
from module.security.api import get_current_user, UNAUTHORIZED
from module.downloader import DownloadClient


router = APIRouter(prefix="/rss", tags=["rss"])


@router.get("", response_model=list[RSSItem])
async def get_rss(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        return engine.rss.search_all()


@router.post("/add", response_model=JSONResponse)
async def add_rss(rss: RSSItem, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.add_rss(rss.url, rss.name, rss.aggregate)
    return u_response(result)


@router.delete("/delete/{rss_id}", response_model=JSONResponse)
async def delete_rss(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.rss.delete(rss_id)
    if result:
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Delete RSS successfully.", "msg_zh": "删除 RSS 成功。"},
        )
    else:
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Delete RSS failed.", "msg_zh": "删除 RSS 失败。"},
        )


@router.patch("/update/{rss_id}", response_model=JSONResponse)
async def update_rss(
    rss_id: int, data: RSSUpdate, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.rss.update(rss_id, data)
    if result:
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Update RSS successfully.", "msg_zh": "更新 RSS 成功。"},
        )
    else:
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Update RSS failed.", "msg_zh": "更新 RSS 失败。"},
        )


@router.get("/refresh/all", response_model=JSONResponse)
async def refresh_all(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine, DownloadClient() as client:
        engine.refresh_rss(client)
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Refresh all RSS successfully.", "msg_zh": "刷新 RSS 成功。"},
        )


@router.get("/refresh/{rss_id}", response_model=JSONResponse)
async def refresh_rss(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine, DownloadClient() as client:
        engine.refresh_rss(client, rss_id)
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Refresh RSS successfully.", "msg_zh": "刷新 RSS 成功。"},
        )


@router.get("/torrent/{rss_id}", response_model=list[Torrent])
async def get_torrent(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        return engine.get_rss_torrents(rss_id)
