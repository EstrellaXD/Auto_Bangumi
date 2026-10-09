<p align="center">
    <img src="docs/public/image/icons/light-icon.svg#gh-light-mode-only" width=50%/ alt="">
    <img src="docs/public/image/icons/dark-icon.svg#gh-dark-mode-only" width=50%/ alt="">
</p>
<p align="center">
    <img title="docker build version" src="https://img.shields.io/docker/v/estrellaxd/auto_bangumi" alt="">
    <img title="release date" src="https://img.shields.io/github/release-date/estrellaxd/auto_bangumi" alt="">
    <img title="docker pull" src="https://img.shields.io/docker/pulls/estrellaxd/auto_bangumi" alt="">
    <img title="python version" src="https://img.shields.io/badge/python-3.13-blue" alt="">
</p>

<p align="center">
  <a href="README.md">简体中文</a> | <a href="README.en.md">English</a> | 日本語
</p>

<p align="center">
  <a href="https://www.autobangumi.org/ja/">公式サイト</a> | <a href="https://www.autobangumi.org/ja/deploy/quick-start.html">クイックスタート</a> | <a href="https://www.autobangumi.org/ja/deploy/upgrade-4.0">4.0 へのアップグレード</a> | <a href="https://www.autobangumi.org/ja/changelog/4.0.html">更新履歴</a> | <a href="https://t.me/autobangumi_update">更新通知</a> | <a href="https://t.me/autobangumi">Telegram グループ</a>
</p>

# プロジェクト概要

<p align="center">
    <img title="AutoBangumi" src="docs/public/image/feature/bangumi-list.png" alt="" width=75%>
</p>

AutoBangumi は RSS ベースの全自動アニメダウンロード・整理ツールです。[Mikan Project][mikan] などのサイトで番組を購読すると、AutoBangumi がトレントのタイトルを解析してダウンロードルールを作成し、トレントをダウンローダーに渡します。完了したファイルは [Plex][plex]、[Jellyfin][jellyfin] などのメディアライブラリがそのまま認識できるフォルダ名とファイル名に整理され、手動のスクレイピングは不要です。

## 主な機能

- 操作不要の RSS パーサー：番組情報を解析し、ダウンロードルールを自動作成。Mikan、DMHY、Nyaa などのサイトと集約 RSS に対応
- Mikan と TMDB のメタデータ解析を内蔵。オプションで LLM タイトル解析（OpenAI 互換 API、Anthropic Claude、Google Gemini）
- シーズン途中から購読しても、そのシーズンの未取得エピソードを補完。劇場版、OVA、OAD、SP を識別して個別に整理
- 番組ごとのリリース設定：字幕グループと解像度を指定し、同じ話の重複ダウンロードを防止
- 初回起動時のセットアップウィザード。アプリ内で更新の確認・適用・ロールバック（sha256 と ed25519 署名で検証）
- ダウンローダー：qBittorrent、aria2
- ファイル整理とリネーム：

    ```
    Bangumi
    ├── bangumi_A_title
    │   ├── Season 1
    │   │   ├── A S01E01.mp4
    │   │   └── A S01E02.mp4
    │   └── Season 2
    │       └── A S02E01.mp4
    └── bangumi_B_title
        └── Season 1
    ```

    ```
    [Lilith-Raws] Kakkou no Iinazuke - 07 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4].mp4
    >>
    Kakkou no Iinazuke S01E07.mp4
    ```

## 4.0 の新機能

