from fastapi import APIRouter, Depends, HTTPException

from module.conf.config import settings
from module.notification import Notifier
from module.notification.base import NotificationContent

router = APIRouter(prefix="/notification", tags=["notification"])


def get_notifier():
    yield Notifier(
        service_name=settings.notification.type,
        config=settings.notification.dict(by_alias=True),
    )


@router.get("")
async def get_notification(notifier: Notifier = Depends(get_notifier)):
    cursor = notifier.q.conn.cursor()
    stmt = r"""
    SELECT message_id, data, in_time as datetime, status as has_read
    FROM Queue
    WHERE status=0
    ORDER BY in_time DESC
    """

    try:
        rows = cursor.execute(stmt).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        return dict(code=0, msg="success", data=dict(total=0, messages=[]))

    messages = [
        dict(message_id=data[0], data=data[1], datetime=data[2]) for data in rows
    ]

    return dict(
        code=0, msg="success", data=dict(total=len(messages), messages=messages)
    )


@router.get("/read")
async def done_notification(
    message_id: str, notifier: Notifier = Depends(get_notifier)
):
    try:
        notifier.q.done(message_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return dict(code=0, msg="success")


@router.post("/send", description="send notification only for test")
async def send_notification(
    content: NotificationContent, notifier: Notifier = Depends(get_notifier)
):
    try:
        await notifier.asend(content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return dict(code=0, msg="success")


@router.get("/clean")
async def clean_notification(notifier: Notifier = Depends(get_notifier)):
    try:
        notifier.q.prune()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return dict(code=0, msg="success")


# Note: put this vildcard route at the end of all routes to avoid masking other routes
@router.get("/get")
async def get_notification_by_id(
    message_id: str, notifier: Notifier = Depends(get_notifier)
):
    message = notifier.q.get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="message not found")

    return dict(code=0, msg="success", data=message)
