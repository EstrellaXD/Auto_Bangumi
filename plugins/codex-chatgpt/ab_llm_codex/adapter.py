"""ChatGPT (Codex) 订阅适配器（device flow → codex responses 端点）。

⚠️ 自担风险：ChatGPT 订阅凭据仅供官方 Codex 客户端使用，token 被限定到
Codex client。第三方使用未获官方书面许可（灰色默许），originator 白名单
是其执法手段，可能收紧。

⚠️ 待核实（研究标注中/低置信度）：device code 端点 URL、responses 端点的
精确请求头大小写。发货前须对 openai/codex 源码复核；下方以结构化占位实现，
便于单元测试与后续替换。

流程：
1. device flow：POST auth.openai.com/oauth/device/code → user_code；
   服务端轮询 oauth/token 换 access_token（JWT，含 chatgpt_account_id）。
2. 刷新：refresh_token 换新 access_token（临期主动刷新）。
3. 推理：POST chatgpt.com/backend-api/codex/responses（Responses API），
   头带 Bearer + ChatGPT-Account-Id + originator=codex_cli_rs。
"""

import base64
import json
import time

from module.parser.analyser.providers.base import (
    AdapterContext,
    AuthChallenge,
    AuthExpiredError,
    LLMProviderAdapter,
    ProviderInfo,
    TokenSet,
)
from module.parser.analyser.providers.schema import DEFAULT_PROMPT, EPISODE_JSON_SCHEMA

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"  # Codex CLI 公开应用
# TODO(ship): 对 openai/codex 源码复核以下端点/头
DEVICE_CODE_URL = "https://auth.openai.com/oauth/device/code"
TOKEN_URL = "https://auth.openai.com/oauth/token"
RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
DEFAULT_MODEL = "gpt-5.1-codex"

_ORIGINATOR = "codex_cli_rs"


def _decode_account_id(access_token: str) -> str:
    """从 JWT 的 chatgpt_account_id claim 取账号 id（best-effort，失败返回空）。"""
    try:
        payload_b64 = access_token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        return claims.get("chatgpt_account_id", "") or claims.get(
            "https://api.openai.com/auth", {}
        ).get("chatgpt_account_id", "")
    except Exception:
        return ""


class CodexChatgptAdapter(LLMProviderAdapter):
    info = ProviderInfo(
        id="codex-chatgpt",
        display_name="ChatGPT (Codex)",
        auth_kind="device_code",
        builtin=False,
        default_model=DEFAULT_MODEL,
    )

    def __init__(self, ctx: AdapterContext) -> None:
        super().__init__(ctx)
        self.model = ctx.model or DEFAULT_MODEL
        self._http_client = ctx.build_http_client(ctx.timeout)

    # ------------------------------------------------------------ device flow

    async def begin_auth(self) -> AuthChallenge:
        resp = await self._http_client.post(
            DEVICE_CODE_URL,
            data={"client_id": CLIENT_ID, "scope": "openid profile email"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        state = json.dumps(
            {"device_code": data["device_code"], "interval": data.get("interval", 5)}
        )
        return AuthChallenge(
            method="device_code",
            user_code=data["user_code"],
            verification_uri=data.get("verification_uri_complete")
            or data.get("verification_uri"),
            expires_in=data.get("expires_in", 900),
            state=state,
        )

    async def complete_auth(self, state: str, user_input: str = "") -> TokenSet:
        blob = json.loads(state)
        resp = await self._http_client.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "device_code": blob["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        if "access_token" not in data:
            raise AuthExpiredError(data.get("error", "authorization_pending"))
        return self._tokens_from_response(data)

    def _tokens_from_response(self, data: dict) -> TokenSet:
        access = data["access_token"]
        account_id = _decode_account_id(access)
        expires_at = time.time() + float(data.get("expires_in", 3600))
        return TokenSet(
            access_token=access,
            refresh_token=data.get("refresh_token", ""),
            expires_at=expires_at,
            account_label="ChatGPT",
            extra={"account_id": account_id},
        )

    async def refresh(self, tokens: TokenSet) -> TokenSet:
        if not tokens.refresh_token:
            raise AuthExpiredError("no refresh token")
        resp = await self._http_client.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": tokens.refresh_token,
            },
            headers={"Accept": "application/json"},
        )
        if resp.status_code >= 400:
            raise AuthExpiredError("refresh failed")
        data = resp.json()
        refreshed = self._tokens_from_response(data)
        # 有些实现刷新响应不回 refresh_token，沿用旧的
        if not refreshed.refresh_token:
            refreshed = refreshed.model_copy(
                update={"refresh_token": tokens.refresh_token}
            )
        return refreshed

    # ------------------------------------------------------------ inference

    async def _valid_tokens(self) -> TokenSet:
        tokens = await self.ctx.credentials.load()
        if tokens is None or not tokens.access_token:
            raise AuthExpiredError("ChatGPT is not connected")
        if tokens.expires_at is not None and tokens.expires_at - 60 < time.time():
            tokens = await self.refresh(tokens)
            await self.ctx.credentials.save(tokens)
        return tokens

    async def parse(self, raw: str) -> dict | None:
        tokens = await self._valid_tokens()
        resp = await self._http_client.post(
            RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {tokens.access_token}",
                "ChatGPT-Account-Id": tokens.extra.get("account_id", ""),
                "originator": _ORIGINATOR,
                "User-Agent": _ORIGINATOR,
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "instructions": DEFAULT_PROMPT,
                "input": raw,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "episode",
                        "schema": EPISODE_JSON_SCHEMA,
                    }
                },
            },
        )
        if resp.status_code == 401:
            raise AuthExpiredError("ChatGPT token rejected")
        resp.raise_for_status()
        return self._extract_json(resp.json())

    def _extract_json(self, data: dict) -> dict | None:
        # Responses API：output[].content[].text 承载 JSON 字符串
        try:
            for item in data.get("output", []):
                for block in item.get("content", []):
                    text = block.get("text")
                    if text:
                        return json.loads(text)
        except (json.JSONDecodeError, AttributeError):
            return None
        return None

    async def list_models(self) -> list[str]:
        # Codex 后端不暴露稳定的 /models；返回已知默认，交由用户自定义
        return [DEFAULT_MODEL, "gpt-5.1"]
