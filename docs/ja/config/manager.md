# アニメ管理設定

## WebUI

![manager](/image/config/manager.png){width=700}{class=ab-shadow-card}

- **有効化**：ファイル整理とリネームを有効化します。
- **リネーム方式**：
  - `normal`：控えめなタイトルと話数の命名。
  - `pn`：リリースタイトル情報を多めに保持する `Torrent title S0XE0X` 形式。
  - `advance`：公式タイトルと標準的なシーズン/話数形式。
  - `none`：リネームしません。
- **話数補完**：不足している話数を補完ダウンロードします。
- **グループタグ追加**：字幕組関連タグをダウンローダータスクに追加します。
- **不良Torrent削除**：エラー状態のタスクを削除します。
- **未一致Torrentを記録**：ルールに一致しないTorrentを孤児レコードとして保存します。

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
