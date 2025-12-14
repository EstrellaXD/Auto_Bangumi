import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from models import APIResponse
from models.config import Notification
from module.security.api import get_current_user

router = APIRouter(prefix="/config", tags=["config"])
logger = logging.getLogger(__name__)

#TODO: 配置管理接口待完善
# @router.get("/get", response_model=Config, dependencies=[Depends(get_current_user)])
# async def get_config():
#     return settings


# 测试通知的是否生效
@router.post("/test_notify", response_model=APIResponse, dependencies=[Depends(get_current_user)])
async def test_notify(config: Notification):
    try:
        from module.notification.notification import PostNotification
        from models import Message

        print(config)

        title = "AB通知测试"
        link = "https://mikanani.me/images/Bangumi/202507/8a6beaff.jpg"
        nt = Message(title=title, season="1", episode="1", poster_path=link)
        sender = PostNotification()
        sender.initialize(config)
        await sender.send(nt)

        logger.info("Notification test completed")
        return JSONResponse(
            status_code=200,
            content={
                "msg_en": "Test notification sent successfully.",
                "msg_zh": "测试通知发送成功。",
            },
        )
    except Exception as e:
        logger.warning(e)
        return JSONResponse(
            status_code=406,
            content={"msg_en": "Test notification failed.", "msg_zh": "测试通知失败。"},
        )


# @router.patch("/update", response_model=APIResponse, dependencies=[Depends(get_current_user)])
# async def update_config(config: Config):
#     try:
#         settings.save(config_dict=config.model_dump())
#         settings.load()
#         # update_rss()
#         logger.info("Config updated")
#         return JSONResponse(
#             status_code=200,
#             content={
#                 "msg_en": "Update config successfully.",
#                 "msg_zh": "更新配置成功。",
#             },
#         )
#     except Exception as e:
#         logger.warning(e)
#         return JSONResponse(
#             status_code=406,
#             content={"msg_en": "Update config failed.", "msg_zh": "更新配置失败。"},
#         )
