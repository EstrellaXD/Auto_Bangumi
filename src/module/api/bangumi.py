import logging

from fastapi import Depends, HTTPException, status
from fastapi.responses import JSONResponse

from .log import router

from module.models import BangumiData
from module.manager import TorrentManager
from module.security import get_current_user

logger = logging.getLogger(__name__)

@router.get(
    "/api/v1/bangumi/getAll", tags=["bangumi"], response_model=list[BangumiData]
)
async def get_all_data(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.search_all()


@router.get(
    "/api/v1/bangumi/getData/{bangumi_id}", tags=["bangumi"], response_model=BangumiData
)
async def get_data(bangumi_id: str, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.search_one(bangumi_id)


@router.post("/api/v1/bangumi/updateRule", tags=["bangumi"])
async def update_rule(data: BangumiData, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        try:
            return torrent.update_rule(data)
        except Exception as e:
            logger.error(f"Failed to update rule: {e}")
            return JSONResponse(status_code=500, content={"message": "Failed"})


@router.delete("/api/v1/bangumi/deleteRule/{bangumi_id}", tags=["bangumi"])
async def delete_rule(bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.delete_rule(bangumi_id, file)


@router.delete("/api/v1/bangumi/disableRule/{bangumi_id}", tags=["bangumi"])
async def disable_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.disable_rule(bangumi_id, file)


@router.get("/api/v1/bangumi/enableRule/{bangumi_id}", tags=["bangumi"])
async def enable_rule(bangumi_id: str, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.enable_rule(bangumi_id)


@router.get("/api/v1/bangumi/resetAll", tags=["bangumi"])
async def reset_all(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        torrent.delete_all()
        return JSONResponse(status_code=200, content={"message": "OK"})
