"""
Portfolio ranking module.
"""


def rank_portfolio(metrics):
    """
    Score from annual_return, Sharpe, and drawdown (large drawdown lowers score).
    Tuned to be less punishing: softer drawdown penalty, more credit for return & Sharpe.
    Final score is clamped to [0, 100]; rank is derived from score bands.
    """
    ar = float(metrics["annual_return"])
    sh = float(metrics["sharpe"])
    dd = float(metrics["drawdown"])
    # ar in ~0–0.2 typical; sh is daily (often <1.5); dd in [0,1] — weights keep scores in 40–90 range
    raw = 52.0 + 240.0 * ar + 6.0 * sh - 48.0 * dd
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
