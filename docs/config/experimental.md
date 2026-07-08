# 旧版实验性功能

::: warning
旧版 `experimental_openai` 配置已被新的 [LLM 解析器](/config/llm) 取代。此页面仅保留给旧配置文件和旧链接参考。
:::

从 3.3 开始，标题解析相关的 AI 配置统一迁移到 `llm` 配置节。旧版 `experimental_openai` 中的 OpenAI / Azure OpenAI 配置在启动时会自动迁移：

- 旧配置已有 API Key 或启用状态，而新 `llm` 段还没有有效配置时，AB 会生成新的 `llm` 配置。
- 旧版语义是 LLM 优先解析，因此迁移后的 `mode` 会设为 `primary`。
- `experimental_openai` 字段会保留在配置文件中，以便降级回滚时仍可读取。

新配置请使用：

- [LLM 解析器](/config/llm)
- [代理设置](/config/proxy)
- [网络设置](/config/network)

## 旧配置节

配置节：`experimental_openai`

| 参数 | 说明 | 状态 |
| --- | --- | --- |
| `enable` | 启用旧版 OpenAI 解析器 | 已弃用 |
| `api_key` | OpenAI API Key | 已迁移到 `llm.api_key` |
| `api_base` | OpenAI / Azure API Base URL | 已迁移到 `llm.base_url` |
| `api_type` | `openai` 或 `azure` | 已弃用 |
| `api_version` | Azure API 版本 | 已弃用 |
| `model` | OpenAI 模型 | 已迁移到 `llm.model` |
| `deployment_id` | Azure Deployment ID | 已弃用 |
