# LLM 提供商（llm_provider）

增加一个 LLM 解析提供商。`@provider(points.LLM_PROVIDER, id=...)` 返回 `ab_sdk.llm.LLMProviderAdapter` 的子类，**`id` 必须等于其 `info.id`**。用户在 设置 → LLM → 提供商 里选择它。内置提供商的 id 不能被覆盖。

```python
from ab_sdk import Plugin, points, provider
from ab_sdk.llm import AdapterContext, LLMProviderAdapter, ProviderInfo


class MyAdapter(LLMProviderAdapter):
    info = ProviderInfo(
        id="my-llm",
        display_name="My LLM",
        auth_kind="api_key",
        needs_base_url=True,
        default_model="my-model",
    )
    ...  # 实现 parse / list_models 等抽象方法


class MyPlugin(Plugin):
    @provider(points.LLM_PROVIDER, id="my-llm")
    def adapter(self):
        return MyAdapter
```

## 要点

- `ProviderInfo` 驱动前端表单和提供商列表：`auth_kind` 为 `api_key`、`oauth` 或 `device_code`。
- 适配器通过 `AdapterContext` 拿到模型名、密钥、`base_url`、超时和代理感知的 httpx 客户端工厂，不读全局配置。
- 订阅类提供商（`oauth` / `device_code`）实现认证流程钩子（`AuthChallenge`、`TokenSet`）。凭据失效且刷新失败时抛出 `AuthExpiredError`，AB 会熔断该提供商并发 `llm_auth_failure` 事件。
- 现有的 `plugin.json` 格式 LLM 插件（`llm-plugins` 发布）继续可用；新插件使用 `plugin.toml` 与本扩展点。
