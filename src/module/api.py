import logging
from fastapi import FastAPI
from fastapi.responses import FileResponse

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
    data = json_config.load(DATA_PATH)
    return data


@router.get("/api/v1/log")
async def get_log():
    return FileResponse(LOG_PATH)


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


@router.post("/api/v1/updateConfig", tags=["config"])
async def update_config(config: Config):
    return api_func.update_config(config)

