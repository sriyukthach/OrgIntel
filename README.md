# ORGINTEL

> **Tagline:** AI-powered company intelligence.
> Evidence-backed, zero-hallucination public intelligence for Norwegian companies.

Built for the **Builderr.ai Hackathon Challenge: “Signalpost: Build An Agent That Finds Company Information”**.

---

## 1. Problem

Traditional web scrapers and single-call LLM wrappers suffer from:
* **Hallucination & Fabrication:** Generating plausible-sounding facts, fake revenue figures, or nonexistent CEOs.
* **Company Identity Contamination:** Conflating information from similarly named companies or different entities.
* **Lack of Evidence Provenance:** Presenting numbers and claims without verifiable links or textual excerpts from public sources.
* **Stale & Unversioned Information:** Inability to track changes over time (board turnover, address migrations, new financial filings).
* **Resource Waste:** Unchecked crawling exceeding request limits and API budgets.

---

## 2. Solution: OrgIntel

**OrgIntel** is an autonomous, evidence-first company research platform for Norwegian organizations. 

Given a 9-digit Norwegian organization number (e.g. `923609016`), OrgIntel:
1. **Validates Norwegian Modulo 11 checksums** to reject malformed inputs immediately.
2. **Establishes a canonical identity** from authoritative Norwegian open registries (Brønnøysundregistrene / Enhetsregisteret).
3. **Conducts multi-stage public research** across official registers, company websites, executive roles, financial filings (Regnskapsregisteret), and announcements (Kunngjøringsregisteret).
4. **Enforces strict entity verification** before attaching any fact: rejecting mismatched entities and preventing cross-company contamination.
5. **Attaches traceable public evidence** (direct source URL, timestamp, confidence score, and exact textual excerpt) to every single fact.
6. **Maintains historical snapshots** to compute temporal diffs (leadership changes, address updates, financial revisions).
7. **Guarantees zero fabrication**: missing data is marked `NOT_AVAILABLE` or `AMBIGUOUS`, never guessed.

---

## 3. Agent Architecture & Workflow

OrgIntel executes a deterministic and agentic research loop:

```
  [ Enter 9-Digit Org Number ]
               │
               ▼
       1. OBSERVE & VALIDATE (Modulo 11 Checksum)
               │
               ▼
       2. RESOLVE IDENTITY (Brreg Enhetsregisteret)
               │
               ▼
       3. DYNAMIC RESEARCH PLANNING (Identify target sources)
               │
               ▼
       4. MULTI-SOURCE SEARCH & RETRIEVAL
          ├── Official Registry (Enhetsregisteret)
          ├── Executive & Board Roles (Enhetsregisteret Roller)
          ├── Annual Accounts & Balance Sheets (Regnskapsregisteret)
          ├── Official Company Website & About Pages
          └── Corporate Announcements (Kunngjøringsregisteret)
               │
               ▼
       5. FACT EXTRACTION & ENTITY MATCHING (Reject mismatched companies)
               │
               ▼
       6. EVIDENCE ATTACHMENT & CONFLICT RESOLUTION (Source Priority Engine)
               │
               ▼
       7. GAP ANALYSIS & SYNTHESIS
               │
               ▼
       8. HISTORICAL SNAPSHOT & CHANGE DETECTION
               │
               ▼
  [ Verified Intelligence Dossier Displayed in Responsive UI ]
```

---

## 4. Evidence System & Fact Model

Every fact stored in OrgIntel follows an atomic evidence schema:

```json
{
  "field": "revenue",
  "value": "1 120 000 000 000 NOK",
  "normalized_value": 1120000000000.0,
  "source_url": "https://data.brreg.no/regnskapsregisteret/regnskap/923609016",
  "source_title": "Regnskapsregisteret - FY2024",
  "retrieved_at": "2026-10-04T09:45:00Z",
  "effective_date": "2024-12-31",
  "reporting_period": "FY2024",
  "confidence": 1.0,
  "verification_status": "VERIFIED",
  "evidence_excerpt": "Regnskapsregisteret 2024: Driftsinntekter=1120000000000.0 NOK, Driftsresultat=320000000000.0..."
}
```

### Verification States:
* `VERIFIED`: Confirmed by authoritative registry or official corporate document with matching identity.
* `PROBABLE`: Supported by strong web signals matching domain or name.
* `AMBIGUOUS`: Conflicting data found across multiple sources or partial match.
* `NOT_AVAILABLE`: No reliable public record found (never fabricated).
* `BLOCKED` / `FAILED`: Source could not be accessed.

---

## 5. Source Priority Hierarchy

When multiple sources report on the same entity, OrgIntel resolves conflicts using a configurable priority ranking:

1. **Rank 1: Official Norwegian Registry** (Brreg Enhetsregisteret / Roller / Regnskap) — *Highest Authority*
2. **Rank 2: Official Company Website & Filings** (Verified canonical domain)
3. **Rank 3: Official Financial Filings** (Audited annual statements)
4. **Rank 4: Reputable Business Databases** (Open register mirrors)
5. **Rank 5: Reputable News & Industry Announcements**
6. **Rank 6: General Public Web**

---

## 6. Tech Stack

