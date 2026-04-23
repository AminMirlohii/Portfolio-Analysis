"""
Data fetching module for market data.
"""

import pandas as pd
import yfinance as yf


def fetch_asset_data(ticker, years):
    """
    Fetch historical prices and dividends for an asset.
    Returns DataFrame with columns: date, price, dividend.
    """
    period = f"{years}y"
    t = yf.Ticker(ticker)
    hist = t.history(period=period)
    if hist.empty:
        return pd.DataFrame(columns=["date", "price", "dividend"])

    df = hist.reset_index()
    df = df.rename(columns={"Date": "date", "Close": "price"})

    if "Dividends" in df.columns:
        df["dividend"] = df["Dividends"].fillna(0)
    else:
        df["dividend"] = 0.0

    return df[["date", "price", "dividend"]]


def fetch_benchmark(years):
    """
    Fetch S&P 500 (SPY) benchmark data.
    Returns DataFrame with columns: date, price, dividend.
    """
    return fetch_asset_data("SPY", years)


def simulate_benchmark(years):
    """
    Benchmark time series: same shape as portfolio simulate output.
    Returns DataFrame with columns: date, benchmark_value (starting 10000, compounded from price).
    """
    benchmark_df = fetch_benchmark(years).copy()
    if benchmark_df.empty:
        return pd.DataFrame(columns=["date", "benchmark_value"])

    benchmark_df["return"] = benchmark_df["price"].pct_change()
    rets = benchmark_df["return"].fillna(0.0)
    benchmark_df["benchmark_value"] = 10000.0 * (1.0 + rets).cumprod()
    return benchmark_df[["date", "benchmark_value"]].copy()
