import logging
try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logger = logging.getLogger(__name__)

def detect_anomalies(data_matrix: list[list[float]]) -> list[int]:
    """
    Uses Isolation Forest to detect anomalies in a numeric data matrix.
    Returns indices of anomalous rows.
    """
    if not HAS_SKLEARN or not data_matrix:
        logger.warning("scikit-learn not installed or empty data. Skipping anomaly detection.")
        return []
        
    try:
        clf = IsolationForest(contamination=0.1, random_state=42)
        X = np.array(data_matrix)
        preds = clf.fit_predict(X)
        # -1 indicates anomaly, 1 indicates normal
        anomaly_indices = [i for i, p in enumerate(preds) if p == -1]
        return anomaly_indices
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        return []
