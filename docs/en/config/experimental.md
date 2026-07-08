# Legacy Experimental Features

::: warning
The old `experimental_openai` section has been replaced by the new [LLM Parser](/en/config/llm). This page remains only for old config files and old links.
:::

Since 3.3, AI title parsing is configured through the `llm` section.

- If the old OpenAI config has an API key or is enabled, and the new `llm` section is still empty, AutoBangumi migrates it on startup.
- The old behavior was LLM-first, so migrated configs use `mode: "primary"`.
- `experimental_openai` remains in the config file for downgrade compatibility.

Use these pages for new deployments:

- [LLM Parser](/en/config/llm)
- [Proxy Settings](/en/config/proxy)
- [Network Settings](/en/config/network)

## Legacy Section

Section: `experimental_openai`

| Key | Description | Status |
| --- | --- | --- |
| `enable` | Enable old OpenAI parser | deprecated |
| `api_key` | OpenAI API key | migrated to `llm.api_key` |
| `api_base` | OpenAI / Azure API base URL | migrated to `llm.base_url` |
| `api_type` | `openai` or `azure` | deprecated |
| `api_version` | Azure API version | deprecated |
| `model` | OpenAI model | migrated to `llm.model` |
| `deployment_id` | Azure deployment ID | deprecated |
