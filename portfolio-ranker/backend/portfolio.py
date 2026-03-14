"""
Portfolio management and validation module.
"""


def validate_portfolio_input(data):
    """
    Validate portfolio submission payload.
    Returns (is_valid, error_message).
    """
    if not data or not isinstance(data, dict):
        return False, "Invalid JSON payload"

    portfolio = data.get("portfolio")
    years = data.get("years")
    dividends = data.get("dividends")

    if not isinstance(portfolio, list) or len(portfolio) == 0:
        return False, "portfolio must be a non-empty list"

    weight_sum = 0.0
    for i, item in enumerate(portfolio):
        if not isinstance(item, dict):
            return False, f"portfolio[{i}] must be an object"
        ticker = item.get("ticker")
        weight = item.get("weight")
        if not ticker or not isinstance(ticker, str) or not ticker.strip():
            return False, "each item must have a non-empty ticker string"
        if weight is None or not isinstance(weight, (int, float)):
            return False, "each item must have a numeric weight"
        if weight < 0:
            return False, "weights must be non-negative"
        weight_sum += float(weight)

    if abs(weight_sum - 1.0) > 0.001:
        return False, "weights must sum to 1.0"

    if years not in (5, 10):
        return False, "years must be 5 or 10"

    if not isinstance(dividends, bool):
        return False, "dividends must be a boolean"

    return True, None
