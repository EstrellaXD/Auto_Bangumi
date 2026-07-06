"""国产提供商 base_url 预设 + OpenAI 兼容降级路径 + 按提供商配置覆盖。"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from module.api.config import _restore_masked, _sanitize_dict
from module.models.config import LLM, LLMProviderOverride
from module.parser.analyser.llm import LLMParser
from module.parser.analyser.providers import registry
from module.parser.analyser.providers.builtin import OpenAIAdapter

EPISODE_DICT = {
    "title_en": "Test",
    "title_zh": None,
    "title_jp": None,
    "season": 1,
    "season_raw": "",
    "episode": 5,
    "sub": "CHS",
    "group": "G",
    "resolution": "1080p",
    "source": "Web",
}


class TestPresetRegistry:
    def test_presets_listed_with_endpoints(self):
        infos = {i.id: i for i in registry.list_infos()}
        assert infos["deepseek"].preset_base_url == "https://api.deepseek.com"
        assert infos["zai"].preset_base_url == "https://api.z.ai/api/paas/v4"
        assert (
            infos["zai-cn"].preset_base_url
            == "https://open.bigmodel.cn/api/coding/paas/v4"
        )
        assert infos["kimi"].preset_base_url == "https://api.moonshot.ai/v1"
        assert infos["kimi-cn"].preset_base_url == "https://api.moonshot.cn/v1"
        assert infos["minimax"].preset_base_url == "https://api.minimax.io/v1"
        for preset_id in ("zai", "zai-cn", "minimax", "minimax-cn", "deepseek", "kimi"):
            assert infos[preset_id].auth_kind == "api_key"
            assert infos[preset_id].builtin is False
            assert infos[preset_id].needs_base_url is True

    def test_preset_resolves_to_openai_dialect_adapter(self):
        adapter_cls = registry.resolve("kimi")
        assert issubclass(adapter_cls, OpenAIAdapter)
        assert adapter_cls.info.id == "kimi"

    def test_preset_base_url_fills_when_config_blank(self):
        parser = LLMParser(api_key="sk-test", provider="deepseek", model="m")
        assert str(parser._openai_client.base_url).startswith(
            "https://api.deepseek.com"
        )

    def test_explicit_base_url_overrides_preset(self):
        parser = LLMParser(
            api_key="sk-test",
            provider="deepseek",
            model="m",
            base_url="http://localhost:11434/v1",
        )
        assert str(parser._openai_client.base_url).startswith(
            "http://localhost:11434/v1"
        )


class TestJsonObjectFallback:
    """json_schema 不受支持的预设（DeepSeek/MiniMax）降级为
    json_object + schema 写入提示词。"""

    def _completion(self, content: str):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    async def test_deepseek_uses_json_object_mode(self):
        parser = LLMParser(api_key="sk-test", provider="deepseek", model="m")
        mock_create = AsyncMock(return_value=self._completion(json.dumps(EPISODE_DICT)))
        parser._openai_client.chat.completions.create = mock_create

        result = await parser.parse("[G] Test - 05 [1080p]")

        assert result == EPISODE_DICT
        kwargs = mock_create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
        # schema 字段清单进入系统提示词
        assert "title_en" in kwargs["messages"][0]["content"]

    async def test_json_object_mode_invalid_json_returns_none(self):
        parser = LLMParser(api_key="sk-test", provider="minimax", model="m")
        parser._openai_client.chat.completions.create = AsyncMock(
            return_value=self._completion("not json")
        )
        assert await parser.parse("raw") is None

    async def test_openai_still_uses_beta_parse(self):
        """内置 openai 提供商不受降级影响，仍走 beta 结构化输出。"""
        parser = LLMParser(api_key="sk-test", provider="openai", model="m")
        mock_parse = AsyncMock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=SimpleNamespace(model_dump=lambda: EPISODE_DICT)
                        )
                    )
                ]
            )
        )
        parser._openai_client.beta.chat.completions.parse = mock_parse

        assert await parser.parse("raw") == EPISODE_DICT
        mock_parse.assert_awaited_once()


class TestLLMEffective:
    def test_effective_prefers_provider_override(self):
        conf = LLM(
            provider="kimi",
            api_key="flat-key",
            model="flat-model",
            base_url="flat-url",
            providers={
                "kimi": LLMProviderOverride(
                    api_key="kimi-key", model="kimi-k2.5", base_url="https://k/v1"
                )
            },
        )
        assert conf.effective() == ("kimi-key", "kimi-k2.5", "https://k/v1")

    def test_effective_falls_back_to_flat_fields(self):
        conf = LLM(provider="openai", api_key="flat-key", model="m0", base_url="b0")
        assert conf.effective() == ("flat-key", "m0", "b0")

    def test_effective_blank_override_fields_stay_blank(self):
        """有覆盖项时不跨提供商回退到扁平 openai 字段：空模型保持空，
        由适配器回退到本提供商默认（避免把 gpt-5-mini 发给 Kimi）。"""
        conf = LLM(
            provider="kimi",
            api_key="flat-key",
            model="flat-model",
            base_url="flat-url",
            providers={"kimi": LLMProviderOverride(api_key="kimi-key")},
        )
        api_key, model, base_url = conf.effective()
        assert api_key == "kimi-key"
        assert model == ""  # 不再串到 flat-model
        assert base_url == ""  # 不再串到 flat-url

    def test_blank_model_falls_back_to_provider_default(self):
        """空模型的预设适配器使用自己的 default_model，而非 openai 的默认。"""
        parser = LLMParser(api_key="sk", provider="kimi", model="")
        assert parser._adapter.model == "kimi-k2.5"


class TestNestedProviderMasking:
    def test_sanitize_masks_nested_provider_api_key(self):
        data = {"llm": {"providers": {"kimi": {"api_key": "sk-secret", "model": "m"}}}}
        masked = _sanitize_dict(data)
        assert masked["llm"]["providers"]["kimi"]["api_key"] == "********"
        assert masked["llm"]["providers"]["kimi"]["model"] == "m"

    def test_restore_swaps_mask_back_to_saved_value(self):
        saved = {"llm": {"providers": {"kimi": {"api_key": "sk-secret"}}}}
        incoming = {"llm": {"providers": {"kimi": {"api_key": "********"}}}}
        _restore_masked(incoming, saved)
        assert incoming["llm"]["providers"]["kimi"]["api_key"] == "sk-secret"
