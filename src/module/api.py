import uvicorn
from uvicorn.config import LOGGING_CONFIG
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import logging

from module.core import APIProcess
from module.conf import settings, DATA_PATH, LOG_PATH, VERSION
from module.utils import json_config
from module.models.api import *
from module.models import Config

logger = logging.getLogger(__name__)

router = FastAPI()
api_func = APIProcess()

if VERSION != "DEV_VERSION":
    router.mount("/assets", StaticFiles(directory="templates/assets"), name="assets")
    templates = Jinja2Templates(directory="templates")



@router.get("/api/v1/data")
def get_data():
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

if VERSION != "DEV_VERSION":
# HTML Response
    @router.get("/{full_path:path}", response_class=HTMLResponse)
    def index(request: Request):
        context = {"request": request}
        return templates.TemplateResponse("index.html", context)
else:
    @router.get("/", status_code=302)
    def index():
        return RedirectResponse("/docs")


def run():
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "[%(asctime)s] %(levelprefix)s %(message)s"
    uvicorn.run(router, host="0.0.0.0", port=settings.program.webui_port)



