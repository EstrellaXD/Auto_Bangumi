# プレイヤー設定

プレイヤー設定はサイドバーの **プレイヤー** ページで使われます。

![player](/image/config/player.png){width=700}{class=ab-shadow-card}

- **種類**：
  - `jump`：プレイヤーページを開くと外部メディアサーバーへ移動します。
  - `iframe`：AutoBangumi内にメディアサーバーを埋め込みます。
- **プレイヤーURL**：Jellyfin、Emby、PlexなどのURLです。プロトコルがない場合、フロントエンドが `http://` を補います。

::: tip
プレイヤー設定はブラウザーのローカルストレージに保存されます。`config.json` には含まれず、**保存して再起動** は不要です。
:::
