"""
Portfolio ranking module.
"""


def rank_portfolio(metrics):
    """
    Score from annual_return (higher return → higher score, 0–100).
    Rank label unchanged for now.
    """
    ar = float(metrics["annual_return"])
    # 0% annual return → 50; +0.25 → 100; −0.25 → 0; clamped
    score = max(0.0, min(100.0, 50.0 + ar * 200.0))
    return {"score": round(score, 2), "rank": "Average"}
