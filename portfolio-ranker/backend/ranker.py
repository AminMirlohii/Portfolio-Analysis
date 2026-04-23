"""
Portfolio ranking module.
"""


def rank_portfolio(metrics):
    """
    Score from annual_return, Sharpe, and drawdown (large drawdown lowers score).
    Final score is clamped to [0, 100]; rank is derived from score bands.
    """
    ar = float(metrics["annual_return"])
    sh = float(metrics["sharpe"])
    dd = float(metrics["drawdown"])
    # drawdown is fraction in [0, 1]; subtract up to 100 points at full drawdown
    raw = 50.0 + ar * 200.0 + sh - dd * 100.0
    score = max(0.0, min(100.0, raw))
    score = round(score, 2)
    score = max(0.0, min(100.0, score))

    if score >= 90:
        rank = "Elite"
    elif score >= 80:
        rank = "Excellent"
    elif score >= 70:
        rank = "Strong"
    elif score >= 60:
        rank = "Average"
    elif score >= 50:
        rank = "Weak"
    else:
        rank = "Poor"

    return {"score": score, "rank": rank}
