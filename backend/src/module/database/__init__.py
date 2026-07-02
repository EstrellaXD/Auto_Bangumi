from .combine import Database
from .engine import engine


def get_db():
    """FastAPI dependency yielding a request-scoped Database."""
    with Database() as db:
        yield db
