"""订阅提供商凭据仓储。读写以 TokenSet 为交换格式（extra 透明 JSON 编解码）。"""

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from module.models.llm_credential import LLMCredential, utcnow_iso
from module.parser.analyser.providers.base import TokenSet

logger = logging.getLogger(__name__)


class LLMCredentialDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _row(self, provider_id: str) -> Optional[LLMCredential]:
        result = await self.session.execute(
            select(LLMCredential).where(LLMCredential.provider_id == provider_id)
        )
        return result.scalars().first()

    async def get(self, provider_id: str) -> Optional[TokenSet]:
        row = await self._row(provider_id)
        if row is None:
            return None
        extra: dict = {}
        if row.extra:
            try:
                extra = json.loads(row.extra)
            except json.JSONDecodeError:
                logger.warning("Corrupt credential extra for %s", provider_id)
        return TokenSet(
            access_token=row.access_token,
            refresh_token=row.refresh_token,
            expires_at=row.expires_at,
            account_label=row.account_label,
            extra=extra,
        )

    async def upsert(self, provider_id: str, tokens: TokenSet) -> None:
        row = await self._row(provider_id)
        if row is None:
            row = LLMCredential(provider_id=provider_id)
        row.access_token = tokens.access_token
        row.refresh_token = tokens.refresh_token
        row.expires_at = tokens.expires_at
        row.account_label = tokens.account_label
        row.extra = json.dumps(tokens.extra, ensure_ascii=False)
        row.updated_at = utcnow_iso()
        self.session.add(row)
        await self.session.commit()

    async def delete(self, provider_id: str) -> bool:
        row = await self._row(provider_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(LLMCredential)
        )
        return int(result.scalar_one())
