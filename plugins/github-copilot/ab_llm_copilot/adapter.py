"""GitHub Copilot 订阅适配器（device flow → OpenAI 兼容端点）。

⚠️ 自担风险：Copilot 内部端点仅供官方客户端使用，第三方调用可能违反
GitHub 条款并触发滥用检测。低请求量降低但不消除风险。

流程（2026-07 核实）：
1. device flow：POST github.com/login/device/code → 展示 user_code；
   服务端轮询 login/oauth/access_token 换取长期 ``ghu_`` token。
2. 每次调用前用 ``ghu_`` 换短命 Copilot token（~30min，主动刷新）：
   GET api.github.com/copilot_internal/v2/token。
3. 推理走 api.githubcopilot.com/chat/completions（OpenAI 兼容），
   仿编辑器请求头。结构化输出用 tool-calling 兜底。
"""

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

CLIENT_ID = "Iv1.b507a08c87ecfe98"  # VS Code Copilot 公开应用
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
API_BASE = "https://api.githubcopilot.com"
DEFAULT_MODEL = "gpt-4o"

# 仿 VS Code Copilot 客户端的请求头（值会随版本漂移，保持可配置）。
_EDITOR_HEADERS = {
    "Editor-Version": "vscode/1.95.0",
    "Editor-Plugin-Version": "copilot-chat/0.22.0",
    "Copilot-Integration-Id": "vscode-chat",
    "User-Agent": "GithubCopilot/1.155.0",
}

_EPISODE_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_episode",
        "description": "Return the structured anime episode fields.",
        "parameters": EPISODE_JSON_SCHEMA,
    },
}


class GithubCopilotAdapter(LLMProviderAdapter):
    info = ProviderInfo(
        id="github-copilot",
        display_name="GitHub Copilot",
        auth_kind="device_code",
        builtin=False,
        default_model=DEFAULT_MODEL,
    )

    def __init__(self, ctx: AdapterContext) -> None:
        super().__init__(ctx)
        self.model = ctx.model or DEFAULT_MODEL
        self._http_client = ctx.build_http_client(ctx.timeout)
        # (copilot_token, expires_at) 短命缓存
        self._copilot_token: tuple[str, float] | None = None

    # ------------------------------------------------------------ device flow

    async def begin_auth(self) -> AuthChallenge:
        resp = await self._http_client.post(
            DEVICE_CODE_URL,
            data={"client_id": CLIENT_ID, "scope": "read:user"},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        # device_code 是敏感态，藏进 state（服务端 pending 存储，不下发前端）
        state = json.dumps(
            {"device_code": data["device_code"], "interval": data.get("interval", 5)}
        )
        return AuthChallenge(
            method="device_code",
            user_code=data["user_code"],
            verification_uri=data["verification_uri"],
            expires_in=data.get("expires_in", 900),
            state=state,
        )

    async def complete_auth(self, state: str, user_input: str = "") -> TokenSet:
        """轮询一次 access_token 端点（服务端轮询循环每次调用一次本方法）。"""
        blob = json.loads(state)
        resp = await self._http_client.post(
            ACCESS_TOKEN_URL,
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
            # authorization_pending / slow_down：告知调用方继续轮询
            raise AuthExpiredError(data.get("error", "authorization_pending"))
        return TokenSet(
            access_token=data["access_token"],  # ghu_ 长期 token
            account_label="GitHub Copilot",
        )

    async def refresh(self, tokens: TokenSet) -> TokenSet:
        # ghu_ token 本身长期有效；短命 Copilot token 在 _ensure_copilot_token 刷新
        return tokens

    # ------------------------------------------------------------ inference

    async def _ensure_copilot_token(self, ghu_token: str) -> str:
        now = time.time()
        if self._copilot_token is not None and self._copilot_token[1] - 60 > now:
            return self._copilot_token[0]
        resp = await self._http_client.get(
            COPILOT_TOKEN_URL,
            headers={
                "Authorization": f"token {ghu_token}",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["token"]
        expires_at = float(data.get("expires_at", now + 1500))
        self._copilot_token = (token, expires_at)
        return token

    async def parse(self, raw: str) -> dict | None:
        tokens = await self.ctx.credentials.load()
        if tokens is None or not tokens.access_token:
            raise AuthExpiredError("GitHub Copilot is not connected")
        copilot_token = await self._ensure_copilot_token(tokens.access_token)
        resp = await self._http_client.post(
            f"{API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {copilot_token}",
                "Content-Type": "application/json",
                **_EDITOR_HEADERS,
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": DEFAULT_PROMPT},
                    {"role": "user", "content": raw},
                ],
                "tools": [_EPISODE_TOOL],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": "emit_episode"},
                },
                "temperature": 0,
            },
        )
        if resp.status_code == 401:
            self._copilot_token = None
            raise AuthExpiredError("Copilot token rejected")
        resp.raise_for_status()
        data = resp.json()
        try:
            call = data["choices"][0]["message"]["tool_calls"][0]
            return json.loads(call["function"]["arguments"])
        except (KeyError, IndexError, json.JSONDecodeError):
            return None

    async def list_models(self) -> list[str]:
        tokens = await self.ctx.credentials.load()
        if tokens is None or not tokens.access_token:
            raise AuthExpiredError("GitHub Copilot is not connected")
        copilot_token = await self._ensure_copilot_token(tokens.access_token)
        resp = await self._http_client.get(
            f"{API_BASE}/models",
            headers={"Authorization": f"Bearer {copilot_token}", **_EDITOR_HEADERS},
        )
        resp.raise_for_status()
        data = resp.json()
        return sorted(m["id"] for m in data.get("data", []))
