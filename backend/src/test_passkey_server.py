"""
Minimal test server for passkey development.
Uses the real auth and passkey API routes without the downloader check.
Run with: uv run python test_passkey_server.py
"""
import uvicorn
from fastapi import FastAPI

from module.api.auth import router as auth_router
from module.api.passkey import router as passkey_router
from module.database import Database
from module.update.startup import first_run

app = FastAPI(title="AutoBangumi Passkey Test")

# Mount real routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(passkey_router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    """Create tables and default user (no downloader check)"""
    with Database() as db:
        db.create_table()
        db.user.add_default_user()


@app.get("/")
def index():
    return {"status": "Passkey test server running"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7892)
