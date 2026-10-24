# MCP 工具与资源（mcp_tool / mcp_resource）

把插件的能力暴露给 MCP 客户端。

```python
from ab_sdk import points, provider
from ab_sdk.mcp import McpResource, McpTool

@provider(points.MCP_TOOL, id="search")
def search_tool(self):
    async def handler(args: dict):
        return {"results": [...], "keyword": args["keyword"]}

    return McpTool(
        description="在私有站点搜索",
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

    return McpResource(name="统计", handler=handler)
```

- 对外名称自动加插件 id 前缀：工具名为 `<插件 id>__<id>`（双下划线），资源 URI 为 `autobangumi://plugins/<插件 id>/<id>`。不用 `.` 分隔，因为不少 MCP 客户端把工具名原样交给 LLM API，而后者通常只接受 `^[a-zA-Z0-9_-]{1,64}$`。不合规的工具名会被跳过并写日志。
- 工具处理函数接收已按 `input_schema` 校验的参数字典，返回可 JSON 序列化的对象。资源处理函数返回字符串（原样）或可 JSON 序列化的对象。
- 抛出的异常以 `{"error": "..."}` 返回给客户端，并计入熔断。工具默认超时 60 秒（`McpTool(timeout=...)`）。
- MCP 端点沿用 AB 的访问控制（IP 白名单或 `scope=mcp` 令牌），插件无需自行鉴权。
