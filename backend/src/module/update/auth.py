"""One-way migration of legacy plaintext bearer tokens into the database."""

import asyncio
import logging
from collections.abc import Callable

from module.conf import settings
from module.database import Database

logger = logging.getLogger(__name__)


async def migrate_legacy_auth_tokens(
    *,
    database_factory: Callable[[], Database] = Database,
    runtime_settings=settings,
) -> int:
    login_tokens = list(runtime_settings.security.login_tokens)
    mcp_tokens = list(runtime_settings.security.mcp_tokens)
    if not login_tokens and not mcp_tokens:
        return 0

    async with database_factory() as db:
        users = [user for user in await db.user.list_users() if user.enabled]
        if not users:
            logger.warning("[Auth] Legacy tokens remain in config: no enabled user")
            return 0
        owner = users[0]
        if owner.id is None:
            raise RuntimeError("Persisted token owner has no primary key")
        for index, raw_token in enumerate(login_tokens, start=1):
            await db.auth.import_api_token(
                owner.id,
                raw_token,
                name=f"Imported API token {index}",
                scope="api",
            )
        for index, raw_token in enumerate(mcp_tokens, start=1):
            await db.auth.import_api_token(
                owner.id,
                raw_token,
                name=f"Imported MCP token {index}",
                scope="mcp",
            )

    runtime_settings.security.login_tokens = []
    runtime_settings.security.mcp_tokens = []
    await asyncio.to_thread(runtime_settings.save)
    imported = len(login_tokens) + len(mcp_tokens)
    logger.info("[Auth] Imported %s legacy bearer tokens", imported)
    return imported
