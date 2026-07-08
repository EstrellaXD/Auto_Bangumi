# LLMパーサー

LLMパーサーは、正規表現解析が失敗した場合やより高品質な解析が必要な場合に、大規模言語モデルでRSSタイトルを解析します。

![LLM parser](/image/config/llm-parser.png){width=700}{class=ab-shadow-card}

## 解析モード

- **フォールバック（正規表現優先）**：既定値です。まず正規表現で解析し、失敗時にLLMを使います。
- **優先（LLM優先）**：まずLLMを使い、失敗時に正規表現へ戻します。

## Provider

内蔵provider：

- OpenAI。DeepSeek、Ollama、LM Studio、OpenRouter、OneAPIなどのOpenAI互換エンドポイントにも対応します。
- Anthropic
- Google Gemini

設定ページには、インストール済みプリセット、購読アカウントprovider、ダウンロード可能providerも表示されます。LLM通信はアプリの[プロキシ設定](/ja/config/proxy)を使用します。

## `config.json`

セクション：`llm`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `enable` | LLM解析を有効化 | 真偽値 | LLM解析を有効化 | `false` |
| `provider` | provider ID | 文字列 | provider | `openai` |
| `api_key` | 内蔵OpenAI providerのAPI Key | 文字列 | API Key | `""` |
| `model` | モデル名 | 文字列 | モデル | `gpt-5-mini` |
| `base_url` | OpenAI互換エンドポイント | 文字列 | API URL | `""` |
| `mode` | `fallback` または `primary` | 文字列 | 解析モード | `fallback` |
| `timeout` | リクエストタイムアウト | 数値（秒） | 詳細設定 | `20` |
| `cache_ttl` | キャッシュ時間 | 整数（秒） | 詳細設定 | `900` |
| `max_concurrency` | 最大並列数 | 整数 | 詳細設定 | `2` |
| `failure_threshold` | サーキットブレーカー失敗回数 | 整数 | 詳細設定 | `3` |
| `failure_backoff` | 一時停止時間 | 整数（秒） | 詳細設定 | `300` |
| `providers` | provider別上書き設定 | オブジェクト | provider別保存 | `{}` |
