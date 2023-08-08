from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from module.manager import TorrentManager
from module.models import Bangumi, BangumiUpdate
from module.security.api import get_current_user, UNAUTHORIZED

router = APIRouter(prefix="/bangumi", tags=["bangumi"])


@router.get("/get/all", response_model=list[Bangumi])
async def get_all_data(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        return manager.bangumi.search_all()


@router.get("/get/{bangumi_id}", response_model=Bangumi)
async def get_data(bangumi_id: str, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        return manager.search_one(bangumi_id)


@router.patch("/update/{bangumi_id}")
async def update_rule(
    bangumi_id: int, data: BangumiUpdate, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        return manager.update_rule(bangumi_id, data)


@router.delete("/delete/{bangumi_id}")
async def delete_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        return manager.delete_rule(bangumi_id, file)


@router.delete("/disable/{bangumi_id}")
async def disable_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        return manager.disable_rule(bangumi_id, file)


@router.get("/enable/{bangumi_id}")
async def enable_rule(bangumi_id: str, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        return manager.enable_rule(bangumi_id)


@router.get("/reset/all")
async def reset_all(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        manager.bangumi.delete_all()
        return JSONResponse(status_code=200, content={"message": "OK"})
