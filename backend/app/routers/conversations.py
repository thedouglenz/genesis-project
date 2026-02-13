import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import AppSession
from app.models.app import Conversation, Message
from app.schemas.api import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
)

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
    raise NotImplementedError


@router.get("/{conversation_id}/stream")
async def stream_pipeline(conversation_id: uuid.UUID, current_user: str = Depends(get_current_user)):
    """SSE endpoint for pipeline progress."""
    raise NotImplementedError


@router.get("/{conversation_id}/pipeline-runs")
async def get_pipeline_runs(conversation_id: uuid.UUID, current_user: str = Depends(get_current_user)):
    """Get pipeline runs for a conversation."""
    raise NotImplementedError
