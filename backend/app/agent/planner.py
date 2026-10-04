"""
Research Planner Engine
Determines the research roadmap, prioritizes missing fields, and plans retrieval stages.
"""

from typing import List, Dict, Any, Set
from backend.app.models import CompanyIdentity, Fact, VerificationStatus


class ResearchPlan:
    """Represents a planned sequence of research steps."""

    def __init__(self, org_number: str):
        self.org_number = org_number
        self.steps: List[Dict[str, Any]] = []
        self.missing_critical_fields: Set[str] = set()

    def add_step(self, stage: str, source_type: str, description: str, priority: int = 1):
        self.steps.append({
            "stage": stage,
            "source_type": source_type,
            "description": description,
            "priority": priority,
            "status": "PENDING",
        })


class ResearchPlanner:
    """Plans source searches and analyzes information gaps."""

    @staticmethod
    def create_initial_plan(org_number: str) -> ResearchPlan:
        """Constructs the baseline research strategy for a Norwegian organization number."""
        plan = ResearchPlan(org_number)
        plan.add_step(
            stage="RESOLVE_IDENTITY",
            source_type="brreg_enheter",
            description="Query authoritative Enhetsregisteret for legal entity validation.",
            priority=1,
        )
        plan.add_step(
            stage="DISCOVER_ROLES",
            source_type="brreg_roller",
            description="Extract verified executive leadership, board chair, and board members.",
            priority=2,
        )
        plan.add_step(
            stage="FETCH_FINANCIALS",
            source_type="brreg_regnskap",
            description="Retrieve audited annual accounts and balance sheet figures.",
            priority=3,
        )
        plan.add_step(
            stage="RESEARCH_WEBSITE",
            source_type="company_web",
            description="Analyze official company website for business overview, products, and mission.",
            priority=4,
        )
        plan.add_step(
            stage="ANALYZE_ACTIVITY",
            source_type="brreg_kunngjoringer",
            description="Extract official register announcements and corporate events.",
            priority=5,
        )
        return plan

    @staticmethod
    def evaluate_gaps(identity: CompanyIdentity, facts: List[Fact]) -> List[str]:
        """Identifies missing facts that require supplementary targeted research."""
        existing_fields = {f.field for f in facts if f.verification_status == VerificationStatus.VERIFIED}
        gaps: List[str] = []

        if "business_description" not in existing_fields:
            gaps.append("business_description")
        if "ceo" not in existing_fields and "board_chair" not in existing_fields:
            gaps.append("leadership")
        if "revenue" not in existing_fields:
            gaps.append("financials")
        if "website" not in existing_fields:
            gaps.append("website")

        return gaps
