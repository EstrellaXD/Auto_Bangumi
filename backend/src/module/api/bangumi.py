from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from module.manager import TorrentManager
from module.models import Bangumi
from module.security import get_current_user

router = APIRouter(prefix="/bangumi", tags=["bangumi"])


@router.get("/getAll", response_model=list[Bangumi])
async def get_all_data(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.search_all()


@router.get("/getData/{bangumi_id}", response_model=Bangumi)
async def get_data(bangumi_id: str, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.search_one(bangumi_id)


@router.post("/updateRule")
async def update_rule(data: Bangumi, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.update_rule(data)


@router.delete("/deleteRule/{bangumi_id}")
async def delete_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.delete_rule(bangumi_id, file)


@router.delete("/disableRule/{bangumi_id}")
async def disable_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.disable_rule(bangumi_id, file)


@router.get("/enableRule/{bangumi_id}")
async def enable_rule(bangumi_id: str, current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        return torrent.enable_rule(bangumi_id)


@router.get("/resetAll")
async def reset_all(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    with TorrentManager() as torrent:
        torrent.delete_all()
        return JSONResponse(status_code=200, content={"message": "OK"})
