import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.util.concurrency import asyncio

from module.database import Database, engine
from module.manager import BangumiManager
from models import APIResponse, Bangumi, ResponseModel
from module.network import load_image
from module.security.api import get_current_user

from .response import u_response

router = APIRouter(prefix="/bangumi", tags=["bangumi"])
logger = logging.getLogger(__name__)


@router.get("/get/all", response_model=list[Bangumi], dependencies=[Depends(get_current_user)])
async def get_all_data():
    with Database() as db:
        return db.bangumi.search_all()


@router.get(
    "/get/{bangumi_id}",
    response_model=Bangumi,
    dependencies=[Depends(get_current_user)],
)
async def get_data(bangumi_id: str):
    resp = BangumiManager().search_one(bangumi_id)
    if resp is None:
        return ResponseModel(
            status_code=406,
            status=False,
            msg_en=f"Can't find id {bangumi_id}",
            msg_zh=f"无法找到 id {bangumi_id}",
        )
    return resp


@router.patch(
    "/update/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def update_rule(
    bangumi_id: int,
    data: Bangumi,
):
    resp = await BangumiManager().update_rule(data)
    if resp:
        resp = ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Update rule for {data.official_title}",
            msg_zh=f"更新 {data.official_title} 规则",
        )

    else:
        resp = ResponseModel(
            status_code=406,
            status=False,
            msg_en=f"Can't find data with {bangumi_id}",
            msg_zh=f"无法找到 id {bangumi_id} 的数据",
        )
    return u_response(resp)


@router.delete(
    path="/delete/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_rule(bangumi_id: str, file: bool = False):
    data = await BangumiManager().delete_rule(bangumi_id, file)
    if data:
        resp = ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Delete rule for {data.official_title}. ",
            msg_zh=f"删除 {data.official_title} 规则。",
        )
    else:
        resp = ResponseModel(
            status_code=406,
            status=False,
            msg_en=f"Can't find id {bangumi_id}",
            msg_zh=f"无法找到 id {bangumi_id}",
        )
    return u_response(resp)


@router.delete(
    path="/delete/many/",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def delete_many_rule(bangumi_id: list, file: bool = False):
    tasks = []
    for i in bangumi_id:
        tasks.append(BangumiManager().delete_rule(i, file))

    resp = await asyncio.gather(*tasks)
    resp = resp[0]
    return u_response(resp)


@router.delete(
    path="/disable/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_rule(bangumi_id: str, file: bool = False):
    resp = await BangumiManager().disable_rule(bangumi_id, file)
    if resp:
        resp = ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Disable rule for {bangumi_id}",
            msg_zh=f"禁用 {bangumi_id} 规则",
        )
    else:
        resp = ResponseModel(
            status_code=406,
            status=False,
            msg_en=f"Can't find id {bangumi_id}",
            msg_zh=f"无法找到 id {bangumi_id}",
        )
    return u_response(resp)


@router.delete(
    path="/disable/many/",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def disable_many_rule(bangumi_id: list[int], file: bool = False):
    tasks = []
    for i in bangumi_id:
        tasks.append(BangumiManager().disable_rule(i, file))
    resp = await asyncio.gather(*tasks)
    resp = resp[-1]
    return u_response(resp)


@router.get(
    path="/enable/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def enable_rule(bangumi_id: str):
    resp = await BangumiManager().enable_rule(bangumi_id)
    if resp:
        resp = ResponseModel(
            status_code=200,
            status=True,
            msg_en=f"Enable rule for {bangumi_id}",
            msg_zh=f"启用 {bangumi_id} 规则",
        )
    else:
        resp = ResponseModel(
            status_code=406,
            status=False,
            msg_en=f"Can't find id {bangumi_id}",
            msg_zh=f"无法找到 id {bangumi_id}",
        )
    return u_response(resp)


@router.get(
    path="/refresh/poster/all",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_poster():
    resp = await BangumiManager().refresh_poster()
    resp = ResponseModel(
        status_code=200,
        status=True,
        msg_en="Refresh poster link successfully.",
        msg_zh="刷新海报链接成功。",
    )
    return u_response(resp)


@router.get(
    path="/refresh/poster/{bangumi_id}",
    response_model=APIResponse,
    dependencies=[Depends(get_current_user)],
)
async def refresh_single_poster(bangumi_id: int):
    resp = await BangumiManager().refind_poster(bangumi_id)
    if resp:
        resp = ResponseModel(
            status_code=200,
            status=True,
            msg_en="Refresh poster link successfully.",
            msg_zh="刷新海报链接成功。",
        )
    else:
        resp = ResponseModel(
            status_code=406,
            status=False,
            msg_en=f"Can't find id {bangumi_id}",
            msg_zh=f"无法找到 id {bangumi_id}",
        )
    return u_response(resp)


@router.get("/reset/all", response_model=APIResponse, dependencies=[Depends(get_current_user)])
async def reset_all():
    with Database(engine) as db:
        db.bangumi.delete_all()
    return JSONResponse(
        status_code=200,
        content={
            "msg_en": "Reset all rules successfully.",
            "msg_zh": "重置所有规则成功。",
        },
    )


@router.get("/posters/{path:path}", dependencies=[Depends(get_current_user)])
async def get_poster(path: str):
    """
    安全的poster图片访问端点
    - 添加了用户鉴权
    - 防止路径遍历攻击
    - 限制只能访问posters目录下的文件
    """
    # 验证路径安全性 - 阻止路径遍历
    if ".." in path or path.startswith("/") or "\\" in path:
        logger.warning(f"[Poster] Blocked path traversal attempt: {path}")
        raise HTTPException(status_code=400, detail="Invalid path")

    # 构建安全的文件路径
    poster_dir = Path("data") / Path("posters")
    post_path = poster_dir / Path(path)

    # 确保解析后的路径仍在预期目录内
    try:
        post_path.resolve().relative_to(poster_dir.resolve())
    except ValueError:
        logger.warning(f"[Poster] Path outside allowed directory: {path}")
        raise HTTPException(status_code=400, detail="Path outside allowed directory")

    # 如果文件不存在，尝试下载
    if not post_path.exists():
        try:
            await load_image(path)
        except Exception as e:
            logger.warning(f"[Poster] Failed to load image {path}: {e}")

    # 返回文件
    if post_path.exists() and post_path.is_file():
        return FileResponse(
            post_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},  # 缓存1天
        )
    else:
        logger.warning(f"[Poster] File not found: {post_path}")
        raise HTTPException(status_code=404, detail="Poster not found")
