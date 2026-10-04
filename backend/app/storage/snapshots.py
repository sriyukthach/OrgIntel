"""
Historical Snapshot & Change Detection Engine
Calculates temporal diffs between successive company research runs.
"""

import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.models import CompanyProfile


def compute_profile_hash(profile: CompanyProfile) -> str:
    """Deterministic hash of core profile attributes for diff detection."""
    core_state = {
        "org_nr": profile.organization_number,
        "name": profile.canonical_identity.legal_name,
        "status": profile.canonical_identity.registration_status,
        "address": profile.canonical_identity.registered_address,
        "industry": profile.canonical_identity.industry_description,
        "website": profile.canonical_identity.website,
        "leadership": sorted([f"{p.role}:{p.name}" for p in profile.leadership]),
        "financials": sorted([f"{f.reporting_year}:{f.revenue}" for f in profile.financials]),
    }
    raw = json.dumps(core_state, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def detect_changes_between_snapshots(
    old_profile_dict: Dict[str, Any], new_profile_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compares two historical profile records and extracts structured diffs:
    - Status changes
    - Address changes
    - Leadership appointments/departures
    - Financial updates
    - General field revisions
    """
    changes: Dict[str, Any] = {
        "has_changes": False,
        "modified_fields": [],
        "leadership_changes": {"added": [], "removed": [], "changed": []},
        "financial_updates": [],
        "address_changed": False,
        "status_changed": False,
    }

    old_id = old_profile_dict.get("canonical_identity", {})
    new_id = new_profile_dict.get("canonical_identity", {})

    # Check identity fields
    for field in ["legal_name", "registration_status", "registered_address", "industry_description", "website"]:
        old_val = old_id.get(field)
        new_val = new_id.get(field)
        if old_val != new_val and (old_val is not None or new_val is not None):
            changes["has_changes"] = True
            changes["modified_fields"].append({
                "field": field,
                "old_value": old_val,
                "new_value": new_val,
            })
            if field == "registration_status":
                changes["status_changed"] = True
            if field == "registered_address":
                changes["address_changed"] = True

    # Compare Leadership
    old_lead_map = {p.get("name"): p.get("role") for p in old_profile_dict.get("leadership", []) if p.get("name")}
    new_lead_map = {p.get("name"): p.get("role") for p in new_profile_dict.get("leadership", []) if p.get("name")}

    for name, role in new_lead_map.items():
        if name not in old_lead_map:
            changes["has_changes"] = True
            changes["leadership_changes"]["added"].append({"name": name, "role": role})
        elif old_lead_map[name] != role:
            changes["has_changes"] = True
            changes["leadership_changes"]["changed"].append({
                "name": name,
                "old_role": old_lead_map[name],
                "new_role": role,
            })

    for name, role in old_lead_map.items():
        if name not in new_lead_map:
            changes["has_changes"] = True
            changes["leadership_changes"]["removed"].append({"name": name, "role": role})

    # Compare Financials
    old_years = {f.get("reporting_year"): f for f in old_profile_dict.get("financials", []) if f.get("reporting_year")}
    new_years = {f.get("reporting_year"): f for f in new_profile_dict.get("financials", []) if f.get("reporting_year")}

    for year, fin in new_years.items():
        if year not in old_years:
            changes["has_changes"] = True
            changes["financial_updates"].append({"year": year, "action": "NEW_REPORTING_PERIOD", "data": fin})
        elif old_years[year].get("revenue") != fin.get("revenue"):
            changes["has_changes"] = True
            changes["financial_updates"].append({
                "year": year,
                "action": "REVISED_FIGURES",
                "old_revenue": old_years[year].get("revenue"),
                "new_revenue": fin.get("revenue"),
            })

    return changes
