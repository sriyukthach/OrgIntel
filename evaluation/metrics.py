"""
OrgIntel Evaluation Metrics
Computes quality, accuracy, coverage, evidence provenance, and resource efficiency metrics.
"""

from typing import List, Dict, Any
from backend.app.models import CompanyProfile, Fact, VerificationStatus


def compute_evaluation_metrics(profiles: List[CompanyProfile], total_requests: int, total_cost: float, total_latency_ms: float) -> Dict[str, Any]:
    """
    Evaluates batch of researched profiles against the competition criteria:
    - Coverage: percentage of standard fields populated (identity, leadership, financials, overview, activity)
    - Verification Accuracy: verified facts ratio vs unverified/ambiguous
    - Evidence Provenance: 100% of verified facts must link to public source URL + non-empty excerpt
    - Resource Efficiency: requests per company, latency, API costs
    """
    total_companies = len(profiles)
    if total_companies == 0:
        return {"error": "No profiles to evaluate"}

    total_facts = 0
    total_verified_facts = 0
    total_ambiguous_facts = 0
    facts_with_valid_evidence = 0

    companies_with_leadership = 0
    companies_with_financials = 0
    companies_with_overview = 0
    companies_with_activities = 0

    for p in profiles:
        if p.leadership:
            companies_with_leadership += 1
        if p.financials:
            companies_with_financials += 1
        if p.overview and p.overview.business_description:
            companies_with_overview += 1
        if p.activities:
            companies_with_activities += 1

        for f in p.facts:
            total_facts += 1
            if f.verification_status == VerificationStatus.VERIFIED:
                total_verified_facts += 1
            elif f.verification_status == VerificationStatus.AMBIGUOUS:
                total_ambiguous_facts += 1

            if f.source_url.startswith("http") and f.evidence_excerpt and len(f.evidence_excerpt) > 5:
                facts_with_valid_evidence += 1

    fact_verification_rate = round(total_verified_facts / max(total_facts, 1), 4)
    evidence_provenance_rate = round(facts_with_valid_evidence / max(total_facts, 1), 4)
    leadership_coverage = round(companies_with_leadership / total_companies, 4)
    financial_coverage = round(companies_with_financials / total_companies, 4)
    overview_coverage = round(companies_with_overview / total_companies, 4)
    avg_latency_ms = round(total_latency_ms / total_companies, 2)
    avg_requests_per_company = round(total_requests / total_companies, 2)

    # Composite Score (0 - 100)
    composite_score = round(
        (fact_verification_rate * 30)
        + (evidence_provenance_rate * 30)
        + (leadership_coverage * 15)
        + (financial_coverage * 15)
        + (overview_coverage * 10),
        2,
    )

    return {
        "total_companies_evaluated": total_companies,
        "composite_intelligence_score": composite_score,
        "facts": {
            "total_extracted": total_facts,
            "total_verified": total_verified_facts,
            "total_ambiguous": total_ambiguous_facts,
            "verification_rate": fact_verification_rate,
            "evidence_provenance_rate": evidence_provenance_rate,
        },
        "coverage": {
            "leadership_rate": leadership_coverage,
            "financials_rate": financial_coverage,
            "overview_rate": overview_coverage,
            "activities_rate": round(companies_with_activities / total_companies, 4),
        },
        "performance": {
            "total_outbound_requests": total_requests,
            "avg_requests_per_company": avg_requests_per_company,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": avg_latency_ms,
            "challenge_limits_compliant": total_requests <= 2000 and total_cost <= 10.0,
        },
    }
