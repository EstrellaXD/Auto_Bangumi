from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .response import u_response

from module.models import RSSItem, RSSUpdate, Torrent, APIResponse, Bangumi
from module.rss import RSSEngine, RSSAnalyser
from module.security.api import get_current_user, UNAUTHORIZED
from module.downloader import DownloadClient
from module.manager import SeasonCollector


router = APIRouter(prefix="/rss", tags=["rss"])


@router.get(path="", response_model=list[RSSItem])
async def get_rss(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        return engine.rss.search_all()


@router.post(path="/add", response_model=APIResponse)
async def add_rss(rss: RSSItem, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        result = engine.add_rss(rss.url, rss.name, rss.aggregate)
    return u_response(result)


@router.delete(path="/delete/{rss_id}", response_model=APIResponse)
async def delete_rss(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        if engine.rss.delete(rss_id):
            return JSONResponse(
                status_code=200,
                content={"msg_en": "Delete RSS successfully.", "msg_zh": "删除 RSS 成功。"},
            )
        else:
            return JSONResponse(
                status_code=406,
                content={"msg_en": "Delete RSS failed.", "msg_zh": "删除 RSS 失败。"},
            )


@router.patch(path="/disable/{rss_id}", response_model=APIResponse)
async def disable_rss(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        if engine.rss.disable(rss_id):
            return JSONResponse(
                status_code=200,
                content={"msg_en": "Disable RSS successfully.", "msg_zh": "禁用 RSS 成功。"},
            )
        else:
            return JSONResponse(
                status_code=406,
                content={"msg_en": "Disable RSS failed.", "msg_zh": "禁用 RSS 失败。"},
            )


@router.post(path="/disable/many", response_model=APIResponse)
async def disable_many_rss(rss_ids: list[int], current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        if engine.disable_list(rss_ids):
            return JSONResponse(
                status_code=200,
                content={"msg_en": "Disable RSS successfully.", "msg_zh": "禁用 RSS 成功。"},
            )
        else:
            return JSONResponse(
                status_code=406,
                content={"msg_en": "Disable RSS failed.", "msg_zh": "禁用 RSS 失败。"},
            )


@router.patch(path="/update/{rss_id}", response_model=APIResponse)
async def update_rss(
    rss_id: int, data: RSSUpdate, current_user=Depends(get_current_user)
):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        if engine.rss.update(rss_id, data):
            return JSONResponse(
                status_code=200,
                content={"msg_en": "Update RSS successfully.", "msg_zh": "更新 RSS 成功。"},
            )
        else:
            return JSONResponse(
                status_code=406,
                content={"msg_en": "Update RSS failed.", "msg_zh": "更新 RSS 失败。"},
            )


@router.get(path="/refresh/all", response_model=APIResponse)
async def refresh_all(current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine, DownloadClient() as client:
        engine.refresh_rss(client)
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Refresh all RSS successfully.", "msg_zh": "刷新 RSS 成功。"},
        )


@router.get(path="/refresh/{rss_id}", response_model=APIResponse)
async def refresh_rss(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine, DownloadClient() as client:
        engine.refresh_rss(client, rss_id)
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Refresh RSS successfully.", "msg_zh": "刷新 RSS 成功。"},
        )


@router.get(path="/torrent/{rss_id}", response_model=list[Torrent])
async def get_torrent(rss_id: int, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with RSSEngine() as engine:
        return engine.get_rss_torrents(rss_id)


# Old API
analyser = RSSAnalyser()


@router.post("/analysis", response_model=Bangumi)
async def analysis(rss: RSSItem, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    data = analyser.link_to_data(rss)
    if isinstance(data, Bangumi):
        return data
    else:
        return u_response(data)


@router.post("/collect", response_model=APIResponse)
async def download_collection(data: Bangumi, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with SeasonCollector() as collector:
        resp = collector.collect_season(data, data.rss_link)
        return u_response(resp)


@router.post("/subscribe", response_model=APIResponse)
async def subscribe(data: Bangumi, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    with SeasonCollector() as collector:
        resp = collector.subscribe_season(data)
        return u_response(resp)

