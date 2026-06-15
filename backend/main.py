import os
import logging
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=FutureWarning, module="instructor")
warnings.filterwarnings("ignore", message=".*allowed_objects.*")

load_dotenv(dotenv_path="../.env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional

from db.database import init_db, close_db, AsyncSessionLocal
from db import service as db_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Project Raven Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ──────────────────────────────────────────────────────

from api.admin import router as admin_router
from api.candidate import router as candidate_router
from api.websocket import router as ws_router

app.include_router(admin_router)
app.include_router(candidate_router)
app.include_router(ws_router)

# ── Auth endpoints ───────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None

class LoginResponse(BaseModel):
    user_id: str
    email: str
    role: str
    token: str
    message: str

@app.post("/auth/login", response_model=LoginResponse)
async def dev_login(request: LoginRequest):
    """
    Dev mode login. Creates user if not exists.
    Token is the user UUID (no JWT needed for dev).
    """
    async with AsyncSessionLocal() as db:
        user = await db_service.get_or_create_user(db, email=request.email, role="admin")
        return LoginResponse(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            token=str(user.id),
            message="Login successful (dev mode)",
        )

@app.get("/auth/me")
async def get_me(token: str = None):
    """Get current user from token (dev mode — token = user ID)."""
    if not token:
        raise HTTPException(status_code=401, detail="Token required")

    async with AsyncSessionLocal() as db:
        from uuid import UUID
        try:
            user = await db_service.get_user_by_id(db, UUID(token))
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid token format")

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        org_name = None
        if user.org_id:
            from db.models import Organisation
            from sqlalchemy import select
            org_result = await db.execute(select(Organisation).where(Organisation.id == user.org_id))
            org = org_result.scalar_one_or_none()
            if org:
                org_name = org.name

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "org_id": str(user.org_id) if user.org_id else None,
            "org_name": org_name,
        }

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Project Raven Backend is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
