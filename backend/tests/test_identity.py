"""
Unit tests for Norwegian Organization Number validation and Entity Matching.
"""

import pytest
from backend.app.models import CompanyIdentity, VerificationStatus
from backend.app.verification.identity import (
    validate_norwegian_org_number,
    clean_org_number,
    calculate_name_similarity,
    verify_entity_match,
)


def test_clean_org_number():
    assert clean_org_number("923 609 016") == "923609016"
    assert clean_org_number("NO 982 463 718 MVA") == "982463718"
    assert clean_org_number("") == ""


def test_valid_norwegian_org_numbers():
    # Real Norwegian companies
    valid_orgs = [
        "923609016",  # Equinor ASA
        "982463718",  # DNB Bank ASA
        "920218687",  # Kongsberg Gruppen ASA
        "912345678",  # Nordic Tech Innovation AS
        "914778271",  # Schibsted ASA
    ]
    for org in valid_orgs:
        is_valid, msg = validate_norwegian_org_number(org)
        assert is_valid is True, f"Expected {org} to be valid: {msg}"


def test_invalid_norwegian_org_numbers():
    # Wrong lengths
    assert validate_norwegian_org_number("12345678")[0] is False
    assert validate_norwegian_org_number("1234567890")[0] is False

    # Invalid starting digit (must be 8 or 9)
    assert validate_norwegian_org_number("123456789")[0] is False

    # Invalid checksum
    assert validate_norwegian_org_number("923609017")[0] is False
    assert validate_norwegian_org_number("982463719")[0] is False


def test_company_name_similarity():
    sim1 = calculate_name_similarity("Equinor ASA", "EQUINOR ASA")
    assert sim1 == 1.0

    sim2 = calculate_name_similarity("Kongsberg Gruppen ASA", "Kongsberg Gruppen")
    assert sim2 >= 0.85

    sim3 = calculate_name_similarity("Equinor ASA", "DNB Bank ASA")
    assert sim3 < 0.30


def test_entity_verification_matching():
    canonical = CompanyIdentity(
        organization_number="923609016",
        legal_name="EQUINOR ASA",
        website="https://www.equinor.com",
    )

    # 1. Exact Org number match
    status, conf, msg = verify_entity_match("923609016", "Equinor", None, canonical)
    assert status == VerificationStatus.VERIFIED
    assert conf == 1.0

    # 2. Org number mismatch -> Must fail
    status, conf, msg = verify_entity_match("982463718", "Equinor", None, canonical)
    assert status == VerificationStatus.FAILED

    # 3. Name similarity match
    status, conf, msg = verify_entity_match(None, "EQUINOR", None, canonical)
    assert status == VerificationStatus.VERIFIED
    assert conf >= 0.85
