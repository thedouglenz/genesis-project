import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import AppSession
from app.models.app import Message, PipelineRun
from app.pipeline.orchestrator import Pipeline
from app.schemas.api import PipelineRunResponse

router = APIRouter(prefix="/api/pipeline-runs", tags=["pipeline-runs"])


@router.post("/{run_id}/retry", response_model=PipelineRunResponse)
async def retry_pipeline_run(run_id: uuid.UUID, current_user: str = Depends(get_current_user)):
    """Retry a failed pipeline run."""
    async with AppSession() as session:
        result = await session.execute(
            select(PipelineRun)
            .options(selectinload(PipelineRun.steps))
            .where(PipelineRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        if run.status != "failed":
            raise HTTPException(status_code=400, detail="Only failed runs can be retried")

        # Load the original message and its content
        msg_result = await session.execute(
            select(Message).where(Message.id == run.message_id)
        )
        message = msg_result.scalar_one()

        # Find the user message that triggered this (the one right before the assistant message)
        user_msg_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == message.conversation_id)
            .where(Message.role == "user")
            .where(Message.created_at <= message.created_at)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        user_msg = user_msg_result.scalar_one_or_none()
        if not user_msg:
            raise HTTPException(status_code=400, detail="Original user message not found")

        question = user_msg.content

        # Run pipeline in background with a new pipeline run
        async def _retry():
            pipeline = Pipeline(message.conversation_id, message.id)
            answer = await pipeline.run(question)
            async with AppSession() as bg_session:
                result = await bg_session.execute(
                    select(Message).where(Message.id == message.id)
                )
                msg = result.scalar_one()
                msg.content = answer.text_answer
                msg.table_data = answer.table_data.model_dump() if answer.table_data else None
                msg.chart_data = answer.chart_data.model_dump() if answer.chart_data else None
                await bg_session.commit()

        asyncio.create_task(_retry())

        # Return the original (failed) run — the new run will be created by the pipeline
        return run
