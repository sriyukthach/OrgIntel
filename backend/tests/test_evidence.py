"""
Unit tests for Evidence Provenance, Validation, and Multi-Source Conflict Resolution.
"""

import pytest
from backend.app.models import Fact, VerificationStatus, SourcePriority
from backend.app.verification.evidence import (
    validate_evidence_provenance,
    resolve_fact_conflict,
    create_evidence_record,
)


def test_valid_evidence_provenance():
    fact = Fact(
        field="legal_name",
        value="EQUINOR ASA",
        source_url="https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
        source_title="Brønnøysundregistrene",
        evidence_excerpt="Organisasjonsnummer 923609016 registrert som EQUINOR ASA",
    )
    is_valid, msg = validate_evidence_provenance(fact)
    assert is_valid is True


def test_reject_missing_or_fake_evidence():
    # Missing http url
    f1 = Fact(
        field="legal_name",
        value="EQUINOR ASA",
        source_url="fake-url",
        source_title="Test",
        evidence_excerpt="Valid text excerpt",
    )
    assert validate_evidence_provenance(f1)[0] is False

    # Empty excerpt
    f2 = Fact(
        field="legal_name",
        value="EQUINOR ASA",
        source_url="https://example.com",
        source_title="Test",
        evidence_excerpt="   ",
    )
    assert validate_evidence_provenance(f2)[0] is False

    # Placeholder excerpt
    f3 = Fact(
        field="legal_name",
        value="EQUINOR ASA",
        source_url="https://example.com",
        source_title="Test",
        evidence_excerpt="N/A",
    )
    assert validate_evidence_provenance(f3)[0] is False


def test_resolve_fact_conflict_priority():
    # Official registry (prio 1) vs 3rd party web (prio 2)
    brreg_fact = Fact(
        field="status",
        value="Active",
        source_url="https://data.brreg.no/enheter/923609016",
        source_title="Brreg",
        evidence_excerpt="Status: Aktiv",
    )
    web_fact = Fact(
        field="status",
        value="Dissolved",
        source_url="https://example.com/blog",
        source_title="Blog",
        evidence_excerpt="Company appears closed",
    )

    # Brreg should win
    winner = resolve_fact_conflict(
        existing_fact=brreg_fact,
        new_fact=web_fact,
        existing_priority=SourcePriority.OFFICIAL_REGISTRY.value,
        new_priority=SourcePriority.OTHER.value,
    )
    assert winner.value == "Active"
