from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from module.manager import TorrentManager
from module.models import APIResponse, Bangumi, BangumiUpdate
from module.security.api import UNAUTHORIZED, get_current_user

from .response import u_response


class OffsetSuggestion(BaseModel):
    suggested_offset: int
    reason: str

router = APIRouter(prefix="/bangumi", tags=["bangumi"])


def str_to_list(data: Bangumi):
    data.filter = data.filter.split(",")
    data.rss_link = data.rss_link.split(",")
    return data


@router.get(
    "/get/all", response_model=list[Bangumi], dependencies=[Depends(get_current_user)]
)
async def get_all_data():
    with TorrentManager() as manager:
        return manager.bangumi.search_all()


@router.get(
    "/get/{bangumi_id}",
    response_model=Bangumi,
    dependencies=[Depends(get_current_user)],
)
async def get_data(bangumi_id: str):
    with TorrentManager() as manager:
        resp = manager.search_one(bangumi_id)
    return resp


@router.patch(
    "/update/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def update_rule(
    bangumi_id: int,
    data: BangumiUpdate,
):
    with TorrentManager() as manager:
        resp = await manager.update_rule(bangumi_id, data)
    return u_response(resp)


@router.delete(
    path="/delete/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_rule(bangumi_id: str, file: bool = False):
    with TorrentManager() as manager:
        resp = await manager.delete_rule(bangumi_id, file)
    return u_response(resp)


@router.delete(
    path="/delete/many/",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_many_rule(bangumi_id: list, file: bool = False):
    with TorrentManager() as manager:
        for i in bangumi_id:
            resp = await manager.delete_rule(i, file)
    return u_response(resp)


@router.delete(
    path="/disable/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_rule(bangumi_id: str, file: bool = False):
    with TorrentManager() as manager:
        resp = await manager.disable_rule(bangumi_id, file)
    return u_response(resp)


@router.delete(
    path="/disable/many/",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_many_rule(bangumi_id: list, file: bool = False):
    with TorrentManager() as manager:
        for i in bangumi_id:
            resp = await manager.disable_rule(i, file)
    return u_response(resp)


@router.get(
    path="/enable/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def enable_rule(bangumi_id: str):
    with TorrentManager() as manager:
        resp = manager.enable_rule(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/poster/all",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_poster_all():
    with TorrentManager() as manager:
        resp = await manager.refresh_poster()
    return u_response(resp)

@router.get(
    path="/refresh/poster/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_poster_one(bangumi_id: int):
    with TorrentManager() as manager:
        resp = await manager.refind_poster(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/calendar",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_calendar():
    with TorrentManager() as manager:
        resp = await manager.refresh_calendar()
    return u_response(resp)


@router.get(
    "/reset/all", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def reset_all():
    with TorrentManager() as manager:
        manager.bangumi.delete_all()
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Reset all rules successfully.", "msg_zh": "重置所有规则成功。"},
        )


@router.patch(
    path="/archive/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def archive_rule(bangumi_id: int):
    """Archive a bangumi."""
    with TorrentManager() as manager:
        resp = manager.archive_rule(bangumi_id)
    return u_response(resp)


@router.patch(
    path="/unarchive/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def unarchive_rule(bangumi_id: int):
    """Unarchive a bangumi."""
    with TorrentManager() as manager:
        resp = manager.unarchive_rule(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/metadata",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_metadata():
    """Refresh TMDB metadata and auto-archive ended series."""
    with TorrentManager() as manager:
        resp = await manager.refresh_metadata()
    return u_response(resp)


@router.get(
    path="/suggest-offset/{bangumi_id}",
    response_model=OffsetSuggestion,
    dependencies=[Depends(get_current_user)],
)
async def suggest_offset(bangumi_id: int):
    """Suggest offset based on TMDB episode counts."""
    with TorrentManager() as manager:
        resp = await manager.suggest_offset(bangumi_id)
    return resp
