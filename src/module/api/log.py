import os
from fastapi import Response

from .auth import router

from module.conf import LOG_PATH


@router.get("/api/v1/log", tags=["log"])
async def get_log():
    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            return Response(f.read(), media_type="text/plain")
    else:
        return Response("Log file not found", status_code=404)


@router.get("/api/v1/log/clear", tags=["log"])
async def clear_log():
    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, "w") as f:
            f.write("")
        return {"status": "ok"}
    else:
        return Response("Log file not found", status_code=404)





