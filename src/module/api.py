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


@router.get("/api/v1/data")
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


@router.get("/api/v1/log")
async def get_log():
    if os.path.isfile(LOG_PATH):
        return FileResponse(LOG_PATH)
    else:
        return Response("Log file not found", status_code=404)


@router.get("/api/v1/resetRule")
def reset_rule():
    return api_func.reset_rule()


@router.get("api/v1/removeRule/{bangumi_title}")
def remove_rule(bangumi_title: str):
    return api_func.remove_rule(bangumi_title)


@router.post("/api/v1/collection")
async def collection(link: RssLink):
    return api_func.download_collection(link.rss_link)


@router.post("/api/v1/subscribe")
async def subscribe(link: RssLink):
    return api_func.add_subscribe(link.rss_link)


@router.post("/api/v1/addRule")
async def add_rule(info: AddRule):
    return api_func.add_rule(info.title, info.season)


@router.get("/api/v1/getConfig", tags=["config"])
async def get_config():
    return api_func.get_config()


@router.post("/api/v1/updateConfig", tags=["config"])
async def update_config(config: Config):
    return api_func.update_config(config)


@router.get("/RSS/MyBangumi")
async def get_rss(token: str):
    content = api_func.get_rss(token)
    return Response(content, media_type="application/xml")


@router.get("/Download/{full_path:path}")
async def download(full_path: str):
    torrent = api_func.get_torrent(full_path)
    return Response(torrent, media_type="application/x-bittorrent")

