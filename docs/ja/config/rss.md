# RSS購読設定

AutoBangumiは集約されたアニメRSSフィードを自動的に解析し、字幕グループとアニメ名に基づいてダウンロードルールを生成して、完全自動のアニメ追跡を可能にします。
以下では、[Mikan Project][mikan-site]を例として、RSS購読URLを取得する方法を説明します。

Mikan Projectのメインサイトは一部の地域でブロックされている場合があります。プロキシなしでアクセスできない場合は、以下の代替ドメインを使用してください：

[Mikan Project (代替)][mikan-cn-site]

## 購読URLの取得

このプロジェクトはMikan Projectが提供するRSS URLの解析に基づいています。自動アニメ追跡を有効にするには、Mikan ProjectのRSS URLを登録して取得する必要があります：

![image](/image/rss/rss-token.png){data-zoomable}

RSS URLは以下のようになります：

```txt
https://mikanani.me/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# または
https://mikanime.tv/RSS/MyBangumi?token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Mikan Project購読のヒント

AutoBangumiは受信したすべてのRSSエントリを解析するため、購読時に以下の点に注意してください：

![image](/image/rss/advanced-subscription.png){data-zoomable}

- プロファイル設定で詳細設定を有効にしてください。
- アニメごとに1つの字幕グループのみを購読してください。Mikan Projectでアニメのポスターをクリックしてサブメニューを開き、単一の字幕グループを選択します。
- 字幕グループが簡体字中国語と繁体字中国語の両方の字幕を提供している場合、Mikan Projectは通常選択方法を提供します。1つの字幕タイプを選択してください。
- 字幕タイプの選択がない場合は、AutoBangumiで`filter`を設定してフィルタリングするか、ルール生成後にqBittorrentで手動でフィルタリングできます。
- OVAと映画の購読は現在解析がサポートされていません。


[mikan-site]: https://mikanani.me/
[mikan-cn-site]: https://mikanime.tv/
