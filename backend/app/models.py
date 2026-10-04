"""
OrgIntel Data Models & Schemas
Defines core domain entities, fact models, verification states, and profile schemas.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class VerificationStatus(str, Enum):
    """Fact verification lifecycle state."""
    VERIFIED = "VERIFIED"
    PROBABLE = "PROBABLE"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    FAILED = "FAILED"


class ResearchRunStatus(str, Enum):
    """Research run lifecycle state."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    AMBIGUOUS = "AMBIGUOUS"


class SourcePriority(int, Enum):
    """Source authority hierarchy."""
    OFFICIAL_REGISTRY = 1      # Brreg / official registry (highest)
    COMPANY_WEBSITE = 2        # Official domain / filings
    FINANCIAL_FILING = 3       # Official audited financials
    REPUTABLE_DATABASE = 4     # Open business registries / Proff / Purehelp
    REPUTABLE_NEWS = 5         # Official announcements / press releases
    OTHER = 6                  # General public web


class Fact(BaseModel):
    """Atomic verifiable company fact traceable to public evidence."""
    field: str = Field(..., description="Fact field name, e.g. 'legal_name', 'revenue'")
    value: Any = Field(..., description="Raw or formatted extracted value")
    normalized_value: Any = Field(None, description="Normalized representation (numeric, ISO date, standardized text)")
    source_url: str = Field(..., description="Direct URL where the fact was obtained")
    source_title: str = Field(..., description="Title of the source document/page")
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    effective_date: Optional[str] = Field(None, description="Effective or publication date")
    reporting_period: Optional[str] = Field(None, description="Accounting period, e.g. 'FY2024'")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    verification_status: VerificationStatus = Field(default=VerificationStatus.VERIFIED)
    evidence_excerpt: str = Field(..., description="Exact textual excerpt or JSON segment proving this fact")


class EvidenceRecord(BaseModel):
    """Full evidence provenance record for traceability."""
    id: str
    source_url: str
    source_title: str
    publisher_domain: str
    retrieval_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    publication_date: Optional[str] = None
    evidence_excerpt: str
    supported_fields: List[str] = Field(default_factory=list)
    source_priority: int = SourcePriority.OTHER.value
    content_hash: Optional[str] = None


class CompanyIdentity(BaseModel):
    """Canonical Norwegian company identity resolved from authoritative registries."""
    organization_number: str = Field(..., description="9-digit Norwegian Org Number")
    legal_name: str
    organization_form: str = Field(default="AS", description="Org form code, e.g. AS, ASA, ENK")
    organization_form_description: Optional[str] = None
    registration_status: str = Field(default="Active")
    is_active: bool = True
    registered_address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    municipality: Optional[str] = None
    municipality_number: Optional[str] = None
    country: str = "Norway"
    industry_code: Optional[str] = None
    industry_description: Optional[str] = None
    registration_date: Optional[str] = None
    founding_date: Optional[str] = None
    website: Optional[str] = None
    source: str = "Brønnøysundregistrene (Brreg)"
    source_url: str = "https://data.brreg.no/enhetsregisteret/api"
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verification_status: VerificationStatus = VerificationStatus.VERIFIED


class CompanyOverview(BaseModel):
    """Business overview, descriptions, and operations."""
    business_description: Optional[str] = None
    products_services: List[str] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)
    markets: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    number_of_employees: Optional[int] = None
    description_source_url: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.NOT_AVAILABLE


class PersonRole(BaseModel):
    """Leadership or board member associated with company."""
    name: str
    role: str
    role_code: Optional[str] = None
    birth_year: Optional[int] = None
    effective_date: Optional[str] = None
    source_url: str
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    evidence_excerpt: Optional[str] = None


class FinancialRecord(BaseModel):
    """Yearly/periodic financial performance record."""
    reporting_year: int
    currency: str = "NOK"
    revenue: Optional[float] = None
    operating_result: Optional[float] = None
    profit_loss: Optional[float] = None
    total_assets: Optional[float] = None
    equity: Optional[float] = None
    source: str
    source_url: str
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    evidence_excerpt: Optional[str] = None


class CompanyActivity(BaseModel):
    """Recent announcements, registry changes, or news."""
    title: str
    date: Optional[str] = None
    summary: str
    activity_type: str = "Announcement"
    source_url: str


class ResearchRun(BaseModel):
    """Execution metadata and performance metrics for a single research run."""
    run_id: str
    organization_number: str
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    status: ResearchRunStatus = ResearchRunStatus.RUNNING
    sources_attempted: List[str] = Field(default_factory=list)
    sources_successful: List[str] = Field(default_factory=list)
    facts_found: int = 0
    facts_verified: int = 0
    outbound_requests_count: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class CompanyProfile(BaseModel):
    """Complete synthesized intelligence dossier for a company."""
    organization_number: str
    canonical_identity: CompanyIdentity
    overview: CompanyOverview = Field(default_factory=CompanyOverview)
    leadership: List[PersonRole] = Field(default_factory=list)
    financials: List[FinancialRecord] = Field(default_factory=list)
    activities: List[CompanyActivity] = Field(default_factory=list)
    facts: List[Fact] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    last_researched: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    research_status: ResearchRunStatus = ResearchRunStatus.COMPLETED
    change_summary: Optional[Dict[str, Any]] = None
