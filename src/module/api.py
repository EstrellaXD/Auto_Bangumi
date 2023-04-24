import uvicorn
from uvicorn.config import LOGGING_CONFIG
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import logging

from module.core import APIProcess
from module.conf import settings, DATA_PATH, LOG_PATH
from module.utils import json_config
from module.models.api import *
from module.models import Config

logger = logging.getLogger(__name__)

app = FastAPI()
api_func = APIProcess()

app.mount("/assets", StaticFiles(directory="templates/assets"), name="assets")
templates = Jinja2Templates(directory="templates")


@app.get("/api/v1/data")
def get_data():
    data = json_config.load(DATA_PATH)
    return data


@app.get("/api/v1/log")
async def get_log():
    return FileResponse(LOG_PATH)


@app.get("/api/v1/resetRule")
def reset_rule():
    return api_func.reset_rule()


@app.get("api/v1/removeRule/{bangumi_title}")
def remove_rule(bangumi_title: str):
    return api_func.remove_rule(bangumi_title)


@app.post("/api/v1/collection")
async def collection(link: RssLink):
    return api_func.download_collection(link.rss_link)


@app.post("/api/v1/subscribe")
async def subscribe(link: RssLink):
    return api_func.add_subscribe(link.rss_link)


@app.post("/api/v1/addRule")
async def add_rule(info: AddRule):
    return api_func.add_rule(info.title, info.season)


@app.post("/api/v1/updateConfig", tags=["config"])
async def update_config(config: Config):
    return api_func.update_config(config)


# HTML Response
@app.get("/{full_path:path}", response_class=HTMLResponse)
def index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context)


def run():
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "[%(asctime)s] %(levelprefix)s %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=settings.program.webui_port)



