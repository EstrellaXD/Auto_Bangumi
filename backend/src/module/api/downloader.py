from fastapi import APIRouter, Depends
from pydantic import BaseModel

from module.downloader import DownloadClient
from module.security.api import get_current_user

router = APIRouter(prefix="/downloader", tags=["downloader"])


class TorrentHashesRequest(BaseModel):
    hashes: list[str]


class TorrentDeleteRequest(BaseModel):
    hashes: list[str]
    delete_files: bool = False


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
