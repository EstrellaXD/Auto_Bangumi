import asyncio
import ipaddress
import logging
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from module.conf import VERSION, settings
from module.core import AppContext
from module.models import Config, ResponseModel
from module.models.config import NotificationProvider as ProviderConfig
from module.network import RequestContent
from module.notification import PROVIDER_REGISTRY
from module.security.jwt import get_password_hash, verify_password

from .deps import get_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])

SENTINEL_PATH = Path("config/.setup_complete")


def _require_setup_needed():
    """Guard: raise 403 if setup is already completed."""
    if SENTINEL_PATH.exists():
        raise HTTPException(status_code=403, detail="Setup already completed.")
    # Allow setup in dev mode even if settings differ
    if VERSION != "DEV_VERSION" and settings.dict() != Config().dict():
        raise HTTPException(status_code=403, detail="Setup already completed.")


async def _require_default_admin_or_authenticated(request: Request) -> None:
    """Extra guard for /setup/complete specifically.

    ``_require_setup_needed()`` only compares the on-disk config to its
    defaults, which stays true on an upgraded install that never ran the
    wizard even after the real admin already changed their password some
    other way (e.g. the old settings UI). Without this check, an
    unauthenticated caller could hit /setup/complete on such an install and
    overwrite the admin's real credentials. Allow completion only if the
    caller already has a valid session, or the "admin" account still has the
    untouched factory-default password.
    """
    from module.security.api import get_current_user

    try:
        await get_current_user(request, token=request.cookies.get("token"))
        return
    except HTTPException:
        pass

    from module.database import Database

    async with Database() as db:
        try:
            user = await db.user.get_user("admin")
        except HTTPException:
            # No admin account yet (fresh install) — setup may proceed.
            return

    if not verify_password("adminadmin", user.password):
        raise HTTPException(status_code=403, detail="Setup already completed.")


def _validate_scheme(url: str) -> None:
    """Reject non-HTTP schemes and URLs without a hostname."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed.")
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: no hostname.")


def _validate_url(url: str) -> None:
    """Reject non-HTTP schemes and private/reserved/loopback IPs."""
    _validate_scheme(url)
    hostname = urlparse(url).hostname
    try:
        addrs = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Cannot resolve hostname.")
    for family, _, _, _, sockaddr in addrs:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_reserved or ip.is_loopback:
            raise HTTPException(
                status_code=400,
                detail="URLs pointing to private/reserved IPs are not allowed.",
            )


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
    # In dev mode, always allow setup wizard for testing
    if VERSION == "DEV_VERSION":
        need_setup = not SENTINEL_PATH.exists()
    else:
        need_setup = not SENTINEL_PATH.exists() and settings.dict() == Config().dict()
    return SetupStatusResponse(need_setup=need_setup, version=VERSION)


@router.post("/test-downloader", response_model=TestResultResponse)
async def test_downloader(req: TestDownloaderRequest):
    """Test connection to the download client."""
    _require_setup_needed()

    # Support mock mode for development
    if req.type == "mock":
        return TestResultResponse(
            success=True,
            message_en="Mock downloader enabled.",
            message_zh="已启用模拟下载器。",
        )

    scheme = "https" if req.ssl else "http"
    host = req.host if "://" in req.host else f"{scheme}://{req.host}"
    # Private/loopback IPs stay allowed (a LAN NAS is the normal case), but
    # only http/https schemes may be probed from this pre-auth endpoint (#1041).
    _validate_scheme(host)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if host is reachable and is qBittorrent
            resp = await client.get(host)
            if (
                "qbittorrent" not in resp.text.lower()
                and "vuetorrent" not in resp.text.lower()
            ):
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
            # qBittorrent < 5.2 answers 200 + "Ok."; >= 5.2 answers 204 with
            # an empty body on success (#1044). Keep the positive body check
            # for 200 so a proxy answering 200 + HTML is not reported as a
            # working login.
            if login_resp.status_code == 204 or (
                login_resp.status_code == 200 and "ok" in login_resp.text.lower()
            ):
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
        # Log the detail server-side only — this endpoint is reachable before
        # authentication, so raw errors must not be echoed back (#1041).
        logger.error(f"[Setup] Downloader test failed: {e}")
        return TestResultResponse(
            success=False,
            message_en="Connection failed.",
            message_zh="连接失败。",
        )


@router.post("/test-rss", response_model=TestResultResponse)
async def test_rss(req: TestRSSRequest):
    """Test an RSS feed URL."""
    _require_setup_needed()
    _validate_url(req.url)

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
            message_en="Failed to fetch RSS feed.",
            message_zh="获取 RSS 源失败。",
        )


@router.post("/test-notification", response_model=TestResultResponse)
async def test_notification(req: TestNotificationRequest):
    """Send a test notification."""
    _require_setup_needed()

    provider_cls = PROVIDER_REGISTRY.get(req.type.lower())
    if provider_cls is None:
        return TestResultResponse(
            success=False,
            message_en=f"Unknown notification type: {req.type}",
            message_zh=f"未知的通知类型：{req.type}",
        )

    try:
        # Create provider config
        config = ProviderConfig(
            type=req.type,
            enabled=True,
            token=req.token,
            chat_id=req.chat_id,
        )
        provider = provider_cls(config)
        async with provider:
            success, message = await provider.test()
            if success:
                return TestResultResponse(
                    success=True,
                    message_en="Test notification sent successfully.",
                    message_zh="测试通知发送成功。",
                )
            else:
                return TestResultResponse(
                    success=False,
                    message_en=f"Failed to send test notification: {message}",
                    message_zh=f"测试通知发送失败：{message}",
                )
    except Exception as e:
        logger.error(f"[Setup] Notification test failed: {e}")
        return TestResultResponse(
            success=False,
            message_en="Notification test failed.",
            message_zh="通知测试失败。",
        )


@router.post("/complete", response_model=ResponseModel)
async def complete_setup(
    req: SetupCompleteRequest,
    request: Request,
    ctx: AppContext = Depends(get_context),
):
    """Save all wizard configuration and mark setup as complete."""
    _require_setup_needed()
    await _require_default_admin_or_authenticated(request)

    try:
        # 1. Update user credentials
        from module.database import Database

        async with Database() as db:
            from module.models.user import UserUpdate

            await db.user.update_user(
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
                "providers": [
                    {
                        "type": req.notification_type,
                        "enabled": True,
                        "token": req.notification_token,
                        "chat_id": req.notification_chat_id,
                    }
                ],
            }

        # settings.save() does synchronous file I/O; keep it off the event loop.
        await asyncio.to_thread(settings.save, config_dict)
        # Route through the AppContext reload path so the shared httpx client,
        # notifier, and scheduler are rebuilt against the new config too — not
        # just the in-memory settings dict.
        await ctx.reload_settings()

        # 3. Add RSS feed if provided
        if req.rss_url:
            from module.rss import RSSEngine

            async with Database() as db:
                rss_engine = RSSEngine(db)
                await rss_engine.add_rss(req.rss_url, name=req.rss_name or None)

        # 4. Create sentinel file
        SENTINEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        SENTINEL_PATH.touch()
        await ctx.start_tasks()

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
            msg_en="Setup failed. Check the server log for details.",
            msg_zh="设置失败，请查看服务器日志。",
        )
