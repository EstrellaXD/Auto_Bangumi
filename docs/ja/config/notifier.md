# 通知設定

## WebUI設定

![notification](/image/config/notifier.png){width=500}{class=ab-shadow-card}

<br/>

- **有効**は通知を有効にします。無効にすると、以下の設定は効果がありません。
- **タイプ**は通知タイプです。現在サポートされているもの：
  - Telegram
  - Wecom
  - Bark
  - ServerChan
- **Chat ID**は`telegram`通知を使用する場合にのみ入力が必要です。[Telegram Bot Chat IDの取得方法][1]
- **Wecom**：Chat IDフィールドにカスタムプッシュURLを入力し、サーバー側で[リッチテキストメッセージ][2]タイプを追加します。[Wecom設定ガイド][3]

## `config.json`設定オプション

設定ファイルの対応するオプションは以下のとおりです：

設定セクション：`notification`

| パラメータ | 説明             | タイプ    | WebUIオプション    | デフォルト |
|-----------|-----------------|---------|------------------|----------|
| enable    | 通知有効         | ブール値 | 通知              | false    |
| type      | 通知タイプ       | 文字列   | 通知タイプ        | telegram |
| token     | 通知トークン     | 文字列   | 通知トークン       |          |
| chat_id   | 通知Chat ID     | 文字列   | 通知Chat ID       |          |


[1]: https://core.telegram.org/bots#6-botfather
[2]: https://github.com/umbors/wecomchan-alifun
[3]: https://github.com/easychen/wecomchan
