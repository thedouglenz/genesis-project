import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_no_token(client: AsyncClient):
    resp = await client.get("/api/conversations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_token(client: AsyncClient):
    login = await client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    token = login.json()["token"]
    resp = await client.get("/api/conversations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code != 401
