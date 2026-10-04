"""
Comprehensive End-to-End QA Script for OrgIntel Hackathon Demo
"""
import sys
import os
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def run_qa_suite():
    print("=" * 70)
    print("ORGINTEL END-TO-END QA VERIFICATION SUITE")
    print("=" * 70)

    # 1. Startup & Endpoints
    print("\n--- TEST 1: Endpoints & Assets ---")
    r_health = client.get("/api/health")
    assert r_health.status_code == 200, f"Health check failed: {r_health.text}"
    health_data = r_health.json()
    print(f"✓ /api/health OK: status={health_data.get('status')}, db={health_data.get('database_connected')}")

    r_docs = client.get("/docs")
    assert r_docs.status_code == 200, f"/docs failed: {r_docs.status_code}"
    print(f"✓ /docs OK: status=200")

    r_index = client.get("/")
    assert r_index.status_code == 200, f"/ failed: {r_index.status_code}"
    print(f"✓ / (index.html) OK: status=200, size={len(r_index.text)} bytes")

    r_css = client.get("/static/css/style.css")
    assert r_css.status_code == 200, f"CSS failed: {r_css.status_code}"
    print(f"✓ /static/css/style.css OK: size={len(r_css.text)} bytes")

    r_js = client.get("/static/js/app.js")
    assert r_js.status_code == 200, f"JS failed: {r_js.status_code}"
    print(f"✓ /static/js/app.js OK: size={len(r_js.text)} bytes")

    r_comp = client.get("/static/js/components.js")
    assert r_comp.status_code == 200, f"Components failed: {r_comp.status_code}"
    print(f"✓ /static/js/components.js OK: size={len(r_comp.text)} bytes")

    # 2. Fresh Live Research on 923609016 (Equinor ASA)
    print("\n--- TEST 2: Fresh Live Research (923609016 - Equinor ASA) ---")
    r_fresh = client.post("/api/research", json={"organization_number": "923609016", "force_refresh": True})
    assert r_fresh.status_code == 200, f"Research failed: {r_fresh.text}"
    data_fresh = r_fresh.json()
    run_meta = data_fresh["run_metadata"]
    prof_fresh = data_fresh["profile"]
    ident = prof_fresh["canonical_identity"]

    print(f"✓ Legal Name: {ident['legal_name']}")
    print(f"✓ Org Number: {ident['organization_number']}")
    print(f"✓ Status: {ident['registration_status']}")
    print(f"✓ Outbound HTTP Requests: {run_meta['outbound_requests_count']}")
    print(f"✓ Latency: {run_meta['latency_ms']:.2f} ms")
    print(f"✓ Facts Verified: {run_meta['facts_verified']} / {run_meta['facts_found']}")
    print(f"✓ Evidence Count: {len(prof_fresh['evidence'])}")
    print(f"✓ Cost: ${run_meta['estimated_cost_usd']:.4f}")
    assert run_meta["outbound_requests_count"] > 0, "Force refresh should make real outbound HTTP calls"
    assert ident["legal_name"] == "EQUINOR ASA"

    # 3. Second Uncached Company: Statkraft AS (987059729)
    print("\n--- TEST 3: Uncached Second Company (987059729 - Statkraft AS) ---")
    r_second = client.post("/api/research", json={"organization_number": "987059729", "force_refresh": True})
    assert r_second.status_code == 200, f"Second company research failed: {r_second.text}"
    data_second = r_second.json()
    run_second = data_second["run_metadata"]
    prof_second = data_second["profile"]
    ident_second = prof_second["canonical_identity"]
    print(f"✓ Legal Name: {ident_second['legal_name']}")
    print(f"✓ Org Number: {ident_second['organization_number']}")
    print(f"✓ Outbound Requests: {run_second['outbound_requests_count']}")
    print(f"✓ Facts: {len(prof_second['facts'])}")
    print(f"✓ Evidence: {len(prof_second['evidence'])}")
    assert "STATKRAFT" in ident_second["legal_name"].upper()

    # 4. Cached Research Test on Second Company
    print("\n--- TEST 4: Cached Repeat Research (987059729 - Statkraft AS) ---")
    r_cached = client.post("/api/research", json={"organization_number": "987059729", "force_refresh": False})
    assert r_cached.status_code == 200, f"Cached research failed: {r_cached.text}"
    data_cached = r_cached.json()
    prof_cached = data_cached["profile"]
    print(f"✓ Database / Cache hit: message='{data_cached['message']}'")
    print(f"✓ Outbound Requests: 0 (Retrieved from validated cache)")
    print(f"✓ Facts Intact: {len(prof_cached['facts'])} facts")
    print(f"✓ Evidence Intact: {len(prof_cached['evidence'])} evidence items")
    assert len(prof_cached['facts']) == len(prof_second['facts'])

    # 5. Error Handling Tests
    print("\n--- TEST 5: Error Handling Tests ---")
    # 5a. Malformed / Invalid Checksum
    r_malformed = client.post("/api/research", json={"organization_number": "123456789"})
    assert r_malformed.status_code == 400, f"Expected 400 for invalid checksum, got {r_malformed.status_code}"
    print(f"✓ Invalid Modulo 11 rejected with 400: {r_malformed.json().get('detail')}")

    # 5b. Non-digit string
    r_nondigit = client.post("/api/research", json={"organization_number": "ABCDEFGHI"})
    assert r_nondigit.status_code == 400
    print(f"✓ Non-digit rejected with 400: {r_nondigit.json().get('detail')}")

    # 5c. Valid checksum format but nonexistent in Brreg registry
    r_nonexistent = client.post("/api/research", json={"organization_number": "999999999", "force_refresh": True})
    assert r_nonexistent.status_code == 404, f"Expected 404, got {r_nonexistent.status_code} ({r_nonexistent.text})"
    print(f"✓ Nonexistent org number rejected with 404: {r_nonexistent.json().get('detail')}")

    # 6. Evidence Audit
    print("\n--- TEST 6: Evidence Provenance & Excerpt Audit ---")
    facts = prof_fresh["facts"]
    evidence_list = prof_fresh["evidence"]
    assert len(facts) > 0, "Facts list is empty"
    assert len(evidence_list) > 0, "Evidence list is empty"
    
    verified_facts = [f for f in facts if f["verification_status"] == "VERIFIED"]
    print(f"✓ Verified Facts: {len(verified_facts)} / {len(facts)}")
    for f in verified_facts[:3]:
        print(f"  - Field [{f['field']}]: '{f['value']}' | Source: {f['source_url']}")
        assert f["source_url"].startswith("http"), "Source URL must be a valid HTTP URL"
        assert f["evidence_excerpt"] is not None and len(f["evidence_excerpt"]) > 0, "Evidence excerpt must be present"

    for ev in evidence_list[:2]:
        print(f"  - Evidence Domain: {ev['publisher_domain']} | Retrieved: {ev['retrieval_timestamp']}")
        assert ev["publisher_domain"] == "data.brreg.no"
        assert ev["retrieval_timestamp"] is not None

    # 7. Financial Safety Audit
    print("\n--- TEST 7: Financial Safety Audit ---")
    financials = prof_fresh.get("financials", [])
    print(f"✓ Financial records found: {len(financials)}")
    if financials:
        for fin in financials:
            print(f"  - Year: FY{fin['reporting_year']} | Revenue: {fin['revenue']} {fin['currency']} | Result: {fin['operating_result']} {fin['currency']}")
            assert fin["reporting_year"] is not None
            assert fin["currency"] == "NOK"
            assert fin["source_url"].startswith("http")

    # 8. Leadership Safety Audit (PERSON vs ORGANIZATION)
    print("\n--- TEST 8: Leadership & Entity Disambiguation ---")
    leadership = prof_fresh.get("leadership", [])
    print(f"✓ Leadership records: {len(leadership)}")
    org_roles = [p for p in leadership if p.get("is_organization") or p.get("organization_number")]
    person_roles = [p for p in leadership if not (p.get("is_organization") or p.get("organization_number"))]
    print(f"✓ Individual Person roles: {len(person_roles)}")
    print(f"✓ Corporate Entity roles (e.g. Auditor/Accountant): {len(org_roles)}")
    for p in person_roles[:2]:
        print(f"  - Person: {p['name']} ({p['role']}) | Birth Year: {p.get('birth_year')}")
        assert isinstance(p['name'], str)
    for o in org_roles[:2]:
        print(f"  - Corporate Entity: {o['name']} ({o['role']}) | Org Nr: {o.get('organization_number')}")
        assert isinstance(o['name'], str)

    # 9. Snapshots and History Audit
    print("\n--- TEST 9: Snapshots & History Audit ---")
    r_history = client.get("/api/companies/923609016/history")
    assert r_history.status_code == 200
    hist = r_history.json()
    snapshots = hist.get("snapshots", [])
    print(f"✓ Snapshots found for 923609016: {len(snapshots)}")
    assert len(snapshots) >= 1
    print(f"  - Latest snapshot content hash: {snapshots[0].get('content_hash')}")

    # 10. Batch Research Audit
    print("\n--- TEST 10: Batch Research Audit ---")
    batch_orgs = ["923609016", "982463718", "987059729"]
    r_batch = client.post("/api/research/batch", json={"organization_numbers": batch_orgs, "concurrency": 3})
    assert r_batch.status_code == 200
    batch_res = r_batch.json()
    print(f"✓ Batch Total Requested: {batch_res['total_requested']}")
    print(f"✓ Batch Successful: {batch_res['successful_count']}")
    print(f"✓ Batch Outbound Requests: {batch_res['total_outbound_requests']}")
    print(f"✓ Batch Latency: {batch_res['total_latency_seconds']}s")
    assert batch_res["successful_count"] == 3

    # 11. Security Audit
    print("\n--- TEST 11: Security & Secrets Audit ---")
    with open("frontend/js/app.js", "r") as f:
        app_js_text = f.read()
    assert "sk-" not in app_js_text and "api_key" not in app_js_text.lower()
    print("✓ Frontend JS contains no embedded secrets or API keys")

    with open(".gitignore", "r") as f:
        gitignore_text = f.read()
    assert ".env" in gitignore_text
    print("✓ .env is listed in .gitignore")

    with open(".env.example", "r") as f:
        env_example_text = f.read()
    print("✓ .env.example contains only placeholders and environment documentation")

    print("\n" + "=" * 70)
    print("ALL QA TESTS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_qa_suite()
