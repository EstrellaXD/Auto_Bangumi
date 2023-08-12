from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

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
async def add_rss(
    url: str, name: Optional[str], combine: bool, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.add_rss(url, name, combine)
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
