import re
import logging

logger = logging.getLogger(__name__)

# Currency conversion rates for demonstration
# In production, these should be pulled from a live FX API
FX_RATES = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.25,
    "INR": 0.012
}

def normalize_units_and_currency(value_str: str, target_currency: str = "USD") -> float:
    """
    Normalizes numeric strings containing units (Cr, Lakh, K, M, B) 
    and currencies ($, €, ₹) into a standard float value in the target currency.
    """
    if not value_str or not isinstance(value_str, str):
        return value_str
        
    value_str = value_str.upper().replace(",", "").strip()
    
    # 1. Extract numeric part
    numeric_match = re.search(r"[-+]?[0-9]*\.?[0-9]+", value_str)
    if not numeric_match:
        return 0.0
    
    numeric_val = float(numeric_match.group())
    
    # 2. Apply unit multipliers
    if "CR" in value_str or "CRORE" in value_str:
        numeric_val *= 10_000_000
    elif "LAKH" in value_str:
        numeric_val *= 100_000
    elif "B" in value_str or "BILLION" in value_str:
        numeric_val *= 1_000_000_000
    elif "M" in value_str or "MILLION" in value_str:
        numeric_val *= 1_000_000
    elif "K" in value_str or "THOUSAND" in value_str:
        numeric_val *= 1_000
        
    # 3. Apply FX conversion
    base_currency = "USD"
    if "₹" in value_str or "INR" in value_str or "RS" in value_str:
        base_currency = "INR"
    elif "€" in value_str or "EUR" in value_str:
        base_currency = "EUR"
    elif "£" in value_str or "GBP" in value_str:
        base_currency = "GBP"
        
    if base_currency != target_currency:
        numeric_val = numeric_val * FX_RATES.get(base_currency, 1.0) / FX_RATES.get(target_currency, 1.0)
        
    return numeric_val
