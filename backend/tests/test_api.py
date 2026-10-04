"""
Integration tests for FastAPI REST Endpoints.
"""

import pytest
import httpx
from backend.app.main import app
from backend.app.database import init_sync_db


@pytest.fixture(autouse=True)
def setup_db():
    init_sync_db()


@pytest.mark.asyncio
async def test_api_health():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == "OrgIntel"
        assert data["status"] in ("healthy", "degraded")
        assert "challenge_limits" in data


@pytest.mark.asyncio
async def test_api_research_and_retrieval():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Research company
        res = await client.post("/api/research", json={"organization_number": "923609016"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["profile"]["canonical_identity"]["organization_number"] == "923609016"

        # 2. Get company facts
        facts_res = await client.get("/api/companies/923609016/facts")
        assert facts_res.status_code == 200
        facts = facts_res.json()
        assert len(facts) > 0

        # 3. Get company evidence
        ev_res = await client.get("/api/companies/923609016/evidence")
        assert ev_res.status_code == 200
        evidence = ev_res.json()
        assert len(evidence) > 0


@pytest.mark.asyncio
async def test_api_invalid_org_number():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/research", json={"organization_number": "000000000"})
        assert res.status_code == 400
