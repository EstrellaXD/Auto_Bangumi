import logging
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response

from module.conf import LOG_PATH

logger = logging.getLogger(__name__)

router = FastAPI()


@router.get("/api/v1/log", tags=["log"])
async def get_log():
    if os.path.isfile(LOG_PATH):
        return FileResponse(LOG_PATH)
    else:
        return Response("Log file not found", status_code=404)


@router.get("/api/v1/resetRule")
def reset_rule():
    pass





