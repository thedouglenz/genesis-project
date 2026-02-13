from fastapi import APIRouter, HTTPException

from app.auth import create_token
from app.config import settings
from app.schemas.api import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Authenticate with username/password and return a JWT token."""
    if req.username != settings.AUTH_USERNAME or req.password != settings.AUTH_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginResponse(token=create_token(req.username))
