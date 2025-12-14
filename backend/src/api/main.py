from fastapi import APIRouter

from api.routes import auth, bangumi, config, log, program, rss, search, torrent
from api.routes.program import lifespan

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(log.router)
api_router.include_router(program.router)
api_router.include_router(bangumi.router)
api_router.include_router(config.router)
api_router.include_router(rss.router)
api_router.include_router(search.router)
api_router.include_router(torrent.router)

