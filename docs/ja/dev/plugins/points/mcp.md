# MCP ツールとリソース (mcp_tool / mcp_resource)

プラグインの機能を MCP クライアントに公開します。

```python
from ab_sdk import points, provider
from ab_sdk.mcp import McpResource, McpTool

@provider(points.MCP_TOOL, id="search")
def search_tool(self):
    async def handler(args: dict):
        return {"results": [...], "keyword": args["keyword"]}

    return McpTool(
        description="プライベートサイトを検索する",
        handler=handler,
        input_schema={
            "type": "object",
            "properties": {"keyword": {"type": "string"}},
            "required": ["keyword"],
        },
    )

@provider(points.MCP_RESOURCE, id="stats")
def stats_resource(self):
    async def handler():
        return {"count": 3}

    return McpResource(name="統計", handler=handler)
```

- 公開名には、AB が自動でプラグイン id を付けます：ツール名は `<プラグイン id>__<id>`（アンダースコア 2 つ）、リソースの URI は `autobangumi://plugins/<プラグイン id>/<id>` です。区切りに `.` は使いません。多くの MCP クライアントはツール名をそのまま LLM API に渡し、その API は通常 `^[a-zA-Z0-9_-]{1,64}$` しか受け付けないためです。この形式に合わないツール名は、スキップされてログに記録されます。
- ツールのハンドラーは、AB が `input_schema` で検証した引数の辞書を受け取り、JSON にできるオブジェクトを返します。リソースのハンドラーは、文字列（そのまま返す）か、JSON にできるオブジェクトを返します。
- 送出された例外は `{"error": "..."}` としてクライアントに返り、ブレーカーに数えられます。ツールの既定のタイムアウトは 60 秒です（`McpTool(timeout=...)`）。
- MCP エンドポイントは AB のアクセス制御（IP 許可リスト、または `scope=mcp` のトークン）に従います。プラグインが独自に認証する必要はありません。
