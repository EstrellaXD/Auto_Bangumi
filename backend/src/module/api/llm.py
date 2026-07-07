"""LLM 提供商与订阅认证 API（/config/llm/*）。

- providers：内置 + 预设 + 已安装插件的合并视图（含连接状态）。
- auth begin/complete/status/disconnect：订阅类提供商的授权流程；
  PKCE verifier / device_code 等敏感中间态留服务端 ``_PENDING``，
  device-code 轮询在服务端 asyncio task 完成，token 永不下发前端。
"""

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from module.api.deps import get_context
from module.conf import VERSION
from module.core import AppContext
from module.database import Database
from module.parser.analyser.llm import _build_http_client
from module.parser.analyser.providers.base import (
    AdapterContext,
    AuthChallenge,
    AuthExpiredError,
    LLMProviderAdapter,
)
from module.parser.analyser.providers.credentials import (
    CredentialStore,
    bump_auth_generation,
)
from module.parser.analyser.providers.registry import registry
from module.security.api import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config/llm", tags=["config"])

# 不透明 handle -> 待完成授权的服务端明细。``blob`` 是适配器 begin_auth
# 返回的 state（device_code / PKCE verifier 等敏感态），只留服务端，绝不
# 下发前端——前端只拿到 handle 用于轮询 status / 回传 redirect code。
_PENDING: dict[str, "PendingAuth"] = {}
_PENDING_TTL = 900.0
# 保留 device-flow 轮询任务的强引用，防止被 GC。
_POLL_TASKS: set = set()


@dataclass
class PendingAuth:
    provider_id: str
    created: float
    expires: float
    blob: str = ""  # 适配器 challenge.state（敏感，服务端专用）
    extra: dict = field(default_factory=dict)


def _prune_pending(now: float) -> None:
    for state in [s for s, p in _PENDING.items() if p.expires < now]:
        _PENDING.pop(state, None)


def _make_adapter(provider_id: str) -> LLMProviderAdapter:
    adapter_cls = registry.resolve(provider_id)
    ctx = AdapterContext(
        model=adapter_cls.info.default_model,
        build_http_client=_build_http_client,
        credentials=CredentialStore(provider_id),
    )
    return adapter_cls(ctx)


async def _provider_status(provider_id: str) -> dict:
    """返回可下发前端的连接状态（绝不含 token）。"""
    tokens = await CredentialStore(provider_id).load()
    if tokens is None:
        return {"connected": False, "account_label": "", "expires_at": None}
    return {
        "connected": True,
        "account_label": tokens.account_label,
        "expires_at": tokens.expires_at,
    }


class ProviderView(BaseModel):
    id: str
    display_name: str
    auth_kind: str
    builtin: bool
    needs_base_url: bool
    preset_base_url: str
    default_model: str
    plugin_version: str | None = None
    connected: bool = False
    account_label: str = ""
    expires_at: float | None = None


class ProvidersResponse(BaseModel):
    providers: list[ProviderView]


@router.get(
    "/providers",
    response_model=ProvidersResponse,
    dependencies=[Depends(get_current_user)],
)
async def list_providers():
    infos = registry.list_infos()
    # 订阅类提供商的连接状态在一个 DB 会话里批量取，避免每个提供商各开一次连接。
    statuses: dict[str, dict] = {}
    subscription_ids = [i.id for i in infos if i.auth_kind != "api_key"]
    if subscription_ids:
        async with Database() as db:
            for pid in subscription_ids:
                tokens = await db.llm_credential.get(pid)
                statuses[pid] = (
                    {"connected": False, "account_label": "", "expires_at": None}
                    if tokens is None
                    else {
                        "connected": True,
                        "account_label": tokens.account_label,
                        "expires_at": tokens.expires_at,
                    }
                )
    views: list[ProviderView] = []
    for info in infos:
        status = statuses.get(info.id, {})
        views.append(
            ProviderView(
                id=info.id,
                display_name=info.display_name,
                auth_kind=info.auth_kind,
                builtin=info.builtin,
                needs_base_url=info.needs_base_url,
                preset_base_url=info.preset_base_url,
                default_model=info.default_model,
                plugin_version=info.plugin_version,
                connected=status.get("connected", False),
                account_label=status.get("account_label", ""),
                expires_at=status.get("expires_at"),
            )
        )
    return ProvidersResponse(providers=views)


@router.post(
    "/providers/{provider_id}/install",
    dependencies=[Depends(get_current_user)],
)
async def install_provider(provider_id: str, ctx: AppContext = Depends(get_context)):
    from module.llm_plugins import PluginInstaller
    from module.notification import LLMPluginInstallFailedEvent

    installer = PluginInstaller(app_version=VERSION)
    result = await installer.install(provider_id)
    if not result.success:
        try:
            await ctx.notifier.send_event(
                LLMPluginInstallFailedEvent(
                    plugin_id=provider_id,
                    version=result.version,
                    message=result.message,
                )
            )
        except Exception:
            logger.debug("install-failure notification best-effort failed")
        raise HTTPException(status_code=400, detail=result.message)
    return {"success": True, "version": result.version}


