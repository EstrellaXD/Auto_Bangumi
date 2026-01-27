import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from module.database import Database
from module.downloader import DownloadClient
from module.security.api import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/downloader", tags=["downloader"])


class TorrentHashesRequest(BaseModel):
    hashes: list[str]


class TorrentDeleteRequest(BaseModel):
    hashes: list[str]
    delete_files: bool = False


class TorrentTagRequest(BaseModel):
    """Request to tag a torrent with a bangumi ID."""
    hash: str
    bangumi_id: int


@router.get("/torrents", dependencies=[Depends(get_current_user)])
async def get_torrents():
    async with DownloadClient() as client:
        return await client.get_torrent_info(category="Bangumi", status_filter=None)


@router.post("/torrents/pause", dependencies=[Depends(get_current_user)])
async def pause_torrents(req: TorrentHashesRequest):
    hashes = "|".join(req.hashes)
    async with DownloadClient() as client:
        await client.pause_torrent(hashes)
    return {"msg_en": "Torrents paused", "msg_zh": "种子已暂停"}


@router.post("/torrents/resume", dependencies=[Depends(get_current_user)])
async def resume_torrents(req: TorrentHashesRequest):
    hashes = "|".join(req.hashes)
    async with DownloadClient() as client:
        await client.resume_torrent(hashes)
    return {"msg_en": "Torrents resumed", "msg_zh": "种子已恢复"}


@router.post("/torrents/delete", dependencies=[Depends(get_current_user)])
async def delete_torrents(req: TorrentDeleteRequest):
    hashes = "|".join(req.hashes)
    async with DownloadClient() as client:
        await client.delete_torrent(hashes, delete_files=req.delete_files)
    return {"msg_en": "Torrents deleted", "msg_zh": "种子已删除"}


@router.post("/torrents/tag", dependencies=[Depends(get_current_user)])
async def tag_torrent(req: TorrentTagRequest):
    """Tag a torrent with a bangumi ID for accurate offset lookup.

    This adds the 'ab:ID' tag to the torrent in qBittorrent, which allows
    the renamer to look up the correct episode/season offset.
    """
    # Verify bangumi exists
    with Database() as db:
        bangumi = db.bangumi.search_id(req.bangumi_id)
        if not bangumi:
            return {
                "status": False,
                "msg_en": f"Bangumi {req.bangumi_id} not found",
                "msg_zh": f"未找到番剧 {req.bangumi_id}",
            }

    tag = f"ab:{req.bangumi_id}"
    async with DownloadClient() as client:
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

    async with DownloadClient() as client:
        # Get all Bangumi torrents
        torrents = await client.get_torrent_info(category="Bangumi", status_filter=None)

        with Database() as db:
            for torrent in torrents:
                torrent_hash = torrent["hash"]
                torrent_name = torrent["name"]
                save_path = torrent["save_path"]
                tags = torrent.get("tags", "")

                # Skip if already has ab: tag
                if "ab:" in tags:
                    continue

                # Try to match bangumi
                bangumi = None

                # First try by torrent name
                bangumi = db.bangumi.match_torrent(torrent_name)

                # Then try by save_path
                if not bangumi:
                    bangumi = db.bangumi.match_by_save_path(save_path)

                if bangumi and not bangumi.deleted:
                    tag = f"ab:{bangumi.id}"
                    await client.add_tag(torrent_hash, tag)
                    tagged_count += 1
                    logger.info(
                        f"[AutoTag] Tagged '{torrent_name[:50]}...' with {tag} "
                        f"(matched: {bangumi.official_title})"
                    )
                else:
                    unmatched.append({
                        "hash": torrent_hash,
                        "name": torrent_name,
                        "save_path": save_path,
                    })

    return {
        "status": True,
        "tagged_count": tagged_count,
        "unmatched_count": len(unmatched),
        "unmatched": unmatched[:10],  # Return first 10 unmatched for debugging
        "msg_en": f"Tagged {tagged_count} torrents, {len(unmatched)} could not be matched",
        "msg_zh": f"已标记 {tagged_count} 个种子，{len(unmatched)} 个无法匹配",
    }
