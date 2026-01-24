import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from module.conf import VERSION, settings
from module.models import Config, ResponseModel
from module.network import RequestContent
from module.notification.notification import getClient
from module.security.jwt import get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])

SENTINEL_PATH = Path("config/.setup_complete")


def _require_setup_needed():
    """Guard: raise 403 if setup is already completed."""
    if SENTINEL_PATH.exists():
        raise HTTPException(status_code=403, detail="Setup already completed.")
    if settings.dict() != Config().dict():
        raise HTTPException(status_code=403, detail="Setup already completed.")


# --- Request/Response Models ---


class SetupStatusResponse(BaseModel):
    need_setup: bool
    version: str


class TestDownloaderRequest(BaseModel):
    type: str = Field("qbittorrent")
    host: str
    username: str
    password: str
    ssl: bool = False


class TestRSSRequest(BaseModel):
    url: str


class TestNotificationRequest(BaseModel):
    type: str
    token: str
    chat_id: str = ""


class TestResultResponse(BaseModel):
    success: bool
    message_en: str
    message_zh: str
    title: str | None = None
    item_count: int | None = None


class SetupCompleteRequest(BaseModel):
    username: str = Field(..., min_length=4, max_length=20)
    password: str = Field(..., min_length=8)
    downloader_type: str = Field("qbittorrent")
    downloader_host: str
    downloader_username: str
    downloader_password: str
    downloader_path: str = Field("/downloads/Bangumi")
    downloader_ssl: bool = False
    rss_url: str = ""
    rss_name: str = ""
    notification_enable: bool = False
    notification_type: str = "telegram"
    notification_token: str = ""
    notification_chat_id: str = ""


# --- Endpoints ---


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """Check whether the setup wizard is needed."""
    need_setup = not SENTINEL_PATH.exists() and settings.dict() == Config().dict()
    return SetupStatusResponse(need_setup=need_setup, version=VERSION)


@router.post("/test-downloader", response_model=TestResultResponse)
async def test_downloader(req: TestDownloaderRequest):
    """Test connection to the download client."""
    _require_setup_needed()

    scheme = "https" if req.ssl else "http"
    host = req.host if "://" in req.host else f"{scheme}://{req.host}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if host is reachable and is qBittorrent
            resp = await client.get(host)
            if "qbittorrent" not in resp.text.lower() and "vuetorrent" not in resp.text.lower():
                return TestResultResponse(
                    success=False,
                    message_en="Host is reachable but does not appear to be qBittorrent.",
                    message_zh="主机可达但似乎不是 qBittorrent。",
                )

            # Try to authenticate
            login_url = f"{host}/api/v2/auth/login"
            login_resp = await client.post(
                login_url,
                data={"username": req.username, "password": req.password},
            )
            if login_resp.status_code == 200 and "ok" in login_resp.text.lower():
                return TestResultResponse(
                    success=True,
                    message_en="Connection successful.",
                    message_zh="连接成功。",
                )
            elif login_resp.status_code == 403:
                return TestResultResponse(
                    success=False,
                    message_en="Authentication failed: IP is banned by qBittorrent.",
                    message_zh="认证失败：IP 被 qBittorrent 封禁。",
                )
            else:
                return TestResultResponse(
                    success=False,
                    message_en="Authentication failed: incorrect username or password.",
                    message_zh="认证失败：用户名或密码错误。",
                )
    except httpx.TimeoutException:
        return TestResultResponse(
            success=False,
            message_en="Connection timed out.",
            message_zh="连接超时。",
        )
    except httpx.ConnectError:
        return TestResultResponse(
            success=False,
            message_en="Cannot connect to the host.",
            message_zh="无法连接到主机。",
        )
    except Exception as e:
        logger.error(f"[Setup] Downloader test failed: {e}")
        return TestResultResponse(
            success=False,
            message_en=f"Connection failed: {e}",
            message_zh=f"连接失败：{e}",
        )


