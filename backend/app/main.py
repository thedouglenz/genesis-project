from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, conversations, pipeline_runs

app = FastAPI(title="Genesis Data Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations.router)
app.include_router(auth.router)
app.include_router(pipeline_runs.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/llm-health")
async def llm_health():
    """Check if the LiteLLM proxy is reachable and accepting requests."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.LITELLM_PROXY_URL}health",
                headers={"Authorization": f"Bearer {settings.LITELLM_API_KEY}"},
            )
            if resp.status_code < 500:
                return {"status": "ok"}
            return {"status": "unavailable", "detail": "LLM service returned an error"}
    except Exception:
        return {"status": "unavailable", "detail": "Cannot reach LLM service"}


# Serve frontend static files in production
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the SPA index.html for all non-API routes."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
