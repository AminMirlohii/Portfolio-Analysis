"""
Flask application entry point for Portfolio Ranker API.
"""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def index():
    """Health check / root endpoint."""
    return "Portfolio Ranker API running"


if __name__ == "__main__":
    app.run(debug=True)
