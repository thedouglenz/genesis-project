import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.auth import get_current_user
from app.database import AppSession
from app.models.app import Conversation, Message, PipelineRun
from app.models.app import PipelineStep as PipelineStepModel
from app.pipeline.orchestrator import Pipeline
from app.schemas.api import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    PipelineRunResponse,
    SendMessageRequest,
)
from app.services import events

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse)
async def create_conversation(req: CreateConversationRequest, current_user: str = Depends(get_current_user)):
    """Create a new conversation."""
    async with AppSession() as session:
        convo = Conversation(title=req.title)
        session.add(convo)
        await session.commit()
        await session.refresh(convo)
        return convo


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(current_user: str = Depends(get_current_user)):
    """List all conversations."""
    async with AppSession() as session:
        result = await session.execute(
            select(Conversation).order_by(Conversation.created_at.desc())
        )
        return result.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: uuid.UUID, current_user: str = Depends(get_current_user)):
    """Get a conversation with its messages."""
    async with AppSession() as session:
        result = await session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        convo = result.scalar_one_or_none()
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return convo


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: uuid.UUID, current_user: str = Depends(get_current_user)):
    """Delete a conversation."""
    async with AppSession() as session:
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        convo = result.scalar_one_or_none()
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await session.delete(convo)
        await session.commit()
        return {"ok": True}


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: uuid.UUID, req: SendMessageRequest, current_user: str = Depends(get_current_user)):
    """Send a user message and trigger the pipeline."""
    async with AppSession() as session:
        # Verify conversation exists
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        convo = result.scalar_one_or_none()
        if not convo:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Create user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=req.content,
        )
        session.add(user_msg)
        await session.commit()

        # Create placeholder assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
        )
        session.add(assistant_msg)
        await session.commit()
        await session.refresh(assistant_msg)

        # Load conversation history (prior messages, excluding the new ones)
        msg_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.id != user_msg.id)
            .where(Message.id != assistant_msg.id)
            .order_by(Message.created_at)
        )
        prior_messages = msg_result.scalars().all()

        history = [
            {"role": m.role, "content": m.content or ""}
            for m in prior_messages
        ]

        # Extract schema_context from last ExploreOutput in pipeline history
        schema_context = None
        explore_result = await session.execute(
            select(PipelineStepModel)
            .join(PipelineRun, PipelineStepModel.pipeline_run_id == PipelineRun.id)
            .join(Message, PipelineRun.message_id == Message.id)
            .where(Message.conversation_id == conversation_id)
            .where(PipelineStepModel.step_name == "explore")
            .where(PipelineStepModel.status == "completed")
            .order_by(PipelineStepModel.created_at.desc())
            .limit(1)
        )
        explore_step = explore_result.scalar_one_or_none()
        if explore_step and explore_step.output_json:
            schema_context = explore_step.output_json.get("schema_context")

        # Run pipeline as background task so SSE can stream events
        async def _run_pipeline():
            pipeline = Pipeline(conversation_id, assistant_msg.id)
            answer = await pipeline.run(req.content, history, schema_context)
            async with AppSession() as bg_session:
                result = await bg_session.execute(
                    select(Message).where(Message.id == assistant_msg.id)
                )
                msg = result.scalar_one()
                msg.content = answer.text_answer
                msg.table_data = answer.table_data.model_dump() if answer.table_data else None
                msg.chart_data = answer.chart_data.model_dump() if answer.chart_data else None
                await bg_session.commit()

        asyncio.create_task(_run_pipeline())

        return assistant_msg


@router.get("/{conversation_id}/stream")
async def stream_pipeline(conversation_id: uuid.UUID, current_user: str = Depends(get_current_user)):
    """SSE endpoint for pipeline progress."""
    return EventSourceResponse(events.subscribe(str(conversation_id)))


@router.get("/{conversation_id}/pipeline-runs", response_model=list[PipelineRunResponse])
async def get_pipeline_runs(conversation_id: uuid.UUID, current_user: str = Depends(get_current_user)):
    """Get pipeline runs for a conversation."""
    async with AppSession() as session:
        result = await session.execute(
            select(PipelineRun)
            .join(Message, PipelineRun.message_id == Message.id)
            .options(selectinload(PipelineRun.steps))
            .where(Message.conversation_id == conversation_id)
            .order_by(PipelineRun.created_at.desc())
        )
        return result.scalars().all()
