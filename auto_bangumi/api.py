import re

import uvicorn
from uvicorn.config import LOGGING_CONFIG
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import logging

from core import RSSAnalyser, DownloadClient, FullSeasonGet
from conf import settings, parse
from utils import json_config

logger = logging.getLogger(__name__)

app = FastAPI()


# templates = Jinja2Templates(directory="templates")


# @app.get("/", response_class=HTMLResponse)
# def index(request: Request):
#     context = {"request": request}
#     return templates.TemplateResponse("index.html", context)

@app.get("/api/v1/data")
def get_data():
    data = json_config.load(settings.info_path)
    return data


@app.get("/api/v1/log")
def get_log():
    with open(settings.log_path, "r") as f:
        return f.read()


@app.get("/api/v1/resetRule")
def reset_rule():
    data = json_config.load(settings.info_path)
    data["bangumi_info"] = []
    json_config.save(settings.info_path, data)
    return "Success"


class RuleName(BaseModel):
    name: str


@app.post("/api/v1/removeRule")
def remove_rule(name: RuleName):
    datas = json_config.load(settings.info_path)["bangumi_info"]
    for data in datas:
        if re.search(name.name.lower(), data["title_raw"].lower()) is not None:
            datas.remove(data)
            json_config.save(settings.info_path, datas)
            return "Success"
    return "Not matched"


class RSS(BaseModel):
    link: str


@app.post("/api/v1/subscriptions")
async def receive(link: RSS):
    client = DownloadClient()
    try:
        data = RSSAnalyser().rss_to_data(link.link)
        FullSeasonGet().download_collection(data, link.link, client)
        return data
    except Exception as e:
        logger.debug(e)
        return "Error"


class Search(BaseModel):
    group: str
    title: str
    subtitle: str


@app.post("/api/v1/search")
async def search(input: Search):
    return "Nothing Happened"


class AddRule(BaseModel):
    title: str
    season: int


@app.post("/api/v1/addRule")
async def add_rule(info: AddRule):
    return "Not complete"


def run():
    args = parse()
    if args.debug:
        try:
            from conf.const_dev import DEV_SETTINGS
            settings.init(DEV_SETTINGS)
        except ModuleNotFoundError:
            logger.debug("Please copy `const_dev.py` to `const_dev.py` to use custom settings")
    else:
        settings.init()
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s %(levelprefix)s %(message)s"
    uvicorn.run(app, host="0.0.0.0", port=settings.webui_port)


if __name__ == "__main__":
    run()

