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


def _fx_pair_for_currency(currency: str) -> str | None:
    """Yahoo FX ticker quoting units of `currency` per 1 USD."""
    if currency == "USD":
        return None
    mapping = {
        "CAD": "USDCAD=X",
        "GBP": "USDGBP=X",
        "AUD": "USDAUD=X",
        "HKD": "USDHKD=X",
    }
    return mapping.get(currency)


def fetch_fx_to_usd(currency: str, years: int) -> pd.DataFrame:
    """
    Daily FX for converting local prices to USD.
    `fx` is units of local currency per 1 USD (e.g. USDCAD). USD price = local / fx.
    """
    if currency == "USD":
        return pd.DataFrame(columns=["date", "fx"])

    pair = _fx_pair_for_currency(currency)
    if pair is None:
        return pd.DataFrame(columns=["date", "fx"])

    hist = yf.Ticker(pair).history(period=f"{years}y")
    if hist.empty:
        return pd.DataFrame(columns=["date", "fx"])

    df = hist.reset_index()
    df = df.rename(columns={"Date": "date", "Close": "fx"})
    df["date"] = pd.to_datetime(cast(pd.Series, df["date"])).dt.tz_localize(None)
    df["fx"] = cast(pd.Series, df["fx"]).astype(float)
    return df[["date", "fx"]]


def fetch_asset_data(ticker, years, target_currency: str = "USD"):
    """
    Fetch historical prices and dividends for an asset.
    Non-US listings are converted to USD using Yahoo FX rates.
    Returns DataFrame with columns: date, price, dividend.
    """
    period = f"{years}y"
    hist = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if hist.empty:
        return pd.DataFrame(columns=["date", "price", "dividend"])

    df = hist.reset_index()
    df = df.rename(columns={"Date": "date"})
    df["date"] = pd.to_datetime(cast(pd.Series, df["date"])).dt.tz_localize(None)
    df["price"] = cast(pd.Series, df["Close"]).astype(float)
    if "Dividends" in df.columns:
        df["dividend"] = cast(pd.Series, df["Dividends"]).fillna(0.0).astype(float)
    else:
        df["dividend"] = 0.0

    df = df[["date", "price", "dividend"]]

    native = infer_currency(ticker)
    if target_currency == "USD" and native != "USD":
        fx_df = fetch_fx_to_usd(native, years)
        if not fx_df.empty:
            merged = df.merge(fx_df, on="date", how="left")
            fx_series = cast(pd.Series, merged["fx"]).ffill().bfill()
            merged["price"] = cast(pd.Series, merged["price"]) / fx_series
            merged["dividend"] = cast(pd.Series, merged["dividend"]) / fx_series
            df = merged[["date", "price", "dividend"]]

    return df.copy()


def fetch_benchmark(years):
    """Fetch S&P 500 (SPY) benchmark data."""
    return fetch_asset_data("SPY", years)


def simulate_benchmark(years, include_dividends=True, initial_value=10000.0):
    """Benchmark time series compounded from SPY returns."""
    benchmark_df = fetch_benchmark(years).copy()
    if benchmark_df.empty:
        return pd.DataFrame(columns=["date", "benchmark_value"])

    if include_dividends:
        price_series = cast(pd.Series, benchmark_df["price"])
        dividend_series = cast(pd.Series, benchmark_df["dividend"])
        total = price_series + dividend_series
        benchmark_df["return"] = total / total.shift(1) - 1
    else:
        price_series = cast(pd.Series, benchmark_df["price"])
        benchmark_df["return"] = price_series.pct_change()
    rets = cast(pd.Series, benchmark_df["return"]).fillna(0.0)
    benchmark_df["benchmark_value"] = float(initial_value) * (1.0 + rets).cumprod()
    return benchmark_df[["date", "benchmark_value"]].copy()
