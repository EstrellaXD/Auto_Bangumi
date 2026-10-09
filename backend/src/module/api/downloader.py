import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from module.conf import settings
from module.database import Database
from module.database.bangumi import (
    build_save_path_index,
    match_bangumi_in_list,
    normalize_save_path,
)
from module.downloader import (
    DownloadClient,
    DownloaderPool,
    downloader_ids,
    list_torrents,
)
from module.models.config import DOWNLOADER_POINT
from module.security.api import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/downloader", tags=["downloader"])


class TorrentHashesRequest(BaseModel):
    hashes: list[str]
    # 种子所在的下载器实例；为空时为默认实例
    downloader_id: str | None = None


class TorrentDeleteRequest(TorrentHashesRequest):
    delete_files: bool = False


class TorrentTagRequest(BaseModel):
    """Request to tag a torrent with a bangumi ID."""

    hash: str
    bangumi_id: int
    downloader_id: str | None = None


def _client(downloader_id: str | None) -> DownloadClient:
    if downloader_id is not None and downloader_id not in downloader_ids():
        raise HTTPException(
            status_code=404, detail=f"Downloader instance {downloader_id} not found"
        )
    return DownloadClient(downloader_id)


@router.get("/instances", dependencies=[Depends(get_current_user)])
async def get_instances():
    """下载器实例列表（供规则 / 订阅选择下载器）。"""
    return {
        "default": settings.plugins.slots.downloader,
        "instances": [
            {"id": i.id, "provider": i.provider}
            for i in settings.plugins.instances
            if i.point == DOWNLOADER_POINT
        ],
    }


@router.get("/torrents", dependencies=[Depends(get_current_user)])
async def get_torrents():
    """所有下载器实例的种子（每条带 downloader_id）；不可用的实例跳过。"""
    torrents = await list_torrents()
    if torrents is None:
        raise HTTPException(status_code=503, detail="No downloader is reachable")
    return torrents


@router.get("/rename-conflicts", dependencies=[Depends(get_current_user)])
async def get_rename_conflicts():
    """List durable media rename conflicts awaiting user action."""

    async with Database() as db:
        rows = await db.rename_operation.list_conflicts()
    return [row.model_dump(mode="json") for row in rows]


@router.post(
    "/rename-conflicts/{operation_id}/retry",
    dependencies=[Depends(get_current_user)],
)
async def retry_rename_conflict(operation_id: int):
    """Clear one terminal conflict so the next rename pass revalidates it."""

    async with Database() as db:
        row = await db.rename_operation.get(operation_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Rename conflict not found")
        if row.state != "conflict" or row.kind != "conflict":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only non-destructive terminal conflicts can be retried; "
                    "replacement recovery state must be preserved"
                ),
            )
        await db.rename_operation.delete(operation_id)
    return {
        "status": True,
        "msg_en": "Rename conflict cleared; it will be revalidated",
        "msg_zh": "重命名冲突已清除，将在下一轮重新校验",
    }


@router.post("/torrents/pause", dependencies=[Depends(get_current_user)])
async def pause_torrents(req: TorrentHashesRequest):
    hashes = "|".join(req.hashes)
    async with _client(req.downloader_id) as client:
        await client.pause_torrent(hashes)
    return {"msg_en": "Torrents paused", "msg_zh": "种子已暂停"}


@router.post("/torrents/resume", dependencies=[Depends(get_current_user)])
async def resume_torrents(req: TorrentHashesRequest):
    hashes = "|".join(req.hashes)
    async with _client(req.downloader_id) as client:
        await client.resume_torrent(hashes)
    return {"msg_en": "Torrents resumed", "msg_zh": "种子已恢复"}


