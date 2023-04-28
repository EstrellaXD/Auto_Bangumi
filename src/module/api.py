import logging
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response

from module.core import APIProcess
from module.conf import DATA_PATH, LOG_PATH, settings
from module.utils import json_config
from module.models.api import *
from module.models import Config


router = FastAPI()
api_func = APIProcess()


@router.on_event("startup")
async def startup_event():
    logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s  %(message)s"))
    logger.addHandler(handler)


@router.get("/api/v1/data", tags=["info"])
async def get_data():
    try:
        data = json_config.load(DATA_PATH)
        return data
    except FileNotFoundError:
        return {
            "rss_link": "",
            "data_version": settings.data_version,
            "bangumi_info": [],
        }


@router.get("/api/v1/log", tags=["info"])
async def get_log():
    if os.path.isfile(LOG_PATH):
        return FileResponse(LOG_PATH)
    else:
        return Response("Log file not found", status_code=404)


@router.get("/api/v1/resetRule")
def reset_rule():
    return api_func.reset_rule()


@router.get("api/v1/removeRule/{bangumi_id}")
def remove_rule(bangumi_id: str):
    bangumi_id = int(bangumi_id)
    return api_func.remove_rule(bangumi_id)


@router.post("/api/v1/collection", tags=["download"])
async def collection(link: RssLink):
    response = api_func.download_collection(link.rss_link)
    if response:
        return response.dict()
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/subscribe", tags=["download"])
async def subscribe(link: RssLink):
    response = api_func.add_subscribe(link.rss_link)
    if response:
        return response.dict()
    else:
        return {"status": "Failed to parse link"}


@router.post("/api/v1/addRule", tags=["download"])
async def add_rule(info: AddRule):
    return api_func.add_rule(info.title, info.season)


@router.get("/api/v1/getConfig", tags=["config"])
async def get_config():
    return api_func.get_config()


@router.post("/api/v1/updateConfig", tags=["config"])
async def update_config(config: Config):
    return api_func.update_config(config)


@router.get("/RSS/MyBangumi", tags=["proxy"])
async def get_my_bangumi(token: str):
    full_path = "MyBangumi?token=" + token
    content = api_func.get_rss(full_path)
    return Response(content, media_type="application/xml")


@router.get("/RSS/Search", tags=["proxy"])
async def get_search_result(searchstr: str):
    full_path = "Search?searchstr=" + searchstr
    content = api_func.get_rss(full_path)
    return Response(content, media_type="application/xml")


@router.get("/RSS/Bangumi", tags=["proxy"])
async def get_bangumi(bangumiId: str, groupid: str):
    full_path = "Bangumi?bangumiId=" + bangumiId + "&groupid=" + groupid
    content = api_func.get_rss(full_path)
    return Response(content, media_type="application/xml")


@router.get("/RSS/{full_path:path}", tags=["proxy"])
async def get_rss(full_path: str):
    content = api_func.get_rss(full_path)
    return Response(content, media_type="application/xml")


@router.get("/Download/{full_path:path}", tags=["proxy"])
async def download(full_path: str):
    torrent = api_func.get_torrent(full_path)
    return Response(torrent, media_type="application/x-bittorrent")

