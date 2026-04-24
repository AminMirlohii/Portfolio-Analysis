"""
Machine learning helpers for portfolio anomaly detection.
"""

import random
from importlib import import_module


def _get_isolation_forest():
    """
    Resolve IsolationForest lazily to avoid hard static import errors in IDEs
    when the active environment does not have scikit-learn installed.
    """
    try:
        sklearn_ensemble = import_module("sklearn.ensemble")
        return sklearn_ensemble.IsolationForest
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "scikit-learn is required for anomaly detection. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc


def _get_kmeans():
    """Resolve KMeans lazily for the same reason as IsolationForest."""
    try:
        sklearn_cluster = import_module("sklearn.cluster")
        return sklearn_cluster.KMeans
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "scikit-learn is required for risk classification. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc


def detect_anomaly(features):
    """
    Detect anomaly from [annual_return, volatility, drawdown, sharpe].

    Returns:
        dict: {"is_anomaly": bool, "anomaly_score": float}
    """
    x = [float(v) for v in features]

    # Create a tiny synthetic "normal" cloud around the current point so the
    # model is fully self-contained and requires no external dataset.
    synthetic = []
    for _ in range(120):
        synthetic.append(
            [
                x[0] + random.gauss(0.0, 0.02),
                x[1] + random.gauss(0.0, 0.03),
                x[2] + random.gauss(0.0, 0.03),
                x[3] + random.gauss(0.0, 0.25),
            ]
        )

    IsolationForest = _get_isolation_forest()
    model = IsolationForest(
        n_estimators=100,
        contamination=0.1,
        random_state=42,
    )
    model.fit(synthetic)

    pred = int(model.predict([x])[0])  # 1 normal, -1 anomaly
    score = float(model.decision_function([x])[0])  # lower => more anomalous
    return {"is_anomaly": pred == -1, "anomaly_score": score}


def classify_risk(features):
    """
    Classify risk level from [annual_return, volatility, drawdown, sharpe].

    Uses KMeans with 3 clusters and maps centroid risk scores to:
    Low risk, Medium risk, High risk.
    """
    x = [float(v) for v in features]

    synthetic = []
    for _ in range(90):
        synthetic.append(
            [
                x[0] + random.gauss(0.0, 0.03),
                max(0.0, x[1] + random.gauss(0.0, 0.04)),
                max(0.0, x[2] + random.gauss(0.0, 0.04)),
                x[3] + random.gauss(0.0, 0.35),
            ]
        )

    # Anchor representative low/medium/high risk profiles to stabilize labels.
    synthetic.extend(
        [
            [0.06, 0.10, 0.08, 1.2],
            [0.08, 0.16, 0.15, 0.8],
            [0.12, 0.30, 0.35, 0.3],
        ]
    )

    KMeans = _get_kmeans()
    model = KMeans(n_clusters=3, random_state=42, n_init=10)
    model.fit(synthetic)

    def risk_score(center):
        # Higher vol/drawdown => riskier; higher return/sharpe => less risky.
        annual_return, volatility, drawdown, sharpe = center
        return (1.8 * volatility) + (2.2 * drawdown) - (0.5 * annual_return) - (0.15 * sharpe)

    centers = model.cluster_centers_
    ordered = sorted(range(3), key=lambda i: risk_score(centers[i]))
    cluster_to_label = {
        ordered[0]: "Low risk",
        ordered[1]: "Medium risk",
        ordered[2]: "High risk",
    }

    cluster = int(model.predict([x])[0])
    return {"risk_level": cluster_to_label[cluster]}
