# アニメ管理設定

## WebUI

![manager](/image/config/manager.png){width=700}{class=ab-shadow-card}

- **有効化**：ファイル整理とリネームを有効化します。
- **リネーム方式**：
  - `pn`：リリースタイトル情報を多めに保持する `Torrent title S0XE0X` 形式。
  - `advance`：公式タイトルと標準的なシーズン/話数形式。
  - `none`：リネームしません。
  - `template`：独自テンプレートで命名します（[テンプレートリネーム](#テンプレートリネーム)参照）。
  - プラグインが追加のリネーム方式を提供することもあります。
- **話数補完**：不足している話数を補完ダウンロードします。
- **グループタグ追加**：字幕組関連タグをダウンローダータスクに追加します。
- **不良Torrent削除**：エラー状態のタスクを削除します。
- **未一致Torrentを記録**：ルールに一致しないTorrentを孤児レコードとして保存します。

## テンプレートリネーム

`template` を選ぶと、内蔵プラグイン「テンプレートリネーム」（`rename-template`）がファイル名を生成します。テンプレートは **設定 → プラグイン** で編集します。

| 項目 | 用途 | 既定値 |
| --- | --- | --- |
| 話数テンプレート | 通常の話数 | `{{ title }} S{{ season\|pad(2) }}E{{ episode\|pad(2) }}` |
| 劇場版テンプレート | 劇場版 | `{{ title }}` |

既定値は `pn` と同じ結果になります。サンドボックス化された [Jinja2](https://jinja.palletsprojects.com/) 構文で、変数 `title`、`bangumi_name`、`season`、`episode`、`group`、`episode_type`、`kind`、`language` が使えます。`pad(n)` フィルターで数値をゼロ埋めできます（`{{ episode|pad(3) }}` → `005`）。

- テンプレートはファイル名の本体のみを生成し、拡張子（字幕は `.zh.ass` 形式）は自動で付きます。
- 結果が空、`/` や `\` を含む、未定義の変数を使う場合、そのファイルは元の名前のままになり、エラーがログに記録されます。
- 構文エラーのあるテンプレートは保存時に拒否されます。

## `config.json`

セクション：`bangumi_manage`

| キー | 説明 | 型 | WebUI項目 | 既定値 |
| --- | --- | --- | --- | --- |
| `enable` | 管理機能を有効化 | 真偽値 | 有効化 | `true` |
| `eps_complete` | 話数補完を有効化 | 真偽値 | 話数補完 | `false` |
| `rename_method` | リネーム方式 | 文字列 | リネーム方式 | `pn` |
| `group_tag` | グループタグ追加 | 真偽値 | グループタグ追加 | `false` |
| `remove_bad_torrent` | エラーTorrent削除 | 真偽値 | 不良Torrent削除 | `false` |
| `track_orphans` | 未一致Torrentを記録 | 真偽値 | 未一致Torrentを記録 | `true` |
