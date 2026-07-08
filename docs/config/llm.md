# LLM 解析器

LLM 解析器用于在正则解析失败或需要更高解析质量时，调用大语言模型解析 RSS 标题。

![LLM parser](/image/config/llm-parser.png){width=700}{class=ab-shadow-card}

## 解析模式

- **回退（正则优先）**：默认模式。先使用内置正则解析，失败时再调用 LLM。
- **优先（LLM 优先）**：先调用 LLM，失败时再回退到正则。

## 服务商

内置 provider 包括：

- OpenAI：可填写 OpenAI 兼容端点，支持 DeepSeek、Ollama、LM Studio、OpenRouter、OneAPI 等。
- Anthropic
- Google Gemini

设置页还会显示已安装预设、订阅账号 provider，以及可下载 provider。订阅类 provider 需要先完成连接；可下载 provider 安装前请阅读界面中的风险提示。

## 高级设置

高级设置用于控制 LLM 调用的稳定性：

- **请求超时**：单次请求超时时间。
- **解析缓存**：成功或失败结果的缓存时间，`0` 表示关闭缓存。
- **最大并发数**：同时发出的 LLM 请求数量上限。
- **熔断失败次数**：连续失败达到该次数后暂时停止调用。
- **熔断暂停时长**：熔断后暂停调用的时间。

LLM 调用会使用应用的 [代理设置](/config/proxy)。

## `config.json` 配置选项

配置节：`llm`

| 参数 | 说明 | 类型 | WebUI 选项 | 默认值 |
| --- | --- | --- | --- | --- |
| `enable` | 启用 LLM 解析 | 布尔值 | 启用 LLM 解析 | `false` |
| `provider` | provider ID | 字符串 | 服务商 | `openai` |
| `api_key` | 内置 OpenAI provider 的 API Key | 字符串 | API 密钥 | `""` |
| `model` | 模型名称 | 字符串 | 模型 | `gpt-5-mini` |
| `base_url` | OpenAI 兼容端点 | 字符串 | API 地址 | `""` |
| `mode` | `fallback` 或 `primary` | 字符串 | 解析模式 | `fallback` |
| `timeout` | 请求超时 | 数字（秒） | 高级设置 | `20` |
| `cache_ttl` | 缓存时长 | 整数（秒） | 高级设置 | `900` |
| `max_concurrency` | 最大并发 | 整数 | 高级设置 | `2` |
| `failure_threshold` | 熔断失败次数 | 整数 | 高级设置 | `3` |
| `failure_backoff` | 熔断暂停时长 | 整数（秒） | 高级设置 | `300` |
| `providers` | 非内置 provider 的覆盖配置 | 对象 | 按 provider 保存 | `{}` |

旧版 `experimental_openai` 配置会在启动时自动迁移到 `llm` 段。
