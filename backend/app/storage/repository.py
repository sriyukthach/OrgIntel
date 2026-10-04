"""
OrgIntel Data Repository
Handles persistent storage of companies, facts, evidence, leadership, financials, runs, and cache.
"""

import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import aiosqlite
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import (
    CompanyProfile,
    CompanyIdentity,
    CompanyOverview,
    PersonRole,
    FinancialRecord,
    CompanyActivity,
    Fact,
    EvidenceRecord,
    ResearchRun,
    ResearchRunStatus,
    VerificationStatus,
)
from backend.app.storage.snapshots import compute_profile_hash, detect_changes_between_snapshots


class Repository:
    """Async database repository."""

    @staticmethod
    async def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves non-expired cached response."""
        if not settings.CACHE_ENABLED:
            return None
        now_iso = datetime.now(timezone.utc).isoformat()
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT response_body, status_code, headers_json FROM source_cache WHERE cache_key = ? AND expires_at > ?",
                (cache_key, now_iso),
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "body": row["response_body"],
                    "status_code": row["status_code"],
                    "headers": json.loads(row["headers_json"]) if row["headers_json"] else {},
                }
        return None

    @staticmethod
    async def save_cached_response(
        cache_key: str,
        url: str,
        body: str,
        status_code: int = 200,
        headers: Optional[Dict[str, Any]] = None,
        ttl_hours: int = 24,
    ) -> None:
        """Stores response in cache with TTL."""
        if not settings.CACHE_ENABLED:
            return
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=ttl_hours)
        async with get_db() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO source_cache (cache_key, url, response_body, status_code, headers_json, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    url,
                    body,
                    status_code,
                    json.dumps(headers or {}),
                    now.isoformat(),
                    expires.isoformat(),
                ),
            )
            await db.commit()

    @staticmethod
    async def save_research_run(run: ResearchRun) -> None:
        """Persists or updates a research run log."""
        async with get_db() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO research_runs (
                    run_id, org_number, started_at, completed_at, status,
                    sources_attempted_json, sources_successful_json, facts_found, facts_verified,
                    outbound_requests_count, estimated_cost_usd, latency_ms, warnings_json, errors_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.organization_number,
                    run.started_at,
                    run.completed_at,
                    run.status.value,
                    json.dumps(run.sources_attempted),
                    json.dumps(run.sources_successful),
                    run.facts_found,
                    run.facts_verified,
                    run.outbound_requests_count,
                    run.estimated_cost_usd,
                    run.latency_ms,
                    json.dumps(run.warnings),
                    json.dumps(run.errors),
                ),
            )
            await db.commit()

    @staticmethod
    async def get_research_run(run_id: str) -> Optional[ResearchRun]:
        """Fetches a research run by ID."""
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM research_runs WHERE run_id = ?", (run_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return ResearchRun(
                run_id=row["run_id"],
                organization_number=row["org_number"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                status=ResearchRunStatus(row["status"]),
                sources_attempted=json.loads(row["sources_attempted_json"] or "[]"),
                sources_successful=json.loads(row["sources_successful_json"] or "[]"),
                facts_found=row["facts_found"],
                facts_verified=row["facts_verified"],
                outbound_requests_count=row["outbound_requests_count"],
                estimated_cost_usd=row["estimated_cost_usd"],
                latency_ms=row["latency_ms"],
                warnings=json.loads(row["warnings_json"] or "[]"),
                errors=json.loads(row["errors_json"] or "[]"),
            )

    @staticmethod
    async def save_company_profile(profile: CompanyProfile) -> Dict[str, Any]:
        """
        Saves company, facts, evidence, people, financials, and creates historical snapshot with diff.
        """
        org_nr = profile.organization_number
        now_iso = datetime.now(timezone.utc).isoformat()
        ident = profile.canonical_identity

        async with get_db() as db:
            # 1. Upsert Company
            await db.execute(
                """
                INSERT INTO companies (
                    org_number, legal_name, org_form, org_form_description, registration_status,
                    is_active, address, postal_code, city, municipality, municipality_number,
                    country, industry_code, industry_description, registration_date, founding_date,
                    website, source, source_url, raw_identity_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(org_number) DO UPDATE SET
                    legal_name=excluded.legal_name,
                    org_form=excluded.org_form,
                    org_form_description=excluded.org_form_description,
                    registration_status=excluded.registration_status,
                    is_active=excluded.is_active,
                    address=excluded.address,
                    postal_code=excluded.postal_code,
                    city=excluded.city,
                    municipality=excluded.municipality,
                    municipality_number=excluded.municipality_number,
                    country=excluded.country,
                    industry_code=excluded.industry_code,
                    industry_description=excluded.industry_description,
                    registration_date=excluded.registration_date,
                    founding_date=excluded.founding_date,
                    website=excluded.website,
                    source=excluded.source,
                    source_url=excluded.source_url,
                    raw_identity_json=excluded.raw_identity_json,
                    updated_at=excluded.updated_at
                """,
                (
                    org_nr,
                    ident.legal_name,
                    ident.organization_form,
                    ident.organization_form_description,
                    ident.registration_status,
                    1 if ident.is_active else 0,
                    ident.registered_address,
                    ident.postal_code,
                    ident.city,
                    ident.municipality,
                    ident.municipality_number,
                    ident.country,
                    ident.industry_code,
                    ident.industry_description,
                    ident.registration_date,
                    ident.founding_date,
                    ident.website,
                    ident.source,
                    ident.source_url,
                    ident.model_dump_json(),
                    now_iso,
                    now_iso,
                ),
            )

            # 2. Refresh Facts
            await db.execute("DELETE FROM facts WHERE org_number = ?", (org_nr,))
            for f in profile.facts:
                fact_id = f"f_{uuid.uuid4().hex[:12]}"
                await db.execute(
                    """
                    INSERT INTO facts (
                        id, org_number, field, value, normalized_value, source_url,
                        source_title, retrieved_at, effective_date, reporting_period,
                        confidence, verification_status, evidence_excerpt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fact_id,
                        org_nr,
                        f.field,
                        str(f.value),
                        str(f.normalized_value) if f.normalized_value is not None else None,
                        f.source_url,
                        f.source_title,
                        f.retrieved_at,
                        f.effective_date,
                        f.reporting_period,
                        f.confidence,
                        f.verification_status.value,
                        f.evidence_excerpt,
                    ),
                )

            # 3. Refresh Evidence
            await db.execute("DELETE FROM evidence WHERE org_number = ?", (org_nr,))
            for ev in profile.evidence:
                await db.execute(
                    """
                    INSERT INTO evidence (
                        id, org_number, source_url, source_title, publisher_domain,
                        retrieval_timestamp, publication_date, evidence_excerpt,
                        supported_fields_json, source_priority, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ev.id,
                        org_nr,
                        ev.source_url,
                        ev.source_title,
                        ev.publisher_domain,
                        ev.retrieval_timestamp,
                        ev.publication_date,
                        ev.evidence_excerpt,
                        json.dumps(ev.supported_fields),
                        ev.source_priority,
                        ev.content_hash,
                    ),
                )

            # 4. Refresh People
            await db.execute("DELETE FROM people WHERE org_number = ?", (org_nr,))
            for p in profile.leadership:
                pid = f"p_{uuid.uuid4().hex[:12]}"
                await db.execute(
                    """
                    INSERT INTO people (
                        id, org_number, name, role, role_code, birth_year,
                        effective_date, source_url, verification_status, evidence_excerpt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid,
                        org_nr,
                        p.name,
                        p.role,
                        p.role_code,
                        p.birth_year,
                        p.effective_date,
                        p.source_url,
                        p.verification_status.value,
                        p.evidence_excerpt,
                    ),
                )

            # 5. Refresh Financials
            await db.execute("DELETE FROM financials WHERE org_number = ?", (org_nr,))
            for fin in profile.financials:
                fid = f"fin_{uuid.uuid4().hex[:12]}"
                await db.execute(
                    """
                    INSERT INTO financials (
                        id, org_number, reporting_year, currency, revenue,
                        operating_result, profit_loss, total_assets, equity,
                        source, source_url, verification_status, evidence_excerpt
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fid,
                        org_nr,
                        fin.reporting_year,
                        fin.currency,
                        fin.revenue,
                        fin.operating_result,
                        fin.profit_loss,
                        fin.total_assets,
                        fin.equity,
                        fin.source,
                        fin.source_url,
                        fin.verification_status.value,
                        fin.evidence_excerpt,
                    ),
                )

            # 6. Refresh Activities
            await db.execute("DELETE FROM activities WHERE org_number = ?", (org_nr,))
            for act in profile.activities:
                aid = f"act_{uuid.uuid4().hex[:12]}"
                await db.execute(
                    """
                    INSERT INTO activities (id, org_number, title, date, summary, activity_type, source_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (aid, org_nr, act.title, act.date, act.summary, act.activity_type, act.source_url),
                )

            # 7. Historical Snapshot & Diff Tracking
            cursor = await db.execute(
                "SELECT profile_json FROM company_snapshots WHERE org_number = ? ORDER BY snapshot_timestamp DESC LIMIT 1",
                (org_nr,),
            )
            last_snapshot_row = await cursor.fetchone()
            changes = {"has_changes": False}
            if last_snapshot_row:
                try:
                    old_data = json.loads(last_snapshot_row["profile_json"])
                    changes = detect_changes_between_snapshots(old_data, profile.model_dump())
                except Exception:
                    pass

            content_hash = compute_profile_hash(profile)
            snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
            await db.execute(
                """
                INSERT INTO company_snapshots (id, org_number, snapshot_timestamp, profile_json, content_hash)
                VALUES (?, ?, ?, ?, ?)
                """,
                (snapshot_id, org_nr, now_iso, profile.model_dump_json(), content_hash),
            )

            await db.commit()

        return changes

    @staticmethod
    async def get_company_profile(org_number: str) -> Optional[CompanyProfile]:
        """Reconstructs complete CompanyProfile from database."""
        async with get_db() as db:
            # 1. Company Identity
            cursor = await db.execute("SELECT * FROM companies WHERE org_number = ?", (org_number,))
            comp_row = await cursor.fetchone()
            if not comp_row:
                return None

            ident_data = json.loads(comp_row["raw_identity_json"])
            canonical_identity = CompanyIdentity(**ident_data)

            # 2. Facts
            cursor = await db.execute("SELECT * FROM facts WHERE org_number = ?", (org_number,))
            fact_rows = await cursor.fetchall()
            facts = [
                Fact(
                    field=r["field"],
                    value=r["value"],
                    normalized_value=r["normalized_value"],
                    source_url=r["source_url"],
                    source_title=r["source_title"],
                    retrieved_at=r["retrieved_at"],
                    effective_date=r["effective_date"],
                    reporting_period=r["reporting_period"],
                    confidence=r["confidence"],
                    verification_status=VerificationStatus(r["verification_status"]),
                    evidence_excerpt=r["evidence_excerpt"],
                )
                for r in fact_rows
            ]

            # 3. Evidence
            cursor = await db.execute("SELECT * FROM evidence WHERE org_number = ?", (org_number,))
            ev_rows = await cursor.fetchall()
            evidence = [
                EvidenceRecord(
                    id=r["id"],
                    source_url=r["source_url"],
                    source_title=r["source_title"],
                    publisher_domain=r["publisher_domain"],
                    retrieval_timestamp=r["retrieval_timestamp"],
                    publication_date=r["publication_date"],
                    evidence_excerpt=r["evidence_excerpt"],
                    supported_fields=json.loads(r["supported_fields_json"] or "[]"),
                    source_priority=r["source_priority"],
                    content_hash=r["content_hash"],
                )
                for r in ev_rows
            ]

            # 4. People
            cursor = await db.execute("SELECT * FROM people WHERE org_number = ?", (org_number,))
            people_rows = await cursor.fetchall()
            leadership = [
                PersonRole(
                    name=r["name"],
                    role=r["role"],
                    role_code=r["role_code"],
                    birth_year=r["birth_year"],
                    effective_date=r["effective_date"],
                    source_url=r["source_url"],
                    verification_status=VerificationStatus(r["verification_status"]),
                    evidence_excerpt=r["evidence_excerpt"],
                )
                for r in people_rows
            ]

            # 5. Financials
            cursor = await db.execute(
                "SELECT * FROM financials WHERE org_number = ? ORDER BY reporting_year DESC",
                (org_number,),
            )
            fin_rows = await cursor.fetchall()
            financials = [
                FinancialRecord(
                    reporting_year=r["reporting_year"],
                    currency=r["currency"],
                    revenue=r["revenue"],
                    operating_result=r["operating_result"],
                    profit_loss=r["profit_loss"],
                    total_assets=r["total_assets"],
                    equity=r["equity"],
                    source=r["source"],
                    source_url=r["source_url"],
                    verification_status=VerificationStatus(r["verification_status"]),
                    evidence_excerpt=r["evidence_excerpt"],
                )
                for r in fin_rows
            ]

            # 6. Activities
            cursor = await db.execute(
                "SELECT * FROM activities WHERE org_number = ? ORDER BY date DESC",
                (org_number,),
            )
            act_rows = await cursor.fetchall()
            activities = [
                CompanyActivity(
                    title=r["title"],
                    date=r["date"],
                    summary=r["summary"],
                    activity_type=r["activity_type"],
                    source_url=r["source_url"],
                )
                for r in act_rows
            ]

            # 7. Overview reconstruct from facts / identity
            desc_fact = next((f for f in facts if f.field == "business_description"), None)
            overview = CompanyOverview(
                business_description=desc_fact.value if desc_fact else comp_row["industry_description"],
                products_services=[],
                sectors=[comp_row["industry_description"]] if comp_row["industry_description"] else [],
                locations=[comp_row["city"]] if comp_row["city"] else [],
                description_source_url=desc_fact.source_url if desc_fact else comp_row["source_url"],
                verification_status=desc_fact.verification_status if desc_fact else VerificationStatus.PROBABLE,
            )

            return CompanyProfile(
                organization_number=org_number,
                canonical_identity=canonical_identity,
                overview=overview,
                leadership=leadership,
                financials=financials,
                activities=activities,
                facts=facts,
                evidence=evidence,
                last_researched=comp_row["updated_at"],
                research_status=ResearchRunStatus.COMPLETED,
            )

    @staticmethod
    async def get_snapshots_history(org_number: str) -> List[Dict[str, Any]]:
        """Retrieves list of snapshots with diffs for historical review."""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT id, snapshot_timestamp, profile_json, content_hash FROM company_snapshots WHERE org_number = ? ORDER BY snapshot_timestamp DESC",
                (org_number,),
            )
            rows = await cursor.fetchall()
            snapshots = []
            for r in rows:
                snapshots.append({
                    "id": r["id"],
                    "timestamp": r["snapshot_timestamp"],
                    "content_hash": r["content_hash"],
                    "profile": json.loads(r["profile_json"]),
                })
            return snapshots

    @staticmethod
    async def get_all_companies(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List summary of all cached companies in database."""
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT org_number, legal_name, org_form, registration_status, city, industry_description, updated_at
                FROM companies ORDER BY updated_at DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
