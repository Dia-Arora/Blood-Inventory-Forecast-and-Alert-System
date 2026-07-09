from config import DEMAND_SCALE_FACTOR
from ml import inference


def test_predict_demand_by_type_splits_the_aggregate(monkeypatch):
    fake_total = [{"date": "2024-01-01", "predicted_demand": 100.0}]
    monkeypatch.setattr(inference, "predict_demand", lambda days: fake_total)

    result = inference.predict_demand_by_type(1)

    assert set(result.keys()) == {"A", "B", "AB", "O"}
    day_total = sum(result[bt][0]["predicted_demand"] for bt in result)
    assert abs(day_total - 100.0) < 1e-6


def test_predict_demand_applies_the_scale_factor(monkeypatch):
    class FakeModel:
        def predict(self, X):
            return [10.0] * len(X)

    monkeypatch.setattr(inference, "get_demand_model", lambda: FakeModel())

    result = inference.predict_demand(days=1)

    assert result[0]["predicted_demand"] == round(10.0 * DEMAND_SCALE_FACTOR)
