from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from module.models import RSSItem
from module.rss import RSSEngine
from module.security import get_current_user
from module.downloader import DownloadClient


router = APIRouter(prefix="/rss", tags=["rss"])


@router.get("", response_model=list[RSSItem])
async def get_rss(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with RSSEngine() as engine:
        return engine.rss.search_all()


@router.delete("/delete/{id}")
async def delete_rss(_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with RSSEngine() as engine:
        result = engine.rss.delete(_id)
    if result:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": f"Success deleted {_id}"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": f"Failed to delete {_id}"},
        )


@router.put("/update/{id}")
async def update_rss(data: RSSItem, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with RSSEngine() as engine:
        result = engine.rss.update(data)
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with RSSEngine() as engine:
        response = engine.refresh_rss()
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


@router.get("/refresh/{id}")
async def refresh_rss(_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with RSSEngine() as engine:
        response = engine.refresh_rss(_id)
    if response:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": f"Success refresh {_id}"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": f"Failed to refresh {_id}"},
        )