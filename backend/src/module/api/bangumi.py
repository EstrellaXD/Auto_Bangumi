from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .response import u_response

from module.manager import TorrentManager
from module.models import Bangumi, BangumiUpdate, APIResponse
from module.security.api import get_current_user, UNAUTHORIZED

router = APIRouter(prefix="/bangumi", tags=["bangumi"])


def str_to_list(data: Bangumi):
    data.filter = data.filter.split(",")
    data.rss_link = data.rss_link.split(",")
    return data


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
        resp = manager.search_one(bangumi_id)
    return resp


@router.patch("/update/{bangumi_id}", response_model=APIResponse)
async def update_rule(
    bangumi_id: int, data: BangumiUpdate, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        resp = manager.update_rule(bangumi_id, data)
    return u_response(resp)


@router.delete(path="/delete/{bangumi_id}", response_model=APIResponse)
async def delete_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        resp = manager.delete_rule(bangumi_id, file)
    return u_response(resp)


@router.delete(path="/delete/many/", response_model=APIResponse)
async def delete_many_rule(
    bangumi_id: list, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        for i in bangumi_id:
            resp = manager.delete_rule(i, file)
    return u_response(resp)


@router.delete(path="/disable/{bangumi_id}", response_model=APIResponse)
async def disable_rule(
    bangumi_id: str, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        resp = manager.disable_rule(bangumi_id, file)
    return u_response(resp)


@router.delete(path="/disable/many/", response_model=APIResponse)
async def disable_many_rule(
    bangumi_id: list, file: bool = False, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        for i in bangumi_id:
            resp = manager.disable_rule(i, file)
    return u_response(resp)


@router.get(path="/enable/{bangumi_id}", response_model=APIResponse)
async def enable_rule(bangumi_id: str, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        resp = manager.enable_rule(bangumi_id)
    return u_response(resp)


@router.get("/reset/all", response_model=APIResponse)
async def reset_all(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with TorrentManager() as manager:
        manager.bangumi.delete_all()
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Reset all rules successfully.", "msg_zh": "重置所有规则成功。"},
        )
