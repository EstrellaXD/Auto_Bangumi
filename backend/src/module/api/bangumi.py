from typing import Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from module.conf import settings
from module.database import Database, get_db
from module.downloader import DownloadClient
from module.manager import Renamer, TorrentManager
from module.models import APIResponse, Bangumi, BangumiUpdate, ResponseModel, Torrent
from module.parser.analyser.offset_detector import (
    OffsetSuggestion as DetectorSuggestion,
)
from module.parser.analyser.offset_detector import detect_offset_mismatch
from module.parser.analyser.tmdb_parser import tmdb_parser
from module.security.api import get_current_user

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


class SetWeekdayRequest(BaseModel):
    weekday: Optional[int] = None  # 0-6 for Mon-Sun, None to reset


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


@router.get(
    "/get/all", response_model=list[Bangumi], dependencies=[Depends(get_current_user)]
)
async def get_all_data(db: Database = Depends(get_db)):
    return await db.bangumi.search_all()


@router.get(
    "/get/{bangumi_id}",
    response_model=Bangumi,
    dependencies=[Depends(get_current_user)],
)
async def get_data(bangumi_id: int, db: Database = Depends(get_db)):
    manager = TorrentManager(db)
    resp = await manager.search_one(bangumi_id)
    return resp


@router.patch(
    "/update/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def update_rule(
    bangumi_id: int,
    data: BangumiUpdate,
    db: Database = Depends(get_db),
):
    manager = TorrentManager(db)
    resp = await manager.update_rule(bangumi_id, data)
    return u_response(resp)


def _empty_id_list_response() -> JSONResponse:
    return u_response(
        ResponseModel(
            status_code=400,
            status=False,
            msg_en="No bangumi id provided.",
            msg_zh="未提供番剧 id。",
        )
    )


def _aggregate_response(
    action_en: str, action_zh: str, results: list[ResponseModel]
) -> JSONResponse:
    succeeded = sum(1 for r in results if r.status)
    all_ok = succeeded == len(results)
    return u_response(
        ResponseModel(
            status_code=200 if all_ok else 500,
            status=all_ok,
            msg_en=f"{action_en} {succeeded}/{len(results)} rules.",
            msg_zh=f"已{action_zh} {succeeded}/{len(results)} 条规则。",
        )
    )