@router.delete(
    "/providers/{provider_id}",
    dependencies=[Depends(get_current_user)],
)
async def uninstall_provider(provider_id: str):
    from module.llm_plugins import PluginInstaller

    installer = PluginInstaller(app_version=VERSION)
    result = await installer.uninstall(provider_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {"success": True}


class AuthCompleteRequest(BaseModel):
    state: str
    code: str = ""


def _poll_interval(blob: str) -> int:
    try:
        return max(1, int(json.loads(blob).get("interval", 5)))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 5


async def _device_poll_loop(provider_id: str, handle: str, expires_in: int) -> None:
    """device flow 服务端轮询：到期前按 interval 反复调 complete_auth，
    成功即写库并 bump generation。前端只需轮询 auth/status。"""
    deadline = time.monotonic() + min(float(expires_in), _PENDING_TTL)
    try:
        adapter = _make_adapter(provider_id)
    except ValueError:
        _PENDING.pop(handle, None)
        return
    try:
        while time.monotonic() < deadline:
            pending = _PENDING.get(handle)
            if pending is None:
                return  # 被取消 / 已完成 / 断开
            await asyncio.sleep(_poll_interval(pending.blob))
            pending = _PENDING.get(handle)
            if pending is None:
                return
            try:
                tokens = await adapter.complete_auth(pending.blob)
            except AuthExpiredError:
                continue  # authorization_pending / slow_down：继续轮询
            except Exception as e:  # noqa: BLE001
                logger.warning("device auth poll failed for %s: %s", provider_id, e)
                continue
            await CredentialStore(provider_id).save(tokens)
            bump_auth_generation(provider_id)
            _PENDING.pop(handle, None)
            logger.info("LLM provider %s connected via device flow", provider_id)
            return
    finally:
        await adapter.aclose()
        _PENDING.pop(handle, None)


def _store_pending(provider_id: str, challenge: AuthChallenge) -> str:
    """把敏感 blob 存服务端，返回给前端的不透明 handle。"""
    now = time.monotonic()
    _prune_pending(now)
    handle = secrets.token_urlsafe(24)
    _PENDING[handle] = PendingAuth(
        provider_id=provider_id,
        created=now,
        expires=now + min(float(challenge.expires_in), _PENDING_TTL),
        blob=challenge.state,
    )
    return handle


@router.post(
    "/providers/{provider_id}/auth/begin",
    dependencies=[Depends(get_current_user)],
)
async def auth_begin(provider_id: str):
    try:
        adapter = _make_adapter(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        challenge = await adapter.begin_auth()
    except NotImplementedError:
        raise HTTPException(
            status_code=400, detail="Provider does not support interactive auth"
        )
    finally:
        await adapter.aclose()

    handle = _store_pending(provider_id, challenge)
    if challenge.method == "device_code":
        # 服务端起轮询任务；前端只轮询 auth/status。
        task = asyncio.create_task(
            _device_poll_loop(provider_id, handle, challenge.expires_in)
        )
        _POLL_TASKS.add(task)
        task.add_done_callback(_POLL_TASKS.discard)

    # 返回前端：state 用不透明 handle，绝不含 device_code / verifier。
    return {
        "method": challenge.method,
        "authorize_url": challenge.authorize_url,
        "user_code": challenge.user_code,
        "verification_uri": challenge.verification_uri,
        "expires_in": challenge.expires_in,
        "state": handle,
    }


@router.post(
    "/providers/{provider_id}/auth/complete",
    dependencies=[Depends(get_current_user)],
)
async def auth_complete(provider_id: str, req: AuthCompleteRequest):
    """redirect_paste 流程：前端回传授权 code；device flow 由服务端轮询完成。"""
    pending = _PENDING.get(req.state)
    if pending is None or pending.provider_id != provider_id:
        raise HTTPException(status_code=400, detail="Unknown or expired auth state")
    try:
        adapter = _make_adapter(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        tokens = await adapter.complete_auth(pending.blob, req.code)
    except Exception as e:
        logger.warning("LLM auth complete failed for %s: %s", provider_id, e)
        raise HTTPException(status_code=400, detail="Authorization failed")
    finally:
        await adapter.aclose()
    await CredentialStore(provider_id).save(tokens)
    bump_auth_generation(provider_id)
    _PENDING.pop(req.state, None)
    return {"connected": True, "account_label": tokens.account_label}


@router.get(
    "/providers/{provider_id}/auth/status",
    dependencies=[Depends(get_current_user)],
)
async def auth_status(provider_id: str):
    return await _provider_status(provider_id)


@router.delete(
    "/providers/{provider_id}/auth",
    dependencies=[Depends(get_current_user)],
)
async def auth_disconnect(provider_id: str):
    store = CredentialStore(provider_id)
    tokens = await store.load()
    if tokens is not None:
        try:
            adapter = _make_adapter(provider_id)
        except ValueError:
            adapter = None
        if adapter is not None:
            try:
                await adapter.revoke(tokens)
            except Exception as e:
                logger.debug("revoke best-effort failed for %s: %s", provider_id, e)
            finally:
                await adapter.aclose()
    await store.clear()
    bump_auth_generation(provider_id)
    return {"connected": False}
