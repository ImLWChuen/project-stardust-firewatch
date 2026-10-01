from science.anomaly.anomaly_score import compute_anomaly_zscore

def test_anomaly_zscore():
    score = compute_anomaly_zscore(15.0, 10.0, 2.5)
    assert score == 2.0
