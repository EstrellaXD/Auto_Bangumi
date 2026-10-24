# MCP Tools and Resources (mcp_tool / mcp_resource)

Exposes plugin abilities to MCP clients.

```python
from ab_sdk import points, provider
from ab_sdk.mcp import McpResource, McpTool

@provider(points.MCP_TOOL, id="search")
def search_tool(self):
    async def handler(args: dict):
        return {"results": [...], "keyword": args["keyword"]}

    return McpTool(
        description="Search a private site",
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

    return McpResource(name="Statistics", handler=handler)
```

- AB adds the plugin id to the public name: the tool name is `<plugin id>__<id>` (double underscore) and the resource URI is `autobangumi://plugins/<plugin id>/<id>`. AB does not use `.` as a separator. Many MCP clients give the tool name unchanged to the LLM API, and that API usually accepts only `^[a-zA-Z0-9_-]{1,64}$`. AB skips a tool name that does not match and writes a log line.
- A tool handler receives the argument dict that AB validated against `input_schema`. It returns a JSON-serializable object. A resource handler returns a string (sent as it is) or a JSON-serializable object.
- AB returns a raised exception to the client as `{"error": "..."}`, and it counts toward the breaker. The default tool timeout is 60 seconds (`McpTool(timeout=...)`).
- The MCP endpoint uses the access control of AB (IP allowlist or a token with `scope=mcp`). A plugin does not need its own authentication.
