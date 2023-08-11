from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
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
    if result:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": f"Success deleted {rss_id}"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": f"Failed to delete {rss_id}"},
        )


@router.patch("/update/{rss_id}")
async def update_rss(
    rss_id: int, data: RSSUpdate, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.rss.update(rss_id, data)
    if result:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": f"Success updated {data.item_path}"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": f"Failed to update {data.item_path}"},
        )


@router.get("/refresh/all")
async def refresh_all(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine, DownloadClient() as client:
        response = engine.refresh_rss(client)
    if response:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": f"Success refresh all rss"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": f"Failed to refresh all rss"},
        )


@router.get("/refresh/{rss_id}")
async def refresh_rss(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine, DownloadClient() as client:
        response = engine.refresh_rss(client, rss_id)
    if response:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": f"Success refresh {rss_id}"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": f"Failed to refresh {rss_id}"},
        )
