"""
Integration tests for Autonomous Research Agent Workflow.
"""

import pytest
from backend.app.agent.orchestrator import ResearchOrchestrator
from backend.app.models import ResearchRunStatus
from backend.app.database import init_db


@pytest.mark.asyncio
async def test_agent_research_valid_company():
    await init_db()
    orchestrator = ResearchOrchestrator()
    profile, run, changes = await orchestrator.run_research("923609016")

    assert profile is not None
    assert profile.canonical_identity.legal_name == "EQUINOR ASA"
    assert profile.canonical_identity.organization_number == "923609016"
    assert run.status == ResearchRunStatus.COMPLETED
    assert run.facts_verified > 0
    assert len(profile.evidence) > 0


@pytest.mark.asyncio
async def test_agent_research_invalid_org_number():
    await init_db()
    orchestrator = ResearchOrchestrator()
    profile, run, changes = await orchestrator.run_research("123456789")

    assert profile is None
    assert run.status == ResearchRunStatus.FAILED
    assert len(run.errors) > 0
