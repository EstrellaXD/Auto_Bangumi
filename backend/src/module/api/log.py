import os

from fastapi import APIRouter, Depends, HTTPException, Response, status

from module.conf import LOG_PATH
from module.security import get_current_user

router = APIRouter(prefix='/log', tags=["log"])


@router.get("")
async def get_log(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, "rb") as f:
            return Response(f.read(), media_type="text/plain")
    else:
        return Response("Log file not found", status_code=404)


@router.get("/clear")
async def clear_log(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        )
    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, "w") as f:
            f.write("")
        return {"status": "ok"}
    else:
        return Response("Log file not found", status_code=404)
