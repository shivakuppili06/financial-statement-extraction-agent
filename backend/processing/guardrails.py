"""
guardrails.py
This is the part of the project that actually matters for the pitch:
"a banker will stake their name on its output" means the system needs
to catch its OWN mistakes, not just trust the LLM.

Each check below returns a flag dict if something looks off.
Start with these three, then add more (see README "Ideas to extend").
"""

import os
import sys

# Optional integration with ratio module
try:
    from processing.ratios import calculate_and_check_ratios
except ImportError:
    # Handle if run outside package
    def calculate_and_check_ratios(line_items): return []

TOLERANCE = 0.02  # 2% slack for rounding in reported financials


def _val(line_items, key):
    item = line_items.get(key) or {}
    return item.get("value")


def check_balance_sheet_balances(line_items: dict) -> dict | None:
    """Assets should ~= Liabilities + Equity."""
    assets = _val(line_items, "total_assets")
    liabilities = _val(line_items, "total_liabilities")
    equity = _val(line_items, "total_equity")

    if None in (assets, liabilities, equity):
        return None  # can't check what wasn't extracted

    expected = liabilities + equity
    diff_pct = abs(assets - expected) / max(abs(expected), 1)

    if diff_pct > TOLERANCE:
        return {
            "check": "balance_sheet_balances",
            "severity": "high",
            "message": (
                f"Assets ({assets:,.0f}) does not equal Liabilities + Equity "
                f"({expected:,.0f}). Off by {diff_pct*100:.1f}%."
            ),
        }
    return None


def check_low_confidence_fields(line_items: dict, threshold: float = 0.5) -> list[dict]:
    """Flag any extracted field the model itself wasn't confident about or failed to extract."""
    flags = []
    for key, item in line_items.items():
        conf = (item or {}).get("confidence", 0)
        val = (item or {}).get("value")
        if val is None or conf < threshold:
            flags.append({
                "check": "low_confidence_extraction",
                "severity": "medium" if val is not None else "high",
                "message": f"'{key}' missing or extracted with low confidence ({conf}). Verify manually.",
            })
    return flags


def check_ebitda_consistency(line_items: dict) -> dict | None:
    """Rough sanity check: EBITDA shouldn't wildly exceed revenue."""
    revenue = _val(line_items, "total_revenue")
    ebitda = _val(line_items, "ebitda")

    if None in (revenue, ebitda):
        return None

    if ebitda > revenue:
        return {
            "check": "ebitda_exceeds_revenue",
            "severity": "high",
            "message": f"EBITDA ({ebitda:,.0f}) exceeds total revenue ({revenue:,.0f}) — likely an extraction error.",
        }
    return None


def check_unit_currency_anomaly(line_items: dict) -> list[dict]:
    """Flags values that look off by a factor of ~1,000 (e.g., ₹Crore vs ₹Lakh unit confusion).
    If revenue and expenses differ in order of magnitude by ~100x-10000x, flag as unit error.
    """
    flags = []
    revenue = _val(line_items, "total_revenue")
    expenses = _val(line_items, "total_expenses")

    if revenue and expenses and revenue > 0 and expenses > 0:
        ratio = revenue / expenses if revenue > expenses else expenses / revenue
        if 500 <= ratio <= 5000:
            flags.append({
                "check": "unit_currency_anomaly",
                "severity": "high",
                "message": (
                    f"Possible unit/currency confusion (e.g. ₹Crore vs ₹Lakh). "
                    f"Ratio between Revenue ({revenue:,.0f}) and Expenses ({expenses:,.0f}) is off by a factor of ~{ratio:.0f}x."
                ),
            })
    return flags


def check_source_snippet_consistency(line_items: dict) -> list[dict]:
    """Self-consistency check: confirms each source_snippet plausibly contains the extracted value."""
    flags = []
    for key, item in line_items.items():
        val = item.get("value")
        snippet = item.get("source_snippet") or ""

        if val is not None and snippet:
            # Clean non-digits from integer portion for substring search
            val_str = str(int(val)) if isinstance(val, (int, float)) else str(val)
            cleaned_snippet = "".join(c for c in snippet if c.isdigit() or c == ".")

            if val_str not in snippet and val_str not in cleaned_snippet:
                flags.append({
                    "check": "source_snippet_unmatched",
                    "severity": "medium",
                    "message": (
                        f"Field '{key}' value ({val}) was not found literally within its quote "
                        f"source_snippet ('{snippet}'). Verify hallucination or unit scaling."
                    ),
                })
    return flags


def check_retained_earnings_consistency(line_items: dict) -> dict | None:
    """Net income should roughly equal the change in retained earnings (minus dividends, which we might ignore here)."""
    net_income = _val(line_items, "net_income")
    re_start = _val(line_items, "retained_earnings_start")
    re_end = _val(line_items, "retained_earnings_end")
    if None not in (net_income, re_start, re_end):
        expected_change = net_income
        actual_change = re_end - re_start
        diff_pct = abs(expected_change - actual_change) / max(abs(expected_change), 1)
        if diff_pct > 0.1: # Allow larger tolerance for dividends
            return {
                "check": "retained_earnings_consistency",
                "severity": "medium",
                "message": f"Net Income ({net_income:,.0f}) does not match Retained Earnings change ({actual_change:,.0f}). Check for dividends or errors."
            }
    return None

def check_cash_flow_balance(line_items: dict) -> dict | None:
    """Ending cash from CF statement should equal cash on Balance Sheet."""
    cf_cash = _val(line_items, "cash_end_cf")
    bs_cash = _val(line_items, "cash_and_equivalents")
    if None not in (cf_cash, bs_cash):
        if cf_cash != bs_cash:
            return {
                "check": "cash_flow_consistency",
                "severity": "high",
                "message": f"CF Ending Cash ({cf_cash:,.0f}) != BS Cash ({bs_cash:,.0f})."
            }
    return None

def check_debt_interest_consistency(line_items: dict) -> dict | None:
    """Interest expense should be > 0 if total debt > 0."""
    debt = _val(line_items, "total_debt")
    interest = _val(line_items, "interest_expense")
    if None not in (debt, interest):
        if debt > 0 and interest == 0:
            return {
                "check": "debt_interest_consistency",
                "severity": "medium",
                "message": "Company reports debt but zero interest expense."
            }
    return None

def check_extraction_completeness(line_items: dict) -> dict | None:
    """If most fields failed to extract, don't let the system claim 'clean'."""
    total = len(line_items)
    if total == 0:
        return None
    missing = sum(1 for item in line_items.values() if (item or {}).get("value") is None)
    if missing >= total * 0.5:
        return {
            "check": "extraction_incomplete",
            "severity": "high",
            "message": f"{missing}/{total} fields could not be extracted. Results are unreliable.",
        }
    return None


def run_all_checks(extraction_result: dict) -> list[dict]:
    line_items = extraction_result.get("line_items", {})
    flags = []

    for check_fn in (
        check_balance_sheet_balances, 
        check_ebitda_consistency, 
        check_extraction_completeness,
        check_retained_earnings_consistency,
        check_cash_flow_balance,
        check_debt_interest_consistency
    ):
        result = check_fn(line_items)
        if result:
            flags.append(result)

    flags.extend(check_low_confidence_fields(line_items))
    flags.extend(check_unit_currency_anomaly(line_items))
    flags.extend(check_source_snippet_consistency(line_items))
    flags.extend(calculate_and_check_ratios(line_items))
    return flags
