import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from ml.train_demand import train as train_demand
    from ml.train_supply import train as train_supply

    train_demand()
    train_supply()

    from api.main import app
    return TestClient(app)


def test_simulate_returns_all_four_blood_types_with_valid_labels(client):
    resp = client.get("/api/simulate?days=10")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] == "success"

    data = body["data"]
    assert set(data.keys()) == {"A", "B", "AB", "O"}
    for records in data.values():
        assert len(records) == 10
        for r in records:
            assert r["stock"] >= 0
            assert r["shortage_risk"] in {"SAFE", "WARNING", "CRITICAL"}
            assert r["wastage_risk"] in {"LOW", "MED", "HIGH"}
