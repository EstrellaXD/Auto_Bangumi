from typing import Optional

from fastapi import APIRouter, Depends

from .response import u_response

from module.models import RSSItem, RSSUpdate
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


@router.post("/add")
async def add_rss(rss: RSSItem, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.add_rss(rss.url, rss.name, rss.aggregate)
    return u_response(result)


@router.delete("/delete/{rss_id}")
async def delete_rss(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.rss.delete(rss_id)


@router.patch("/update/{rss_id}")
async def update_rss(
    rss_id: int, data: RSSUpdate, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.rss.update(rss_id, data)


@router.get("/refresh/all")
async def refresh_all(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine, DownloadClient() as client:
        response = engine.refresh_rss(client)


@router.get("/refresh/{rss_id}")
async def refresh_rss(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine, DownloadClient() as client:
        response = engine.refresh_rss(client, rss_id)


@router.get("/torrent/{rss_id}")
async def get_torrent(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        return engine.get_rss_torrents(rss_id)
