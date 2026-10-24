# 旧版实验性功能

::: warning
4.0 已移除旧版 `experimental_openai` 配置节，请改用 [LLM 解析器](/config/llm)。
:::

3.3 起，AB 每次启动都会把 `experimental_openai` 自动迁移到 `llm` 配置节，并写回配置文件。4.0 只支持从 3.3.x 升级，届时迁移早已完成，所以 4.0 不再读取这个旧配置节，保存配置时也会把它从文件中删除。

相关配置：

- [LLM 解析器](/config/llm)
- [代理设置](/config/proxy)
- [网络设置](/config/network)
