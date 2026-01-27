---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

title: AutoBangumi
titleTemplate: 全自動アニメ追跡、手間いらず！

hero:
  name: AutoBangumi
  text: 全自動アニメ追跡、手間いらず！
  tagline: RSS購読の自動解析、ダウンロード管理、ファイル整理
  actions:
    - theme: brand
      text: クイックスタート
      link: /ja/deploy/quick-start
    - theme: alt
      text: 概要
      link: /ja/home/
    - theme: alt
      text: 更新履歴
      link: /ja/changelog/3.2

features:
  - icon:
      src: /image/icons/rss.png
    title: RSS購読解析
    details: アニメのRSS購読を自動的に認識・解析。手動入力不要で、購読するだけで自動的に解析、ダウンロード、整理を完了します。
  - icon:
      src: /image/icons/qbittorrent-logo.svg
    title: qBittorrentダウンローダー
    details: qBittorrentを使用してアニメをダウンロード。AutoBangumiで既存のアニメ管理、過去のエピソードのダウンロード、エントリの削除が可能です。
  - icon:
      src: /image/icons/tmdb-icon.png
    title: TMDBメタデータマッチング
    details: TMDBを通じてアニメ情報をマッチングし、正確なメタデータを取得。複数の字幕グループ間でも正しく解析できます。
  - icon:
      src: /image/icons/plex-icon.png
    title: Plex / Jellyfin / Infuse ...
    details: マッチング結果に基づいてファイル名とディレクトリ構造を自動整理。メディアライブラリソフトウェアが高い成功率でメタデータをスクレイピングできるようにします。
---


<div class="container">
<div class="vp-doc">

## 謝辞

### 感謝
- [Mikan Project](https://mikanani.me) - 優れたアニメリソースを提供していただきありがとうございます。
- [VitePress](https://vitepress.dev) - 優れたドキュメントフレームワークを提供していただきありがとうございます。
- [qBittorrent](https://www.qbittorrent.org) - 優れたダウンローダーを提供していただきありがとうございます。
- [Plex](https://www.plex.tv) / [Jellyfin](https://jellyfin.org) - 優れたセルフホストメディアライブラリを提供していただきありがとうございます。
- [Infuse](https://firecore.com/infuse) - エレガントなビデオプレーヤーを提供していただきありがとうございます。
- [弾弾 Play](https://www.dandanplay.com) - 優れたコメント付きプレーヤーを提供していただきありがとうございます。
- すべてのアニメ制作チーム / 字幕グループ / ファンの皆様。

### コントリビューター

[
  ![](https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi){class=contributors-avatar}
](https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors)

## 免責事項

AutoBangumiは非公式の著作権チャンネルを通じてアニメを取得するため：

- AutoBangumiを**商業目的で使用しないでください**。
- AutoBangumiを含むビデオコンテンツを作成し、国内のビデオプラットフォーム（著作権関係者）で**公開しないでください**。
- AutoBangumiを法律や規制に違反する活動に**使用しないでください**。

</div>
</div>

<style scoped>
.container {
  display: flex;
  position: relative;
  margin: 0 auto;
  padding: 0 24px;
  max-width: 1280px;
}

@media (min-width: 640px) {
  .container {
    padding-inline: 48px;
  }
}

@media (min-width: 960px) {
  .container {
    padding-inline: 64px;
  }
}


.contributors-avatar {
  width: 600px;
}
</style>
