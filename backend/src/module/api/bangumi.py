from typing import Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from module.conf import settings
from module.database import Database
from module.manager import TorrentManager
from module.models import APIResponse, Bangumi, BangumiUpdate
from module.parser.analyser.offset_detector import (
    OffsetSuggestion as DetectorSuggestion,
)
from module.parser.analyser.offset_detector import detect_offset_mismatch
from module.parser.analyser.tmdb_parser import tmdb_parser
from module.security.api import UNAUTHORIZED, get_current_user

from .response import u_response


class OffsetSuggestion(BaseModel):
    """Legacy offset suggestion model."""
    suggested_offset: int
    reason: str


class TMDBSummary(BaseModel):
    """Summary of TMDB data for display."""
    title: str
    total_seasons: int
    season_episode_counts: dict[int, int]
    status: Optional[str]
    virtual_season_starts: Optional[dict[int, list[int]]] = None  # {1: [1, 29], ...}


class OffsetSuggestionDetail(BaseModel):
    """Detailed offset suggestion from detector."""
    season_offset: int
    episode_offset: int
    reason: str
    confidence: Literal["high", "medium", "low"]


class DetectOffsetRequest(BaseModel):
    """Request body for detect-offset endpoint."""
    title: str
    parsed_season: int
    parsed_episode: int


class DetectOffsetResponse(BaseModel):
    """Response for detect-offset endpoint."""
    has_mismatch: bool
    suggestion: Optional[OffsetSuggestionDetail]
    tmdb_info: Optional[TMDBSummary]

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


@router.post(
    path="/detect-offset",
    response_model=DetectOffsetResponse,
    dependencies=[Depends(get_current_user)],
)
async def detect_offset(request: DetectOffsetRequest):
    """Detect season/episode mismatch with TMDB data.

    Called by frontend before adding/subscribing to check if offsets are needed.
    """
    language = settings.rss_parser.language
    tmdb_info = await tmdb_parser(request.title, language)

    if not tmdb_info:
        return DetectOffsetResponse(
            has_mismatch=False,
            suggestion=None,
            tmdb_info=None,
        )

    # Detect mismatch
    suggestion = detect_offset_mismatch(
        parsed_season=request.parsed_season,
        parsed_episode=request.parsed_episode,
        tmdb_info=tmdb_info,
    )

    # Build TMDB summary
    tmdb_summary = TMDBSummary(
        title=tmdb_info.title,
        total_seasons=tmdb_info.last_season,
        season_episode_counts=tmdb_info.season_episode_counts or {},
        status=tmdb_info.series_status,
        virtual_season_starts=tmdb_info.virtual_season_starts,
    )

    if suggestion:
        return DetectOffsetResponse(
            has_mismatch=True,
            suggestion=OffsetSuggestionDetail(
                season_offset=suggestion.season_offset,
                episode_offset=suggestion.episode_offset,
                reason=suggestion.reason,
                confidence=suggestion.confidence,
            ),
            tmdb_info=tmdb_summary,
        )

    return DetectOffsetResponse(
        has_mismatch=False,
        suggestion=None,
        tmdb_info=tmdb_summary,
    )


@router.post(
    path="/dismiss-review/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def dismiss_review(bangumi_id: int):
    """Clear the needs_review flag for a bangumi after user reviews."""
    with Database() as db:
        success = db.bangumi.clear_needs_review(bangumi_id)

    if success:
        return JSONResponse(
            status_code=200,
            content={
                "status": True,
                "msg_en": "Review dismissed.",
                "msg_zh": "已取消检查标记。",
            },
        )
    else:
        return JSONResponse(
            status_code=404,
            content={
                "status": False,
                "msg_en": f"Bangumi {bangumi_id} not found.",
                "msg_zh": f"未找到番剧 {bangumi_id}。",
            },
        )


@router.get(
    path="/needs-review",
    response_model=list[Bangumi],
    dependencies=[Depends(get_current_user)],
)
async def get_needs_review():
    """Get all bangumi that need review for offset mismatch."""
    with Database() as db:
        return db.bangumi.get_needs_review()
