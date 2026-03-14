"""
Flask application entry point for Portfolio Ranker API.
"""

from flask import Flask, request, jsonify

from portfolio import validate_portfolio_input

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


if __name__ == "__main__":
    app.run(debug=True)
