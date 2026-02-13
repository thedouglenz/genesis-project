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
    """send_message returns placeholder assistant message, pipeline runs in background."""
    convo = _make_convo()
    ctx, session = _mock_session()

    def track_add(obj):
        if isinstance(obj, Message):
            obj.id = uuid.uuid4()
            obj.created_at = datetime(2026, 1, 1)

    session.add = track_add
    session.refresh = AsyncMock()

    convo_result = MagicMock()
    convo_result.scalar_one_or_none.return_value = convo
    msg_result = MagicMock()
    msg_result.scalars.return_value.all.return_value = []
    explore_result = MagicMock()
    explore_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[convo_result, msg_result, explore_result])

    fake_answer = _fake_answer()

    with (
        patch("app.routers.conversations.AppSession", return_value=ctx),
        patch("app.routers.conversations.Pipeline") as MockPipeline,
    ):
        mock_instance = AsyncMock()
        mock_instance.run = AsyncMock(return_value=fake_answer)
        MockPipeline.return_value = mock_instance

        resp = await auth_client.post(
            f"/api/conversations/{convo.id}/messages",
            json={"content": "How many companies are in the dataset?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    # Content is None — pipeline runs as background task
    assert data["content"] is None


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
async def test_pipeline_skips_explore_when_flagged():
    """Pipeline.run() skips explore step when plan says skip_explore=True."""
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

    fake_plan = PlanOutput(
        reasoning="User wants a pie chart of already-fetched data",
        query_strategy="Reformat existing data",
        expected_answer_type="chart",
        suggested_chart_type="pie",
        tables_to_explore=[],
        skip_explore=True,
    )
    fake_answer = AnswerOutput(
        text_answer="Here is the pie chart.",
        table_data=None,
        chart_data=None,
    )

    call_count = 0

    async def mock_execute_with_retry(input_data, llm_client):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return fake_plan
        else:
            return fake_answer

    with patch("app.pipeline.orchestrator.AppSession", return_value=ctx):
        from app.pipeline.orchestrator import Pipeline

        pipeline = Pipeline(uuid.uuid4(), uuid.uuid4())
        for step in pipeline.steps:
            step.execute_with_retry = mock_execute_with_retry

        with patch("app.pipeline.orchestrator.LLMClient"):
            result = await pipeline.run(
                "Show that as a pie chart",
                conversation_history=[
                    {"role": "user", "content": "How many companies per industry?"},
                    {"role": "assistant", "content": "Construction: 34, Legal Tech: 31..."},
                ],
            )

    assert isinstance(result, AnswerOutput)
    assert result.text_answer == "Here is the pie chart."

    # Should have 1 PipelineRun + 2 PipelineSteps (plan + answer, no explore)
    runs = [r for r in records_added if isinstance(r, PipelineRun)]
    steps = [r for r in records_added if isinstance(r, PipelineStepModel)]
    assert len(runs) == 1
    assert len(steps) == 2
    assert [s.step_name for s in steps] == ["plan", "answer"]


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
