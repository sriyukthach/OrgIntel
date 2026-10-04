"""
Unit tests for Fact Extraction, Name Normalization, and Leadership Extraction.
"""

from backend.app.models import CompanyIdentity, PersonRole, VerificationStatus
from backend.app.extraction.facts import normalize_numeric_amount, extract_identity_facts
from backend.app.extraction.people import (
    normalize_name,
    extract_people_from_brreg_roles,
    people_to_facts,
)
from backend.app.extraction.financial import extract_financials_from_regnskap, financials_to_facts


def test_normalize_numeric_amount():
    assert normalize_numeric_amount("42,5 MNOK") == 42_500_000.0
    assert normalize_numeric_amount("1 200 000 kr") == 1_200_000.0
    assert normalize_numeric_amount("1.5 mrd") == 1_500_000_000.0
    assert normalize_numeric_amount(500000) == 500000.0
    assert normalize_numeric_amount("N/A") is None


def test_normalize_name_various_shapes():
    # 1. Regression test: single-element list from Brreg enhet.navn
    assert normalize_name(["ERNST & YOUNG AS"]) == "ERNST & YOUNG AS"

    # 2. Plain string
    assert normalize_name("ERNST & YOUNG AS") == "ERNST & YOUNG AS"
    assert normalize_name("   Anders   Opedal   ") == "Anders Opedal"

    # 3. Empty list & None
    assert normalize_name([]) == ""
    assert normalize_name(None) == ""
    assert normalize_name(["", "  ", None]) == ""

    # 4. Multi-item list (multiline company / department names)
    assert normalize_name(["STATOIL PETROLEUM AS", "AVDELING OSLO"]) == "STATOIL PETROLEUM AS AVDELING OSLO"
    assert normalize_name(["", "  ", "ERNST & YOUNG AS"]) == "ERNST & YOUNG AS"

    # 5. Dict structure with fornavn / etternavn
    assert normalize_name({"fornavn": "Anders", "mellomnavn": None, "etternavn": "Opedal"}) == "Anders Opedal"
    assert normalize_name({"fornavn": "Jon", "mellomnavn": "Erik", "etternavn": "Reinhardsen"}) == "Jon Erik Reinhardsen"
    assert normalize_name({"navn": ["KPMG AS"]}) == "KPMG AS"


def test_extract_identity_facts():
    identity = CompanyIdentity(
        organization_number="923609016",
        legal_name="EQUINOR ASA",
        organization_form="ASA",
        registration_status="Active",
        registered_address="Forusbeen 50",
        postal_code="4035",
        city="STAVANGER",
        industry_code="06.100",
        industry_description="Utvinning av råolje",
        website="https://www.equinor.com",
    )
    facts = extract_identity_facts(identity)
    assert len(facts) >= 6
    fields = {f.field for f in facts}
    assert "organization_number" in fields
    assert "legal_name" in fields
    assert "registered_address" in fields
    assert "industry_code" in fields


def test_extract_people_from_brreg_roles():
    mock_roles_payload = {
        "rollegrupper": [
            {
                "type": {"kode": "STYR", "beskrivelse": "Styre"},
                "roller": [
                    {
                        "type": {"kode": "LEDE", "beskrivelse": "Styreleder"},
                        "person": {
                            "navn": {"fornavn": "Jon", "mellomnavn": "Erik", "etternavn": "Reinhardsen"},
                            "fodselsdato": "1956-01-01",
                        },
                        "fratraadt": False,
                    }
                ],
            },
            {
                "type": {"kode": "DAGL", "beskrivelse": "Daglig leder"},
                "roller": [
                    {
                        "type": {"kode": "DAGL", "beskrivelse": "Daglig leder / adm.dir"},
                        "person": {
                            "navn": {"fornavn": "Anders", "etternavn": "Opedal"},
                            "fodselsdato": "1968-01-01",
                        },
                        "fratraadt": False,
                    }
                ],
            },
            {
                "type": {"kode": "REVI", "beskrivelse": "Revisor"},
                "roller": [
                    {
                        "type": {"kode": "REVI", "beskrivelse": "Revisor"},
                        "enhet": {
                            "organisasjonsnummer": "976389387",
                            "navn": ["ERNST & YOUNG AS"],
                            "organisasjonsform": {"kode": "AS", "beskrivelse": "Aksjeselskap"},
                        },
                        "fratraadt": False,
                    }
                ],
            },
        ]
    }

    people = extract_people_from_brreg_roles(mock_roles_payload, "https://data.brreg.no/roles")
    assert len(people) == 3

    # Verify all names are valid strings
    for p in people:
        assert isinstance(p.name, str)
        assert len(p.name) > 0

    names = [p.name for p in people]
    assert "Jon Erik Reinhardsen" in names
    assert "Anders Opedal" in names
    assert "ERNST & YOUNG AS" in names

    # Verify institutional entity distinction
    ey_role = next(p for p in people if p.name == "ERNST & YOUNG AS")
    assert ey_role.is_organization is True
    assert ey_role.organization_number == "976389387"
    assert ey_role.role_code == "REVI"

    facts = people_to_facts(people)
    assert any(f.field == "board_chair" for f in facts)
    assert any(f.field == "ceo" for f in facts)
    assert any(f.field == "auditor" for f in facts)


def test_extract_financials_from_regnskap():
    mock_regnskap = [
        {
            "regnskapsperiode": {"fraDato": "2024-01-01", "tilDato": "2024-12-31"},
            "valuta": "NOK",
            "resultatregnskapResultat": {
                "driftsinntekter": {"sumDriftsinntekter": 850000000.0},
                "driftsresultat": {"driftsresultat": 120000000.0},
                "aarsresultat": {"aarsresultat": 95000000.0},
            },
            "eiendeler": {"sumEiendeler": 1500000000.0},
            "balanse": {"egenkapital": {"sumEgenkapital": 600000000.0}},
        }
    ]

    records = extract_financials_from_regnskap(mock_regnskap, "https://data.brreg.no/regnskap")
    assert len(records) == 1
    rec = records[0]
    assert rec.reporting_year == 2024
    assert rec.revenue == 850000000.0
    assert rec.profit_loss == 95000000.0

    facts = financials_to_facts(records)
    assert any(f.field == "revenue" for f in facts)
    assert any(f.field == "operating_result" for f in facts)
