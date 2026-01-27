---
title: 概要
---

<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/image/icons/dark-icon.svg">
  <source media="(prefers-color-scheme: light)" srcset="/image/icons/light-icon.svg">
  <img src="/image/icons/light-icon.svg" width=50%>
</picture>
</p>


## AutoBangumiについて


<p align="center">
  <img
    title="AutoBangumi WebUI"
    alt="AutoBangumi WebUI"
    src="/image/preview/window.png"
    width=85%
    data-zoomable
  >
</p>

**`AutoBangumi`** は、RSSフィードに基づく全自動アニメダウンロード・整理ツールです。[Mikan Project][mikan]などのサイトでアニメを購読するだけで、新しいエピソードを自動的に追跡・ダウンロードします。

整理されたファイル名とディレクトリ構造は、追加のメタデータスクレイピングなしで[Plex][plex]、[Jellyfin][jellyfin]などのメディアライブラリソフトウェアと直接互換性があります。

## 機能

- シンプルな一回限りの設定で継続的に使用可能
- アニメ情報を抽出し、自動的にダウンロードルールを生成する手間いらずのRSSパーサー
- アニメファイルの整理：

  ```
  Bangumi
  ├── bangumi_A_title
  │   ├── Season 1
  │   │   ├── A S01E01.mp4
  │   │   ├── A S01E02.mp4
  │   │   ├── A S01E03.mp4
  │   │   └── A S01E04.mp4
  │   └── Season 2
  │       ├── A S02E01.mp4
  │       ├── A S02E02.mp4
  │       ├── A S02E03.mp4
  │       └── A S02E04.mp4
  ├── bangumi_B_title
  │   └─── Season 1
  ```

- 完全自動リネーム — リネーム後、99%以上のアニメファイルがメディアライブラリソフトウェアで直接スクレイピング可能

  ```
  [Lilith-Raws] Kakkou no Iinazuke - 07 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4
  >>
  Kakkou no Iinazuke S01E07.mp4
  ```

- 親フォルダ名に基づくすべての子ファイルのカスタムリネーム
- シーズン途中からの追跡で現在のシーズンの見逃したエピソードをすべて補完
- 異なるメディアライブラリソフトウェアに合わせて微調整できる高度にカスタマイズ可能なオプション
- メンテナンス不要、完全に透明な動作
- 完全なTMDB形式のファイルとアニメメタデータを生成する内蔵TMDBパーサー
- Mikan RSSフィードのリバースプロキシサポート

## コミュニティ

- 更新通知：[Telegramチャンネル](https://t.me/autobangumi_update)
- バグ報告：[Telegram](https://t.me/+yNisOnDGaX5jMTM9)

## 謝辞

[Sean](https://github.com/findix)氏のプロジェクトへの多大なご協力に感謝いたします。

## コントリビュート

IssuesとPull Requestsを歓迎します！

<a href="https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi" />
</a>

## 免責事項

AutoBangumiは非公式の著作権チャンネルを通じてアニメを取得するため：

- AutoBangumiを**商業目的で使用しないでください**。
- AutoBangumiを含むビデオコンテンツを作成し、国内のビデオプラットフォーム（著作権関係者）で**配信しないでください**。
- AutoBangumiを法律や規制に違反する活動に**使用しないでください**。

AutoBangumiは教育目的および個人使用のみを目的としています。

## ライセンス

[MIT License](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/LICENSE)

[mikan]: https://mikanani.me
[plex]: https://plex.tv
[jellyfin]: https://jellyfin.org
