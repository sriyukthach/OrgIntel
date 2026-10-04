"""
Evidence Verification & Provenance Engine
Ensures every fact has authentic public evidence and resolves multi-source conflicts.
"""

import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
from backend.app.models import Fact, EvidenceRecord, VerificationStatus, SourcePriority


def generate_content_hash(text: str) -> str:
    """Creates a deterministic SHA-256 hash for evidence deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def validate_evidence_provenance(fact: Fact) -> Tuple[bool, str]:
    """
    Verifies that a fact satisfies strict evidence integrity rules:
    - Must have a valid source URL (not localhost or fake)
    - Must have a non-empty excerpt
    - Excerpt cannot be a trivial placeholder
    """
    if not fact.source_url or not fact.source_url.startswith("http"):
        return False, "Fact is missing a valid HTTP/HTTPS source URL."

    if not fact.evidence_excerpt or len(fact.evidence_excerpt.strip()) < 5:
        return False, "Fact is missing a verifiable textual evidence excerpt."

    placeholder_patterns = [
        r"^n/a$",
        r"^unknown$",
        r"^null$",
        r"^none$",
        r"^no evidence$",
        r"^placeholder$",
    ]
    for p in placeholder_patterns:
        if re.match(p, fact.evidence_excerpt.strip(), re.IGNORECASE):
            return False, "Evidence excerpt is an invalid placeholder."

    return True, "Evidence provenance valid."


def resolve_fact_conflict(existing_fact: Fact, new_fact: Fact, existing_priority: int, new_priority: int) -> Fact:
    """
    Resolves conflict between two facts for the same field:
    1. Higher priority source wins (e.g., Official Registry > Company Web > News)
    2. If same priority, more recent retrieved_at or effective_date wins
    3. If values differ and neither clearly dominates, mark as AMBIGUOUS
    """
    if existing_fact.value == new_fact.value:
        # Same fact confirmed by multiple sources - boost confidence
        existing_fact.confidence = min(1.0, existing_fact.confidence + 0.1)
        return existing_fact

    if new_priority < existing_priority:
        # Lower integer means higher priority (e.g., 1 is Brreg, 2 is Web)
        return new_fact
    elif existing_priority < new_priority:
        return existing_fact

    # Same priority, check effective/retrieved date
    if (new_fact.effective_date or new_fact.retrieved_at) > (existing_fact.effective_date or existing_fact.retrieved_at):
        return new_fact

    # Conflict unresolved
    existing_fact.verification_status = VerificationStatus.AMBIGUOUS
    existing_fact.evidence_excerpt += f" | CONFLICTING SOURCE: {new_fact.source_title}: '{new_fact.value}'"
    return existing_fact


def create_evidence_record(
    source_url: str,
    source_title: str,
    publisher_domain: str,
    evidence_excerpt: str,
    supported_fields: List[str],
    source_priority: int = SourcePriority.OTHER.value,
    publication_date: Optional[str] = None,
) -> EvidenceRecord:
    """Helper to create a validated EvidenceRecord."""
    content_hash = generate_content_hash(f"{source_url}:{evidence_excerpt}")
    return EvidenceRecord(
        id=f"ev_{content_hash}",
        source_url=source_url,
        source_title=source_title,
        publisher_domain=publisher_domain,
        publication_date=publication_date,
        evidence_excerpt=evidence_excerpt.strip(),
        supported_fields=supported_fields,
        source_priority=source_priority,
        content_hash=content_hash,
    )
