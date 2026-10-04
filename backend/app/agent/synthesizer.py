"""
Profile Synthesis & Dossier Assembly Engine
Synthesizes verified facts, attaches provenance evidence, and compiles final company intelligence profile.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.models import (
    CompanyIdentity,
    CompanyOverview,
    PersonRole,
    FinancialRecord,
    CompanyActivity,
    Fact,
    EvidenceRecord,
    CompanyProfile,
    ResearchRunStatus,
    VerificationStatus,
    SourcePriority,
)
from backend.app.verification.evidence import resolve_fact_conflict, create_evidence_record, validate_evidence_provenance
from backend.app.verification.confidence import calculate_profile_confidence


class ProfileSynthesizer:
    """Combines extracted facts, deduplicates records, attaches evidence, and builds final profile."""

    @staticmethod
    def synthesize_profile(
        canonical_identity: CompanyIdentity,
        raw_facts: List[Fact],
        leadership: List[PersonRole],
        financials: List[FinancialRecord],
        activities: List[CompanyActivity],
        overview: Optional[CompanyOverview] = None,
    ) -> CompanyProfile:
        """
        Synthesizes validated profile:
        1. Validates evidence provenance on every fact
        2. Deduplicates facts and resolves conflicting sources
        3. Creates structured EvidenceRecord repository
        4. Calculates confidence
        """
        # 1. Fact Deduplication & Conflict Resolution
        fact_map: Dict[str, Fact] = {}
        for fact in raw_facts:
            # Validate provenance
            is_valid_ev, msg = validate_evidence_provenance(fact)
            if not is_valid_ev:
                fact.verification_status = VerificationStatus.AMBIGUOUS
                fact.confidence = 0.2

            field_key = fact.field
            if field_key not in fact_map:
                fact_map[field_key] = fact
            else:
                existing = fact_map[field_key]
                # Determine source priorities
                p_exist = SourcePriority.OFFICIAL_REGISTRY.value if "brreg.no" in existing.source_url else SourcePriority.COMPANY_WEBSITE.value
                p_new = SourcePriority.OFFICIAL_REGISTRY.value if "brreg.no" in fact.source_url else SourcePriority.COMPANY_WEBSITE.value
                fact_map[field_key] = resolve_fact_conflict(existing, fact, p_exist, p_new)

        final_facts = list(fact_map.values())

        # 2. Build Evidence Records
        evidence_dict: Dict[str, EvidenceRecord] = {}
        for f in final_facts:
            if f.source_url not in evidence_dict:
                from urllib.parse import urlparse
                domain = urlparse(f.source_url).netloc or "brreg.no"
                prio = SourcePriority.OFFICIAL_REGISTRY.value if "brreg.no" in f.source_url else SourcePriority.COMPANY_WEBSITE.value
                ev = create_evidence_record(
                    source_url=f.source_url,
                    source_title=f.source_title,
                    publisher_domain=domain,
                    evidence_excerpt=f.evidence_excerpt,
                    supported_fields=[f.field],
                    source_priority=prio,
                    publication_date=f.effective_date,
                )
                evidence_dict[f.source_url] = ev
            else:
                if f.field not in evidence_dict[f.source_url].supported_fields:
                    evidence_dict[f.source_url].supported_fields.append(f.field)

        evidence_list = list(evidence_dict.values())

        # 3. Overview Resolution
        final_overview = overview or CompanyOverview(
            business_description=canonical_identity.industry_description,
            products_services=[],
            sectors=[canonical_identity.industry_description] if canonical_identity.industry_description else [],
            locations=[canonical_identity.city] if canonical_identity.city else [],
            description_source_url=canonical_identity.source_url,
            verification_status=VerificationStatus.PROBABLE,
        )

        return CompanyProfile(
            organization_number=canonical_identity.organization_number,
            canonical_identity=canonical_identity,
            overview=final_overview,
            leadership=leadership,
            financials=financials,
            activities=activities,
            facts=final_facts,
            evidence=evidence_list,
            last_researched=datetime.now(timezone.utc).isoformat(),
            research_status=ResearchRunStatus.COMPLETED,
        )
