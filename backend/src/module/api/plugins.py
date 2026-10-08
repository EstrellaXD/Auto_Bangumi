from fastapi import APIRouter, Depends
from pydantic import BaseModel

from module.core import AppContext
from module.security.api import get_current_user

from .deps import get_context

router = APIRouter(prefix="/plugins", tags=["plugins"])


class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    source: str
    signed: bool
    state: str
    description: str
    permissions: list[str]
    error: str | None


@router.get(
    "", response_model=list[PluginInfo], dependencies=[Depends(get_current_user)]
)
async def list_plugins(ctx: AppContext = Depends(get_context)):
    """已发现的插件及其运行状态（active / disabled / error）。"""
    return [PluginInfo(**vars(status)) for status in ctx.plugins.statuses()]
