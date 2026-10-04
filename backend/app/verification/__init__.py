"""
Verification package
"""
from backend.app.verification.identity import (
    validate_norwegian_org_number,
    clean_org_number,
    verify_entity_match,
    calculate_name_similarity,
)
from backend.app.verification.evidence import (
    validate_evidence_provenance,
    resolve_fact_conflict,
    create_evidence_record,
    generate_content_hash,
)
from backend.app.verification.confidence import calculate_profile_confidence
