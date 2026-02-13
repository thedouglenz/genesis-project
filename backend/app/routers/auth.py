from fastapi import APIRouter

from app.schemas.api import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Authenticate with username/password and return a JWT token."""
    raise NotImplementedError
