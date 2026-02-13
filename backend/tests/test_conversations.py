import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.app import Conversation


def _make_convo(title="Test convo", convo_id=None):
    """Create a fake Conversation model instance."""
    c = Conversation()
    c.id = convo_id or uuid.uuid4()
    c.title = title
    c.created_at = datetime(2026, 1, 1)
    c.updated_at = datetime(2026, 1, 1)
    c.messages = []
    return c


def _mock_session():
    """Create a mock async session with context manager support."""
    session = AsyncMock()
    # add() is synchronous on SQLAlchemy sessions
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
async def test_create_conversation(auth_client: AsyncClient):
    fake_convo = _make_convo("Test convo")
    ctx, session = _mock_session()

    async def mock_refresh(obj):
        obj.id = fake_convo.id
        obj.created_at = fake_convo.created_at
        obj.updated_at = fake_convo.updated_at

    session.refresh = mock_refresh

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        resp = await auth_client.post("/api/conversations", json={"title": "Test convo"})

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["title"] == "Test convo"


@pytest.mark.asyncio
async def test_create_conversation_auto_title(auth_client: AsyncClient):
    fake_convo = _make_convo(title=None)
    ctx, session = _mock_session()

    async def mock_refresh(obj):
        obj.id = fake_convo.id
        obj.created_at = fake_convo.created_at
        obj.updated_at = fake_convo.updated_at

    session.refresh = mock_refresh

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        resp = await auth_client.post("/api/conversations", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(auth_client: AsyncClient):
    convos = [_make_convo("Convo 1"), _make_convo("Convo 2")]
    ctx, session = _mock_session()

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = convos
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        resp = await auth_client.get("/api/conversations")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_conversation(auth_client: AsyncClient):
    fake_convo = _make_convo("Get test")
    ctx, session = _mock_session()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = fake_convo
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        resp = await auth_client.get(f"/api/conversations/{fake_convo.id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(fake_convo.id)
    assert data["title"] == "Get test"
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_get_conversation_not_found(auth_client: AsyncClient):
    ctx, session = _mock_session()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        fake_id = str(uuid.uuid4())
        resp = await auth_client.get(f"/api/conversations/{fake_id}")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation(auth_client: AsyncClient):
    fake_convo = _make_convo("Delete test")
    ctx, session = _mock_session()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = fake_convo
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        resp = await auth_client.delete(f"/api/conversations/{fake_convo.id}")

    assert resp.status_code == 200
    session.delete.assert_called_once_with(fake_convo)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_conversation_not_found(auth_client: AsyncClient):
    ctx, session = _mock_session()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    with patch("app.routers.conversations.AppSession", return_value=ctx):
        fake_id = str(uuid.uuid4())
        resp = await auth_client.delete(f"/api/conversations/{fake_id}")

    assert resp.status_code == 404
