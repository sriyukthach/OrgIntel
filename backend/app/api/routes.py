"""
OrgIntel FastAPI Route Handlers
Defines all public REST endpoints for research, retrieval, snapshots, history, and batch operations.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from backend.app.config import settings
from backend.app.models import CompanyProfile, Fact, EvidenceRecord, ResearchRun
from backend.app.storage.repository import Repository
from backend.app.agent.orchestrator import ResearchOrchestrator
from backend.app.verification.identity import clean_org_number, validate_norwegian_org_number
from backend.app.api.schemas import (
    ResearchRequest,
    BatchResearchRequest,
    ResearchResponse,
    BatchResearchResponse,
    HealthResponse,
)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Health status and challenge resource limits."""
    db_ok = False
    try:
        companies = await Repository.get_all_companies(limit=1)
        db_ok = True
    except Exception:
        db_ok = False

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        app_name=settings.APP_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database_connected=db_ok,
        challenge_limits={
            "max_outbound_requests": 2000,
            "max_external_cost_usd": 10.00,
            "max_execution_time_minutes": 45,
        },
    )


@router.post("/research", response_model=ResearchResponse)
async def research_company(payload: ResearchRequest):
    """
    Main Research Endpoint:
    Triggers autonomous agentic research for a Norwegian organization number.
    Reuses existing profile if already cached unless force_refresh=True.
    """
    clean_nr = clean_org_number(payload.organization_number)
    is_valid, val_msg = validate_norwegian_org_number(clean_nr)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid Norwegian organization number: {val_msg}")

    # Check cached profile if not force_refresh
    if not payload.force_refresh:
        existing_profile = await Repository.get_company_profile(clean_nr)
        if existing_profile:
            return ResearchResponse(
                success=True,
                message="Retrieved existing validated company profile from database.",
                profile=existing_profile,
                run_metadata=None,
                change_summary=None,
            )

    orchestrator = ResearchOrchestrator()
    profile, run, changes = await orchestrator.run_research(clean_nr)

    if not profile:
        raise HTTPException(
            status_code=404 if "not found" in run.errors[0].lower() else 500,
            detail=run.errors[0] if run.errors else "Research failed to resolve company.",
        )

    return ResearchResponse(
        success=True,
        message="Company research and verification completed successfully.",
        profile=profile,
        run_metadata=run,
        change_summary=changes,
    )


@router.get("/companies")
async def list_companies(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """List summary of researched companies."""
    return await Repository.get_all_companies(limit=limit, offset=offset)


@router.get("/companies/{org_number}", response_model=CompanyProfile)
async def get_company(org_number: str):
    """Retrieve full company intelligence profile by organization number."""
    clean_nr = clean_org_number(org_number)
    profile = await Repository.get_company_profile(clean_nr)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Company {clean_nr} not found in database. Run research first.")
    return profile


@router.get("/companies/{org_number}/facts", response_model=List[Fact])
async def get_company_facts(org_number: str):
    """Retrieve atomic facts and verification states for a company."""
    clean_nr = clean_org_number(org_number)
    profile = await Repository.get_company_profile(clean_nr)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Company {clean_nr} not found.")
    return profile.facts


@router.get("/companies/{org_number}/evidence", response_model=List[EvidenceRecord])
async def get_company_evidence(org_number: str):
    """Retrieve public source evidence records and excerpts."""
    clean_nr = clean_org_number(org_number)
    profile = await Repository.get_company_profile(clean_nr)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Company {clean_nr} not found.")
    return profile.evidence


@router.get("/companies/{org_number}/history")
async def get_company_history(org_number: str):
    """Retrieve historical snapshots and temporal diffs."""
    clean_nr = clean_org_number(org_number)
    snapshots = await Repository.get_snapshots_history(clean_nr)
    if not snapshots:
        raise HTTPException(status_code=404, detail=f"No snapshot history for company {clean_nr}.")
    return {
        "organization_number": clean_nr,
        "total_snapshots": len(snapshots),
        "snapshots": snapshots,
    }


@router.post("/companies/{org_number}/refresh", response_model=ResearchResponse)
async def refresh_company(org_number: str):
    """Forces fresh re-audit of company information across all public sources."""
    return await research_company(ResearchRequest(organization_number=org_number, force_refresh=True))


@router.post("/research/batch", response_model=BatchResearchResponse)
async def batch_research_companies(payload: BatchResearchRequest):
    """
    Batch research endpoint to process multiple companies with controlled concurrency.
    Supports scaling to 1,000 company profiles within API limits.
    """
    start_time = time.time()
    results = []
    sem = asyncio.Semaphore(payload.concurrency)
    total_outbound = 0

    async def _research_one(org_nr: str):
        nonlocal total_outbound
        clean_nr = clean_org_number(org_nr)
        async with sem:
            orchestrator = ResearchOrchestrator()
            profile, run, changes = await orchestrator.run_research(clean_nr)
            total_outbound += run.outbound_requests_count
            return {
                "org_number": clean_nr,
                "success": profile is not None,
                "legal_name": profile.canonical_identity.legal_name if profile else None,
                "status": run.status.value,
                "facts_verified": run.facts_verified,
                "latency_ms": run.latency_ms,
                "error": run.errors[0] if run.errors else None,
            }

    tasks = [_research_one(nr) for nr in payload.organization_numbers]
    results = await asyncio.gather(*tasks)

    success_cnt = sum(1 for r in results if r["success"])
    fail_cnt = len(results) - success_cnt

    return BatchResearchResponse(
        total_requested=len(payload.organization_numbers),
        successful_count=success_cnt,
        failed_count=fail_cnt,
        total_latency_seconds=round(time.time() - start_time, 2),
        total_outbound_requests=total_outbound,
        results=results,
    )


@router.get("/research/runs/{run_id}", response_model=ResearchRun)
async def get_research_run(run_id: str):
    """Retrieve execution metrics and logs for a specific research run."""
    run = await Repository.get_research_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Research run {run_id} not found.")
    return run
