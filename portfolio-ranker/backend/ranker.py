"""
Portfolio ranking module.
"""


def rank_portfolio(metrics):
    """
    Score from annual_return and Sharpe (both higher → higher score, 0–100).
    Rank label unchanged for now.
    """
    ar = float(metrics["annual_return"])
    sh = float(metrics["sharpe"])
    # Return leg: 0% → 50; +0.25 → 100; −0.25 → 0. Add Sharpe (positive → higher), clamp 0–100.
    score = max(0.0, min(100.0, 50.0 + ar * 200.0 + sh))
    return {"score": round(score, 2), "rank": "Average"}
