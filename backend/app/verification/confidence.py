"""
Confidence & Reliability Scoring Engine
Calculates overall profile confidence scores based on evidence depth and source authority.
"""

from typing import List, Dict, Any
from backend.app.models import Fact, VerificationStatus, SourcePriority


def calculate_profile_confidence(facts: List[Fact]) -> Dict[str, Any]:
    """
    Computes summary confidence metrics across all verified facts:
    - overall_score (0.0 to 1.0)
    - verified_fact_ratio
    - authoritative_sources_count
    - ambiguity_count
    """
    if not facts:
        return {
            "overall_score": 0.0,
            "total_facts": 0,
            "verified_facts": 0,
            "ambiguous_facts": 0,
            "unverified_facts": 0,
            "quality_tier": "EMPTY",
        }

    total = len(facts)
    verified = sum(1 for f in facts if f.verification_status == VerificationStatus.VERIFIED)
    probable = sum(1 for f in facts if f.verification_status == VerificationStatus.PROBABLE)
    ambiguous = sum(1 for f in facts if f.verification_status == VerificationStatus.AMBIGUOUS)
    unverified = total - (verified + probable)

    weighted_sum = sum(f.confidence for f in facts)
    overall_score = round(weighted_sum / total, 3)

    if overall_score >= 0.85 and verified >= 4:
        tier = "HIGH"
    elif overall_score >= 0.60:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return {
        "overall_score": overall_score,
        "total_facts": total,
        "verified_facts": verified,
        "probable_facts": probable,
        "ambiguous_facts": ambiguous,
        "unverified_facts": unverified,
        "quality_tier": tier,
    }
