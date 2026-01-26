"""Minimal dev server that skips downloader check for UI testing."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter

from module.database.combine import Database
from module.database.engine import engine

# Initialize DB + migrations + default user
with Database(engine) as db:
    db.create_table()
    db.user.add_default_user()

# Build v1 router without program router (which blocks on downloader check)
from module.api.auth import router as auth_router
from module.api.bangumi import router as bangumi_router
from module.api.config import router as config_router
from module.api.log import router as log_router
from module.api.rss import router as rss_router
from module.api.search import router as search_router

v1 = APIRouter(prefix="/v1")
v1.include_router(auth_router)
v1.include_router(bangumi_router)
v1.include_router(config_router)
v1.include_router(log_router)
v1.include_router(rss_router)
v1.include_router(search_router)

# Stub status endpoint (real one lives in program router which blocks on downloader)
@v1.get("/status")
async def stub_status():
    return {"status": True, "version": "dev"}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(v1, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7892)