@router.post("/test-rss", response_model=TestResultResponse)
async def test_rss(req: TestRSSRequest):
    """Test an RSS feed URL."""
    _require_setup_needed()

    try:
        async with RequestContent() as request:
            soup = await request.get_xml(req.url)
            if soup is None:
                return TestResultResponse(
                    success=False,
                    message_en="Failed to fetch or parse the RSS feed.",
                    message_zh="无法获取或解析 RSS 源。",
                )
            title = soup.find("./channel/title")
            title_text = title.text if title is not None else None
            items = soup.findall("./channel/item")
            return TestResultResponse(
                success=True,
                message_en="RSS feed is valid.",
                message_zh="RSS 源有效。",
                title=title_text,
                item_count=len(items),
            )
    except Exception as e:
        logger.error(f"[Setup] RSS test failed: {e}")
        return TestResultResponse(
            success=False,
            message_en=f"Failed to fetch RSS feed: {e}",
            message_zh=f"获取 RSS 源失败：{e}",
        )


@router.post("/test-notification", response_model=TestResultResponse)
async def test_notification(req: TestNotificationRequest):
    """Send a test notification."""
    _require_setup_needed()

    NotifierClass = getClient(req.type)
    if NotifierClass is None:
        return TestResultResponse(
            success=False,
            message_en=f"Unknown notification type: {req.type}",
            message_zh=f"未知的通知类型：{req.type}",
        )

    try:
        notifier = NotifierClass(token=req.token, chat_id=req.chat_id)
        async with notifier:
            # Send a simple test message
            data = {"chat_id": req.chat_id, "text": "AutoBangumi 通知测试成功！"}
            if req.type.lower() == "telegram":
                resp = await notifier.post_data(notifier.message_url, data)
                if resp.status_code == 200:
                    return TestResultResponse(
                        success=True,
                        message_en="Test notification sent successfully.",
                        message_zh="测试通知发送成功。",
                    )
                else:
                    return TestResultResponse(
                        success=False,
                        message_en="Failed to send test notification.",
                        message_zh="测试通知发送失败。",
                    )
            else:
                # For other providers, just verify the notifier can be created
                return TestResultResponse(
                    success=True,
                    message_en="Notification configuration is valid.",
                    message_zh="通知配置有效。",
                )
    except Exception as e:
        logger.error(f"[Setup] Notification test failed: {e}")
        return TestResultResponse(
            success=False,
            message_en=f"Notification test failed: {e}",
            message_zh=f"通知测试失败：{e}",
        )


@router.post("/complete", response_model=ResponseModel)
async def complete_setup(req: SetupCompleteRequest):
    """Save all wizard configuration and mark setup as complete."""
    _require_setup_needed()

    try:
        # 1. Update user credentials
        from module.database import Database

        with Database() as db:
            from module.models.user import UserUpdate

            db.user.update_user(
                "admin",
                UserUpdate(username=req.username, password=req.password),
            )

        # 2. Update configuration
        config_dict = settings.dict()
        config_dict["downloader"] = {
            "type": req.downloader_type,
            "host": req.downloader_host,
            "username": req.downloader_username,
            "password": req.downloader_password,
            "path": req.downloader_path,
            "ssl": req.downloader_ssl,
        }
        if req.notification_enable:
            config_dict["notification"] = {
                "enable": True,
                "type": req.notification_type,
                "token": req.notification_token,
                "chat_id": req.notification_chat_id,
            }

        settings.save(config_dict)
        # Reload settings in-place
        config_obj = Config.parse_obj(config_dict)
        settings.__dict__.update(config_obj.__dict__)

        # 3. Add RSS feed if provided
        if req.rss_url:
            from module.rss import RSSEngine

            with RSSEngine() as rss_engine:
                await rss_engine.add_rss(req.rss_url, name=req.rss_name or None)

        # 4. Create sentinel file
        SENTINEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        SENTINEL_PATH.touch()

        return ResponseModel(
            status=True,
            status_code=200,
            msg_en="Setup completed successfully.",
            msg_zh="设置完成。",
        )
    except Exception as e:
        logger.error(f"[Setup] Complete failed: {e}")
        return ResponseModel(
            status=False,
            status_code=500,
            msg_en=f"Setup failed: {e}",
            msg_zh=f"设置失败：{e}",
        )
