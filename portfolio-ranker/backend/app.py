"""
Flask application entry point for Portfolio Ranker API.
"""

import traceback

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

from data_fetcher import simulate_benchmark
from metrics import calculate_metrics
from ml_analysis import classify_risk, detect_anomaly
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


def _json_safe(obj):
    """Coerce numpy/pandas scalars for jsonify."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return float(obj)
    if hasattr(obj, "item"):
        try:
            return float(obj.item())
        except (ValueError, TypeError):
            return obj
    return obj


def ok(data):
    return jsonify({"status": "success", "data": _json_safe(data)}), 200


def err(message, code=400):
    return jsonify({"status": "error", "message": str(message)}), code


app = Flask(__name__)
CORS(
    app,
    origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    methods=["GET", "POST", "OPTIONS"],
)


@app.route("/")
def index():
    """Health check / root endpoint."""
    return ok({"service": "Portfolio Ranker API", "message": "running"})


@app.route("/portfolio", methods=["POST"])
def submit_portfolio():
    """Accept and validate portfolio submission."""
    data = request.get_json(silent=True)
    is_valid, error = validate_portfolio_input(data)
    if not is_valid:
        return err(error, 400)
    return ok({"message": "portfolio accepted"})


@app.route("/analyze", methods=["POST"])
def analyze():
    """Full portfolio analysis."""
    data = request.get_json(silent=True)
    if data is None:
        return err("Request body must be valid JSON.", 400)
    is_valid, error = validate_portfolio_input(data)
    if not is_valid:
        return err(error, 400)

    portfolio = data["portfolio"]
    years = data["years"]

    try:
        simulation_result = simulate_portfolio(portfolio, years)
        portfolio_daily_returns = simulation_result["portfolio_value"].pct_change()
        metrics_result = calculate_metrics(
            simulation_result["portfolio_value"],
            portfolio_daily_returns,
            years,
        )
        ranking_result = rank_portfolio(metrics_result)
        features = [
            metrics_result["annual_return"],
            metrics_result["volatility"],
            metrics_result["drawdown"],
            metrics_result["sharpe"],
        ]
        anomaly_result = detect_anomaly(features)
        risk_result = classify_risk(features)
        benchmark_result = simulate_benchmark(years)
        portfolio_curve, benchmark_curve = _aligned_curves(simulation_result, benchmark_result)
    except Exception:
        traceback.print_exc()
        return err(
            "Analysis failed. Check tickers and network, then try again.",
            500,
        )

    payload = {
        "score": ranking_result["score"],
        "rank": ranking_result["rank"],
        "annual_return": metrics_result["annual_return"],
        "volatility": metrics_result["volatility"],
        "drawdown": metrics_result["drawdown"],
        "sharpe": metrics_result["sharpe"],
        "risk_level": risk_result["risk_level"],
        "is_anomaly": anomaly_result["is_anomaly"],
        "anomaly_score": anomaly_result["anomaly_score"],
        "portfolio_curve": portfolio_curve,
        "benchmark_curve": benchmark_curve,
    }
    return ok(payload)


if __name__ == "__main__":
    app.run(debug=True)
