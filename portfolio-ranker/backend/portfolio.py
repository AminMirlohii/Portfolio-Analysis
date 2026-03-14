"""
Portfolio management and validation module.
"""

import pandas as pd

from data_fetcher import fetch_asset_data


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


def simulate_portfolio(portfolio, years):
    """
    Simulate portfolio performance over time.
    portfolio: list of {"ticker": str, "weight": float}
    years: 5 or 10
    Returns DataFrame with columns: date, portfolio_value
    """
    dfs = []
    for item in portfolio:
        ticker = item["ticker"]
        weight = item["weight"]
        df = fetch_asset_data(ticker, years)
        df = df.rename(columns={"price": f"{ticker}_price", "dividend": f"{ticker}_div"})
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        dfs.append((df, weight))

    if not dfs:
        return pd.DataFrame(columns=["date", "portfolio_value"])

    merged = dfs[0][0][["date"]]
    for df, _ in dfs:
        merged = merged.merge(df[["date", f"{df.columns[1]}", f"{df.columns[2]}"]], on="date", how="inner")
    merged = merged.sort_values("date").drop_duplicates(subset=["date"])

    weighted_returns = pd.Series(0.0, index=merged.index)
    for df, weight in dfs:
        ticker = [c.replace("_price", "") for c in df.columns if c.endswith("_price")][0]
        price_col = f"{ticker}_price"
        div_col = f"{ticker}_div"
        asset_df = merged[["date"]].merge(df, on="date", how="inner")
        if len(asset_df) < 2:
            continue
        total = asset_df[price_col] + asset_df[div_col]
        ret = total / total.shift(1) - 1
        ret = ret.reindex(merged.index).fillna(0)
        weighted_returns += weight * ret

    values = [10000.0]
    for r in weighted_returns.iloc[1:]:
        values.append(values[-1] * (1 + r))

    result = pd.DataFrame({
        "date": merged["date"].values,
        "portfolio_value": values,
    })
    return result
