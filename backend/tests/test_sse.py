import asyncio
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.app import Conversation, Message
from app.schemas.api import AnswerOutput
from app.services import events


def _make_convo(convo_id=None):
    c = Conversation()
    c.id = convo_id or uuid.uuid4()
    c.title = "Test"
    c.created_at = datetime(2026, 1, 1)
    c.updated_at = datetime(2026, 1, 1)
    c.messages = []
    return c


def _mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, session


@pytest.fixture
async def auth_client(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
async def test_event_bus_emit_and_subscribe():
    """Test that emitted events are received by subscribers."""
    conv_id = str(uuid.uuid4())

    # Emit events in a task
    async def emit_events():
        await asyncio.sleep(0.01)
        await events.emit(conv_id, {"step": "plan", "status": "running"})
        await events.emit(conv_id, {"step": "plan", "status": "completed"})
        await events.emit(conv_id, {"step": "done"})

    asyncio.create_task(emit_events())

    received = []
    async for event_data in events.subscribe(conv_id, timeout=5.0):
        received.append(json.loads(event_data))

    assert len(received) == 3
    assert received[0] == {"step": "plan", "status": "running"}
    assert received[1] == {"step": "plan", "status": "completed"}
    assert received[2] == {"step": "done"}


@pytest.mark.asyncio
async def test_event_bus_cleanup():
    """Queue is cleaned up after subscribe finishes."""
    conv_id = str(uuid.uuid4())

    async def emit_done():
        await asyncio.sleep(0.01)
        await events.emit(conv_id, {"step": "done"})

    asyncio.create_task(emit_done())

    async for _ in events.subscribe(conv_id, timeout=5.0):
        pass

    assert conv_id not in events._event_bus


@pytest.mark.asyncio
async def test_send_message_returns_immediately(auth_client: AsyncClient):
    """send_message should return the placeholder assistant message immediately."""
    convo = _make_convo()
    ctx, session = _mock_session()

    messages_added = []

    def track_add(obj):
        if isinstance(obj, Message):
            obj.id = uuid.uuid4()
            obj.created_at = datetime(2026, 1, 1)
            messages_added.append(obj)

    session.add = track_add
    session.refresh = AsyncMock()

    convo_result = MagicMock()
    convo_result.scalar_one_or_none.return_value = convo
    msg_result = MagicMock()
    msg_result.scalars.return_value.all.return_value = []
    explore_result = MagicMock()
    explore_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[convo_result, msg_result, explore_result])

    with (
        patch("app.routers.conversations.AppSession", return_value=ctx),
        patch("app.routers.conversations.Pipeline") as MockPipeline,
    ):
        mock_instance = AsyncMock()
        mock_instance.run = AsyncMock(return_value=AnswerOutput(
            text_answer="answer", table_data=None, chart_data=None
        ))
        MockPipeline.return_value = mock_instance

        resp = await auth_client.post(
            f"/api/conversations/{convo.id}/messages",
            json={"content": "test question"},
        )

    assert resp.status_code == 200
    data = resp.json()
    # The response is the placeholder assistant message (content may be None)
    assert data["role"] == "assistant"


@pytest.mark.asyncio
async def test_orchestrator_emits_events():
    """Pipeline.run() should emit SSE events for each step."""
    from app.pipeline.orchestrator import Pipeline

    conv_id = uuid.uuid4()
    msg_id = uuid.uuid4()

    ctx, session = _mock_session()
    records_added = []

    def track_add(obj):
        obj.id = uuid.uuid4()
        records_added.append(obj)

    session.add = track_add
    session.refresh = AsyncMock()

    from app.schemas.api import ExploreOutput, PlanOutput

    fake_plan = PlanOutput(
        reasoning="Count records",
        query_strategy="SELECT COUNT(*)",
        expected_answer_type="scalar",
        suggested_chart_type=None,
        tables_to_explore=["t"],
    )
    fake_explore = ExploreOutput(
        queries_executed=[], raw_data=[], exploration_notes="ok", schema_context={}
    )
    fake_answer = AnswerOutput(text_answer="42", table_data=None, chart_data=None)

    call_count = 0

    async def mock_execute_with_retry(input_data, llm_client):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return fake_plan
        elif call_count == 2:
            return fake_explore
        else:
            return fake_answer

    # Collect events
    received_events = []
    original_emit = events.emit

    async def capture_emit(cid, data):
        received_events.append(data)
        await original_emit(cid, data)

    with (
        patch("app.pipeline.orchestrator.AppSession", return_value=ctx),
        patch("app.pipeline.orchestrator.LLMClient"),
        patch("app.pipeline.orchestrator.events.emit", side_effect=capture_emit),
    ):
        pipeline = Pipeline(conv_id, msg_id)
        for step in pipeline.steps:
            step.execute_with_retry = mock_execute_with_retry

        await pipeline.run("test")

    # Should have: plan running, plan completed, explore running, explore completed,
    # answer running, answer completed (done is emitted by _run_pipeline after content persist)
    step_events = [(e.get("step"), e.get("status")) for e in received_events]
    assert ("plan", "running") in step_events
    assert ("plan", "completed") in step_events
    assert ("explore", "running") in step_events
    assert ("explore", "completed") in step_events
    assert ("answer", "running") in step_events
    assert ("answer", "completed") in step_events
