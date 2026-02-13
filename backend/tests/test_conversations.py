import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_client(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
async def test_create_conversation(auth_client: AsyncClient):
    resp = await auth_client.post("/api/conversations", json={"title": "Test convo"})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["title"] == "Test convo"


@pytest.mark.asyncio
async def test_create_conversation_auto_title(auth_client: AsyncClient):
    resp = await auth_client.post("/api/conversations", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_list_conversations(auth_client: AsyncClient):
    await auth_client.post("/api/conversations", json={"title": "List test 1"})
    await auth_client.post("/api/conversations", json={"title": "List test 2"})
    resp = await auth_client.get("/api/conversations")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_get_conversation(auth_client: AsyncClient):
    create_resp = await auth_client.post("/api/conversations", json={"title": "Get test"})
    convo_id = create_resp.json()["id"]
    resp = await auth_client.get(f"/api/conversations/{convo_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == convo_id
    assert data["title"] == "Get test"
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_get_conversation_not_found(auth_client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await auth_client.get(f"/api/conversations/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation(auth_client: AsyncClient):
    create_resp = await auth_client.post("/api/conversations", json={"title": "Delete test"})
    convo_id = create_resp.json()["id"]
    del_resp = await auth_client.delete(f"/api/conversations/{convo_id}")
    assert del_resp.status_code == 200
    get_resp = await auth_client.get(f"/api/conversations/{convo_id}")
    assert get_resp.status_code == 404
