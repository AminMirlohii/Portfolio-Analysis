"""
Flask application entry point for Portfolio Ranker API.
"""

from flask import Flask, request, jsonify

from data_fetcher import simulate_benchmark
from metrics import calculate_metrics
from portfolio import validate_portfolio_input, simulate_portfolio
from ranker import rank_portfolio

app = Flask(__name__)


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
    return jsonify(
        {
            "score": ranking_result["score"],
            "rank": ranking_result["rank"],
            "annual_return": metrics_result["annual_return"],
            "volatility": metrics_result["volatility"],
            "drawdown": metrics_result["drawdown"],
            "sharpe": metrics_result["sharpe"],
        }
    ), 200


if __name__ == "__main__":
    app.run(debug=True)
