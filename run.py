#!/usr/bin/env python3
"""
OrgIntel Unified Entry Point & CLI Runner
Supports:
  python run.py                     -> Starts FastAPI server + Frontend Web App
  python run.py <org_number>        -> Direct CLI Company Research & Dossier
  python run.py --eval              -> Runs Evaluation Benchmark Suite
  python run.py --batch <file.json> -> Batch researches company list
"""

import sys
import json
import time
import argparse
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.app.config import settings
from backend.app.database import init_sync_db, init_db
from backend.app.models import VerificationStatus
from backend.app.agent.orchestrator import ResearchOrchestrator
from evaluation.runner import run_evaluation


def print_banner():
    print("=" * 70)
    print("  🧠  ORGINTEL — AI-POWERED COMPANY INTELLIGENCE")
    print("  Tagline: Evidence-Backed Public Intelligence for Norwegian Companies")
    print("=" * 70)


async def run_cli_research(org_number: str):
    """Researches a company via CLI and outputs structured intelligence dossier."""
    print_banner()
    print(f"\n🔍 Initiating Research for Organization Number: [{org_number}] ...\n")
    await init_db()

    orchestrator = ResearchOrchestrator()
    profile, run, changes = await orchestrator.run_research(org_number)

    if not profile:
        print(f"❌ Research Failed: {run.errors[0] if run.errors else 'Company not found'}")
        sys.exit(1)

    ident = profile.canonical_identity
    print("=" * 70)
    print(f"🏢 COMPANY DOSSIER: {ident.legal_name} ({ident.organization_form})")
    print("=" * 70)
    print(f"• Org Number:      {ident.organization_number}")
    print(f"• Status:          {ident.registration_status} (Active: {ident.is_active})")
    print(f"• Address:         {ident.registered_address or 'N/A'}, {ident.postal_code or ''} {ident.city or ''}")
    print(f"• Industry:        {ident.industry_code or ''} - {ident.industry_description or 'N/A'}")
    print(f"• Registered:      {ident.registration_date or 'N/A'} (Founded: {ident.founding_date or 'N/A'})")
    print(f"• Website:         {ident.website or 'N/A'}")
    print(f"• Registry Source: {ident.source_url}")

    print("\n👥 VERIFIED LEADERSHIP & BOARD:")
    if profile.leadership:
        for p in profile.leadership:
            print(f"  - {p.role}: {p.name} (Source: {p.source_url})")
    else:
        print("  - No separate public role records found.")

    print("\n📈 FINANCIAL PERFORMANCE (Regnskapsregisteret):")
    if profile.financials:
        for f in profile.financials[:3]:
            rev = f"{f.revenue:,.0f} {f.currency}".replace(",", " ") if f.revenue else "N/A"
            res = f"{f.operating_result:,.0f} {f.currency}".replace(",", " ") if f.operating_result else "N/A"
            prof = f"{f.profit_loss:,.0f} {f.currency}".replace(",", " ") if f.profit_loss else "N/A"
            print(f"  - FY{f.reporting_year}: Revenue: {rev} | Operating Result: {res} | Net Profit: {prof}")
    else:
        print("  - No public financial statements available.")

    print("\n📢 RECENT REGISTER ACTIVITIES & ANNOUNCEMENTS:")
    if profile.activities:
        for a in profile.activities[:3]:
            print(f"  - [{a.date or 'Recent'}] {a.title}: {a.summary[:100]}...")
    else:
        print("  - No recent announcements found.")

    print(f"\n📑 TRACEABLE EVIDENCE SOURCES ({len(profile.evidence)} sources):")
    for ev in profile.evidence[:5]:
        print(f"  - [{ev.publisher_domain}] {ev.source_title}")
        print(f"    URL: {ev.source_url}")
        print(f"    Evidence Excerpt: \"{ev.evidence_excerpt[:120]}...\"")

    print("\n⚡ RUN PERFORMANCE METRICS:")
    print(f"• Verified Facts:     {run.facts_verified} / {len(profile.facts)}")
    print(f"• Outbound Requests:  {run.outbound_requests_count}")
    print(f"• Execution Latency:  {run.latency_ms:.0f} ms")
    print(f"• Cost:               ${run.estimated_cost_usd:.4f}")
    print("=" * 70 + "\n")


def start_server():
    """Starts FastAPI web server."""
    print_banner()
    init_sync_db()
    import uvicorn
    print(f"\n🌐 Starting OrgIntel Web Application at: http://localhost:{settings.PORT}")
    print(f"📚 Interactive API Documentation at:     http://localhost:{settings.PORT}/docs\n")
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=False)


def main():
    parser = argparse.ArgumentParser(description="OrgIntel - AI-Powered Norwegian Company Intelligence")
    parser.add_argument("org_number", nargs="?", help="Norwegian 9-digit organization number to research")
    parser.add_argument("--server", action="store_true", help="Start the FastAPI web server and UI dashboard")
    parser.add_argument("--eval", action="store_true", help="Run benchmark evaluation suite")
    parser.add_argument("--batch", type=str, help="Path to JSON file with organization numbers for batch research")
    args = parser.parse_args()

    if args.eval:
        dataset_path = Path(__file__).parent / "data" / "sample_org_numbers.json"
        asyncio.run(run_evaluation(dataset_path))
    elif args.batch:
        dataset_path = Path(args.batch)
        asyncio.run(run_evaluation(dataset_path))
    elif args.org_number:
        asyncio.run(run_cli_research(args.org_number))
    else:
        start_server()


if __name__ == "__main__":
    main()
