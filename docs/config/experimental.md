# 实验功能配置

::: warning 警告
实验功能尚处于测试阶段，开启后可能会导致预料之外的问题并且在未来某些版本中很可能被移除，请谨慎使用！
:::

## OpenAI ChatGPT

使用 OpenAI ChatGPT 以获得更好的标题结构化解析效果，例如：

```
input: "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
output: '{"group": "喵萌奶茶屋", "title_en": "Summer Time Rendering", "resolution": "1080p", "episode": 11, "season": 1, "title_zh": "夏日重现", "sub": "", "title_jp": "", "season_raw": "", "source": ""}'
```

![experimental OpenAI](../image/config/experimental-openai.png){width=500}{class=ab-shadow-card}

- **Enable OpenAI** 为是否开启 OpenAI 并使用 ChatGPT 用于标题解析。
- **OpenAI API Type** 默认为 OpenAI。
- **OpenAI API Key** 为 OpenAI 账户的 API Key。
- **OpenAI API Base URL** 为 OpenAI 接口地址，默认情况下为 OpenAI 官方地址；你也可以根据自己的需要修改成其他兼容 OpenAI 服务的第三方地址。
- **OpenAI Model** 为 ChatGPT 的 `model` 模型参数，目前仅提供了 `gpt-3.5-turbo`，因为它足够便宜并且在 Prompt 的加持下可以得到相当不错的效果。

## Microsoft Azure OpenAI


![experimental Microsoft Azure Openai](../image/config/experimental-azure-openai.png){width=500}{class=ab-shadow-card}

除了原始的 OpenAI 之外，在 [3.18 版本](https://github.com/EstrellaXD/Auto_Bangumi/releases/tag/3.1.8) 中我们还加入了 Microsoft Azure OpenAI 的支持，它的使用方法与原始的 OpenAI 一致，部分参数共用，但是在填写参数时可能有几个地方需要注意：

- **Enable OpenAI** 为是否开启 OpenAI 并使用 ChatGPT 用于标题解析。
- **OpenAI API Type** 选择 `azure` 之后才会出现对应的参数选项。
- **OpenAI API Key** 为 Microsoft Azure OpenAI 账户的 API Key。
- **OpenAI API Base URL** 对应 Microsoft Azure OpenAI 的 Entrypoint，**需要你手动填写**。
- **Azure OpenAI Version** 对应 Microsoft Azure OpenAI 的 API 版本，默认为 `2023-05-15`，可参考 [所支持的版本](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#completions)。
- **Azure OpenAI Deployment ID** 对应 Microsoft Azure OpenAI 的 Deployment ID，通常与模型名称相同，需要注意的是 Microsoft Azure OpenAI 不支持除 `_-` 之外的符号，因此原始 OpenAI 中的 `gpt-3.5-turbo` 在 Microsoft Azure OpenAI 中实际为 `gpt-35-turbo`，此处**需要你手动填写**。

参考文档：

- [Quickstart: Get started using GPT-35-Turbo and GPT-4 with Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/chatgpt-quickstart?tabs=command-line&pivots=programming-language-python)
- [Learn how to work with the GPT-35-Turbo and GPT-4 models](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/chatgpt?pivots=programming-language-chat-completions)

## `config.json` 中的配置选项

在配置文件中对应选项如下：

配置文件部分：`experimental_openai`

| 参数名     | 参数说明       | 参数类型 | WebUI 对应选项 | 默认值      |
|---------|------------|------|------------|----------|
| enable  | 是否启用 OpenAI 解析器    | 布尔值  | 启用 OpenAI         | false    |
| api_type   | OpenAI API 类型       | 字符串  | OpenAI API 类型，可选 `openai` 和 `azure`       | openai |
| api_key    | OpenAI API Key       | 字符串  | OpenAI API Key       | |
| api_base   | OpenAI API Base URL(Azure entrypoint)   | 字符串  | OpenAI API Base URL   | https://api.openai.com/v1 |
| model | OpenAI 模型 | 字符串  | OpenAI 模型 | gpt-3.5-turbo |
| api_version | Azure OpenAI API 版本 | 字符串  | Azure OpenAI API 版本 | 2023-05-15 |
| deployment_id | Azure OpenAI Deployment ID | 字符串  | Azure OpenAI Deployment ID |  |
