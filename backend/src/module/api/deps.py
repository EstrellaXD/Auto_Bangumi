"""FastAPI dependencies shared across API routers."""

from fastapi import Request

from module.core import AppContext


def get_context(request: Request) -> AppContext:
    """Return the lifespan-owned :class:`AppContext` stored on ``app.state``."""
    return request.app.state.ctx
