"""
Passkey 数据库操作层
"""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from module.models.passkey import Passkey, PasskeyList

logger = logging.getLogger(__name__)


class PasskeyDatabase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_passkey(self, passkey: Passkey) -> Passkey:
        """创建新的 Passkey 凭证"""
        self.session.add(passkey)
        await self.session.commit()
        await self.session.refresh(passkey)
        logger.info(f"Created passkey '{passkey.name}' for user_id={passkey.user_id}")
        return passkey

    async def get_passkey_by_credential_id(
        self, credential_id: str
    ) -> Optional[Passkey]:
        """通过 credential_id 查找 Passkey（用于认证）"""
        statement = select(Passkey).where(Passkey.credential_id == credential_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_passkeys_by_user_id(self, user_id: int) -> List[Passkey]:
        """获取用户的所有 Passkey"""
        statement = select(Passkey).where(Passkey.user_id == user_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_passkey_by_id(self, passkey_id: int, user_id: int) -> Passkey:
        """获取特定 Passkey（带权限检查）"""
        statement = select(Passkey).where(
            Passkey.id == passkey_id, Passkey.user_id == user_id
        )
        result = await self.session.execute(statement)
        passkey = result.scalar_one_or_none()
        if not passkey:
            raise HTTPException(status_code=404, detail="Passkey not found")
        return passkey

    async def update_passkey_usage(self, passkey: Passkey, new_sign_count: int):
        """更新 Passkey 使用记录（签名计数器 + 最后使用时间）"""
        passkey.sign_count = new_sign_count
        passkey.last_used_at = datetime.utcnow()
        self.session.add(passkey)
        await self.session.commit()

    async def delete_passkey(self, passkey_id: int, user_id: int) -> bool:
        """删除 Passkey"""
        passkey = await self.get_passkey_by_id(passkey_id, user_id)
        await self.session.delete(passkey)
        await self.session.commit()
        logger.info(f"Deleted passkey id={passkey_id} for user_id={user_id}")
        return True

    def to_list_model(self, passkey: Passkey) -> PasskeyList:
        """转换为安全的列表展示模型"""
        return PasskeyList(
            id=passkey.id,
            name=passkey.name,
            created_at=passkey.created_at,
            last_used_at=passkey.last_used_at,
            backup_eligible=passkey.backup_eligible,
            aaguid=passkey.aaguid,
        )
