import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.app import Message, PipelineRun
from app.models.app import PipelineStep as PipelineStepModel


def _mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, session


def _make_pipeline_run(status="completed", steps=None):
    run = PipelineRun()
    run.id = uuid.uuid4()
    run.message_id = uuid.uuid4()
    run.status = status
    run.created_at = datetime(2026, 1, 1)
    run.completed_at = datetime(2026, 1, 2) if status == "completed" else None
    run.steps = steps or []
    return run


def _make_step(run_id, name, order, status="completed"):
    step = PipelineStepModel()
    step.id = uuid.uuid4()
    step.pipeline_run_id = run_id
    step.step_name = name
    step.step_order = order
    step.status = status
    step.attempts = 1
    step.error = "LLM error" if status == "failed" else None
    step.created_at = datetime(2026, 1, 1)
    step.completed_at = datetime(2026, 1, 1) if status == "completed" else None
    return step


@pytest.fixture
async def auth_client(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
async def test_get_pipeline_runs(auth_client: AsyncClient):
    """List pipeline runs for a conversation."""
    convo_id = uuid.uuid4()
    run = _make_pipeline_run()
    run.steps = [
        _make_step(run.id, "plan", 0),
        _make_step(run.id, "explore", 1),
        _make_step(run.id, "answer", 2),
    ]

    ctx, session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [run]
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        resp = await auth_client.get(f"/api/conversations/{convo_id}/pipeline-runs")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["status"] == "completed"
    assert len(data[0]["steps"]) == 3
    assert data[0]["steps"][0]["step_name"] == "plan"


@pytest.mark.asyncio
async def test_get_pipeline_runs_empty(auth_client: AsyncClient):
    """Empty list when no runs exist."""
    ctx, session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        resp = await auth_client.get(f"/api/conversations/{uuid.uuid4()}/pipeline-runs")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_retry_pipeline_run(auth_client: AsyncClient):
    """Retry a failed pipeline run."""
    run = _make_pipeline_run(status="failed")
    run.steps = [
        _make_step(run.id, "plan", 0, status="completed"),
        _make_step(run.id, "explore", 1, status="failed"),
    ]

    msg = Message()
    msg.id = run.message_id
    msg.conversation_id = uuid.uuid4()
    msg.role = "assistant"
    msg.content = None
    msg.created_at = datetime(2026, 1, 1)

    user_msg = Message()
    user_msg.id = uuid.uuid4()
    user_msg.conversation_id = msg.conversation_id
    user_msg.role = "user"
    user_msg.content = "How many companies?"
    user_msg.created_at = datetime(2026, 1, 1)

    ctx, session = _mock_session()

    run_result = MagicMock()
    run_result.scalar_one_or_none.return_value = run
    msg_result = MagicMock()
    msg_result.scalar_one.return_value = msg
    user_msg_result = MagicMock()
    user_msg_result.scalar_one_or_none.return_value = user_msg

    session.execute = AsyncMock(side_effect=[run_result, msg_result, user_msg_result])

    with (
        patch("app.routers.pipeline_runs.AppSession", return_value=ctx),
        patch("app.routers.pipeline_runs.Pipeline") as MockPipeline,
    ):
        mock_instance = AsyncMock()
        MockPipeline.return_value = mock_instance

        resp = await auth_client.post(f"/api/pipeline-runs/{run.id}/retry")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"  # Returns the original run


@pytest.mark.asyncio
async def test_retry_pipeline_run_not_found(auth_client: AsyncClient):
    """404 when run doesn't exist."""
    ctx, session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.pipeline_runs.AppSession", return_value=ctx):
        resp = await auth_client.post(f"/api/pipeline-runs/{uuid.uuid4()}/retry")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retry_pipeline_run_not_failed(auth_client: AsyncClient):
    """400 when trying to retry a non-failed run."""
    run = _make_pipeline_run(status="completed")
    run.steps = []

    ctx, session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = run
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.pipeline_runs.AppSession", return_value=ctx):
        resp = await auth_client.post(f"/api/pipeline-runs/{run.id}/retry")

    assert resp.status_code == 400
    assert "failed" in resp.json()["detail"].lower()
