import re
import logging

from fastapi.responses import Response

from .program import router

from module.conf import settings
from module.network import RequestContent


logger = logging.getLogger(__name__)


def get_rss_content(full_path):
    url = f"https://mikanani.me/RSS/{full_path}"
    custom_url = settings.rss_parser.custom_url
    if "://" not in custom_url:
        custom_url = f"https://{custom_url}"
    with RequestContent() as request:
        content = request.get_html(url)
    return re.sub(r"https://mikanani.me", custom_url, content)


def get_torrent(full_path):
    url = f"https://mikanani.me/Download/{full_path}"
    with RequestContent() as request:
        return request.get_content(url)

    
@router.get("/RSS/MyBangumi", tags=["proxy"])
async def get_my_bangumi(token: str):
    full_path = "MyBangumi?token=" + token
    content = get_rss_content(full_path)
    return Response(content, media_type="application/xml")


@router.get("/RSS/Search", tags=["proxy"])
async def get_search_result(searchstr: str):
    full_path = "Search?searchstr=" + searchstr
    content = get_rss_content(full_path)
    return Response(content, media_type="application/xml")


@router.get("/RSS/Bangumi", tags=["proxy"])
async def get_bangumi(bangumiId: str, groupid: str):
    full_path = "Bangumi?bangumiId=" + bangumiId + "&groupid=" + groupid
    content = get_rss_content(full_path)
    return Response(content, media_type="application/xml")


@router.get("/RSS/{full_path:path}", tags=["proxy"])
async def get_rss(full_path: str):
    content = get_rss_content(full_path)
    return Response(content, media_type="application/xml")


@router.get("/Download/{full_path:path}", tags=["proxy"])
async def download(full_path: str):
    torrent = get_torrent(full_path)
    return Response(torrent, media_type="application/x-bittorrent")