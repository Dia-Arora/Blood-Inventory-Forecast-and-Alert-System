from config import HOSPITAL_SCALE_FACTOR
from ml import inference


def test_predict_demand_by_type_returns_all_four_types(monkeypatch):
    class FakeModel:
        def predict(self, X):
            return [500.0] * len(X)

    fake_models = {bt: FakeModel() for bt in ["a", "b", "ab", "o"]}
    monkeypatch.setattr(inference, "get_demand_models", lambda: fake_models)

    result = inference.predict_demand_by_type(days=3)

    assert set(result.keys()) == {"A", "B", "AB", "O"}
    for bt in result:
        assert len(result[bt]) == 3
        for record in result[bt]:
            assert record["predicted_demand"] == round(500.0 * HOSPITAL_SCALE_FACTOR)
            assert "date" in record


def test_predict_demand_by_type_scales_national_predictions_down(monkeypatch):
    class FakeModel:
        def predict(self, X):
            return [670.0] * len(X)

    monkeypatch.setattr(inference, "get_demand_models", lambda: {"o": FakeModel()})

    result = inference.predict_demand_by_type(days=1)

    # 670 units/day is a plausible national-scale prediction; scaled down
    # it should look like a single hospital's daily demand, not a country's.
    assert result["O"][0]["predicted_demand"] == 7
    assert result["O"][0]["predicted_demand"] < 670


def test_predict_demand_by_type_raises_when_untrained(monkeypatch):
    monkeypatch.setattr(inference, "get_demand_models", lambda: {})

    try:
        inference.predict_demand_by_type(days=1)
        assert False, "expected an exception"
    except Exception as e:
        assert "not trained" in str(e)
