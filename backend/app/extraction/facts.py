"""
Fact Normalization & Extraction Engine
Extracts normalized facts from structured payloads and unstructured text with explicit evidence provenance.
"""

import re
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from backend.app.models import Fact, VerificationStatus, CompanyIdentity


def normalize_numeric_amount(val_str: str) -> Optional[float]:
    """Parses numeric amounts from Norwegian and International formats (e.g. '42,5 MNOK', '1 200 000 kr')."""
    if val_str is None:
        return None
    if isinstance(val_str, (int, float)):
        return float(val_str)

    s = str(val_str).strip()
    multiplier = 1.0

    if re.search(r"\b(mrd|milliard|billion)\b", s, re.IGNORECASE):
        multiplier = 1_000_000_000.0
    elif re.search(r"\b(mnok|mill|million|m)\b", s, re.IGNORECASE):
        multiplier = 1_000_000.0
    elif re.search(r"\b(knok|tusen|k)\b", s, re.IGNORECASE):
        multiplier = 1_000.0

    # Extract digits with optional comma/dot decimal
    clean = re.sub(r"[^\d,\.-]", "", s)
    # Handle European comma decimal: 42,5 -> 42.5
    if "," in clean and "." not in clean:
        clean = clean.replace(",", ".")
    elif "," in clean and "." in clean:
        # e.g. 1.200.000,50 -> 1200000.50
        clean = clean.replace(".", "").replace(",", ".")

    try:
        num = float(clean)
        return round(num * multiplier, 2)
    except (ValueError, TypeError):
        return None


def extract_identity_facts(identity: CompanyIdentity) -> List[Fact]:
    """Generates canonical verified facts from an authoritative CompanyIdentity record."""
    facts: List[Fact] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Organization Number
    facts.append(
        Fact(
            field="organization_number",
            value=identity.organization_number,
            normalized_value=identity.organization_number,
            source_url=identity.source_url,
            source_title=f"{identity.source} - Enhetsregisteret",
            retrieved_at=identity.retrieved_at or now_iso,
            effective_date=identity.registration_date,
            confidence=1.0,
            verification_status=VerificationStatus.VERIFIED,
            evidence_excerpt=f"Organisasjonsnummer: {identity.organization_number} registrert i Enhetsregisteret.",
        )
    )

    # 2. Legal Name
    facts.append(
        Fact(
            field="legal_name",
            value=identity.legal_name,
            normalized_value=identity.legal_name.upper(),
            source_url=identity.source_url,
            source_title=f"{identity.source} - Enhetsregisteret",
            retrieved_at=identity.retrieved_at or now_iso,
            confidence=1.0,
            verification_status=VerificationStatus.VERIFIED,
            evidence_excerpt=f"Foretaksnavn: {identity.legal_name} ({identity.organization_form}).",
        )
    )

    # 3. Organization Form
    if identity.organization_form:
        facts.append(
            Fact(
                field="organization_form",
                value=identity.organization_form,
                normalized_value=identity.organization_form,
                source_url=identity.source_url,
                source_title=f"{identity.source} - Enhetsregisteret",
                retrieved_at=identity.retrieved_at or now_iso,
                confidence=1.0,
                verification_status=VerificationStatus.VERIFIED,
                evidence_excerpt=f"Organisasjonsform: {identity.organization_form} ({identity.organization_form_description or 'Registrert form'}).",
            )
        )

    # 4. Status
    facts.append(
        Fact(
            field="registration_status",
            value=identity.registration_status,
            normalized_value=identity.registration_status.upper(),
            source_url=identity.source_url,
            source_title=f"{identity.source} - Enhetsregisteret",
            retrieved_at=identity.retrieved_at or now_iso,
            confidence=1.0,
            verification_status=VerificationStatus.VERIFIED,
            evidence_excerpt=f"Status: {identity.registration_status}. Aktiv: {identity.is_active}.",
        )
    )

    # 5. Registered Address & Location
    if identity.registered_address or identity.city:
        addr_str = f"{identity.registered_address or ''}, {identity.postal_code or ''} {identity.city or ''}".strip(", ")
        facts.append(
            Fact(
                field="registered_address",
                value=addr_str,
                normalized_value=addr_str,
                source_url=identity.source_url,
                source_title=f"{identity.source} - Forretningsadresse",
                retrieved_at=identity.retrieved_at or now_iso,
                confidence=1.0,
                verification_status=VerificationStatus.VERIFIED,
                evidence_excerpt=f"Forretningsadresse: {addr_str}, Kommune: {identity.municipality or 'Norge'}.",
            )
        )

    # 6. Industry NACE
    if identity.industry_description:
        facts.append(
            Fact(
                field="industry_code",
                value=f"{identity.industry_code or ''} - {identity.industry_description}".strip(" -"),
                normalized_value=identity.industry_code,
                source_url=identity.source_url,
                source_title=f"{identity.source} - Næringskode",
                retrieved_at=identity.retrieved_at or now_iso,
                confidence=1.0,
                verification_status=VerificationStatus.VERIFIED,
                evidence_excerpt=f"Næringskode: {identity.industry_code or 'N/A'} {identity.industry_description}.",
            )
        )

    # 7. Registration Date
    if identity.registration_date:
        facts.append(
            Fact(
                field="registration_date",
                value=identity.registration_date,
                normalized_value=identity.registration_date,
                source_url=identity.source_url,
                source_title=f"{identity.source} - Registreringsdato",
                retrieved_at=identity.retrieved_at or now_iso,
                effective_date=identity.registration_date,
                confidence=1.0,
                verification_status=VerificationStatus.VERIFIED,
                evidence_excerpt=f"Registreringsdato i Enhetsregisteret: {identity.registration_date}.",
            )
        )

    # 8. Website if available
    if identity.website:
        facts.append(
            Fact(
                field="website",
                value=identity.website,
                normalized_value=identity.website.lower(),
                source_url=identity.source_url,
                source_title=f"{identity.source} - Offisiell nettside",
                retrieved_at=identity.retrieved_at or now_iso,
                confidence=0.95,
                verification_status=VerificationStatus.VERIFIED,
                evidence_excerpt=f"Offisiell internettadresse registrert: {identity.website}",
            )
        )

    return facts
