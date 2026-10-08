"""示例插件：手动选种（前端挂载点 ``bangumi.detail.tab`` 的验收演示）。

前端组件（``web/index.js``）经宿主的只读 API 列出规则的种子，选择结果经本插件
自己的路由 ``/api/v1/plugins/manual-pick/picks/<bangumi_id>`` 保存到插件的键值
存储，并发布 ``manual-pick.picked`` 事件；打开着的详情页通过 ``host.events.on``
收到事件后刷新。SDK 0.x 没有「让下载器下载指定种子」的接口，所以这里只记录
选择，不触发下载。
"""

from dataclasses import dataclass
from typing import ClassVar

from fastapi import APIRouter
from pydantic import BaseModel

from ab_sdk import Event, Plugin, points, provider


@dataclass(frozen=True, slots=True)
class Picked(Event):
    kind: ClassVar[str] = "manual-pick.picked"

    bangumi_id: int
    torrent_id: int


class Pick(BaseModel):
    torrent_id: int


class ManualPick(Plugin):
    @provider(points.API_ROUTER, id="api")
    def api(self) -> APIRouter:
        router = APIRouter()

        @router.get("/picks/{bangumi_id}")
        async def get_pick(bangumi_id: int) -> dict[str, int | None]:
            return {"torrent_id": await self.ctx.kv.get(f"pick:{bangumi_id}")}

        @router.put("/picks/{bangumi_id}")
        async def put_pick(bangumi_id: int, body: Pick) -> dict[str, int]:
            await self.ctx.kv.set(f"pick:{bangumi_id}", body.torrent_id)
            self.ctx.bus.publish(
                Picked(bangumi_id=bangumi_id, torrent_id=body.torrent_id)
            )
            return {"torrent_id": body.torrent_id}

        return router
