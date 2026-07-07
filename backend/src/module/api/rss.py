from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from module.conf.search_provider import get_provider
from module.database import Database, get_db
from module.downloader import DownloadClient
from module.manager import SeasonCollector
from module.models import APIResponse, Bangumi, RSSItem, RSSUpdate, Torrent
from module.rss import RSSAnalyser, RSSEngine
from module.security.api import get_current_user

from .response import u_response

router = APIRouter(prefix="/rss", tags=["rss"])

# RSSItem.parser 的合法取值（与 webui ab-add-rss 的选项一致）；
# 这些值即便与搜索站点同名（mikan）也不做站点名映射
PARSER_TYPES = {"mikan", "tmdb", "parser"}


@router.get(
    path="", response_model=list[RSSItem], dependencies=[Depends(get_current_user)]
)
async def get_rss(db: Database = Depends(get_db)):
    return await db.rss.search_all()


@router.post(
    path="/add", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def add_rss(rss: RSSItem, db: Database = Depends(get_db)):
    engine = RSSEngine(db)
    result = await engine.add_rss(rss.url, rss.name, rss.aggregate, rss.parser)
    return u_response(result)


@router.post(
    path="/enable/many",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def enable_many_rss(
    rss_ids: list[int],
    db: Database = Depends(get_db),
):
    engine = RSSEngine(db)
    result = await engine.enable_list(rss_ids)
    return u_response(result)


@router.delete(
    path="/delete/{rss_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_rss(rss_id: int, db: Database = Depends(get_db)):
    if await db.rss.delete(rss_id):
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Delete RSS successfully.", "msg_zh": "删除 RSS 成功。"},
        )
    else:
        return JSONResponse(
            status_code=400,
            content={"msg_en": "Delete RSS failed.", "msg_zh": "删除 RSS 失败。"},
        )


@router.post(
    path="/delete/many",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_many_rss(
    rss_ids: list[int],
    db: Database = Depends(get_db),
):
    engine = RSSEngine(db)
    result = await engine.delete_list(rss_ids)
    return u_response(result)


@router.patch(
    path="/disable/{rss_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_rss(rss_id: int, db: Database = Depends(get_db)):
    if await db.rss.disable(rss_id):
        return JSONResponse(
            status_code=200,
            content={
                "msg_en": "Disable RSS successfully.",
                "msg_zh": "禁用 RSS 成功。",
            },
        )
    else:
        return JSONResponse(
            status_code=404,
            content={"msg_en": "Disable RSS failed.", "msg_zh": "禁用 RSS 失败。"},
        )


@router.post(
    path="/disable/many",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_many_rss(rss_ids: list[int], db: Database = Depends(get_db)):
    engine = RSSEngine(db)
    result = await engine.disable_list(rss_ids)
    return u_response(result)


@router.patch(
    path="/update/{rss_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def update_rss(
    rss_id: int,
    data: RSSUpdate,
    db: Database = Depends(get_db),
):
    if await db.rss.update(rss_id, data):
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Update RSS successfully.", "msg_zh": "更新 RSS 成功。"},
        )
    else:
        return JSONResponse(
            status_code=404,
            content={"msg_en": "Update RSS failed.", "msg_zh": "更新 RSS 失败。"},
        )


@router.post(
    path="/refresh/all",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_all(db: Database = Depends(get_db)):
    async with DownloadClient() as client:
        engine = RSSEngine(db)
        await engine.refresh_rss(client)
    return JSONResponse(
        status_code=200,
        content={
            "msg_en": "Refresh all RSS successfully.",
            "msg_zh": "刷新 RSS 成功。",
        },
    )


@router.post(
    path="/refresh/{rss_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_rss(rss_id: int, db: Database = Depends(get_db)):
    async with DownloadClient() as client:
        engine = RSSEngine(db)
        await engine.refresh_rss(client, rss_id)
    return JSONResponse(
        status_code=200,
        content={"msg_en": "Refresh RSS successfully.", "msg_zh": "刷新 RSS 成功。"},
    )


@router.get(
    path="/torrent/{rss_id}",
    response_model=list[Torrent],
    dependencies=[Depends(get_current_user)],
)
async def get_torrent(
    rss_id: int,
    db: Database = Depends(get_db),
):
    engine = RSSEngine(db)
    return await engine.get_rss_torrents(rss_id)


# Old API
analyser = RSSAnalyser()


@router.post(
    "/analysis", response_model=Bangumi, dependencies=[Depends(get_current_user)]
)
async def analysis(rss: RSSItem):
    data = await analyser.link_to_data(rss)
    if isinstance(data, Bangumi):
        return data
    else:
        return u_response(data)


@router.post(
    "/collect", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def download_collection(data: Bangumi):
    async with DownloadClient() as client:
        collector = SeasonCollector(client)
        resp = await collector.collect_season(data, data.rss_link)
        return u_response(resp)


@router.post(
    "/subscribe", response_model=APIResponse, dependencies=[Depends(get_current_user)]
)
async def subscribe(data: Bangumi, rss: RSSItem):
    # 搜索订阅时前端传来的是站点名（nyaa/dmhy），而分析器只认识解析器类型
    # mikan/tmdb（见 rss/analyser.py），站点名会静默跳过 TMDB 补全（#1053）。
    # 这里按搜索源配置把站点名映射为解析器；已是解析器类型的值原样透传，
    # 且不参与站点映射——避免 "mikan" 这类与站点同名的解析器被配置改写。
    parser = rss.parser
    if parser not in PARSER_TYPES:
        providers = get_provider()
        if parser in providers:
            parser = providers[parser]["parser"]
    resp = await SeasonCollector.subscribe_season(data, parser=parser)
    return u_response(resp)