@router.post("/torrents/delete", dependencies=[Depends(get_current_user)])
async def delete_torrents(req: TorrentDeleteRequest):
    hashes = "|".join(req.hashes)
    async with _client(req.downloader_id) as client:
        ok = await client.delete_torrent(hashes, delete_files=req.delete_files)
    if not ok:
        return {
            "status": False,
            "msg_en": "Failed to delete torrents",
            "msg_zh": "删除种子失败",
        }
    return {"status": True, "msg_en": "Torrents deleted", "msg_zh": "种子已删除"}


@router.post("/torrents/tag", dependencies=[Depends(get_current_user)])
async def tag_torrent(req: TorrentTagRequest):
    """Tag a torrent with a bangumi ID for accurate offset lookup.

    This adds the 'ab:ID' tag to the torrent in qBittorrent, which allows
    the renamer to look up the correct episode/season offset.
    """
    # Verify bangumi exists
    async with Database() as db:
        bangumi = await db.bangumi.search_id(req.bangumi_id)
        if not bangumi:
            return {
                "status": False,
                "msg_en": f"Bangumi {req.bangumi_id} not found",
                "msg_zh": f"未找到番剧 {req.bangumi_id}",
            }

    tag = f"ab:{req.bangumi_id}"
    async with _client(req.downloader_id) as client:
        await client.add_tag(req.hash, tag)

    return {
        "status": True,
        "msg_en": f"Tagged torrent with {tag}",
        "msg_zh": f"已为种子添加标签 {tag}",
    }


@router.post("/torrents/tag/auto", dependencies=[Depends(get_current_user)])
async def auto_tag_torrents():
    """Auto-tag all untagged Bangumi torrents based on name/path matching.

    This helps fix torrents that were added before tagging was implemented.
    Returns the number of torrents tagged and any that couldn't be matched.
    """
    tagged_count = 0
    unmatched = []

    # Load the bangumi list once and match in memory instead of running up to
    # two DB queries (plus save_path fallback variations) per torrent.
    async with Database() as db:
        bangumi_list = await db.bangumi.search_all()
    save_path_index = build_save_path_index(bangumi_list)

    async with DownloaderPool() as downloaders:
        for instance_id in downloader_ids():
            try:
                client = await downloaders.get(instance_id)
            except ConnectionError as e:
                # 不可用的实例跳过，其它实例照常打标签
                logger.warning("Skip auto-tag on %s: %s", instance_id, e)
                continue
            # Get all Bangumi torrents
            torrents = await client.get_torrent_info(
                category="Bangumi", status_filter=None
            )

            for torrent in torrents:
                torrent_hash = torrent["hash"]
                torrent_name = torrent["name"]
                save_path = torrent["save_path"]
                tags = torrent.get("tags", "")

                # Skip if already has an ab:<id> link tag。必须精确匹配数字 id：
                # ab:renamed（处理完成标记）等同前缀标签不代表已关联番剧
                if re.search(r"ab:\d+", tags):
                    continue

                # First try by torrent name, then fall back to save_path
                bangumi = match_bangumi_in_list(torrent_name, bangumi_list)
                if not bangumi:
                    bangumi = save_path_index.get(normalize_save_path(save_path))

                if bangumi and not bangumi.deleted:
                    tag = f"ab:{bangumi.id}"
                    await client.add_tag(torrent_hash, tag)
                    tagged_count += 1
                    logger.info(
                        f"Tagged '{torrent_name[:50]}...' with {tag} "
                        f"(matched: {bangumi.official_title})"
                    )
                else:
                    unmatched.append(
                        {
                            "hash": torrent_hash,
                            "name": torrent_name,
                            "save_path": save_path,
                        }
                    )

    return {
        "status": True,
        "tagged_count": tagged_count,
        "unmatched_count": len(unmatched),
        "unmatched": unmatched[:10],  # Return first 10 unmatched for debugging
        "msg_en": f"Tagged {tagged_count} torrents, {len(unmatched)} could not be matched",
        "msg_zh": f"已标记 {tagged_count} 个种子，{len(unmatched)} 个无法匹配",
    }
