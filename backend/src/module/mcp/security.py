"""MCP access control: configurable IP whitelist and bearer token authentication."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from module.conf import settings
from module.security.ip_allowlist import (  # noqa: F401  (re-exported for existing importers)
    _is_allowed,
    _parse_network,
    clear_network_cache,
)

logger = logging.getLogger(__name__)


class McpAccessMiddleware(BaseHTTPMiddleware):
    """Configurable access control for MCP endpoint.

    Checks client IP against ``settings.security.mcp_whitelist`` CIDR ranges,
    and ``Authorization`` header against ``settings.security.mcp_tokens``.
    If the whitelist is empty and no tokens are configured, all access is denied.
    """

    async def dispatch(self, request: Request, call_next):
        # Check bearer token first
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token and token in settings.security.mcp_tokens:
                return await call_next(request)

        # Check IP whitelist
        client_host = request.client.host if request.client else None
        if client_host and _is_allowed(client_host, settings.security.mcp_whitelist):
            return await call_next(request)

        logger.warning("Rejected connection from %s", client_host)
        return JSONResponse(
            status_code=403,
            content={"error": "MCP access denied"},
        )
