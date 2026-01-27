# Experimental Features

::: warning
Experimental features are still in testing. Enabling them may cause unexpected issues and they may be removed in future versions. Use with caution!
:::

## OpenAI ChatGPT

Use OpenAI ChatGPT for better structured title parsing. For example:

```
input: "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
output: '{"group": "喵萌奶茶屋", "title_en": "Summer Time Rendering", "resolution": "1080p", "episode": 11, "season": 1, "title_zh": "夏日重现", "sub": "", "title_jp": "", "season_raw": "", "source": ""}'
```

![experimental OpenAI](/image/config/experimental-openai.png){width=500}{class=ab-shadow-card}

- **Enable OpenAI** enables OpenAI and uses ChatGPT for title parsing.
- **OpenAI API Type** defaults to OpenAI.
- **OpenAI API Key** is your OpenAI account API key.
- **OpenAI API Base URL** is the OpenAI endpoint. Defaults to the official OpenAI URL; you can change it to a compatible third-party endpoint.
- **OpenAI Model** is the ChatGPT model parameter. Currently provides `gpt-3.5-turbo`, which is affordable and produces excellent results with the right prompts.

## Microsoft Azure OpenAI


![experimental Microsoft Azure OpenAI](/image/config/experimental-azure-openai.png){width=500}{class=ab-shadow-card}

In addition to standard OpenAI, [version 3.1.8](https://github.com/EstrellaXD/Auto_Bangumi/releases/tag/3.1.8) added Microsoft Azure OpenAI support. Usage is similar to standard OpenAI with some shared parameters, but note the following:

- **Enable OpenAI** enables OpenAI and uses ChatGPT for title parsing.
- **OpenAI API Type** — Select `azure` to show Azure-specific options.
- **OpenAI API Key** is your Microsoft Azure OpenAI API key.
- **OpenAI API Base URL** corresponds to the Microsoft Azure OpenAI Entrypoint. **Must be filled in manually**.
- **Azure OpenAI Version** is the API version. Defaults to `2023-05-15`. See [supported versions](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#completions).
- **Azure OpenAI Deployment ID** is your deployment ID, usually the same as the model name. Note that Azure OpenAI doesn't support symbols other than `_-`, so `gpt-3.5-turbo` becomes `gpt-35-turbo` in Azure. **Must be filled in manually**.

Reference documentation:

- [Quickstart: Get started using GPT-35-Turbo and GPT-4 with Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/chatgpt-quickstart?tabs=command-line&pivots=programming-language-python)
- [Learn how to work with the GPT-35-Turbo and GPT-4 models](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/chatgpt?pivots=programming-language-chat-completions)

## `config.json` Configuration Options

The corresponding options in the configuration file are:

Configuration section: `experimental_openai`

| Parameter     | Description              | Type    | WebUI Option               | Default                    |
|---------------|--------------------------|---------|---------------------------|---------------------------|
| enable        | Enable OpenAI parser     | Boolean | Enable OpenAI             | false                     |
| api_type      | OpenAI API type          | String  | API type (`openai`/`azure`) | openai                  |
| api_key       | OpenAI API key           | String  | OpenAI API Key            |                           |
| api_base      | API Base URL (Azure entrypoint) | String | OpenAI API Base URL  | https://api.openai.com/v1 |
| model         | OpenAI model             | String  | OpenAI Model              | gpt-3.5-turbo             |
| api_version   | Azure OpenAI API version | String  | Azure API Version         | 2023-05-15                |
| deployment_id | Azure Deployment ID      | String  | Azure Deployment ID       |                           |
