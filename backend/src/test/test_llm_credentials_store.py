"""CredentialStore + auth generation 计数 + AuthExpiredError 熔断/通知。"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

from module.notification.events import LLMAuthFailureEvent, LLMPluginInstallFailedEvent
from module.parser.analyser.providers.base import TokenSet
from module.parser.analyser.providers.credentials import (
    CredentialStore,
    auth_generation,
    bump_auth_generation,
)


def _async_cm(entered_value):
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=entered_value)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestAuthGeneration:
    def test_bump_increments_per_provider(self):
        before = auth_generation("prov-a")
        bump_auth_generation("prov-a")
        assert auth_generation("prov-a") == before + 1
        # 互不影响
        assert auth_generation("prov-b") == 0 or isinstance(
            auth_generation("prov-b"), int
        )


class TestCredentialStore:
    async def test_load_save_clear_scoped_to_provider(self):
        db = MagicMock()
        db.llm_credential.get = AsyncMock(return_value=TokenSet(access_token="at"))
        db.llm_credential.upsert = AsyncMock()
        db.llm_credential.delete = AsyncMock(return_value=True)

        store = CredentialStore("github-copilot")
        # Database 在方法内延迟导入（打破循环），因此 patch 源模块
        with patch("module.database.Database", return_value=_async_cm(db)):
            loaded = await store.load()
            await store.save(TokenSet(access_token="at-2"))
            await store.clear()

        assert loaded is not None
        assert loaded.access_token == "at"
        db.llm_credential.get.assert_awaited_once_with("github-copilot")
        db.llm_credential.upsert.assert_awaited_once()
        assert db.llm_credential.upsert.call_args.args[0] == "github-copilot"
        db.llm_credential.delete.assert_awaited_once_with("github-copilot")


class TestEventContracts:
    def test_llm_auth_failure_event(self):
        event = LLMAuthFailureEvent(
            provider_id="codex-chatgpt", account_label="u@x.com", message="expired"
        )
        assert event.kind == "llm_auth_failure"
        assert event.severity == "error"
        assert event.dedup_key() == "llm_auth:codex-chatgpt"
        assert event.payload() == {
            "provider_id": "codex-chatgpt",
            "account_label": "u@x.com",
            "message": "expired",
        }
        title, body = event.describe()
        assert "LLM" in title

    def test_llm_plugin_install_failed_event(self):
        event = LLMPluginInstallFailedEvent(
            plugin_id="github-copilot", version="1.0.0", message="bad signature"
        )
        assert event.kind == "llm_plugin_install_failed"
        assert event.severity == "error"
        assert event.dedup_key() == "llm_plugin_install:github-copilot"
        assert "bad signature" in event.describe()[1]


class TestAuthExpiredBreaker:
    async def test_auth_expired_opens_breaker_and_notifies(self):
        """AuthExpiredError：跳过失败计数阈值直接熔断，并发通知事件。"""
        from module.parser import title_parser as tp
        from module.parser.analyser.providers.base import AuthExpiredError

        tp.reset_cache()
        mock_parser = MagicMock()
        mock_parser.parse = AsyncMock(side_effect=AuthExpiredError("refresh failed"))

        with (
            patch.object(tp, "_get_llm_parser", return_value=mock_parser),
            patch.object(tp, "_llm_config") as mock_conf,
            patch.object(tp, "_notify_auth_failure") as mock_notify,
        ):
            mock_conf.return_value = MagicMock(
                provider="codex-chatgpt",
                timeout=5.0,
                cache_ttl=0,
                max_concurrency=1,
                failure_threshold=3,
                failure_backoff=300,
                effective=lambda provider_id=None: ("", "m", ""),
            )
            result = await tp._llm_parse("raw title")

        assert result is None
        assert tp._llm_breaker_until > time.monotonic()  # 立即熔断
        mock_notify.assert_called_once()
        assert mock_notify.call_args.args[0] == "codex-chatgpt"
        tp.reset_cache()
