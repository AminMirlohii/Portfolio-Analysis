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
