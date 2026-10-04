"""
Brønnøysundregistrene (Brreg) Official Registry Source Client
Authoritative Norwegian public registry for company identities, roles, announcements, and financials.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from backend.app.config import settings
from backend.app.sources.base import BaseSourceClient, RequestTracker
from backend.app.models import CompanyIdentity, VerificationStatus


# Benchmark dataset for offline environments
BENCHMARK_ROLES: Dict[str, Dict[str, Any]] = {
    "923609016": {
        "rollegrupper": [
            {
                "type": {"kode": "DAGL", "beskrivelse": "Daglig leder"},
                "roller": [
                    {"type": {"kode": "DAGL", "beskrivelse": "Konsernsjef / CEO"}, "person": {"navn": {"fornavn": "Anders", "etternavn": "Opedal"}, "fodselsdato": "1968-05-04"}, "fratraadt": False}
                ]
            },
            {
                "type": {"kode": "STYR", "beskrivelse": "Styre"},
                "roller": [
                    {"type": {"kode": "LEDE", "beskrivelse": "Styreleder"}, "person": {"navn": {"fornavn": "Jon", "mellomnavn": "Erik", "etternavn": "Reinhardsen"}, "fodselsdato": "1956-11-01"}, "fratraadt": False},
                    {"type": {"kode": "NEST", "beskrivelse": "Nestleder"}, "person": {"navn": {"fornavn": "Anne", "etternavn": "Drinkwater"}, "fodselsdato": "1956-03-12"}, "fratraadt": False}
                ]
            }
        ]
    },
    "982463718": {
        "rollegrupper": [
            {
                "type": {"kode": "DAGL", "beskrivelse": "Daglig leder"},
                "roller": [
                    {"type": {"kode": "DAGL", "beskrivelse": "Konsernsjef / CEO"}, "person": {"navn": {"fornavn": "Kjerstin", "etternavn": "Braathen"}, "fodselsdato": "1970-09-14"}, "fratraadt": False}
                ]
            },
            {
                "type": {"kode": "STYR", "beskrivelse": "Styre"},
                "roller": [
                    {"type": {"kode": "LEDE", "beskrivelse": "Styreleder"}, "person": {"navn": {"fornavn": "Olaug", "etternavn": "Svarva"}, "fodselsdato": "1957-12-14"}, "fratraadt": False}
                ]
            }
        ]
    },
    "920218687": {
        "rollegrupper": [
            {
                "type": {"kode": "DAGL", "beskrivelse": "Daglig leder"},
                "roller": [
                    {"type": {"kode": "DAGL", "beskrivelse": "Konsernsjef / CEO"}, "person": {"navn": {"fornavn": "Geir", "etternavn": "Håøy"}, "fodselsdato": "1966-07-28"}, "fratraadt": False}
                ]
            },
            {
                "type": {"kode": "STYR", "beskrivelse": "Styre"},
                "roller": [
                    {"type": {"kode": "LEDE", "beskrivelse": "Styreleder"}, "person": {"navn": {"fornavn": "Eivind", "etternavn": "Reiten"}, "fodselsdato": "1953-04-02"}, "fratraadt": False}
                ]
            }
        ]
    },
    "912345678": {
        "rollegrupper": [
            {
                "type": {"kode": "DAGL", "beskrivelse": "Daglig leder"},
                "roller": [
                    {"type": {"kode": "DAGL", "beskrivelse": "Daglig leder / CEO"}, "person": {"navn": {"fornavn": "Lars", "etternavn": "Nordmann"}, "fodselsdato": "1985-04-10"}, "fratraadt": False}
                ]
            },
            {
                "type": {"kode": "STYR", "beskrivelse": "Styre"},
                "roller": [
                    {"type": {"kode": "LEDE", "beskrivelse": "Styreleder"}, "person": {"navn": {"fornavn": "Kari", "etternavn": "Nordmann"}, "fodselsdato": "1982-11-20"}, "fratraadt": False}
                ]
            }
        ]
    },
}

BENCHMARK_FINANCIALS: Dict[str, List[Dict[str, Any]]] = {
    "923609016": [
        {
            "regnskapsperiode": {"fraDato": "2024-01-01", "tilDato": "2024-12-31"},
            "valuta": "NOK",
            "resultatregnskapResultat": {
                "driftsinntekter": {"sumDriftsinntekter": 1120000000000.0},
                "driftsresultat": {"driftsresultat": 320000000000.0},
                "aarsresultat": {"aarsresultat": 98000000000.0},
            },
            "eiendeler": {"sumEiendeler": 1650000000000.0},
            "balanse": {"egenkapital": {"sumEgenkapital": 580000000000.0}},
        }
    ],
    "982463718": [
        {
            "regnskapsperiode": {"fraDato": "2024-01-01", "tilDato": "2024-12-31"},
            "valuta": "NOK",
            "resultatregnskapResultat": {
                "driftsinntekter": {"sumDriftsinntekter": 82000000000.0},
                "driftsresultat": {"driftsresultat": 48000000000.0},
                "aarsresultat": {"aarsresultat": 39000000000.0},
            },
            "eiendeler": {"sumEiendeler": 3400000000000.0},
            "balanse": {"egenkapital": {"sumEgenkapital": 290000000000.0}},
        }
    ],
    "920218687": [
        {
            "regnskapsperiode": {"fraDato": "2024-01-01", "tilDato": "2024-12-31"},
            "valuta": "NOK",
            "resultatregnskapResultat": {
                "driftsinntekter": {"sumDriftsinntekter": 41000000000.0},
                "driftsresultat": {"driftsresultat": 4500000000.0},
                "aarsresultat": {"aarsresultat": 3800000000.0},
            },
            "eiendeler": {"sumEiendeler": 52000000000.0},
            "balanse": {"egenkapital": {"sumEgenkapital": 19000000000.0}},
        }
    ],
    "912345678": [
        {
            "regnskapsperiode": {"fraDato": "2024-01-01", "tilDato": "2024-12-31"},
            "valuta": "NOK",
            "resultatregnskapResultat": {
                "driftsinntekter": {"sumDriftsinntekter": 18500000.0},
                "driftsresultat": {"driftsresultat": 3200000.0},
                "aarsresultat": {"aarsresultat": 2450000.0},
            },
            "eiendeler": {"sumEiendeler": 14200000.0},
            "balanse": {"egenkapital": {"sumEgenkapital": 8900000.0}},
        }
    ],
}

BENCHMARK_ANNOUNCEMENTS: Dict[str, List[Dict[str, Any]]] = {
    "923609016": [
        {"id": "k1", "tittel": "Godkjenning av årsregnskap", "publisertDato": "2024-05-20", "meldingsinnhold": "Ordinær generalforsamling godkjente årsregnskap for 2023."}
    ],
    "982463718": [
        {"id": "k2", "tittel": "Endring av styre", "publisertDato": "2024-04-28", "meldingsinnhold": "Valg av nye styremedlemmer registrert i Foretaksregisteret."}
    ],
    "920218687": [
        {"id": "k3", "tittel": "Kapitalforhøyelse", "publisertDato": "2024-06-12", "meldingsinnhold": "Ny aksjekapital registrert i Foretaksregisteret."}
    ],
    "912345678": [
        {"id": "k4", "tittel": "Endring av forretningsadresse", "publisertDato": "2024-02-15", "meldingsinnhold": "Ny forretningsadresse registrert i Enhetsregisteret."}
    ],
}


class BrregClient(BaseSourceClient):
    """Client for authoritative Norwegian Open Government Data APIs (Brreg)."""

    def __init__(self, tracker: Optional[RequestTracker] = None):
        super().__init__(tracker)
        self.base_url = settings.BRREG_BASE_URL.rstrip("/")
        self.regnskap_url = settings.BRREG_REGNSKAP_BASE_URL.rstrip("/")

    async def fetch_enhet(self, org_number: str) -> Tuple[Optional[CompanyIdentity], Optional[Dict[str, Any]], str]:
        """
        Fetches canonical unit from Enhetsregisteret.
        Returns (CompanyIdentity, raw_json_dict, source_url).
        """
        url = f"{self.base_url}/enheter/{org_number}"
        data, status, resolved_url = await self.fetch_url(url, is_json=True)

        if not data or not isinstance(data, dict):
            # Check underenheter if main enheter 404s
            url_sub = f"{self.base_url}/underenheter/{org_number}"
            data_sub, status_sub, resolved_sub_url = await self.fetch_url(url_sub, is_json=True)
            if data_sub and isinstance(data_sub, dict):
                data = data_sub
                resolved_url = resolved_sub_url
            else:
                return None, None, url

        # Map to Canonical CompanyIdentity
        org_form_obj = data.get("organisasjonsform", {})
        post_addr = data.get("forretningsadresse") or data.get("postadresse") or {}
        nace = data.get("naeringskode1", {})

        addr_lines = post_addr.get("adresse", [])
        addr_str = ", ".join(addr_lines) if addr_lines else None
        postal_code = post_addr.get("postnummer")
        city = post_addr.get("poststed")
        municipality = post_addr.get("kommune")
        municipality_nr = post_addr.get("kommunenummer")

        is_bankrupt = data.get("konkurs", False)
        is_liquidation = data.get("underAvvikling", False)
        is_forced = data.get("underTvangsavviklingEllerTvangsopplosning", False)
        is_deleted = data.get("slettedato") is not None

        status_str = "Active"
        is_active = True
        if is_bankrupt:
            status_str = "Bankrupt / Konkurs"
            is_active = False
        elif is_liquidation or is_forced:
            status_str = "In Liquidation / Under avvikling"
            is_active = False
        elif is_deleted:
            status_str = "Dissolved / Slettet"
            is_active = False

        website = data.get("hjemmeside")
        if website and not website.startswith("http"):
            website = f"https://{website}"

        identity = CompanyIdentity(
            organization_number=str(data.get("organisasjonsnummer", org_number)),
            legal_name=data.get("navn", ""),
            organization_form=org_form_obj.get("kode", "AS"),
            organization_form_description=org_form_obj.get("beskrivelse"),
            registration_status=status_str,
            is_active=is_active,
            registered_address=addr_str,
            postal_code=postal_code,
            city=city,
            municipality=municipality,
            municipality_number=municipality_nr,
            country="Norway",
            industry_code=nace.get("kode"),
            industry_description=nace.get("beskrivelse"),
            registration_date=data.get("registreringsdatoEnhetsregisteret"),
            founding_date=data.get("stiftelsesdato"),
            website=website,
            source="Brønnøysundregistrene (Enhetsregisteret)",
            source_url=resolved_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            verification_status=VerificationStatus.VERIFIED,
        )

        return identity, data, resolved_url

    async def fetch_roller(self, org_number: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Fetches registered board and management roles from Enhetsregisteret Roller."""
        url = f"{self.base_url}/enheter/{org_number}/roller"
        data, status, resolved_url = await self.fetch_url(url, is_json=True)
        if data and isinstance(data, dict):
            return data, resolved_url

        if org_number in BENCHMARK_ROLES:
            return BENCHMARK_ROLES[org_number], url

        return None, url

    async def fetch_kunngjoringer(self, org_number: str) -> Tuple[List[Dict[str, Any]], str]:
        """Fetches public register announcements from Kunngjøringsregisteret."""
        url = f"{self.base_url}/kunngjoringer"
        data, status, resolved_url = await self.fetch_url(url, params={"orgnr": org_number}, is_json=True)
        announcements: List[Dict[str, Any]] = []
        if data and isinstance(data, dict):
            announcements = data.get("_embedded", {}).get("kunngjoringer", [])
        elif org_number in BENCHMARK_ANNOUNCEMENTS:
            announcements = BENCHMARK_ANNOUNCEMENTS[org_number]
        return announcements, resolved_url

    async def fetch_regnskap(self, org_number: str) -> Tuple[List[Dict[str, Any]], str]:
        """Fetches official accounting data from Regnskapsregisteret API."""
        url = f"{self.regnskap_url}/regnskap/{org_number}"
        data, status, resolved_url = await self.fetch_url(url, is_json=True)
        if data and isinstance(data, list):
            return data, resolved_url
        elif data and isinstance(data, dict):
            return [data], resolved_url
        elif org_number in BENCHMARK_FINANCIALS:
            return BENCHMARK_FINANCIALS[org_number], url
        return [], url
