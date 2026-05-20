"""
Data fetching module for market data.
"""

import pandas as pd
import yfinance as yf
from typing import cast


def infer_currency(ticker: str) -> str:
    """Infer listing currency from Yahoo suffix (best-effort)."""
    upper = ticker.upper()
    if upper.endswith(".TO") or upper.endswith(".V"):
        return "CAD"
    if upper.endswith(".L"):
        return "GBP"
    if upper.endswith(".AX"):
        return "AUD"
    if upper.endswith(".HK"):
        return "HKD"
    return "USD"


def fetch_asset_data(ticker, years):
    """
    Fetch OHLC history from Yahoo.
    - price: unadjusted close (price return when dividends off)
    - adj_price: adjusted close (total return with dividends reinvested; matches Yahoo)

    Returns columns: date, price, adj_price, currency
    """
    period = f"{years}y"
    hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if hist.empty:
        return pd.DataFrame(columns=["date", "price", "adj_price", "currency"])

    df = hist.reset_index()
    df = df.rename(columns={"Date": "date"})
    df["date"] = pd.to_datetime(cast(pd.Series, df["date"])).dt.tz_localize(None)
    df["price"] = cast(pd.Series, df["Close"]).astype(float)
    if "Adj Close" in df.columns:
        df["adj_price"] = cast(pd.Series, df["Adj Close"]).astype(float)
    else:
        df["adj_price"] = df["price"]
    df["currency"] = infer_currency(ticker)
    return df[["date", "price", "adj_price", "currency"]].copy()


def fetch_benchmark(years):
    """Fetch S&P 500 (SPY) benchmark data."""
    return fetch_asset_data("SPY", years)


def _daily_returns(df: pd.DataFrame, include_dividends: bool) -> pd.Series:
    """Daily simple returns from Yahoo-style series."""
    col = "adj_price" if include_dividends else "price"
    series = cast(pd.Series, df[col])
    return series.pct_change().fillna(0.0)


def simulate_benchmark(years, include_dividends=True, initial_value=10000.0):
    """Benchmark time series compounded from SPY returns."""
    benchmark_df = fetch_benchmark(years).copy()
    if benchmark_df.empty:
        return pd.DataFrame(columns=["date", "benchmark_value"])

    rets = _daily_returns(benchmark_df, include_dividends)
    benchmark_df["benchmark_value"] = float(initial_value) * (1.0 + rets).cumprod()
    out = benchmark_df[["date", "benchmark_value"]].copy()
    if len(out) > 0:
        end = pd.to_datetime(out["date"].max())
        start = end - pd.DateOffset(years=years)
        out = out[out["date"] >= start].copy()
        if len(out) > 0:
            base = float(out["benchmark_value"].iloc[0])
            if base > 0:
                out["benchmark_value"] = float(initial_value) * out["benchmark_value"] / base
    return out
