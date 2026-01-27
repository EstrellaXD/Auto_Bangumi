# 实验性功能

::: warning
实验性功能仍在测试中。启用后可能会导致意外问题，且可能在未来版本中被移除。请谨慎使用！
:::

## OpenAI ChatGPT

使用 OpenAI ChatGPT 进行更好的结构化标题解析。例如：

```
input: "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
output: '{"group": "喵萌奶茶屋", "title_en": "Summer Time Rendering", "resolution": "1080p", "episode": 11, "season": 1, "title_zh": "夏日重现", "sub": "", "title_jp": "", "season_raw": "", "source": ""}'
```

![experimental OpenAI](/image/config/experimental-openai.png){width=500}{class=ab-shadow-card}

- **启用 OpenAI** 启用 OpenAI 并使用 ChatGPT 进行标题解析。
- **OpenAI API 类型** 默认为 OpenAI。
- **OpenAI API Key** 为您的 OpenAI 账户 API 密钥。
- **OpenAI API Base URL** 为 OpenAI 端点。默认为官方 OpenAI URL；您可以将其更改为兼容的第三方端点。
- **OpenAI Model** 为 ChatGPT 模型参数。目前提供 `gpt-3.5-turbo`，价格实惠且在正确的提示下效果出色。

## Microsoft Azure OpenAI


![experimental Microsoft Azure OpenAI](/image/config/experimental-azure-openai.png){width=500}{class=ab-shadow-card}

除了标准 OpenAI 外，[版本 3.1.8](https://github.com/EstrellaXD/Auto_Bangumi/releases/tag/3.1.8) 添加了 Microsoft Azure OpenAI 支持。使用方式与标准 OpenAI 类似，共享部分参数，但请注意以下几点：

- **启用 OpenAI** 启用 OpenAI 并使用 ChatGPT 进行标题解析。
- **OpenAI API 类型** — 选择 `azure` 以显示 Azure 专用选项。
- **OpenAI API Key** 为您的 Microsoft Azure OpenAI API 密钥。
- **OpenAI API Base URL** 对应 Microsoft Azure OpenAI 入口点。**需要手动填写**。
- **Azure OpenAI 版本** 为 API 版本。默认为 `2023-05-15`。查看[支持的版本](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#completions)。
- **Azure OpenAI Deployment ID** 为您的部署 ID，通常与模型名称相同。注意 Azure OpenAI 不支持 `_-` 以外的符号，因此 `gpt-3.5-turbo` 在 Azure 中变为 `gpt-35-turbo`。**需要手动填写**。

参考文档：

- [快速入门：开始使用 Azure OpenAI 服务的 GPT-35-Turbo 和 GPT-4](https://learn.microsoft.com/en-us/azure/ai-services/openai/chatgpt-quickstart?tabs=command-line&pivots=programming-language-python)
- [了解如何使用 GPT-35-Turbo 和 GPT-4 模型](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/chatgpt?pivots=programming-language-chat-completions)

## `config.json` 配置选项

配置文件中的对应选项如下：

配置节：`experimental_openai`

| 参数          | 说明                       | 类型    | WebUI 选项                  | 默认值                     |
|---------------|----------------------------|---------|----------------------------|---------------------------|
| enable        | 启用 OpenAI 解析器         | 布尔值  | 启用 OpenAI                | false                     |
| api_type      | OpenAI API 类型            | 字符串  | API 类型 (`openai`/`azure`) | openai                   |
| api_key       | OpenAI API 密钥            | 字符串  | OpenAI API Key             |                           |
| api_base      | API Base URL (Azure 入口点) | 字符串  | OpenAI API Base URL        | https://api.openai.com/v1 |
| model         | OpenAI 模型                | 字符串  | OpenAI Model               | gpt-3.5-turbo             |
| api_version   | Azure OpenAI API 版本      | 字符串  | Azure API 版本             | 2023-05-15                |
| deployment_id | Azure Deployment ID        | 字符串  | Azure Deployment ID        |                           |