- **プラグインランタイム**：検索サイト、通知チャネル、リネーム方式、ダウンローダーなどの拡張ポイントは `ab_sdk` の契約に基づきます。内蔵プラグインは `ingest-filters`（グローバルな包含フィルター）、`rename`、`hardlink`、`media-server-refresh`（整理後に Jellyfin / Emby / Plex を更新）です。
- **複数のダウンローダーインスタンス**：ダウンローダーは `plugins.instances` で設定し、`plugins.slots.downloader` でデフォルトのインスタンスを指定します。新しいトレントは ルール → 購読 → デフォルトインスタンス の順にダウンローダーを選びます。
- **ハードリンクプラグイン `hardlink`**：デフォルトで無効。整理後に本編と字幕をライブラリフォルダへリンクし、ダウンロードフォルダはシードを続けます。`path_map` でダウンローダーインスタンスごとにパスを変換します。ファイルシステムをまたぐ場合はデフォルトでコピーします（`cross_device`: `copy` / `symlink` / `skip`）。
- **リネームプラグイン `rename`**：`pn`、`advance`、Jinja2 テンプレートの `template` を提供します。テンプレートのレンダリングに失敗した場合、そのファイルをスキップして通知を送り、他の方式には切り替えません。
- **イベントと MCP**：`/api/v1/events/stream`（SSE）がホストとプラグインのイベントを配信し、`/mcp` が MCP サーバーを提供します。プラグインは独自の MCP ツールと REST ルートを登録できます。
- **フロントエンドのプラグインスロット**：プラグインは設定ページ、番組詳細ページなどに独自のコンポーネントを配置できます。
- **プラグイン SDK**：`autobangumi-sdk` wheel（`ab-plugin` CLI を含む）と `autobangumi-plugin` エージェントスキルは GitHub Release に添付されます。PyPI には公開しません。

## クイックスタート

```bash
mkdir -p ${HOME}/AutoBangumi/{config,data}
cd ${HOME}/AutoBangumi
```

`docker-compose.yml` を作成します：

```yaml
services:
  AutoBangumi:
    image: "ghcr.io/estrellaxd/auto_bangumi:latest"
    container_name: AutoBangumi
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    ports:
      - "7892:7892"
    # アプリ内更新にはこの再起動ポリシーが必要
    restart: unless-stopped
    environment:
      - TZ=Asia/Tokyo
      - PGID=${PGID:-1000}
      - PUID=${PUID:-1000}
      - UMASK=022
```

```bash
docker compose up -d
```

`http://<ホスト>:7892` を開き、セットアップウィザードに従って設定します。4.0 ベータ版には `4.0.0-beta.N` または `dev-latest` タグを使用してください。その他のデプロイ方法は [デプロイドキュメント](https://www.autobangumi.org/ja/deploy/quick-start.html) を参照してください。

## 3.x からのアップグレード

- 4.0 は **3.3.x** からのアップグレードのみ対応します。それ以前のバージョンは先に 3.3 へアップグレードしてください。
- 初回起動時、設定マイグレーターが `downloader`、リネーム方式、バージョン競合ポリシーを `plugins` セクションへ移動し、元のファイルを `config/config.json.v3.bak` にバックアップします。移行に失敗した場合は元のファイルを復元し、起動を中止します。
- 詳しい手順とロールバック方法は [4.0 へのアップグレード](https://www.autobangumi.org/ja/deploy/upgrade-4.0) を参照してください。

## プラグイン開発

```bash
uv tool install ./autobangumi_sdk-<バージョン>-py3-none-any.whl   # GitHub Release からダウンロード
ab-plugin new my-plugin --kind rename
ab-plugin validate my-plugin
ab-plugin pack my-plugin
```

- 開発ドキュメント：[プラグイン開発](https://www.autobangumi.org/ja/dev/plugins.html)
- サンプルプラグイン：[`examples/plugins/`](examples/plugins)

## コントリビュート

Issue や PR を歓迎します。コードを提供する前に [CONTRIBUTING.md](CONTRIBUTING.md) をお読みください。[Roadmap](https://github.com/users/EstrellaXD/projects/2)

<a href="https://github.com/EstrellaXD/Auto_Bangumi/graphs/contributors"><img src="https://contrib.rocks/image?repo=EstrellaXD/Auto_Bangumi"></a>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=EstrellaXD/Auto_Bangumi&type=Date)](https://star-history.com/#EstrellaXD/Auto_Bangumi)

## Licence

[MIT licence](https://github.com/EstrellaXD/Auto_Bangumi/blob/main/LICENSE)

[mikan]: https://mikanani.me
[plex]: https://plex.tv
[jellyfin]: https://jellyfin.org
