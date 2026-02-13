import uuid

from fastapi import APIRouter

router = APIRouter(prefix="/api/pipeline-runs", tags=["pipeline-runs"])


@router.post("/{run_id}/retry")
async def retry_pipeline_run(run_id: uuid.UUID):
    """Retry a failed pipeline run."""
    raise NotImplementedError
