from .log import router

from module.models import BangumiData
from module.database import BangumiDatabase
from module.manager import TorrentManager


@router.get("/api/v1/bangumi/getAll", tags=["bangumi"], response_model=list[BangumiData])
async def get_all_data():
    with TorrentManager() as torrent:
        return torrent.search_all()


@router.get("/api/v1/bangumi/getData/{bangumi_id}", tags=["bangumi"], response_model=BangumiData)
async def get_data(bangumi_id: str):
    with TorrentManager() as torrent:
        return torrent.search_data(bangumi_id)


@router.post("/api/v1/bangumi/updateData", tags=["bangumi"])
async def update_data(data: BangumiData):
    with TorrentManager() as torrent:
        return torrent.update_rule(data)


@router.delete("/api/v1/bangumi/deleteData/{bangumi_id}", tags=["bangumi"])
async def delete_data(bangumi_id: str):
    with TorrentManager() as torrent:
        return torrent.delete_data(bangumi_id)


@router.delete("/api/v1/bangumi/deleteRule/{bangumi_id}", tags=["bangumi"])
async def delete_rule(bangumi_id: str, file: bool = False):
    with TorrentManager() as torrent:
        return torrent.delete_rule(bangumi_id, file)


@router.get("/api/v1/bangumi/resetAll", tags=["bangumi"])
async def reset_all():
    with BangumiDatabase() as database:
        database.delete_all()
        return {"status": "ok"}
