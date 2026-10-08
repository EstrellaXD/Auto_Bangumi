# 旧実験的機能

::: warning
4.0 では旧 `experimental_openai` セクションは削除されました。代わりに [LLMパーサー](/ja/config/llm) を使用してください。
:::

3.3 以降、AB は起動のたびに `experimental_openai` を `llm` セクションへ自動移行し、設定ファイルに書き戻していました。4.0 は 3.3.x からのアップグレードのみをサポートするため、この移行はすでに完了しています。4.0 は旧セクションを読み込まず、次に設定を保存したときにファイルから削除します。

関連設定：

- [LLMパーサー](/ja/config/llm)
- [プロキシ](/ja/config/proxy)
- [ネットワーク](/ja/config/network)
