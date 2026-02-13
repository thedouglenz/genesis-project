import uuid

from fastapi import APIRouter

from app.schemas.api import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse)
async def create_conversation(req: CreateConversationRequest):
    """Create a new conversation."""
    raise NotImplementedError


@router.get("", response_model=list[ConversationResponse])
async def list_conversations():
    """List all conversations."""
    raise NotImplementedError


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: uuid.UUID):
    """Get a conversation with its messages."""
    raise NotImplementedError


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: uuid.UUID):
    """Delete a conversation."""
    raise NotImplementedError


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(conversation_id: uuid.UUID, req: SendMessageRequest):
    """Send a user message and trigger the pipeline."""
    raise NotImplementedError


@router.get("/{conversation_id}/stream")
async def stream_pipeline(conversation_id: uuid.UUID):
    """SSE endpoint for pipeline progress."""
    raise NotImplementedError


@router.get("/{conversation_id}/pipeline-runs")
async def get_pipeline_runs(conversation_id: uuid.UUID):
    """Get pipeline runs for a conversation."""
    raise NotImplementedError


