"""
Portfolio management and validation module.
"""

import pandas as pd
from typing import cast

from data_fetcher import fetch_asset_data, infer_currency


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
    initial_value = data.get("initial_value", 10000.0)

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

    if years not in (1, 5, 10):
        return False, "years must be 1, 5, or 10"

    if not isinstance(dividends, bool):
        return False, "dividends must be a boolean"

    if initial_value is None or not isinstance(initial_value, (int, float)) or float(initial_value) <= 0:
        return False, "initial_value must be a positive number"

    return True, None


def _asset_returns_on_calendar(df: pd.DataFrame, dates: pd.DatetimeIndex, include_dividends: bool) -> pd.Series:
    """Forward-fill prices on union calendar, then compute daily returns."""
    aligned = df.set_index("date").reindex(dates).sort_index()
    price = cast(pd.Series, aligned["price"]).ffill()
    div = cast(pd.Series, aligned["dividend"]).fillna(0.0)

    if include_dividends:
        total = price + div
        ret = total / total.shift(1) - 1
    else:
        ret = price.pct_change()

    return cast(pd.Series, ret).fillna(0.0)


def simulate_portfolio(portfolio, years, include_dividends=True, initial_value=10000.0):
    """
    Simulate portfolio performance over time.
    Uses union of all asset trading dates with forward-filled prices (multi-exchange safe).
    Returns (DataFrame, coverage_info).
    """
    asset_frames = []
    coverage_by_ticker = {}
    warnings = []

    for item in portfolio:
        ticker = item["ticker"]
        weight = item["weight"]
        df = fetch_asset_data(ticker, years)
        if df.empty:
            warnings.append(f"{ticker}: no price history returned.")
            continue

        date_series = cast(pd.Series, df["date"])
        first_date = pd.to_datetime(date_series.iloc[0]).tz_localize(None)
        coverage_by_ticker[ticker] = first_date.strftime("%Y-%m-%d")

        native = infer_currency(ticker)
        if native != "USD":
            warnings.append(f"{ticker}: converted from {native} to USD using FX rates.")

        asset_frames.append((df, weight, ticker))

    if not asset_frames:
        return pd.DataFrame(columns=["date", "portfolio_value"]), {"history_warnings": warnings}

    all_dates = pd.DatetimeIndex(sorted(set().union(*[set(cast(pd.Series, f[0]["date"])) for f in asset_frames])))

    weighted_returns = pd.Series(0.0, index=all_dates)
    for df, weight, _ticker in asset_frames:
        ret = _asset_returns_on_calendar(df, all_dates, include_dividends)
        weighted_returns = weighted_returns + weight * ret

    values = [float(initial_value)]
    for r in weighted_returns.iloc[1:]:
        values.append(values[-1] * (1 + float(r)))

    result = pd.DataFrame({
        "date": merged["date"].values,
        "portfolio_value": values,
    })
    requested_start = pd.Timestamp.now().normalize() - pd.DateOffset(years=years)
    for ticker, first_date_str in coverage_by_ticker.items():
        first_date = pd.to_datetime(first_date_str)
        if first_date > requested_start:
            warnings.append(
                f"{ticker} data starts on {first_date_str}, so a full {years}-year backtest is not available."
            )

    return result, {"history_warnings": warnings}
