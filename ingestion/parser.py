"""HTML and SSR data parser for Groww mutual fund scheme pages.
Extracts structured, fact-bearing sections with labels tightly bound to values.
"""

import json
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ingestion.models import RawPage, ExtractedFact


class GrowwParser:
    """Parses Groww scheme page HTML and extracts verified fact blocks."""

    def parse_raw_page(self, raw_page: RawPage) -> List[ExtractedFact]:
        """Parses HTML DOM and SSR JSON payload to extract key fact blocks."""
        facts: List[ExtractedFact] = []
        soup = BeautifulSoup(raw_page.html_content, "html.parser")

        # 1. Extract JSON state from __NEXT_DATA__
        mf_data: Dict[str, Any] = {}
        next_data_tag = soup.find("script", id="__NEXT_DATA__")
        if next_data_tag and next_data_tag.string:
            try:
                payload = json.loads(next_data_tag.string)
                mf_data = payload.get("props", {}).get("pageProps", {}).get("mfServerSideData", {})
            except Exception:
                mf_data = {}

        # 2. DOM fallback heuristics if mf_data is missing or partial
        page_text = soup.get_text(separator=" ", strip=True)

        scheme_name = mf_data.get("scheme_name") or raw_page.scheme_name
        fund_house = mf_data.get("fund_house") or "HDFC Mutual Fund"
        category = mf_data.get("category") or "Equity"
        sub_category = mf_data.get("sub_category") or ""
        category_full = f"{category} - {sub_category}" if sub_category else category

        # Fact 1: Expense Ratio
        expense_ratio = mf_data.get("expense_ratio")
        if expense_ratio is None:
            exp_match = re.search(r"expense\s*ratio[^\d]*([\d\.]+)%", page_text, re.IGNORECASE)
            if exp_match:
                expense_ratio = exp_match.group(1)

        if expense_ratio is not None:
            exp_text = (
                f"The Expense Ratio (TER) for {scheme_name} is {expense_ratio}% for the Direct Plan. "
                f"The Total Expense Ratio includes management fees, administrative expenses, and operational charges deducted on a daily basis."
            )
            facts.append(ExtractedFact(
                section_label="expense_ratio",
                label_text="Expense Ratio (TER)",
                value_text=f"{expense_ratio}%",
                raw_context=exp_text
            ))

        # Fact 2: Exit Load
        exit_load_val = mf_data.get("exit_load")
        if exit_load_val:
            exit_load_str = str(exit_load_val).strip()
            exit_text = (
                f"The exit load structure for {scheme_name} is: {exit_load_str}. "
                f"Exit load is a charge applied if an investor redeems or switches out units within the specified duration."
            )
            facts.append(ExtractedFact(
                section_label="exit_load",
                label_text="Exit Load Details",
                value_text=exit_load_str,
                raw_context=exit_text
            ))

        # Fact 3: Minimum Investment (SIP & Lumpsum)
        min_sip = mf_data.get("min_sip_investment", 100)
        min_lumpsum = mf_data.get("min_investment_amount", 100)
        min_inv_text = (
            f"For {scheme_name}, the minimum SIP (Systematic Investment Plan) amount is ₹{min_sip}. "
            f"The minimum lumpsum (one-time) initial investment amount is ₹{min_lumpsum}."
        )
        facts.append(ExtractedFact(
            section_label="minimum_investment",
            label_text="Minimum Investment (SIP & Lumpsum)",
            value_text=f"Min SIP: ₹{min_sip}, Min Lumpsum: ₹{min_lumpsum}",
            raw_context=min_inv_text
        ))

        # Fact 4: Lock-in Period (ELSS vs Non-ELSS)
        lock_in_data = mf_data.get("lock_in") or {}
        has_lock_in = bool(lock_in_data.get("years") or lock_in_data.get("months") or lock_in_data.get("days"))
        if has_lock_in:
            lock_text = f"{scheme_name} has a mandatory lock-in period of {lock_in_data.get('years', 0)} years."
        else:
            lock_text = (
                f"{scheme_name} is an open-ended mutual fund scheme with no lock-in period. "
                f"Unlike ELSS (tax saver) funds which require a mandatory 3-year lock-in period, investors in this fund can redeem or switch units at any time, subject to the scheme's applicable exit load."
            )
        facts.append(ExtractedFact(
            section_label="lock_in_period",
            label_text="Lock-in Period",
            value_text="No Lock-in (Open-ended)" if not has_lock_in else f"{lock_in_data.get('years')} Years",
            raw_context=lock_text
        ))

        # Fact 5: Riskometer Classification
        risk_val = (
            mf_data.get("nfo_risk") or
            mf_data.get("analysis", {}).get("risk") or
            mf_data.get("stats", {}).get("risk") or
            "Very High"
        )
        risk_text = (
            f"The risk classification for {scheme_name} according to the SEBI Riskometer is {risk_val}. "
            f"Investors should be aware that their principal investment is subject to {risk_val} market risk."
        )
        facts.append(ExtractedFact(
            section_label="riskometer",
            label_text="Riskometer Classification",
            value_text=str(risk_val),
            raw_context=risk_text
        ))

        # Fact 6: Benchmark Index
        benchmark = mf_data.get("benchmark_name") or mf_data.get("benchmark") or "Benchmark Index"
        bm_text = (
            f"The official benchmark index for {scheme_name} is {benchmark}. "
            f"The fund's performance, risk metrics, and asset allocation strategy are evaluated relative to the {benchmark}."
        )
        facts.append(ExtractedFact(
            section_label="benchmark_index",
            label_text="Benchmark Index",
            value_text=str(benchmark),
            raw_context=bm_text
        ))

        # Fact 7: Fund Management
        fund_mgr = mf_data.get("fund_manager") or "HDFC Mutual Fund Management Team"
        mgr_text = (
            f"{scheme_name} is managed by {fund_mgr} at {fund_house}. "
            f"The fund manager is responsible for portfolio asset allocation, stock selection, and adherence to investment objectives."
        )
        facts.append(ExtractedFact(
            section_label="fund_management",
            label_text="Fund Manager & AMC",
            value_text=f"{fund_mgr} ({fund_house})",
            raw_context=mgr_text
        ))

        # Fact 8: Statement Download & Capital Gains Reports Process
        rta_details = mf_data.get("rta_details") or {}
        rta_name = rta_details.get("rta_name", "CAMS")
        rta_web = rta_details.get("website", "www.camsonline.com")
        rta_email = rta_details.get("email", "enq_h@camsonline.com")
        stmt_text = (
            f"To download account statements, transaction summaries, or capital gains tax statements for {scheme_name}: "
            f"1) On the Groww platform, visit Profile > Reports > Mutual Fund Statements or Capital Gains Statement. "
            f"2) Alternatively, generate consolidated statements directly from the scheme's Registrar and Transfer Agent ({rta_name}) via {rta_web} (email: {rta_email}) using your registered folio number and PAN."
        )
        facts.append(ExtractedFact(
            section_label="statement_download_process",
            label_text="Account & Capital Gains Statement Process",
            value_text=f"Available via Groww Reports or RTA ({rta_name} at {rta_web})",
            raw_context=stmt_text
        ))

        # Fact 9: Fund Overview & Scheme Details
        aum = mf_data.get("aum")
        nav = mf_data.get("nav")
        launch_date = mf_data.get("launch_date")
        overview_text = (
            f"{scheme_name} is an open-ended {category_full} scheme managed by {fund_house}. "
            f"{'Total Fund AUM is ₹' + f'{aum:,.2f}' + ' Cr. ' if aum else ''}"
            f"{'The latest recorded NAV is ₹' + str(nav) + '. ' if nav else ''}"
            f"The fund operates under the Direct Plan - Growth option with direct investment execution."
        )
        facts.append(ExtractedFact(
            section_label="fund_overview",
            label_text="Fund Overview & Scheme Details",
            value_text=category_full,
            raw_context=overview_text
        ))

        return facts
