import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.app import Conversation, Message, PipelineRun
from app.models.app import PipelineStep as PipelineStepModel
from app.schemas.api import AnswerOutput, ExploreOutput, PlanOutput


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


def _fake_plan():
    return PlanOutput(
        reasoning="Count companies",
        query_strategy="SELECT COUNT(*) FROM companies",
        expected_answer_type="scalar",
        suggested_chart_type=None,
        tables_to_explore=["companies"],
    )


def _fake_explore():
    return ExploreOutput(
        queries_executed=[{"sql": "SELECT COUNT(*) FROM companies", "result_summary": "42"}],
        raw_data=[{"count": 42}],
        exploration_notes="Found 42 companies.",
        schema_context={"companies": ["id", "name", "industry"]},
    )


def _fake_answer():
    return AnswerOutput(
        text_answer="There are 42 companies in the dataset.",
        table_data=None,
        chart_data=None,
    )


@pytest.fixture
async def auth_client(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
async def test_send_message_e2e(auth_client: AsyncClient):
    """Full flow: create conversation, send message, get assistant response."""
    convo = _make_convo()
    router_ctx, router_session = _mock_session()
    pipeline_ctx, pipeline_session = _mock_session()

    # Track messages added to the router session
    messages_added = []
    original_add = router_session.add

    def track_add(obj):
        if isinstance(obj, Message):
            obj.id = uuid.uuid4()
            obj.created_at = datetime(2026, 1, 1)
            messages_added.append(obj)
        original_add(obj)

    router_session.add = track_add

    # First execute: find conversation
    # Second execute: load prior messages
    # Third execute: find schema_context explore step
    convo_result = MagicMock()
    convo_result.scalar_one_or_none.return_value = convo

    msg_result = MagicMock()
    msg_result.scalars.return_value.all.return_value = []

    explore_result = MagicMock()
    explore_result.scalar_one_or_none.return_value = None

    router_session.execute = AsyncMock(side_effect=[convo_result, msg_result, explore_result])

    async def mock_refresh(obj):
        if isinstance(obj, Message) and not hasattr(obj, "_refreshed"):
            obj._refreshed = True

    router_session.refresh = mock_refresh

    # Mock Pipeline.run to avoid actual LLM calls
    fake_answer = _fake_answer()

    with (
        patch("app.routers.conversations.AppSession", return_value=router_ctx),
        patch("app.routers.conversations.Pipeline") as MockPipeline,
    ):
        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance.run = AsyncMock(return_value=fake_answer)
        MockPipeline.return_value = mock_pipeline_instance

        resp = await auth_client.post(
            f"/api/conversations/{convo.id}/messages",
            json={"content": "How many companies are in the dataset?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert data["content"] == "There are 42 companies in the dataset."

    # Verify pipeline was called with correct args
    MockPipeline.assert_called_once_with(convo.id, messages_added[1].id)
    mock_pipeline_instance.run.assert_awaited_once()
    call_args = mock_pipeline_instance.run.call_args
    assert call_args[0][0] == "How many companies are in the dataset?"


@pytest.mark.asyncio
async def test_send_message_conversation_not_found(auth_client: AsyncClient):
    """404 when conversation doesn't exist."""
    ctx, session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        resp = await auth_client.post(
            f"/api/conversations/{uuid.uuid4()}/messages",
            json={"content": "hello"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pipeline_run_persists_steps():
    """Pipeline.run() creates PipelineRun and PipelineStep records."""
    ctx, session = _mock_session()
    records_added = []

    def track_add(obj):
        if isinstance(obj, (PipelineRun, PipelineStepModel)):
            obj.id = uuid.uuid4()
            records_added.append(obj)

    session.add = track_add

    async def mock_refresh(obj):
        pass

    session.refresh = mock_refresh

    fake_plan = _fake_plan()
    fake_explore = _fake_explore()
    fake_answer = _fake_answer()

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

    with patch("app.pipeline.orchestrator.AppSession", return_value=ctx):
        from app.pipeline.orchestrator import Pipeline

        pipeline = Pipeline(uuid.uuid4(), uuid.uuid4())

        # Patch all steps to use our mock
        for step in pipeline.steps:
            step.execute_with_retry = mock_execute_with_retry

        # Mock LLMClient
        with patch("app.pipeline.orchestrator.LLMClient"):
            result = await pipeline.run("How many companies?")

    assert isinstance(result, AnswerOutput)
    assert result.text_answer == "There are 42 companies in the dataset."

    # Should have created 1 PipelineRun + 3 PipelineSteps
    runs = [r for r in records_added if isinstance(r, PipelineRun)]
    steps = [r for r in records_added if isinstance(r, PipelineStepModel)]
    assert len(runs) == 1
    assert len(steps) == 3
    assert [s.step_name for s in steps] == ["plan", "explore", "answer"]


@pytest.mark.asyncio
async def test_pipeline_run_handles_failure():
    """Pipeline.run() marks run as failed on exception."""
    ctx, session = _mock_session()
    records_added = []

    def track_add(obj):
        if isinstance(obj, (PipelineRun, PipelineStepModel)):
            obj.id = uuid.uuid4()
            records_added.append(obj)

    session.add = track_add
    session.refresh = AsyncMock()

    # Fail on plan step
    async def mock_execute_fail(input_data, llm_client):
        raise ValueError("LLM error")

    # Mock the failed step query
    failed_step_result = MagicMock()
    failed_step_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=failed_step_result)

    with patch("app.pipeline.orchestrator.AppSession", return_value=ctx):
        from app.pipeline.orchestrator import Pipeline

        pipeline = Pipeline(uuid.uuid4(), uuid.uuid4())
        pipeline.steps[0].execute_with_retry = mock_execute_fail

        with (
            patch("app.pipeline.orchestrator.LLMClient"),
            pytest.raises(ValueError, match="LLM error"),
        ):
            await pipeline.run("test question")

    runs = [r for r in records_added if isinstance(r, PipelineRun)]
    assert len(runs) == 1
    assert runs[0].status == "failed"
