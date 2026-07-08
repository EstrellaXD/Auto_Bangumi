# 検索プロバイダー設定

![search provider](/image/config/search-provider.png){width=700}{class=ab-shadow-card}

検索プロバイダーはWebUIのTorrent検索と検索ベースの購読に使われます。内蔵providerは `mikan`、`nyaa`、`dmhy` です。既定providerは削除できませんが、URLテンプレートは編集できます。

検索プロバイダーの変更は `config/search_provider.json` に即時保存されます。下部の **保存して再起動** は不要です。

## カスタムURL

URLテンプレートには検索語を差し込む `%s` が必要です。

```txt
https://example.com/search?q=%s
```

## PTサイト（NexusPHP）

![NexusPHP search provider](/image/config/search-provider-nexusphp.png){width=700}{class=ab-shadow-card}

NexusPHPモードでは、サイトURL、Passkey、任意のカテゴリIDから `torrentrss.php` のRSS検索テンプレートを生成します。

::: warning
一部の新しいNexusPHPサイトでは `search` パラメータが無効化され、どの検索語でも最新Torrentを返すことがあります。追加前にRSS検索が実際に絞り込まれることを確認してください。
:::
