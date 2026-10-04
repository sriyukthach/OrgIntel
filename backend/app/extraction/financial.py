"""
Financial Data Extraction Engine
Parses official annual accounts, Regnskapsregisteret responses, and financial metrics.
Never fabricates financial numbers.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.models import FinancialRecord, Fact, VerificationStatus


def extract_financials_from_regnskap(regnskap_data: List[Dict[str, Any]], source_url: str) -> List[FinancialRecord]:
    """
    Parses Brreg Regnskapsregisteret API records.
    Extracts revenue, operating result, net profit, total assets, equity.
    """
    records: List[FinancialRecord] = []
    if not isinstance(regnskap_data, list):
        if isinstance(regnskap_data, dict):
            regnskap_data = [regnskap_data]
        else:
            return records

    for item in regnskap_data:
        try:
            regnskapsperiode = item.get("regnskapsperiode", {})
            fra_dato = regnskapsperiode.get("fraDato", "")
            til_dato = regnskapsperiode.get("tilDato", "")
            year = int(til_dato[:4]) if til_dato and len(til_dato) >= 4 else None

            if not year and fra_dato and len(fra_dato) >= 4:
                year = int(fra_dato[:4])

            if not year:
                continue

            currency = item.get("valuta", "NOK")
            virksomhet = item.get("virksomhet", {})
            resultatregnskap = item.get("resultatregnskapResultat", {}) or {}
            balanse = item.get("egenkapitalGjeld", {}) or item.get("balanse", {}) or {}
            eiendeler = item.get("eiendeler", {}) or {}

            # Extract metrics
            driftsinntekter = resultatregnskap.get("driftsinntekter", {}).get("sumDriftsinntekter")
            driftsresultat = resultatregnskap.get("driftsresultat", {}).get("driftsresultat")
            aarsresultat = (
                resultatregnskap.get("aarsresultat", {}).get("aarsresultat")
                or resultatregnskap.get("ordinaertResultatEtterSkattekostnad")
            )
            sum_eiendeler = eiendeler.get("sumEiendeler") or eiendeler.get("sumEiendelerVerdi")
            sum_egenkapital = balanse.get("egenkapital", {}).get("sumEgenkapital") or balanse.get("sumEgenkapitalGjeld")

            # Clean and convert to floats
            revenue_val = float(driftsinntekter) if driftsinntekter is not None else None
            op_result_val = float(driftsresultat) if driftsresultat is not None else None
            profit_val = float(aarsresultat) if aarsresultat is not None else None
            assets_val = float(sum_eiendeler) if sum_eiendeler is not None else None
            equity_val = float(sum_egenkapital) if sum_egenkapital is not None else None

            excerpt = (
                f"Regnskapsregisteret {year}: Driftsinntekter={revenue_val or 'N/A'} {currency}, "
                f"Driftsresultat={op_result_val or 'N/A'}, Årsresultat={profit_val or 'N/A'}."
            )

            records.append(
                FinancialRecord(
                    reporting_year=year,
                    currency=currency,
                    revenue=revenue_val,
                    operating_result=op_result_val,
                    profit_loss=profit_val,
                    total_assets=assets_val,
                    equity=equity_val,
                    source="Brønnøysundregistrene - Regnskapsregisteret",
                    source_url=source_url,
                    verification_status=VerificationStatus.VERIFIED,
                    evidence_excerpt=excerpt,
                )
            )
        except Exception:
            continue

    # Sort descending by reporting year
    records.sort(key=lambda x: x.reporting_year, reverse=True)
    return records


def financials_to_facts(financials: List[FinancialRecord]) -> List[Fact]:
    """Generates verifiable facts from the most recent financial statement."""
    facts: List[Fact] = []
    if not financials:
        return facts

    latest = financials[0]
    period_str = f"FY{latest.reporting_year}"

    if latest.revenue is not None:
        facts.append(
            Fact(
                field="revenue",
                value=f"{latest.revenue:,.0f} {latest.currency}".replace(",", " "),
                normalized_value=latest.revenue,
                source_url=latest.source_url,
                source_title=f"Regnskapsregisteret - {period_str}",
                reporting_period=period_str,
                confidence=1.0,
                verification_status=latest.verification_status,
                evidence_excerpt=latest.evidence_excerpt or f"Inntekter for {period_str}: {latest.revenue} {latest.currency}",
            )
        )

    if latest.operating_result is not None:
        facts.append(
            Fact(
                field="operating_result",
                value=f"{latest.operating_result:,.0f} {latest.currency}".replace(",", " "),
                normalized_value=latest.operating_result,
                source_url=latest.source_url,
                source_title=f"Regnskapsregisteret - {period_str}",
                reporting_period=period_str,
                confidence=1.0,
                verification_status=latest.verification_status,
                evidence_excerpt=latest.evidence_excerpt or f"Driftsresultat for {period_str}: {latest.operating_result} {latest.currency}",
            )
        )

    if latest.profit_loss is not None:
        facts.append(
            Fact(
                field="profit_loss",
                value=f"{latest.profit_loss:,.0f} {latest.currency}".replace(",", " "),
                normalized_value=latest.profit_loss,
                source_url=latest.source_url,
                source_title=f"Regnskapsregisteret - {period_str}",
                reporting_period=period_str,
                confidence=1.0,
                verification_status=latest.verification_status,
                evidence_excerpt=latest.evidence_excerpt or f"Årsresultat for {period_str}: {latest.profit_loss} {latest.currency}",
            )
        )

    return facts
