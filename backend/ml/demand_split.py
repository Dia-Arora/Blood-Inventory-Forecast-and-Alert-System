"""
Disaggregates the single aggregate demand forecast (Kaggle dataset has no
blood-type breakdown) into per-ABO-type demand, using each type's historical
share of real Malaysian donation volume as a proxy ratio. This is a
documented approximation, not independently-learned per-type demand -- the
demand dataset doesn't support that.
"""
import os

import pandas as pd

DONATIONS_PATH = os.path.join(os.path.dirname(__file__), "../data/blood_donations.csv")


def compute_type_ratios():
    """Returns {type: ratio} for A/B/AB/O, summing to 1.0."""
    df = pd.read_csv(DONATIONS_PATH)
    df = df[df["blood_type"] != "all"]
    totals = df.groupby("blood_type")["donations"].sum()
    totals.index = totals.index.str.upper()
    ratios = (totals / totals.sum()).to_dict()
    return ratios


def split_by_type(total_demand):
    """
    total_demand: list of {"date": str, "predicted_demand": float}
    Returns: {type: [{"date": str, "predicted_demand": float}, ...]}
    """
    ratios = compute_type_ratios()
    result = {}
    for bt, ratio in ratios.items():
        result[bt] = [
            {"date": d["date"], "predicted_demand": d["predicted_demand"] * ratio}
            for d in total_demand
        ]
    return result
