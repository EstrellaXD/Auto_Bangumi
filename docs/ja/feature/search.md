# トレント検索

v3.1以降、ABにはアニメを素早く見つけるための検索機能が含まれています。

## 検索機能の使用

::: warning
検索機能はメインプログラムのパーサーに依存しています。現在のバージョンはコレクションの解析をサポートしていません。コレクションを解析する際の`warning`は正常な動作です。
:::

検索バーはABのトップバーにあります。クリックして検索パネルを開きます。

![Search Panel](/image/feature/search-panel.png)

ソースサイトを選択し、キーワードを入力すると、ABが自動的に解析して検索結果を表示します。アニメを追加するには、カードの右側にある追加ボタンをクリックします。

::: tip
ソースが**Mikan**の場合、ABはデフォルトで`mikan`パーサーを使用します。他のソースの場合、TMDBパーサーが使用されます。
:::

## 検索ソースの管理

v3.2以降、JSONファイルを編集せずに、設定ページで直接検索ソースを管理できます。

### 検索プロバイダー設定パネル

**設定** → **検索プロバイダー**に移動して、設定パネルにアクセスします。

![Search Provider Settings](/image/feature/search-provider.png)

ここから以下が可能です：
- すべての設定済み検索ソースを**表示**
- 「プロバイダーを追加」ボタンで新しい検索ソースを**追加**
- 既存のソースURLを**編集**
- カスタムソースを**削除**（デフォルトソースmikan、nyaa、dmhyは削除できません）

### URLテンプレート形式

カスタムソースを追加する場合、URLには検索キーワードのプレースホルダーとして`%s`を含める必要があります。

例：
```
https://example.com/rss/search?q=%s
```

`%s`はユーザーの検索クエリに置き換えられます。

### デフォルトソース

以下のソースは組み込みで、削除できません：

| ソース | URLテンプレート |
|--------|---------------|
| mikan | `https://mikanani.me/RSS/Search?searchstr=%s` |
| nyaa | `https://nyaa.si/?page=rss&q=%s&c=0_0&f=0` |
| dmhy | `http://dmhy.org/topics/rss/rss.xml?keyword=%s` |

### 設定ファイル経由でソースを追加

`config/search_provider.json`を編集してソースを手動で追加することもできます：

```json
{
  "mikan": "https://mikanani.me/RSS/Search?searchstr=%s",
  "nyaa": "https://nyaa.si/?page=rss&q=%s&c=0_0&f=0",
  "dmhy": "http://dmhy.org/topics/rss/rss.xml?keyword=%s",
  "bangumi.moe": "https://bangumi.moe/rss/search/%s"
}
```
