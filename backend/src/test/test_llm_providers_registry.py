"""ProviderRegistry — LLM 提供商注册表（内置适配器解析与列举）。"""

import pytest

from module.parser.analyser.providers import registry
from module.parser.analyser.providers.base import LLMProviderAdapter


class TestResolve:
    def test_resolves_builtin_providers(self):
        for provider_id in ("openai", "anthropic", "gemini"):
            adapter_cls = registry.resolve(provider_id)
            assert issubclass(adapter_cls, LLMProviderAdapter)
            assert adapter_cls.info.id == provider_id
            assert adapter_cls.info.builtin is True

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            registry.resolve("nonexistent")


class TestListInfos:
    def test_lists_builtins_with_api_key_auth(self):
        infos = {info.id: info for info in registry.list_infos()}
        assert {"openai", "anthropic", "gemini"} <= set(infos)
        for provider_id in ("openai", "anthropic", "gemini"):
            assert infos[provider_id].auth_kind == "api_key"

    def test_openai_needs_base_url(self):
        infos = {info.id: info for info in registry.list_infos()}
        assert infos["openai"].needs_base_url is True
        assert infos["anthropic"].needs_base_url is False
