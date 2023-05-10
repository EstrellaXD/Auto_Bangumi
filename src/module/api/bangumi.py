from .api import router

from module.models import BangumiData
from module.database import BangumiDatabase
from module.manager import TorrentManager


@router.get("/api/v1/bangumi/getAll", tags=["bangumi"], response_model=list[BangumiData])
async def get_all_data():
    with BangumiDatabase() as database:
        return database.search_all()


@router.get("/api/v1/bangumi/getData/{bangumi_id}", tags=["bangumi"], response_model=BangumiData)
async def get_data(bangumi_id: str):
    with BangumiDatabase() as database:
        data = database.search_id(int(bangumi_id))
        if data:
            return data
        else:
            return {"": "data not exist"}


@router.post("/api/v1/bangumi/updateData", tags=["bangumi"])
async def update_data(data: BangumiData):
    with BangumiDatabase() as database:
        updated = database.update_one(data)
    if updated:
        with TorrentManager() as torrent:
            torrent.set_new_path(data)
        return {"status": "ok"}
    else:
        return {"status": "data not exist"}


@router.delete("/api/v1/bangumi/deleteData/{bangumi_id}", tags=["bangumi"])
async def delete_data(bangumi_id: str):
    with BangumiDatabase() as database:
        _id = int(bangumi_id)
        deleted = database.delete_one(_id)
    if deleted:
        return {"status": "ok"}
    else:
        return {"status": "data not exist"}


@router.delete("/api/v1/bangumi/deleteRule/{bangumi_id}", tags=["bangumi"])
async def delete_rule(bangumi_id: str, file: bool = False):
    with BangumiDatabase() as database:
        _id = int(bangumi_id)
        data = database.search_id(_id)
    if data:
        with TorrentManager() as torrent:
            torrent.delete_rule(data)
            if file:
                torrent.delete_bangumi(data)
        return {"status": "ok"}
    else:
        return {"status": "data not exist"}


@router.get("/api/v1/bangumi/resetAll", tags=["bangumi"])
async def reset_all():
    with BangumiDatabase() as database:
        database.delete_all()
        return {"status": "ok"}