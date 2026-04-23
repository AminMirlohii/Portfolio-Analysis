"""
Portfolio metrics calculation module.
"""


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
