from .api import router

from module.models import BangumiData
from module.database import BangumiDatabase
from module.manager import set_new_path


@router.get("/api/v1/bangumi/getData", tags=["bangumi"])
async def get_all_data():
    with BangumiDatabase() as database:
        return database.search_all()


@router.get("/api/v1/bangumi/getData/{bangumi_id}", tags=["bangumi"])
async def get_data(bangumi_id: str):
    with BangumiDatabase() as database:
        data = database.search_id(int(bangumi_id))
        if data:
            return data
        else:
            return {"": "data not exist"}


@router.post("/api/v1/bangumi/UpdateData", tags=["bangumi"])
async def update_data(data: BangumiData):
    with BangumiDatabase() as database:
        database.update(data)
    set_new_path(data)
