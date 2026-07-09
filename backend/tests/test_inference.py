from ml import inference


def test_predict_demand_by_type_returns_all_four_types(monkeypatch):
    class FakeModel:
        def predict(self, X):
            return [500.0] * len(X)

    fake_models = {bt: FakeModel() for bt in ["a", "b", "ab", "o"]}
    monkeypatch.setattr(inference, "get_demand_models", lambda: fake_models)
    # Isolate this test from the scenario-shock layer (tested separately
    # below) so it only verifies shape/structure, not shock arithmetic.
    monkeypatch.setattr(inference, "demand_shock_multiplier", lambda bt, date: 1.0)

    result = inference.predict_demand_by_type(days=3)

    assert set(result.keys()) == {"A", "B", "AB", "O"}
    for bt in result:
        assert len(result[bt]) == 3
        for record in result[bt]:
            assert "date" in record
            assert record["predicted_demand"] >= 0


def test_predict_demand_by_type_scales_national_predictions_down(monkeypatch):
    class FakeModel:
        def predict(self, X):
            return [670.0] * len(X)

    monkeypatch.setattr(inference, "get_demand_models", lambda: {"o": FakeModel()})
    monkeypatch.setattr(inference, "demand_shock_multiplier", lambda bt, date: 1.0)

    result = inference.predict_demand_by_type(days=1)

    # 670 units/day is a plausible national-scale prediction; scaled down
    # it should look like a single hospital's daily demand, not a country's.
    assert result["O"][0]["predicted_demand"] == 7
    assert result["O"][0]["predicted_demand"] < 670


def test_predict_demand_by_type_applies_the_scenario_shock_multiplier(monkeypatch):
    class FakeModel:
        def predict(self, X):
            return [1000.0] * len(X)

    monkeypatch.setattr(inference, "get_demand_models", lambda: {"o": FakeModel()})
    # A fixed 2x shock, independent of blood type/date, isolates the
    # shock-application arithmetic from the real (random) shock function.
    monkeypatch.setattr(inference, "demand_shock_multiplier", lambda bt, date: 2.0)

    result = inference.predict_demand_by_type(days=1)

    # 1000 (raw) * 0.01 (HOSPITAL_SCALE_FACTOR) * 2.0 (shock) = 20
    assert result["O"][0]["predicted_demand"] == 20


def test_predict_demand_by_type_raises_when_untrained(monkeypatch):
    monkeypatch.setattr(inference, "get_demand_models", lambda: {})

    try:
        inference.predict_demand_by_type(days=1)
        assert False, "expected an exception"
    except Exception as e:
        assert "not trained" in str(e)
