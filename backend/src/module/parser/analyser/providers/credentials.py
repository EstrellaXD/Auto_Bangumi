"""订阅提供商凭据访问 + 进程内 auth generation 计数。

- ``CredentialStore``：适配器唯一被允许的凭据通道（provider 域内
  load/save/clear），内部 session-per-operation 开库。
- ``auth_generation``：连接/断开时 bump（静默刷新不 bump），
  title_parser 把它掺进单例键实现"换号即重建、刷新不抖动"。
  AB 单进程部署，进程内计数即可。
"""

from typing import Optional

from .base import TokenSet

_generations: dict[str, int] = {}


def auth_generation(provider_id: str) -> int:
    return _generations.get(provider_id, 0)


def bump_auth_generation(provider_id: str) -> None:
    _generations[provider_id] = auth_generation(provider_id) + 1


class CredentialStore:
    """单一提供商的凭据读写句柄（注入 AdapterContext.credentials）。"""

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id

    async def load(self) -> Optional[TokenSet]:
        # 延迟导入打破 database ↔ providers 循环（database 的 repo 依赖
        # providers.base 的 TokenSet）。
        from module.database import Database

        async with Database() as db:
            return await db.llm_credential.get(self.provider_id)

    async def save(self, tokens: TokenSet) -> None:
        """持久化凭据（含静默刷新——不 bump generation）。"""
        from module.database import Database

        async with Database() as db:
            await db.llm_credential.upsert(self.provider_id, tokens)

    async def clear(self) -> None:
        from module.database import Database

        async with Database() as db:
            await db.llm_credential.delete(self.provider_id)
