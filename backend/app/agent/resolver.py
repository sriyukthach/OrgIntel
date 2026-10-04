"""
Canonical Identity Resolver
Validates organization numbers and establishes authoritative entity baseline via Brreg Enhetsregisteret.
"""

from typing import Tuple, Optional, Dict, Any
from backend.app.models import CompanyIdentity, VerificationStatus
from backend.app.verification.identity import validate_norwegian_org_number
from backend.app.sources.brreg import BrregClient
from backend.app.sources.base import RequestTracker


class IdentityResolver:
    """Resolves canonical company identity from Norwegian organization numbers via live Brreg registry."""

    def __init__(self, tracker: Optional[RequestTracker] = None):
        self.tracker = tracker or RequestTracker()
        self.brreg_client = BrregClient(self.tracker)

    async def resolve_identity(
        self, raw_org_nr: str, force_refresh: bool = False
    ) -> Tuple[Optional[CompanyIdentity], str]:
        """
        Validates organization number and resolves against authoritative registry.
        Returns (Optional[CompanyIdentity], status_or_error_message).
        """
        is_valid, val_result = validate_norwegian_org_number(raw_org_nr)
        if not is_valid:
            return None, f"Invalid Organization Number: {val_result}"

        org_number = val_result

        # Query live Brreg Enhetsregisteret API
        identity, raw_json, source_url = await self.brreg_client.fetch_enhet(
            org_number, force_refresh=force_refresh
        )
        if identity:
            return identity, "Resolved from authoritative Brreg registry."

        return None, f"Company with organization number {org_number} not found in public registry."
