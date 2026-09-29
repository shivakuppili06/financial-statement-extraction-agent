import os
import yaml
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "thresholds.yaml")

def load_thresholds():
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load thresholds config: {e}")
        return {}

def _val(line_items, key):
    item = line_items.get(key) or {}
    return item.get("value")

def calculate_and_check_ratios(line_items: dict) -> list[dict]:
    flags = []
    config = load_thresholds()
    ratios_cfg = config.get("ratios", {})

    # Current Ratio
    current_assets = _val(line_items, "current_assets")
    current_liabilities = _val(line_items, "current_liabilities")
    if current_assets and current_liabilities and current_liabilities > 0:
        cr = current_assets / current_liabilities
        cfg = ratios_cfg.get("current_ratio", {})
        if "min" in cfg and cr < cfg["min"]:
            flags.append({"check": "current_ratio", "severity": "medium", "message": f"Current Ratio ({cr:.2f}) below minimum {cfg['min']}"})
        if "max" in cfg and cr > cfg["max"]:
            flags.append({"check": "current_ratio", "severity": "medium", "message": f"Current Ratio ({cr:.2f}) above maximum {cfg['max']}"})

    # Debt to Equity
    total_debt = _val(line_items, "total_debt")
    total_equity = _val(line_items, "total_equity")
    if total_debt is not None and total_equity and total_equity > 0:
        de = total_debt / total_equity
        cfg = ratios_cfg.get("debt_to_equity", {})
        if "min" in cfg and de < cfg["min"]:
            flags.append({"check": "debt_to_equity", "severity": "medium", "message": f"Debt to Equity ({de:.2f}) below minimum {cfg['min']}"})
        if "max" in cfg and de > cfg["max"]:
            flags.append({"check": "debt_to_equity", "severity": "medium", "message": f"Debt to Equity ({de:.2f}) above maximum {cfg['max']}"})

    # Interest Coverage
    ebitda = _val(line_items, "ebitda")
    interest = _val(line_items, "interest_expense")
    if ebitda is not None and interest and interest > 0:
        ic = ebitda / interest
        cfg = ratios_cfg.get("interest_coverage", {})
        if "min" in cfg and ic < cfg["min"]:
            flags.append({"check": "interest_coverage", "severity": "medium", "message": f"Interest Coverage ({ic:.2f}) below minimum {cfg['min']}"})
        if "max" in cfg and ic > cfg["max"]:
            flags.append({"check": "interest_coverage", "severity": "medium", "message": f"Interest Coverage ({ic:.2f}) above maximum {cfg['max']}"})

    # ROE
    net_income = _val(line_items, "net_income")
    if net_income is not None and total_equity and total_equity > 0:
        roe = (net_income / total_equity) * 100
        cfg = ratios_cfg.get("roe", {})
        if "min" in cfg and roe < cfg["min"]:
            flags.append({"check": "roe", "severity": "medium", "message": f"ROE ({roe:.2f}%) below minimum {cfg['min']}%"})
        if "max" in cfg and roe > cfg["max"]:
            flags.append({"check": "roe", "severity": "medium", "message": f"ROE ({roe:.2f}%) above maximum {cfg['max']}%"})

    return flags
