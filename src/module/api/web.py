from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .proxy import router

from module.conf import VERSION


if VERSION != "DEV_VERSION":
    router.mount("/assets", StaticFiles(directory="templates/assets"), name="assets")
    templates = Jinja2Templates(directory="templates")

    # HTML Response
    @router.get("/{full_path:path}", response_class=HTMLResponse, tags=["html"])
    def index(request: Request):
        context = {"request": request}
        return templates.TemplateResponse("index.html", context)
else:
    @router.get("/", status_code=302, tags=["html"])
    def index():
        return RedirectResponse("/docs")
