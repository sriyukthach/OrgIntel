"""
Unit tests for Historical Snapshots and Change Detection.
"""

from backend.app.storage.snapshots import detect_changes_between_snapshots


def test_detect_snapshot_changes_leadership_and_financials():
    old_profile = {
        "canonical_identity": {
            "legal_name": "Test AS",
            "registration_status": "Active",
            "registered_address": "Oslogata 1",
        },
        "leadership": [
            {"name": "Alice Smith", "role": "Daglig leder / CEO"},
            {"name": "Bob Jones", "role": "Styreleder / Board Chair"},
        ],
        "financials": [
            {"reporting_year": 2023, "revenue": 10000000.0}
        ],
    }

    # New profile with CEO change, address change, and new financial year
    new_profile = {
        "canonical_identity": {
            "legal_name": "Test AS",
            "registration_status": "Active",
            "registered_address": "Storgata 50",  # Changed address
        },
        "leadership": [
            {"name": "Charlie Brown", "role": "Daglig leder / CEO"},  # New CEO
            {"name": "Bob Jones", "role": "Styreleder / Board Chair"},
        ],
        "financials": [
            {"reporting_year": 2024, "revenue": 15000000.0},  # New Year
            {"reporting_year": 2023, "revenue": 10000000.0},
        ],
    }

    changes = detect_changes_between_snapshots(old_profile, new_profile)
    assert changes["has_changes"] is True
    assert changes["address_changed"] is True
    assert len(changes["leadership_changes"]["added"]) == 1
    assert changes["leadership_changes"]["added"][0]["name"] == "Charlie Brown"
    assert len(changes["leadership_changes"]["removed"]) == 1
    assert changes["leadership_changes"]["removed"][0]["name"] == "Alice Smith"
    assert len(changes["financial_updates"]) == 1
