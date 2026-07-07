from ml import inference


def test_predict_demand_by_type_splits_the_aggregate(monkeypatch):
    fake_total = [{"date": "2024-01-01", "predicted_demand": 100.0}]
    monkeypatch.setattr(inference, "predict_demand", lambda days: fake_total)

    result = inference.predict_demand_by_type(1)

    assert set(result.keys()) == {"A", "B", "AB", "O"}
    day_total = sum(result[bt][0]["predicted_demand"] for bt in result)
    assert abs(day_total - 100.0) < 1e-6
