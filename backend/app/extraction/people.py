"""
Leadership & Roles Extraction Engine
Extracts verified executive management, board members, and institutional roles from registry and web sources.
"""

import re
from typing import List, Dict, Any, Optional, Union
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


def normalize_name(raw_name: Any) -> str:
    """
    Safely normalizes any representation of a person or organizational name into a clean, valid string.
    Handles:
      - Plain string: "ERNST & YOUNG AS" -> "ERNST & YOUNG AS"
      - Single-item list: ["ERNST & YOUNG AS"] -> "ERNST & YOUNG AS"
      - Multi-item list (Brreg multiline entity name): ["STATOIL PETROLEUM AS", "AVDELING OSLO"] -> "STATOIL PETROLEUM AS AVDELING OSLO"
      - Name dictionary: {"fornavn": "Anders", "etternavn": "Opedal"} -> "Anders Opedal"
      - Empty list, None, whitespace: -> ""
    """
    if raw_name is None:
        return ""

    if isinstance(raw_name, str):
        return re.sub(r"\s+", " ", raw_name).strip()

    if isinstance(raw_name, (list, tuple)):
        # Recursively normalize valid non-empty string parts
        parts = [normalize_name(item) for item in raw_name if item is not None]
        clean_parts = [p for p in parts if p]
        return " ".join(clean_parts).strip()

    if isinstance(raw_name, dict):
        first = normalize_name(raw_name.get("fornavn", ""))
        middle = normalize_name(raw_name.get("mellomnavn", ""))
        last = normalize_name(raw_name.get("etternavn", ""))
        parts = [p for p in [first, middle, last] if p]
        if parts:
            return " ".join(parts).strip()
        if "navn" in raw_name:
            return normalize_name(raw_name["navn"])

    return str(raw_name).strip()


def extract_people_from_brreg_roles(roles_json: Dict[str, Any], source_url: str) -> List[PersonRole]:
    """
    Parses Brreg Enhetsregisteret Roller API structure.
    Extracts active board members, executive management, and registered institutional entities.
    """
    people: List[PersonRole] = []
    if not roles_json or not isinstance(roles_json, dict):
        return people

    role_groups = roles_json.get("rollegrupper", [])
    if not isinstance(role_groups, list):
        return people

    for group in role_groups:
        if not isinstance(group, dict):
            continue
        group_type = group.get("type", {}).get("beskrivelse", "Rolle") if isinstance(group.get("type"), dict) else "Rolle"
        roller = group.get("roller", [])
        if not isinstance(roller, list):
            continue

        for r in roller:
            if not isinstance(r, dict):
                continue

            # Check if resigned/fratrådt
            if r.get("fratraadt", False):
                continue

            person_info = r.get("person")
            enhet_info = r.get("enhet")
            full_name = ""
            is_org = False
            org_nr = None
            birth_int = None

            # 1. Natural Person Role Holder
            if person_info and isinstance(person_info, dict):
                full_name = normalize_name(person_info.get("navn"))
                birth_year = str(person_info.get("fodselsdato", ""))[:4] if person_info.get("fodselsdato") else None
                birth_int = int(birth_year) if birth_year and birth_year.isdigit() else None

            # 2. Institutional / Enterprise Role Holder (e.g., Revisor like ERNST & YOUNG AS)
            if not full_name and enhet_info and isinstance(enhet_info, dict):
                full_name = normalize_name(enhet_info.get("navn"))
                is_org = True
                raw_org_nr = enhet_info.get("organisasjonsnummer")
                org_nr = str(raw_org_nr) if raw_org_nr else None

            if not full_name:
                continue

            type_obj = r.get("type", {}) if isinstance(r.get("type"), dict) else {}
            role_code = type_obj.get("kode", "")
            role_desc = type_obj.get("beskrivelse") or ROLE_CODE_MAP.get(role_code, group_type)
            valgt_obj = r.get("valgtAv", {}) if isinstance(r.get("valgtAv"), dict) else {}
            valgt_dato = valgt_obj.get("dato")

            excerpt = (
                f"Brreg Roller: {full_name} (Foretak: {org_nr or 'Registrert'}) registrert som {role_desc} ({role_code})."
                if is_org
                else f"Brreg Roller: {full_name} registrert som {role_desc} ({role_code})."
            )

            people.append(
                PersonRole(
                    name=full_name,
                    role=role_desc,
                    role_code=role_code,
                    birth_year=birth_int,
                    effective_date=valgt_dato,
                    source_url=source_url,
                    verification_status=VerificationStatus.VERIFIED,
                    evidence_excerpt=excerpt,
                    is_organization=is_org,
                    organization_number=org_nr,
                )
            )

    return people


def people_to_facts(people: List[PersonRole]) -> List[Fact]:
    """Converts key leadership members (CEO, Board Chair) into atomic verifiable facts."""
    facts: List[Fact] = []
    for p in people:
        field_name = None
        # Only assign person-specific leadership facts if not an institutional entity holding an auditor/other role
        if not p.is_organization:
            if p.role_code == "DAGL" or "daglig leder" in p.role.lower() or "ceo" in p.role.lower():
                field_name = "ceo"
            elif p.role_code == "LEDE" or "styreleder" in p.role.lower() or "board chair" in p.role.lower():
                field_name = "board_chair"
        else:
            if p.role_code == "REVI" or "revisor" in p.role.lower() or "auditor" in p.role.lower():
                field_name = "auditor"

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
