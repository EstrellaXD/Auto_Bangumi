from fastapi import APIRouter, HTTPException

from module.conf.config import settings
from module.models.bangumi import Notification
from module.notification import Notifier
from module.notification.base import NotificationContent

router = APIRouter(prefix="/notification", tags=["notification"])


@router.get("/")
async def get_notification():
    pass


@router.post("/send")
async def send_notification(content: NotificationContent):
    notifier = Notifier(
        service_name=settings.notification.type,
        config=settings.notification.dict(by_alias=True),
    )

    try:
        await notifier.asend(content=content)
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))

    return dict(code=0, msg="success")


@router.get("/clean")
async def clean_notification():
    pass
