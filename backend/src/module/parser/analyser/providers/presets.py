"""国产提供商 base_url 预设（纯数据，全部复用 OpenAIAdapter）。

这些提供商的订阅（Coding Plan 等）都是"发 API Key + OpenAI 兼容端点"，
无需 OAuth；预设只是替用户省去手抄 base_url。大陆/海外端点分开列
（智谱 Coding Plan 的 Key 只在 coding 专用端点有效，与普通 v4 不互通）。

端点核实日期：2026-07（来源：各家官方文档 / Claude Code 接入指南）。
"""

from dataclasses import dataclass

from .base import ProviderInfo
from .builtin import OpenAIAdapter


@dataclass(frozen=True)
class ProviderPreset:
    id: str
    display_name: str
    base_url: str
    default_model: str
    supports_json_schema: bool = True


PRESETS: tuple[ProviderPreset, ...] = (
    ProviderPreset(
        id="zai",
        display_name="智谱 GLM (Z.ai 海外)",
        base_url="https://api.z.ai/api/paas/v4",
        default_model="glm-4.7",
    ),
    ProviderPreset(
        id="zai-cn",
        display_name="智谱 GLM (大陆 Coding Plan)",
        base_url="https://open.bigmodel.cn/api/coding/paas/v4",
        default_model="glm-4.7",
    ),
    ProviderPreset(
        id="minimax",
        display_name="MiniMax (海外)",
        base_url="https://api.minimax.io/v1",
        default_model="MiniMax-M2.5",
        supports_json_schema=False,
    ),
    ProviderPreset(
        id="minimax-cn",
        display_name="MiniMax (大陆)",
        base_url="https://api.minimaxi.com/v1",
        default_model="MiniMax-M2.5",
        supports_json_schema=False,
    ),
    ProviderPreset(
        id="deepseek",
        display_name="DeepSeek",
        base_url="https://api.deepseek.com",
        default_model="deepseek-v4-flash",
        supports_json_schema=False,
    ),
    ProviderPreset(
        id="kimi",
        display_name="Moonshot Kimi (海外)",
        base_url="https://api.moonshot.ai/v1",
        default_model="kimi-k2.5",
    ),
    ProviderPreset(
        id="kimi-cn",
        display_name="Moonshot Kimi (大陆)",
        base_url="https://api.moonshot.cn/v1",
        default_model="kimi-k2.5",
    ),
)


def _make_adapter(preset: ProviderPreset) -> type[OpenAIAdapter]:
    info = ProviderInfo(
        id=preset.id,
        display_name=preset.display_name,
        auth_kind="api_key",
        builtin=False,
        needs_base_url=True,
        preset_base_url=preset.base_url,
        default_model=preset.default_model,
        supports_json_schema=preset.supports_json_schema,
    )
    class_name = f"{preset.id.replace('-', '_').title().replace('_', '')}PresetAdapter"
    return type(class_name, (OpenAIAdapter,), {"info": info})


PRESET_ADAPTERS: dict[str, type[OpenAIAdapter]] = {
    preset.id: _make_adapter(preset) for preset in PRESETS
}
