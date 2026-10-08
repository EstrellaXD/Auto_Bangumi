# Legacy Experimental Features

::: warning
AutoBangumi 4.0 removes the old `experimental_openai` section. Use the [LLM Parser](/en/config/llm) instead.
:::

Since 3.3, every startup migrated `experimental_openai` into the `llm` section and saved the result to the config file. 4.0 only supports upgrading from 3.3.x, so that migration has already happened. 4.0 no longer reads the old section, and drops it from the file the next time the config is saved.

Related settings:

- [LLM Parser](/en/config/llm)
- [Proxy](/en/config/proxy)
- [Network](/en/config/network)
