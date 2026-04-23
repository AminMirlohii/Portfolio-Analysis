"""
Flask application entry point for Portfolio Ranker API.
"""

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

from data_fetcher import simulate_benchmark
from metrics import calculate_metrics
from portfolio import validate_portfolio_input, simulate_portfolio
from ranker import rank_portfolio


def _day_key(series):
    """Calendar day (UTC) for merging portfolio vs benchmark dates."""
    return pd.to_datetime(series, utc=True).dt.normalize()


def _curve_from_df(df, date_col, value_col):
    """One series → [{date, value}, ...] with YYYY-MM-DD dates."""
    dates = _day_key(df[date_col]).dt.strftime("%Y-%m-%d")
    return [{"date": d, "value": float(v)} for d, v in zip(dates, df[value_col])]


def _aligned_curves(simulation_result, benchmark_result):
    """
    Prefer inner-join on calendar day so both curves share the same timeline.
    If no overlap, fall back to formatting each curve separately.
    """
    s = simulation_result.copy()
    b = benchmark_result.copy()
    s["_day"] = _day_key(s["date"])
    b["_day"] = _day_key(b["date"])
    merged = s.merge(b[["_day", "benchmark_value"]], on="_day", how="inner").sort_values("_day")
    if merged.empty:
        return (
            _curve_from_df(simulation_result, "date", "portfolio_value"),
            _curve_from_df(benchmark_result, "date", "benchmark_value"),
        )
    dates = merged["_day"].dt.strftime("%Y-%m-%d")
    portfolio_curve = [{"date": d, "value": float(v)} for d, v in zip(dates, merged["portfolio_value"])]
    benchmark_curve = [{"date": d, "value": float(v)} for d, v in zip(dates, merged["benchmark_value"])]
    return portfolio_curve, benchmark_curve


app = Flask(__name__)
CORS(
    app,
    origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    methods=["GET", "POST", "OPTIONS"],
)


@app.route("/")
def index():
    """Health check / root endpoint."""
    return "Portfolio Ranker API running"


@app.route("/portfolio", methods=["POST"])
def submit_portfolio():
    """Accept and validate portfolio submission."""
    data = request.get_json(silent=True)
    is_valid, error = validate_portfolio_input(data)
    if not is_valid:
        return jsonify({"status": "error", "message": error}), 400
    return jsonify({"status": "portfolio accepted"}), 200


@app.route("/analyze", methods=["POST"])
def analyze():
    """Full portfolio analysis (placeholder)."""
    data = request.get_json()
    is_valid, error = validate_portfolio_input(data)
    if not is_valid:
        return jsonify({"status": "error", "message": error}), 400
    portfolio = data["portfolio"]
    years = data["years"]
    simulation_result = simulate_portfolio(portfolio, years)
    portfolio_daily_returns = simulation_result["portfolio_value"].pct_change()
    metrics_result = calculate_metrics(
        simulation_result["portfolio_value"],
        portfolio_daily_returns,
        years,
    )
    ranking_result = rank_portfolio(metrics_result)
    benchmark_result = simulate_benchmark(years)
    portfolio_curve, benchmark_curve = _aligned_curves(simulation_result, benchmark_result)
    return jsonify(
        {
            "score": ranking_result["score"],
            "rank": ranking_result["rank"],
            "annual_return": metrics_result["annual_return"],
            "volatility": metrics_result["volatility"],
            "drawdown": metrics_result["drawdown"],
            "sharpe": metrics_result["sharpe"],
            "portfolio_curve": portfolio_curve,
            "benchmark_curve": benchmark_curve,
        }
    ), 200


if __name__ == "__main__":
    app.run(debug=True)
