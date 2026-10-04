"""
Financials Source Researcher
Queries official registers and financial filings for accounting metrics.
"""

from typing import List, Tuple, Optional
from backend.app.sources.base import BaseSourceClient, RequestTracker
from backend.app.sources.brreg import BrregClient
from backend.app.models import FinancialRecord, Fact, VerificationStatus
from backend.app.extraction.financial import extract_financials_from_regnskap, financials_to_facts


class FinancialsResearcher(BaseSourceClient):
    """Coordinates financial research from official accounts."""

    def __init__(self, tracker: Optional[RequestTracker] = None):
        super().__init__(tracker)
        self.brreg_client = BrregClient(tracker)

    async def research_financials(self, org_number: str) -> Tuple[List[FinancialRecord], List[Fact], str]:
        """
        Retrieves official financial accounts.
        Returns (List[FinancialRecord], List[Fact], source_url).
        """
        raw_regnskap, source_url = await self.brreg_client.fetch_regnskap(org_number)
        if raw_regnskap:
            records = extract_financials_from_regnskap(raw_regnskap, source_url)
            facts = financials_to_facts(records)
            return records, facts, source_url

        return [], [], source_url
