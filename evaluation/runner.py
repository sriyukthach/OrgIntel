"""
OrgIntel Evaluation Runner CLI
Evaluates company intelligence extraction across benchmark datasets.
"""

import sys
import json
import time
import asyncio
from pathlib import Path
from backend.app.agent.orchestrator import ResearchOrchestrator
from backend.app.database import init_db
from evaluation.metrics import compute_evaluation_metrics
from evaluation.reports import generate_markdown_report


async def run_evaluation(dataset_path: Path):
    """Executes evaluation on sample benchmark dataset."""
    print("=" * 60)
    print("🚀 ORGINTEL BENCHMARK EVALUATION HARNESS")
    print("=" * 60)

    await init_db()

    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    org_numbers = [item["organization_number"] for item in data]
    print(f"Loaded {len(org_numbers)} benchmark companies from {dataset_path.name}\n")

    profiles = []
    total_requests = 0
    total_cost = 0.0
    total_latency_ms = 0.0

    for idx, org_nr in enumerate(org_numbers, start=1):
        print(f"[{idx}/{len(org_numbers)}] Auditing Company: {org_nr} ...", end=" ", flush=True)
        orchestrator = ResearchOrchestrator()
        t0 = time.time()
        profile, run, changes = await orchestrator.run_research(org_nr)
        elapsed_ms = (time.time() - t0) * 1000

        if profile:
            profiles.append(profile)
            total_requests += run.outbound_requests_count
            total_cost += run.estimated_cost_usd
            total_latency_ms += elapsed_ms
            verified_cnt = sum(1 for f in profile.facts if f.verification_status == "VERIFIED")
            print(f"✓ {profile.canonical_identity.legal_name} ({verified_cnt} verified facts, {len(profile.evidence)} sources, {elapsed_ms:.0f}ms)")
        else:
            print(f"✗ Failed: {run.errors[0] if run.errors else 'Unknown error'}")

    # Compute metrics
    metrics = compute_evaluation_metrics(profiles, total_requests, total_cost, total_latency_ms)
    report_md = generate_markdown_report(metrics)

    print("\n" + report_md)

    # Save report
    out_dir = Path("evaluation/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "latest_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    with open(out_dir / "latest_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nReport saved to: evaluation/results/latest_report.md")


if __name__ == "__main__":
    dataset = Path(__file__).parent.parent / "data" / "sample_org_numbers.json"
    asyncio.run(run_evaluation(dataset))
