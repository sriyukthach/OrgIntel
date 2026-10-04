"""
Company Activity & Announcements Researcher
Extracts official register announcements, changes, capital updates, and news.
"""

from typing import List, Tuple, Optional
from backend.app.sources.base import BaseSourceClient, RequestTracker
from backend.app.sources.brreg import BrregClient
from backend.app.models import CompanyActivity


class ActivityResearcher(BaseSourceClient):
    """Researches recent public company activities and announcements."""

    def __init__(self, tracker: Optional[RequestTracker] = None):
        super().__init__(tracker)
        self.brreg_client = BrregClient(tracker)

    async def research_activities(
        self, org_number: str, force_refresh: bool = False
    ) -> Tuple[List[CompanyActivity], str]:
        """
        Retrieves official register announcements from Kunngjøringsregisteret.
        """
        raw_announcements, source_url = await self.brreg_client.fetch_kunngjoringer(
            org_number, force_refresh=force_refresh
        )
        activities: List[CompanyActivity] = []

        for item in raw_announcements[:10]:
            try:
                title = item.get("tittel") or item.get("undertittel") or "Offisiell kunngjøring"
                date_val = item.get("publisertDato") or item.get("opprettetDato")
                act_type = item.get("type", {}).get("beskrivelse") or "Kunngjøring"
                desc = item.get("meldingsinnhold") or f"Registrert kunngjøring i Brønnøysundregistrene: {title}"

                activities.append(
                    CompanyActivity(
                        title=title,
                        date=date_val[:10] if date_val else None,
                        summary=desc[:300],
                        activity_type=act_type,
                        source_url=f"https://data.brreg.no/kunngjoringer/api/kunngjoringer/{item.get('id', '')}",
                    )
                )
            except Exception:
                continue

        return activities, source_url
