# 旧実験的機能

::: warning
旧 `experimental_openai` セクションは新しい [LLMパーサー](/ja/config/llm) に置き換えられました。このページは旧設定ファイルと旧リンクのために残しています。
:::

3.3以降、AIタイトル解析は `llm` セクションで設定します。

- 旧OpenAI設定にAPI Keyまたは有効化状態があり、新 `llm` が未設定の場合、起動時に自動移行されます。
- 旧動作はLLM優先だったため、移行後は `mode: "primary"` になります。
- `experimental_openai` はダウングレード互換のため設定ファイルに残ります。

新規設定では以下を使ってください：

- [LLMパーサー](/ja/config/llm)
- [プロキシ設定](/ja/config/proxy)
- [ネットワーク設定](/ja/config/network)
