"""
FastAPI Request & Response Schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.app.models import (
    CompanyProfile,
    ResearchRun,
    Fact,
    EvidenceRecord,
    ResearchRunStatus,
)


class ResearchRequest(BaseModel):
    """Payload to initiate research for a single company."""
    organization_number: str = Field(..., json_schema_extra={"example": "923609016"}, description="9-digit Norwegian Organization Number")
    force_refresh: bool = Field(default=False, description="Bypass cache and force full public re-audit")


class BatchResearchRequest(BaseModel):
    """Payload to batch research a list of organization numbers."""
    organization_numbers: List[str] = Field(..., description="List of 9-digit Norwegian Org Numbers")
    concurrency: int = Field(default=5, ge=1, le=20, description="Worker concurrency limit")


class ResearchResponse(BaseModel):
    """Result of a single company research operation."""
    success: bool
    message: str
    profile: Optional[CompanyProfile] = None
    run_metadata: Optional[ResearchRun] = None
    change_summary: Optional[Dict[str, Any]] = None


class BatchResearchResponse(BaseModel):
    """Summary of batch research execution."""
    total_requested: int
    successful_count: int
    failed_count: int
    total_latency_seconds: float
    total_outbound_requests: int
    results: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    """System health check payload."""
    status: str
    app_name: str
    version: str
    environment: str
    database_connected: bool
    challenge_limits: Dict[str, Any]