# Registered before /delete/{bangumi_id} so "many" is never captured as an id.
@router.post(
    path="/delete/many",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_many_rule(
    bangumi_id: list[int], file: bool = False, db: Database = Depends(get_db)
):
    if not bangumi_id:
        return _empty_id_list_response()
    manager = TorrentManager(db)
    results = [await manager.delete_rule(i, file) for i in bangumi_id]
    return _aggregate_response("Deleted", "删除", results)


@router.delete(
    path="/delete/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_rule(
    bangumi_id: int, file: bool = False, db: Database = Depends(get_db)
):
    manager = TorrentManager(db)
    resp = await manager.delete_rule(bangumi_id, file)
    return u_response(resp)


# Registered before /disable/{bangumi_id} so "many" is never captured as an id.
@router.post(
    path="/disable/many",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_many_rule(
    bangumi_id: list[int], file: bool = False, db: Database = Depends(get_db)
):
    if not bangumi_id:
        return _empty_id_list_response()
    manager = TorrentManager(db)
    results = [await manager.disable_rule(i, file) for i in bangumi_id]
    return _aggregate_response("Disabled", "禁用", results)


@router.post(
    path="/disable/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_rule(
    bangumi_id: int, file: bool = False, db: Database = Depends(get_db)
):
    manager = TorrentManager(db)
    resp = await manager.disable_rule(bangumi_id, file)
    return u_response(resp)


@router.post(
    path="/enable/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def enable_rule(bangumi_id: int, db: Database = Depends(get_db)):
    manager = TorrentManager(db)
    resp = await manager.enable_rule(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/poster/all",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_poster_all(db: Database = Depends(get_db)):
    manager = TorrentManager(db)
    resp = await manager.refresh_poster()
    return u_response(resp)


@router.get(
    path="/refresh/poster/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_poster_one(bangumi_id: int, db: Database = Depends(get_db)):
    manager = TorrentManager(db)
    resp = await manager.refind_poster(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/calendar",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_calendar(db: Database = Depends(get_db)):
    manager = TorrentManager(db)
    resp = await manager.refresh_calendar()
    return u_response(resp)


@router.post(
    "/reset/all", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def reset_all(db: Database = Depends(get_db)):
    await db.bangumi.delete_all()
    return JSONResponse(
        status_code=200,
        content={
            "msg_en": "Reset all rules successfully.",
            "msg_zh": "重置所有规则成功。",
        },
    )


@router.patch(
    path="/archive/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def archive_rule(bangumi_id: int, db: Database = Depends(get_db)):
    """Archive a bangumi."""
    manager = TorrentManager(db)
    resp = await manager.archive_rule(bangumi_id)
    return u_response(resp)


@router.patch(
    path="/unarchive/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def unarchive_rule(bangumi_id: int, db: Database = Depends(get_db)):
    """Unarchive a bangumi."""
    manager = TorrentManager(db)
    resp = await manager.unarchive_rule(bangumi_id)
    return u_response(resp)


@router.get(
    path="/refresh/metadata",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_metadata(db: Database = Depends(get_db)):
    """Refresh TMDB metadata and auto-archive ended series."""
    manager = TorrentManager(db)
    resp = await manager.refresh_metadata()
    return u_response(resp)


@router.get(
    path="/suggest-offset/{bangumi_id}",
    response_model=OffsetSuggestion,
    dependencies=[Depends(get_current_user)],
)
async def suggest_offset(bangumi_id: int, db: Database = Depends(get_db)):
    """Suggest offset based on TMDB episode counts."""
    manager = TorrentManager(db)
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
                # None means "no episode offset needed" (see offset_detector).
                episode_offset=suggestion.episode_offset or 0,
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
    async with Database() as db:
        success = await db.bangumi.clear_needs_review(bangumi_id)

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


async def _trigger_rename() -> None:
    """Run a rename pass so applied offsets take effect immediately."""
    async with DownloadClient() as client:
        renamer = Renamer(client)
        await renamer.rename()


# Registered before /apply-offset/{bangumi_id} so "many" is never captured as an id.
@router.post(
    path="/apply-offset/many",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def apply_offset_many(bangumi_id: list[int]):
    """Apply suggested offsets for multiple bangumi and trigger a rename pass."""
    if not bangumi_id:
        return _empty_id_list_response()

    async with Database() as db:
        results = [await db.bangumi.apply_offset(i) for i in bangumi_id]

    succeeded = sum(1 for r in results if r)
    if succeeded:
        await _trigger_rename()

    all_ok = succeeded == len(results)
    return u_response(
        ResponseModel(
            status_code=200 if all_ok else 500,
            status=all_ok,
            msg_en=f"Applied offset for {succeeded}/{len(results)} bangumi.",
            msg_zh=f"已为 {succeeded}/{len(results)} 部番剧应用偏移量。",
        )
    )


@router.post(
    path="/apply-offset/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def apply_offset(bangumi_id: int):
    """Apply the suggested season/episode offset and trigger a rename pass."""
    async with Database() as db:
        success = await db.bangumi.apply_offset(bangumi_id)

    if success:
        await _trigger_rename()
        return JSONResponse(
            status_code=200,
            content={
                "status": True,
                "msg_en": "Offset applied.",
                "msg_zh": "已应用偏移量。",
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
    async with Database() as db:
        return await db.bangumi.get_needs_review()


@router.patch(
    path="/{bangumi_id}/weekday",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def set_weekday(bangumi_id: int, request: SetWeekdayRequest):
    """Manually set the broadcast weekday for a bangumi."""
    if request.weekday is not None and not (0 <= request.weekday <= 6):
        return JSONResponse(
            status_code=400,
            content={
                "status": False,
                "msg_en": "Weekday must be 0-6 (Mon-Sun) or null.",
                "msg_zh": "星期必须是 0-6（周一至周日）或空。",
            },
        )
    async with Database() as db:
        success = await db.bangumi.set_weekday(bangumi_id, request.weekday)
    if success:
        action = (
            f"weekday {request.weekday}" if request.weekday is not None else "unknown"
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": True,
                "msg_en": f"Set bangumi to {action}.",
                "msg_zh": f"已设置放送日为 {action}。",
            },
        )
    return JSONResponse(
        status_code=404,
        content={
            "status": False,
            "msg_en": f"Bangumi {bangumi_id} not found.",
            "msg_zh": f"未找到番剧 {bangumi_id}。",
        },
    )


# ---------------------------------------------------------------------------
# Torrent management (#1020)
# 孤儿种子：bangumi_id 为 NULL 的种子记录（解析失败、取消关联或脏数据残留）。
# /torrents/orphans 使用字面量路径，注册在 /{bangumi_id}/torrents 之前以避免歧义。
# ---------------------------------------------------------------------------


@router.get(
    path="/torrents/orphans",
    response_model=list[Torrent],
    dependencies=[Depends(get_current_user)],
)
async def get_orphan_torrents(db: Database = Depends(get_db)):
    """List all torrent records not associated with any bangumi."""
    return await db.torrent.search_orphans()


@router.get(
    path="/torrents/orphans/count",
    response_model=int,
    dependencies=[Depends(get_current_user)],
)
async def get_orphan_torrent_count(db: Database = Depends(get_db)):
    """Count torrent records not associated with any bangumi."""
    return await db.torrent.count_orphans()


@router.delete(
    path="/torrents/orphans",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_orphan_torrents(db: Database = Depends(get_db)):
    """Delete all torrent records not associated with any bangumi."""
    count = await db.torrent.delete_orphans()
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en=f"Deleted {count} orphan torrents.",
            msg_zh=f"已删除 {count} 条未匹配种子。",
        )
    )


@router.delete(
    path="/torrents/orphans/{torrent_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_orphan_torrent(torrent_id: int, db: Database = Depends(get_db)):
    """Delete a single orphan torrent record."""
    torrent = await db.torrent.search(torrent_id)
    if torrent is None or torrent.bangumi_id is not None:
        return JSONResponse(
            status_code=404,
            content={
                "status": False,
                "msg_en": f"Orphan torrent {torrent_id} not found.",
                "msg_zh": f"未找到孤儿种子 {torrent_id}。",
            },
        )
    await db.torrent.delete_obj(torrent)
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en=f"Deleted torrent {torrent_id}.",
            msg_zh=f"已删除种子 {torrent_id}。",
        )
    )


@router.get(
    path="/{bangumi_id}/torrents",
    response_model=list[Torrent],
    dependencies=[Depends(get_current_user)],
)
async def get_bangumi_torrents(bangumi_id: int, db: Database = Depends(get_db)):
    """List all torrent records associated with a bangumi."""
    return await db.torrent.search_by_bangumi_id(bangumi_id)


@router.delete(
    path="/{bangumi_id}/torrents",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_bangumi_torrents(bangumi_id: int, db: Database = Depends(get_db)):
    """Delete all torrent records associated with a bangumi."""
    count = await db.torrent.delete_by_bangumi_id(bangumi_id)
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en=f"Deleted {count} torrents for bangumi {bangumi_id}.",
            msg_zh=f"已删除番剧 {bangumi_id} 的 {count} 条种子。",
        )
    )


@router.delete(
    path="/{bangumi_id}/torrents/{torrent_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_bangumi_torrent(
    bangumi_id: int, torrent_id: int, db: Database = Depends(get_db)
):
    """Delete a single torrent record under a bangumi."""
    torrent = await db.torrent.search(torrent_id)
    if torrent is None or torrent.bangumi_id != bangumi_id:
        return JSONResponse(
            status_code=404,
            content={
                "status": False,
                "msg_en": f"Torrent {torrent_id} not found under bangumi {bangumi_id}.",
                "msg_zh": f"番剧 {bangumi_id} 下未找到种子 {torrent_id}。",
            },
        )
    await db.torrent.delete_obj(torrent)
    return u_response(
        ResponseModel(
            status=True,
            status_code=200,
            msg_en=f"Deleted torrent {torrent_id}.",
            msg_zh=f"已删除种子 {torrent_id}。",
        )
    )
