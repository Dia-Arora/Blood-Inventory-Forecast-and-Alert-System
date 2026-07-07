from ml.demand_split import compute_type_ratios, split_by_type


def test_ratios_sum_to_one_and_cover_all_types():
    ratios = compute_type_ratios()
    assert set(ratios.keys()) == {"A", "B", "AB", "O"}
    assert abs(sum(ratios.values()) - 1.0) < 1e-6


def test_split_by_type_sums_back_to_original_total():
    total_demand = [
        {"date": "2024-01-01", "predicted_demand": 100.0},
        {"date": "2024-01-02", "predicted_demand": 200.0},
    ]
    split = split_by_type(total_demand)
    assert set(split.keys()) == {"A", "B", "AB", "O"}
    for i in range(len(total_demand)):
        day_total = sum(split[bt][i]["predicted_demand"] for bt in split)
        assert abs(day_total - total_demand[i]["predicted_demand"]) < 1e-6
        assert split["A"][i]["date"] == total_demand[i]["date"]
