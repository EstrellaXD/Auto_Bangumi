from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from module.manager import SeasonCollector
from module.models import Bangumi, RSSItem, APIResponse
from module.rss import RSSAnalyser
from module.security.api import get_current_user, UNAUTHORIZED

router = APIRouter(prefix="/download", tags=["download"])
analyser = RSSAnalyser()


@router.post("/analysis", response_model=Bangumi)
async def analysis(rss: RSSItem, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    data = analyser.link_to_data(rss)
    if data:
        return data
    else:
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Analysis failed.", "msg_zh": "解析失败。"},
        )


@router.post("/collection", response_model=APIResponse)
async def download_collection(data: Bangumi, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    if data:
        with SeasonCollector() as collector:
            if collector.collect_season(data, data.rss_link[0]):
                return JSONResponse(
                    status_code=200,
                    content={"msg_en": "Add torrent successfully.", "msg_zh": "添加种子成功。"},
                )
            else:
                return JSONResponse(
                    status_code=406,
                    content={"msg_en": "Add torrent failed.", "msg_zh": "添加种子失败。"},
                )
    else:
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Add torrent failed.", "msg_zh": "添加种子失败。"},
        )


@router.post("/subscribe", response_model=APIResponse)
async def subscribe(data: Bangumi, current_user=Depends(get_current_user)):
    if not current_user:
        raise UNAUTHORIZED
    if data:
        with SeasonCollector() as collector:
            collector.subscribe_season(data)
        return JSONResponse(
            status_code=200,
            content={"msg_en": "Subscribe successfully.", "msg_zh": "订阅成功。"},
        )
    else:
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Subscribe failed.", "msg_zh": "订阅失败。"},
        )
