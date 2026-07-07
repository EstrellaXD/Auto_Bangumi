"""CIDR-based IP allowlist helpers, shared by the login and MCP guards.

Lives in ``module.security`` (not ``module.mcp``) so the security layer does
not depend on the MCP layer; ``module.mcp.security`` re-exports these names
for backward compatibility.
"""

import ipaddress
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=128)
def _parse_network(cidr: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    try:
        return ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        logger.warning("Invalid CIDR in whitelist: %s", cidr)
        return None


def _is_allowed(host: str, whitelist: list[str]) -> bool:
    """Return True if *host* falls within any CIDR range in *whitelist*."""
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    for cidr in whitelist:
        net = _parse_network(cidr)
        if net and addr in net:
            return True
    return False


def clear_network_cache():
    """Clear the parsed network cache (call after config reload)."""
    _parse_network.cache_clear()
