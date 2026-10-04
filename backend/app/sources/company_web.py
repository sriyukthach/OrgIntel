"""
Official Company Webpage Analyzer
Fetches and analyzes official company website for descriptions, operations, and leadership.
"""

from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import urljoin, urlparse
from backend.app.sources.base import BaseSourceClient, RequestTracker
from backend.app.extraction.html_parser import parse_html_document, find_text_excerpt_around_keyword
from backend.app.models import CompanyOverview, Fact, VerificationStatus, SourcePriority


class CompanyWebClient(BaseSourceClient):
    """Client for retrieving and parsing official company websites."""

    def __init__(self, tracker: Optional[RequestTracker] = None):
        super().__init__(tracker)

    async def analyze_website(
        self, website_url: str, legal_name: str
    ) -> Tuple[Optional[CompanyOverview], List[Fact], str]:
        """
        Retrieves homepage and optionally an 'About' page to extract company overview facts.
        """
        facts: List[Fact] = []
        if not website_url:
            return None, facts, ""

        # Normalize URL
        if not website_url.startswith("http"):
            website_url = f"https://{website_url}"

        html_body, status, resolved_url = await self.fetch_url(website_url, is_json=False)
        if not html_body or status != 200:
            return None, facts, website_url

        parsed = parse_html_document(html_body, base_url=resolved_url)
        description = parsed.get("meta_description") or parsed.get("excerpt", "")
        clean_text = parsed.get("clean_text", "")

        # Look for About page in links if description is short
        about_url = None
        if len(description) < 80:
            for link in parsed.get("links", []):
                link_lower = link.lower()
                if any(kw in link_lower for kw in ["om-oss", "om_oss", "about", "about-us", "selskapet"]):
                    about_url = urljoin(resolved_url, link)
                    break

        if about_url and about_url != resolved_url:
            about_html, about_status, about_resolved = await self.fetch_url(about_url, is_json=False)
            if about_html and about_status == 200:
                parsed_about = parse_html_document(about_html, base_url=about_resolved)
                if parsed_about.get("clean_text"):
                    clean_text = parsed_about.get("clean_text")
                    description = parsed_about.get("meta_description") or clean_text[:400]
                    resolved_url = about_resolved

        if description:
            # Create business description fact
            fact = Fact(
                field="business_description",
                value=description[:500].strip(),
                normalized_value=description[:500].strip(),
                source_url=resolved_url,
                source_title=f"{parsed.get('title', legal_name)} - Official Website",
                confidence=0.90,
                verification_status=VerificationStatus.VERIFIED,
                evidence_excerpt=description[:300],
            )
            facts.append(fact)

        overview = CompanyOverview(
            business_description=description[:600] if description else None,
            products_services=[],
            sectors=[],
            locations=[],
            description_source_url=resolved_url,
            verification_status=VerificationStatus.VERIFIED if description else VerificationStatus.NOT_AVAILABLE,
        )

        return overview, facts, resolved_url
