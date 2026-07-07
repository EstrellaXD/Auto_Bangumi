from .combine import Database


async def get_db():
    """FastAPI dependency yielding a request-scoped async Database."""
    async with Database() as db:
        yield db
