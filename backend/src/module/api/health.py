"""无鉴权的存活探针（liveness probe），供容器/编排系统健康检查使用。

与 program.py 中的 /status 不同，本路由不挂在 /api/v1 前缀下、也不依赖
get_current_user，因此可以直接被 Docker HEALTHCHECK 等外部探针访问。
"""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from module.conf import VERSION
from module.database import Database

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """存活探针：始终返回 200，db_ok 反映一次简单查询是否成功。"""
    try:
        async with Database() as db:
            await db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.warning(f"[Health] DB check failed: {e}")
        db_ok = False
    return {"status": "ok", "version": VERSION, "db_ok": db_ok}
