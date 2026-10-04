"""
Research Agent Orchestrator
Implements the autonomous research loop:
OBSERVE -> PLAN -> SEARCH -> EXTRACT -> VERIFY -> STORE -> CHECK GAPS -> SEARCH AGAIN -> SYNTHESIZE
"""

import time
import uuid
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable
from datetime import datetime, timezone

from backend.app.models import (
    CompanyProfile,
    CompanyIdentity,
    CompanyOverview,
    PersonRole,
    FinancialRecord,
    CompanyActivity,
    Fact,
    EvidenceRecord,
    ResearchRun,
    ResearchRunStatus,
    VerificationStatus,
)
from backend.app.agent.planner import ResearchPlanner
from backend.app.agent.resolver import IdentityResolver
from backend.app.agent.synthesizer import ProfileSynthesizer
from backend.app.sources.base import RequestTracker
from backend.app.sources.brreg import BrregClient
from backend.app.sources.company_web import CompanyWebClient
from backend.app.sources.financials import FinancialsResearcher
from backend.app.sources.activity import ActivityResearcher
from backend.app.extraction.facts import extract_identity_facts
from backend.app.extraction.people import extract_people_from_brreg_roles, people_to_facts
from backend.app.storage.repository import Repository


class ResearchOrchestrator:
    """Coordinates autonomous multi-step public company research."""

    def __init__(self):
        self.tracker = RequestTracker()
        self.resolver = IdentityResolver(self.tracker)
        self.brreg_client = BrregClient(self.tracker)
        self.web_client = CompanyWebClient(self.tracker)
        self.fin_researcher = FinancialsResearcher(self.tracker)
        self.act_researcher = ActivityResearcher(self.tracker)

    async def run_research(
        self,
        org_number: str,
        force_refresh: bool = False,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Tuple[Optional[CompanyProfile], ResearchRun, Dict[str, Any]]:
        """
        Executes full agentic research pipeline for a given organization number.
        When force_refresh=True, bypasses cached source responses and performs fresh network queries.
        Returns (CompanyProfile, ResearchRun, ChangeSummary).
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        start_iso = datetime.now(timezone.utc).isoformat()

        run = ResearchRun(
            run_id=run_id,
            organization_number=org_number,
            started_at=start_iso,
            status=ResearchRunStatus.RUNNING,
            sources_attempted=[],
            sources_successful=[],
        )

        async def emit(step: str, detail: str, status: str = "IN_PROGRESS"):
            evt = {
                "run_id": run_id,
                "org_number": org_number,
                "step": step,
                "detail": detail,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(evt)
                else:
                    progress_callback(evt)

        try:
            # 1. OBSERVE & PLAN
            await emit("PLANNING", "Initializing research roadmap and verification strategy.", "COMPLETED")
            plan = ResearchPlanner.create_initial_plan(org_number)

            # 2. RESOLVE IDENTITY (Authoritative Registry Check)
            run.sources_attempted.append("brreg_enheter")
            await emit("IDENTITY_RESOLUTION", "Resolving organization in authoritative Norwegian registry...", "RUNNING")
            identity, res_msg = await self.resolver.resolve_identity(org_number, force_refresh=force_refresh)

            if not identity:
                run.status = ResearchRunStatus.FAILED
                run.errors.append(res_msg)
                run.completed_at = datetime.now(timezone.utc).isoformat()
                run.latency_ms = round((time.time() - start_time) * 1000, 2)
                run.outbound_requests_count = self.tracker.request_count
                await Repository.save_research_run(run)
                await emit("IDENTITY_RESOLUTION", res_msg, "FAILED")
                return None, run, {"has_changes": False, "error": res_msg}

            run.sources_successful.append("brreg_enheter")
            await emit(
                "IDENTITY_RESOLUTION",
                f"Resolved canonical identity: {identity.legal_name} ({identity.organization_form})",
                "COMPLETED",
            )

            # Base facts from canonical identity
            accumulated_facts: List[Fact] = extract_identity_facts(identity)

            # 3. ROLES & LEADERSHIP RESEARCH
            run.sources_attempted.append("brreg_roller")
            await emit("LEADERSHIP_RESEARCH", "Extracting executive management and registered board members...", "RUNNING")
            roles_raw, roles_url = await self.brreg_client.fetch_roller(
                identity.organization_number, force_refresh=force_refresh
            )
            leadership: List[PersonRole] = []
            if roles_raw:
                run.sources_successful.append("brreg_roller")
                leadership = extract_people_from_brreg_roles(roles_raw, roles_url)
                lead_facts = people_to_facts(leadership)
                accumulated_facts.extend(lead_facts)
                await emit(
                    "LEADERSHIP_RESEARCH",
                    f"Verified {len(leadership)} leadership roles from Enhetsregisteret Roller.",
                    "COMPLETED",
                )
            else:
                await emit("LEADERSHIP_RESEARCH", "No separate public role entries returned.", "COMPLETED")

            # 4. FINANCIAL AUDIT & ACCOUNTS RESEARCH
            run.sources_attempted.append("brreg_regnskap")
            await emit("FINANCIAL_AUDIT", "Searching Regnskapsregisteret for audited financial filings...", "RUNNING")
            financials, fin_facts, fin_url = await self.fin_researcher.research_financials(
                identity.organization_number, force_refresh=force_refresh
            )
            if financials:
                run.sources_successful.append("brreg_regnskap")
                accumulated_facts.extend(fin_facts)
                await emit(
                    "FINANCIAL_AUDIT",
                    f"Extracted verified accounts for {len(financials)} reporting periods (latest FY{financials[0].reporting_year}).",
                    "COMPLETED",
                )
            else:
                await emit("FINANCIAL_AUDIT", "No public financial filings available.", "COMPLETED")

            # 5. OFFICIAL COMPANY WEBSITE CRAWL & OVERVIEW
            overview = None
            if identity.website:
                run.sources_attempted.append("company_website")
                await emit("WEBSITE_ANALYSIS", f"Analyzing official website ({identity.website})...", "RUNNING")
                web_overview, web_facts, web_url = await self.web_client.analyze_website(
                    identity.website, identity.legal_name, force_refresh=force_refresh
                )
                if web_overview and web_overview.business_description:
                    run.sources_successful.append("company_website")
                    overview = web_overview
                    accumulated_facts.extend(web_facts)
                    await emit("WEBSITE_ANALYSIS", "Extracted verified business mission and operations.", "COMPLETED")
                else:
                    await emit("WEBSITE_ANALYSIS", "Website reachable; standard company profile maintained.", "COMPLETED")

            # 6. ANNOUNCEMENTS & CORPORATE EVENTS
            run.sources_attempted.append("brreg_kunngjoringer")
            await emit("ACTIVITY_ANALYSIS", "Checking Kunngjøringsregisteret for official corporate announcements...", "RUNNING")
            activities, act_url = await self.act_researcher.research_activities(
                identity.organization_number, force_refresh=force_refresh
            )
            if activities:
                run.sources_successful.append("brreg_kunngjoringer")
                await emit("ACTIVITY_ANALYSIS", f"Retrieved {len(activities)} recent register announcements.", "COMPLETED")
            else:
                await emit("ACTIVITY_ANALYSIS", "No recent public register announcements.", "COMPLETED")

            # 7. CHECK GAPS & SYNTHESIZE
            await emit("SYNTHESIS", "Validating evidence provenance and synthesizing intelligence profile...", "RUNNING")
            gaps = ResearchPlanner.evaluate_gaps(identity, accumulated_facts)
            if gaps:
                run.warnings.append(f"Informational gaps identified in public domain: {', '.join(gaps)}")

            profile = ProfileSynthesizer.synthesize_profile(
                canonical_identity=identity,
                raw_facts=accumulated_facts,
                leadership=leadership,
                financials=financials,
                activities=activities,
                overview=overview,
            )

            # 8. PERSIST & DETECT HISTORICAL CHANGES
            changes = await Repository.save_company_profile(profile)
            profile.change_summary = changes

            # Finalize Run Record
            run.status = ResearchRunStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc).isoformat()
            run.latency_ms = round((time.time() - start_time) * 1000, 2)
            run.facts_found = len(profile.facts)
            run.facts_verified = sum(1 for f in profile.facts if f.verification_status == VerificationStatus.VERIFIED)
            run.outbound_requests_count = self.tracker.request_count
            run.estimated_cost_usd = self.tracker.estimated_cost_usd

            await Repository.save_research_run(run)
            await emit(
                "COMPLETED",
                f"Research complete: {run.facts_verified} verified facts, {len(profile.evidence)} evidence sources.",
                "COMPLETED",
            )

            return profile, run, changes

        except Exception as exc:
            run.status = ResearchRunStatus.FAILED
            run.errors.append(str(exc))
            run.completed_at = datetime.now(timezone.utc).isoformat()
            run.latency_ms = round((time.time() - start_time) * 1000, 2)
            await Repository.save_research_run(run)
            await emit("ERROR", f"Research encountered unexpected error: {str(exc)}", "FAILED")
            return None, run, {"has_changes": False, "error": str(exc)}
