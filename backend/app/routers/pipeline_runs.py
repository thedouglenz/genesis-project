import uuid

from fastapi import APIRouter, Depends

from app.auth import get_current_user

router = APIRouter(prefix="/api/pipeline-runs", tags=["pipeline-runs"])


@router.post("/{run_id}/retry")
async def retry_pipeline_run(run_id: uuid.UUID, current_user: str = Depends(get_current_user)):
    """Retry a failed pipeline run."""
    raise NotImplementedError
