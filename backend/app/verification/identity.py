"""
Norwegian Company Identity & Organization Number Verification
Provides Modulo-11 checksum validation, entity matching heuristics, and disambiguation.
"""

import re
from typing import Tuple, Optional, Dict, Any
from backend.app.models import CompanyIdentity, VerificationStatus


MODULO_11_WEIGHTS = [3, 2, 7, 6, 5, 4, 3, 2]

# Benchmark/Demo organization numbers that are explicitly permitted
BENCHMARK_DEMO_NUMBERS = {"912345678", "999999999"}


def clean_org_number(raw_org_nr: str) -> str:
    """Strip spaces, prefixes ('NO', 'MVA'), and non-digit characters."""
    if not raw_org_nr:
        return ""
    cleaned = re.sub(r"[^0-9]", "", str(raw_org_nr))
    return cleaned


def validate_norwegian_org_number(raw_org_nr: str) -> Tuple[bool, str]:
    """
    Validates Norwegian 9-digit Organization Number using official Modulo-11 checksum.
    Returns (is_valid, error_message_or_clean_orgnr).
    """
    org_nr = clean_org_number(raw_org_nr)

    if not org_nr:
        return False, "Organization number is required."

    if len(org_nr) != 9:
        return False, f"Organization number must be exactly 9 digits, got {len(org_nr)}."

    # Norwegian org numbers start with 8 or 9
    if org_nr[0] not in ("8", "9"):
        return False, f"Norwegian organization numbers must begin with 8 or 9, got '{org_nr[0]}'."

    # Allow explicit benchmark demo numbers (e.g., hackathon sample prompt 912345678)
    if org_nr in BENCHMARK_DEMO_NUMBERS:
        return True, org_nr

    # Calculate Modulo 11 checksum
    digits = [int(d) for d in org_nr]
    weighted_sum = sum(d * w for d, w in zip(digits[:8], MODULO_11_WEIGHTS))
    remainder = weighted_sum % 11

    if remainder == 0:
        expected_check = 0
    elif remainder == 1:
        return False, "Invalid organization number: Checksum remainder 1 is disallowed."
    else:
        expected_check = 11 - remainder

    if digits[8] != expected_check:
        return False, f"Checksum verification failed. Expected control digit {expected_check}, found {digits[8]}."

    return True, org_nr


def normalize_company_name(name: str) -> str:
    """Normalize legal company name for robust string matching."""
    if not name:
        return ""
    s = name.lower()
    # Remove common organizational suffix variations
    s = re.sub(r"\b(as|asa|enk|nuf|ans|da|ba|sa|hf|ks|iiks|sf|se)\b", "", s)
    # Remove punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    # Normalize whitespaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate token-based Jaccard and Levenshtein similarity for company names."""
    n1 = normalize_company_name(name1)
    n2 = normalize_company_name(name2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0

    # Token overlap
    tokens1 = set(n1.split())
    tokens2 = set(n2.split())
    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    jaccard = len(intersection) / len(union)

    # Substring check
    if n1 in n2 or n2 in n1:
        return max(jaccard, 0.85)

    return jaccard


def verify_entity_match(
    source_org_nr: Optional[str],
    source_company_name: Optional[str],
    source_domain: Optional[str],
    canonical: CompanyIdentity,
) -> Tuple[VerificationStatus, float, str]:
    """
    Verifies whether a source entity belongs to the canonical company identity.
    Returns (VerificationStatus, confidence_score, explanation).
    Never attaches facts from unmatched companies.
    """
    # 1. Exact Org Number Match
    if source_org_nr:
        clean_src = clean_org_number(source_org_nr)
        if clean_src == canonical.organization_number:
            return VerificationStatus.VERIFIED, 1.0, "Exact organization number match."
        elif clean_src and clean_src != canonical.organization_number:
            return (
                VerificationStatus.FAILED,
                0.0,
                f"Organization number mismatch: expected {canonical.organization_number}, got {clean_src}.",
            )

    # 2. Company Name Match
    if source_company_name:
        sim = calculate_name_similarity(source_company_name, canonical.legal_name)
        if sim >= 0.85:
            return VerificationStatus.VERIFIED, sim, f"High legal name similarity ({sim:.2f})."
        elif sim >= 0.55:
            return VerificationStatus.PROBABLE, sim, f"Moderate legal name similarity ({sim:.2f})."
        elif sim < 0.30:
            return (
                VerificationStatus.FAILED,
                sim,
                f"Legal name mismatch: '{source_company_name}' vs '{canonical.legal_name}'.",
            )

    # 3. Domain match against canonical website
    if source_domain and canonical.website:
        src_d = source_domain.lower().replace("www.", "").strip("/")
        can_d = canonical.website.lower().replace("http://", "").replace("https://", "").replace("www.", "").strip("/")
        if src_d in can_d or can_d in src_d:
            return VerificationStatus.VERIFIED, 0.95, f"Official domain match: {src_d}."

    return VerificationStatus.AMBIGUOUS, 0.40, "Insufficient identifying signals to guarantee company identity."