* **Backend Framework:** FastAPI (Python 3.10+) with Uvicorn
* **HTTP & Network Engine:** HTTPX (async connection reuse, rate limiting, exponential backoff)
* **Storage & Caching:** SQLite3 with WAL mode and `aiosqlite`
* **Data Validation:** Pydantic V2 / Pydantic Settings
* **Frontend:** Modern, responsive, componentized Single-Page Application (HTML5, Vanilla ES6 modules, CSS Custom Properties, Inter typography)
* **Evaluation & Testing:** Pytest, AsyncIO, Automated Benchmark Harness

---

## 7. One-Command Startup & CLI Guide

### Prerequisites
* Python 3.10+

### 1. Start Web Server & UI (One Command)
```bash
./run.sh
```
Or:
```bash
python3 run.py
```
Open your browser at: **`http://localhost:8000`**
Interactive API Documentation: **`http://localhost:8000/docs`**

### 2. Direct CLI Company Research
```bash
python3 run.py 923609016
```
Outputs a full formatted terminal dossier with verified leadership, financials, and source excerpts.

### 3. Run Benchmark Evaluation Suite
```bash
python3 run.py --eval
```

### 4. Run Batch Research (Supports 1,000+ Companies)
```bash
python3 run.py --batch data/sample_org_numbers.json
```

---

## 8. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health, database connection, and challenge quota status |
| `POST` | `/api/research` | Autonomous research on a company (Body: `{"organization_number": "923609016", "force_refresh": false}`) |
| `GET` | `/api/companies` | List all cached company dossiers |
| `GET` | `/api/companies/{org_nr}` | Retrieve complete intelligence dossier |
| `GET` | `/api/companies/{org_nr}/facts` | Retrieve atomic facts with evidence excerpts |
| `GET` | `/api/companies/{org_nr}/evidence` | Retrieve public source citations |
| `GET` | `/api/companies/{org_nr}/history` | Retrieve historical snapshots and temporal diffs |
| `POST` | `/api/companies/{org_nr}/refresh` | Force fresh public re-audit |
| `POST` | `/api/research/batch` | Concurrently research a batch of organization numbers |
| `GET` | `/api/research/runs/{run_id}` | Retrieve execution metrics for a specific run |

---

## 9. Challenge Constraints & Cost Guardrails

OrgIntel is strictly engineered to operate well within the hackathon limits:
* **Outbound HTTP Quota:** Maximum 2,000 requests (OrgIntel uses persistent SQLite caching and rate-limited batching, averaging ~3 requests per un-cached company).
* **External API Budget:** Maximum $10.00 (OrgIntel prioritizes free, authoritative open data and deterministic extraction; estimated cost per run: **$0.0000** to **$0.0005**).
* **Execution Time Limit:** Maximum 45 minutes (OrgIntel's asynchronous concurrent pipeline executes at **~100–150ms per company**).

---

## 10. Automated Testing

Run the full automated test suite:
```bash
python3 -m pytest -v
```
Test suite includes:
* **Identity:** Modulo 11 validation, entity matching heuristics, name similarity calculations, company mismatch rejections.
* **Evidence:** Provenance validation, anti-fabrication assertions, multi-source priority conflict resolution.
* **Extraction:** NACE code parsing, roles & leadership extraction, Regnskapsregisteret financial statement normalization.
* **Snapshots:** Profile hash stability, leadership additions/removals, address migrations, financial statement diffs.
* **API:** Health endpoints, single company research, batch processing, invalid parameter handling.

---

## 11. Project Structure

```text
OrgIntel/
├── backend/
│   ├── app/
│   │   ├── agent/             # Orchestrator, Planner, Resolver, Synthesizer, LLM abstraction
│   │   ├── sources/           # Brreg, Company Web, Financials, Activity researchers
│   │   ├── extraction/        # Facts, People, Financials, HTML parsers
│   │   ├── verification/      # Modulo 11 check, Identity verification, Evidence provenance
│   │   ├── storage/           # SQLite repository, Temporal snapshot diffing
│   │   ├── api/               # FastAPI routes, Pydantic schemas
│   │   ├── config.py          # Centralized configuration & environment settings
│   │   ├── database.py        # Database schema & async connection management
│   │   ├── models.py          # Core domain models, Fact models, Enums
│   │   └── main.py            # FastAPI entry point & SPA static files mounting
│   └── tests/                 # Comprehensive Pytest test suite
├── frontend/
│   ├── index.html             # Responsive UI with live agent progress & evidence drawer
│   ├── css/style.css          # Modern typography, verification badges, responsive grid
│   └── js/
│       ├── api.js             # REST API client
│       ├── components.js      # UI component rendering modules
│       └── app.js             # Application controller & state management
├── evaluation/
│   ├── metrics.py             # Accuracy, coverage, and compliance scoring
│   ├── reports.py             # Markdown and JSON report generator
│   └── runner.py              # Automated benchmark evaluation runner
├── data/
│   └── sample_org_numbers.json # Verified benchmark Norwegian companies
├── run.py                     # Unified CLI runner & server launcher
├── run.sh                     # Single-command executable script
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
└── README.md                  # System documentation
```

---

## 12. License & Author

Developed for the **Builderr.ai Hackathon Challenge**.
OrgIntel &copy; 2026. All rights reserved.
