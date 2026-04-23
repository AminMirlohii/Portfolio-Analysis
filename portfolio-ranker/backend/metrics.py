"""
Portfolio metrics calculation module.
"""

import math
import statistics


def annualized_return(values, years):
    """
    Annualized return from first to last value over `years` (CAGR).
    `values` may be a list or a pandas Series.
    """
    if hasattr(values, "iloc"):
        first, last = values.iloc[0], values.iloc[-1]
    else:
        first, last = values[0], values[-1]
    return (float(last) / float(first)) ** (1.0 / float(years)) - 1.0


def volatility(returns):
    """
    Volatility of daily returns, annualized: std(returns) * sqrt(252).
    252 = trading days per year. `returns` may be a list or a pandas Series.
    """
    if hasattr(returns, "std"):
        if len(returns) < 2:
            return 0.0
        daily_std = float(returns.std())
    else:
        r = list(returns)
        if len(r) < 2:
            return 0.0
        daily_std = statistics.stdev(r)
    return daily_std * math.sqrt(252.0)


def max_drawdown(values):
    """
    Largest drop from a running peak, as a fraction in [0, 1].
    `values` may be a list or a pandas Series.
    """
    if hasattr(values, "values"):
        seq = values.values
    else:
        seq = list(values)
    if len(seq) == 0:
        return 0.0
    peak = float(seq[0])
    worst = 0.0
    for v in seq:
        v = float(v)
        peak = max(peak, v)
        if peak > 0:
            worst = max(worst, (peak - v) / peak)
    return worst


def sharpe_ratio(returns):
    """
    Mean return over standard deviation, risk-free rate = 0.
    `returns` may be a list or a pandas Series.
    """
    if hasattr(returns, "mean") and hasattr(returns, "std"):
        if len(returns) < 2:
            return 0.0
        mean_r = float(returns.mean())
        std_r = float(returns.std())
    else:
        r = list(returns)
        if len(r) < 2:
            return 0.0
        mean_r = statistics.mean(r)
        std_r = statistics.stdev(r)
    if std_r == 0.0:
        return 0.0
    return mean_r / std_r


def calculate_metrics(values, returns, years):
    """
    Aggregate portfolio metrics. Not wired to the API.
    `values` and `returns` may be list-like or Series.
    """
    return {
        "annual_return": annualized_return(values, years),
        "volatility": volatility(returns),
        "drawdown": max_drawdown(values),
        "sharpe": sharpe_ratio(returns),
    }
