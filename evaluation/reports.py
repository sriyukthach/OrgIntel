"""
Evaluation Report Formatter
Generates human-readable Markdown and structured JSON evaluation reports.
"""

from typing import Dict, Any


def generate_markdown_report(metrics: Dict[str, Any]) -> str:
    """Renders evaluation metrics as a clean Markdown report."""
    md = []
    md.append("# 🎯 OrgIntel Benchmark Evaluation Report")
    md.append("")
    md.append(f"**Composite Intelligence Score:** `{metrics.get('composite_intelligence_score', 0)} / 100`")
    md.append(f"**Total Companies Evaluated:** `{metrics.get('total_companies_evaluated', 0)}`")
    md.append("")
    md.append("## 📊 Fact & Evidence Integrity")
    md.append("")
    f = metrics.get("facts", {})
    md.append(f"- **Total Facts Extracted:** {f.get('total_extracted', 0)}")
    md.append(f"- **Verified Facts:** {f.get('total_verified', 0)} ({f.get('verification_rate', 0)*100:.1f}%)")
    md.append(f"- **Evidence Provenance Rate:** {f.get('evidence_provenance_rate', 0)*100:.1f}% (100% target)")
    md.append(f"- **Ambiguous / Disputed Facts:** {f.get('total_ambiguous', 0)}")
    md.append("")
    md.append("## 🏢 Intelligence Coverage")
    md.append("")
    c = metrics.get("coverage", {})
    md.append(f"- **Leadership Coverage:** {c.get('leadership_rate', 0)*100:.1f}%")
    md.append(f"- **Financials Coverage:** {c.get('financials_rate', 0)*100:.1f}%")
    md.append(f"- **Overview / Description:** {c.get('overview_rate', 0)*100:.1f}%")
    md.append(f"- **Activities & Announcements:** {c.get('activities_rate', 0)*100:.1f}%")
    md.append("")
    md.append("## ⚡ Resource & Challenge Constraints Compliance")
    md.append("")
    p = metrics.get("performance", {})
    md.append(f"- **Total Outbound Requests:** {p.get('total_outbound_requests', 0)} / 2000 allowed")
    md.append(f"- **Avg Requests / Company:** {p.get('avg_requests_per_company', 0)}")
    md.append(f"- **Total Estimated Cost:** ${p.get('total_cost_usd', 0):.4f} / $10.00 budget")
    md.append(f"- **Average Latency:** {p.get('avg_latency_ms', 0)} ms")
    md.append(f"- **Constraint Compliance Status:** `{'PASSED ✓' if p.get('challenge_limits_compliant') else 'FAILED ✗'}`")
    md.append("")
    return "\n".join(md)
