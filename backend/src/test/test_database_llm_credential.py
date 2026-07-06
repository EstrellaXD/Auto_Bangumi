"""LLMCredentialDatabase — 订阅提供商凭据表（token 只存服务端）。"""

from module.database.llm_credential import LLMCredentialDatabase
from module.parser.analyser.providers.base import TokenSet


async def test_upsert_inserts_then_updates(db_session):
    db = LLMCredentialDatabase(db_session)
    tokens = TokenSet(
        access_token="at-1",
        refresh_token="rt-1",
        expires_at=1000.0,
        account_label="user@example.com",
        extra={"account_id": "acc-1"},
    )
    await db.upsert("github-copilot", tokens)

    loaded = await db.get("github-copilot")
    assert loaded is not None
    assert loaded.access_token == "at-1"
    assert loaded.account_label == "user@example.com"
    assert loaded.extra == {"account_id": "acc-1"}

    await db.upsert("github-copilot", TokenSet(access_token="at-2"))
    updated = await db.get("github-copilot")
    assert updated.access_token == "at-2"
    assert await db.count() == 1  # 同 provider 只有一行


async def test_get_unknown_provider_returns_none(db_session):
    db = LLMCredentialDatabase(db_session)
    assert await db.get("nonexistent") is None


async def test_delete_removes_row(db_session):
    db = LLMCredentialDatabase(db_session)
    await db.upsert("codex-chatgpt", TokenSet(access_token="at"))

    assert await db.delete("codex-chatgpt") is True
    assert await db.get("codex-chatgpt") is None
    assert await db.delete("codex-chatgpt") is False
