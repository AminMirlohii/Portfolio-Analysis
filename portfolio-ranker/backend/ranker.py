"""
Portfolio ranking module.
"""


def rank_portfolio(metrics):
    """
    Score from annual_return, Sharpe, and drawdown (large drawdown lowers score).
    Rank label unchanged for now.
    """
    ar = float(metrics["annual_return"])
    sh = float(metrics["sharpe"])
    dd = float(metrics["drawdown"])
    # drawdown is fraction in [0, 1]; subtract up to 100 points at full drawdown
    score = max(0.0, min(100.0, 50.0 + ar * 200.0 + sh - dd * 100.0))
    return {"score": round(score, 2), "rank": "Average"}
