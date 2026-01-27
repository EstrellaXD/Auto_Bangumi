# 実験的機能

::: warning
実験的機能はまだテスト中です。有効にすると予期しない問題が発生する可能性があり、将来のバージョンで削除される可能性があります。注意して使用してください！
:::

## OpenAI ChatGPT

より良い構造化タイトル解析のためにOpenAI ChatGPTを使用します。例：

```
input: "【喵萌奶茶屋】★04月新番★[夏日重现/Summer Time Rendering][11][1080p][繁日双语][招募翻译]"
output: '{"group": "喵萌奶茶屋", "title_en": "Summer Time Rendering", "resolution": "1080p", "episode": 11, "season": 1, "title_zh": "夏日重现", "sub": "", "title_jp": "", "season_raw": "", "source": ""}'
```

![experimental OpenAI](/image/config/experimental-openai.png){width=500}{class=ab-shadow-card}

- **OpenAI有効**はOpenAIを有効にし、タイトル解析にChatGPTを使用します。
- **OpenAI APIタイプ**はデフォルトでOpenAIです。
- **OpenAI APIキー**はOpenAIアカウントのAPIキーです。
- **OpenAI APIベースURL**はOpenAIエンドポイントです。デフォルトでは公式OpenAI URLですが、互換性のあるサードパーティエンドポイントに変更できます。
- **OpenAIモデル**はChatGPTモデルパラメータです。現在`gpt-3.5-turbo`を提供しており、適切なプロンプトで手頃な価格で優れた結果を生成します。

## Microsoft Azure OpenAI


![experimental Microsoft Azure OpenAI](/image/config/experimental-azure-openai.png){width=500}{class=ab-shadow-card}

標準のOpenAIに加えて、[バージョン3.1.8](https://github.com/EstrellaXD/Auto_Bangumi/releases/tag/3.1.8)でMicrosoft Azure OpenAIサポートが追加されました。使用方法は標準のOpenAIと同様で、一部の共有パラメータがありますが、以下の点に注意してください：

- **OpenAI有効**はOpenAIを有効にし、タイトル解析にChatGPTを使用します。
- **OpenAI APIタイプ** — Azure固有のオプションを表示するには`azure`を選択します。
- **OpenAI APIキー**はMicrosoft Azure OpenAI APIキーです。
- **OpenAI APIベースURL**はMicrosoft Azure OpenAIエントリーポイントに対応します。**手動で入力する必要があります**。
- **Azure OpenAIバージョン**はAPIバージョンです。デフォルトは`2023-05-15`です。[サポートされているバージョン](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/reference#completions)を参照してください。
- **Azure OpenAIデプロイメントID**はデプロイメントIDで、通常はモデル名と同じです。Azure OpenAIは`_-`以外の記号をサポートしていないため、`gpt-3.5-turbo`はAzureでは`gpt-35-turbo`になることに注意してください。**手動で入力する必要があります**。

参考ドキュメント：

- [クイックスタート：Azure OpenAI ServiceでGPT-35-TurboとGPT-4の使用を開始する](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/chatgpt-quickstart?tabs=command-line&pivots=programming-language-python)
- [GPT-35-TurboとGPT-4モデルの操作方法を学ぶ](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/how-to/chatgpt?pivots=programming-language-chat-completions)

## `config.json`設定オプション

設定ファイルの対応するオプションは以下のとおりです：

設定セクション：`experimental_openai`

| パラメータ     | 説明                       | タイプ    | WebUIオプション              | デフォルト                    |
|---------------|---------------------------|---------|----------------------------|------------------------------|
| enable        | OpenAIパーサー有効         | ブール値 | OpenAI有効                  | false                        |
| api_type      | OpenAI APIタイプ           | 文字列   | APIタイプ (`openai`/`azure`) | openai                       |
| api_key       | OpenAI APIキー             | 文字列   | OpenAI APIキー              |                              |
| api_base      | APIベースURL（Azureエントリーポイント） | 文字列 | OpenAI APIベースURL    | https://api.openai.com/v1    |
| model         | OpenAIモデル               | 文字列   | OpenAIモデル                | gpt-3.5-turbo                |
| api_version   | Azure OpenAI APIバージョン  | 文字列   | Azure APIバージョン          | 2023-05-15                   |
| deployment_id | AzureデプロイメントID       | 文字列   | AzureデプロイメントID        |                              |
