"""
Leadership & Roles Extraction Engine
Extracts verified executive management, board members, and roles from registry and web sources.
"""

from typing import List, Dict, Any, Optional
from backend.app.models import PersonRole, Fact, VerificationStatus


ROLE_CODE_MAP = {
    "DAGL": "Daglig leder / CEO",
    "LEDE": "Styreleder / Board Chair",
    "MEDL": "Styremedlem / Board Member",
    "NEST": "Nestleder / Deputy Chair",
    "VARA": "Varamedlem / Deputy Board Member",
    "INNH": "Innehaver / Owner",
    "REVI": "Revisor / Auditor",
    "REGN": "Regnskapsfører / Accountant",
    "PROK": "Prokura / Power of Attorney",
}


def extract_people_from_brreg_roles(roles_json: Dict[str, Any], source_url: str) -> List[PersonRole]:
    """
    Parses Brreg Enhetsregisteret Roller API structure.
    Extracts active board members and executive management.
    """
    people: List[PersonRole] = []
    role_groups = roles_json.get("rollegrupper", [])

    for group in role_groups:
        group_type = group.get("type", {}).get("beskrivelse", "Rolle")
        roller = group.get("roller", [])

        for r in roller:
            # Check if resigned/fratrådt
            if r.get("fratraadt", False):
                continue

            person_info = r.get("person", {})
            navn_obj = person_info.get("navn", {})
            first = navn_obj.get("fornavn", "")
            middle = navn_obj.get("mellomnavn", "")
            last = navn_obj.get("etternavn", "")

            full_name = " ".join(part for part in [first, middle, last] if part).strip()
            if not full_name:
                # If role is held by an enterprise (foretak)
                foretak = r.get("enhet", {})
                full_name = foretak.get("navn", "")

            if not full_name:
                continue

            role_code = r.get("type", {}).get("kode", "")
            role_desc = r.get("type", {}).get("beskrivelse") or ROLE_CODE_MAP.get(role_code, group_type)
            birth_year = person_info.get("fodselsdato", "")[:4] if person_info.get("fodselsdato") else None
            birth_int = int(birth_year) if birth_year and birth_year.isdigit() else None

            people.append(
                PersonRole(
                    name=full_name,
                    role=role_desc,
                    role_code=role_code,
                    birth_year=birth_int,
                    effective_date=r.get("valgtAv", {}).get("dato"),
                    source_url=source_url,
                    verification_status=VerificationStatus.VERIFIED,
                    evidence_excerpt=f"Brreg Roller: {full_name} registrert som {role_desc} ({role_code}).",
                )
            )

    return people


def people_to_facts(people: List[PersonRole]) -> List[Fact]:
    """Converts key leadership members (CEO, Board Chair) into atomic verifiable facts."""
    facts: List[Fact] = []
    for p in people:
        field_name = None
        if p.role_code == "DAGL" or "daglig leder" in p.role.lower() or "ceo" in p.role.lower():
            field_name = "ceo"
        elif p.role_code == "LEDE" or "styreleder" in p.role.lower() or "board chair" in p.role.lower():
            field_name = "board_chair"

        if field_name:
            facts.append(
                Fact(
                    field=field_name,
                    value=p.name,
                    normalized_value=p.name,
                    source_url=p.source_url,
                    source_title="Brønnøysundregistrene - Roller",
                    confidence=1.0,
                    verification_status=p.verification_status,
                    evidence_excerpt=p.evidence_excerpt or f"{p.name} - {p.role}",
                )
            )
    return facts
