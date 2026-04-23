"""
Portfolio ranking module.
"""


def rank_portfolio(metrics):
    """
    Score from annual_return, Sharpe, and drawdown (large drawdown lowers score).
    Final score is clamped to [0, 100]. Rank label unchanged for now.
    """
    ar = float(metrics["annual_return"])
    sh = float(metrics["sharpe"])
    dd = float(metrics["drawdown"])
    # drawdown is fraction in [0, 1]; subtract up to 100 points at full drawdown
    raw = 50.0 + ar * 200.0 + sh - dd * 100.0
    score = max(0.0, min(100.0, raw))
    score = round(score, 2)
    score = max(0.0, min(100.0, score))
    return {"score": score, "rank": "Average"}
