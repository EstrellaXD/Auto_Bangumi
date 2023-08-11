from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .response import u_response

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
        resp = manager.update_rule(bangumi_id, data)
    return u_response(resp)


@router.delete("/delete/{bangumi_id}")
async def delete_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        resp = manager.delete_rule(bangumi_id, file)
    return u_response(resp)


@router.delete("/delete/many/{bangumi_id}")
async def delete_many_rule(
    bangumi_id: list, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        for i in bangumi_id:
            manager.delete_rule(i, file)


@router.delete("/disable/{bangumi_id}")
async def disable_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        return manager.disable_rule(bangumi_id, file)


@router.delete("/disable/many/{bangumi_id}")
async def disable_many_rule(
    bangumi_id: list, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        for i in bangumi_id:
            manager.disable_rule(i, file)


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
