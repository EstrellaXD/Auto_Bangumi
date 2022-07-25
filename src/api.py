import uvicorn
from uvicorn.config import LOGGING_CONFIG
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging

from core import APIProcess
from conf import settings, parse
from utils import json_config

logger = logging.getLogger(__name__)
args = parse()
if args.debug:
    try:
        from conf.const_dev import DEV_SETTINGS

        settings.init(DEV_SETTINGS)
    except ModuleNotFoundError:
        logger.debug("Please copy `const_dev.py` to `const_dev.py` to use custom settings")
else:
    settings.init()
app = FastAPI()
api_func = APIProcess()

app.mount("/assets", StaticFiles(directory="/templates/assets"), name="assets")
templates = Jinja2Templates(directory="/templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context)


@app.get("/api/v1/data")
def get_data():
    data = json_config.load(settings.info_path)
    return data


@app.get("/api/v1/log")
async def get_log():
    log_path = settings.log_path
    return FileResponse(log_path)


@app.get("/api/v1/resetRule")
def reset_rule():
    return api_func.reset_rule()


@app.get("api/v1/removeRule/{bangumi_title}")
def remove_rule(bangumi_title: str):
    return api_func.remove_rule(bangumi_title)


class RssLink(BaseModel):
    rss_link: str


@app.post("/api/v1/collection")
async def collection(link: RssLink):
    return api_func.download_collection(link.rss_link)


@app.post("/api/v1/subscribe")
async def subscribe(link: RssLink):
    return api_func.add_subscribe(link.rss_link)


class AddRule(BaseModel):
    title: str
    season: int


@app.post("/api/v1/addRule")
async def add_rule(info: AddRule):
    return api_func.add_rule(info.title, info.season)


def run():
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "[%(asctime)s] %(levelprefix)s %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=settings.webui_port)


if __name__ == "__main__":
    run()

