"""
Named what-if scenarios for scenario_shocks.py: each scenario overrides the
demand and/or supply multiplier for specific day windows of the simulation,
instead of the always-on random shock ("default"). Grounded in real, cited
events where possible; explicitly flagged as an assumption where not.

A scenario's demand/supply "day windows" are relative to the simulation's
own day_index (0 = the first simulated day), not calendar dates -- so the
same scenario always plays out the same way regardless of which real date
the simulation happens to start on.
"""

SCENARIOS = {
    "default": {
        "label": "Default (random)",
        "description": (
            "The ongoing random weekly demand surges and supply swings "
            "used everywhere else in the simulation -- no scenario override."
        ),
        "source": None,
        "demand_override": None,
        "supply_override": None,
    },
    "mass_casualty": {
        "label": "Mass Casualty Event",
        "description": (
            "A sudden multi-patient trauma surge overwhelms demand for 4 "
            "days, from day 2 through day 5 of the simulation (day 1's "
            "stock level is left alone so it still reflects a normal "
            "pre-event baseline, rather than being seeded from the spike "
            "itself). The surge peaks on days 2-3, then tapers on days "
            "4-5. Supply is left untouched so the shortage stress-test "
            "isn't cushioned by a post-event donation surge."
        ),
        "source": (
            "Derived, not directly cited: clinical \"massive transfusion\" "
            "is defined as 10+ units to a single patient within 24 hours "
            "(NCBI StatPearls). Real single events used hundreds of units "
            "across multiple hospitals within 24 hours (2017 Las Vegas "
            "shooting: ~499 components; Pulse nightclub: ~550 units total) "
            "-- a fraction of that landing at one small hospital already "
            "dwarfs its normal daily volume."
        ),
        "demand_override": [
            {"start_day": 1, "end_day": 3, "range": (6.0, 10.0)},
            {"start_day": 3, "end_day": 5, "range": (2.0, 3.0)},
        ],
        "supply_override": None,
    },
    "donation_drive": {
        "label": "Donation Drive",
        "description": (
            "A public donation drive rallies donors for 2 days, boosting "
            "supply well above normal. Demand is left untouched -- this is "
            "a positive supply event, not a shortage stress-test."
        ),
        "source": (
            "Cited: American Red Cross reported a 53% increase in blood "
            "donations in the two days following the 2017 Las Vegas "
            "shooting -- the same kind of public rallying effect a "
            "targeted donation drive aims to produce."
        ),
        "demand_override": None,
        "supply_override": [
            {"start_day": 0, "end_day": 2, "range": (1.4, 1.7)},
        ],
    },
    "holiday_weekend": {
        "label": "Holiday Weekend",
        "description": (
            "A milder, short dip on both sides over a 3-day holiday "
            "weekend -- donations slow and elective demand eases."
        ),
        "source": (
            "Supply dip is cited, scaled down from a longer real window: "
            "American Red Cross reported a ~7,000-unit shortfall over the "
            "full Christmas-New Year's week; this scenario applies the "
            "same directional effect to a single 3-day weekend. The demand "
            "dip is an assumption (elective procedures commonly pause "
            "around holidays) -- no cited percentage was found for blood "
            "demand specifically."
        ),
        "demand_override": [
            {"start_day": 0, "end_day": 3, "range": (0.85, 0.90)},
        ],
        "supply_override": [
            {"start_day": 0, "end_day": 3, "range": (0.75, 0.80)},
        ],
    },
}


def _range_summary(overrides):
    if not overrides:
        return None
    return {
        "min": min(w["range"][0] for w in overrides),
        "max": max(w["range"][1] for w in overrides),
        "start_day": min(w["start_day"] for w in overrides),
        "end_day": max(w["end_day"] for w in overrides),
    }


def list_scenarios():
    """Serializable summary for the API/frontend: one entry per scenario,
    with the demand/supply multiplier range and duration if it overrides
    anything, or null if that side is left at the default random behavior."""
    return [
        {
            "key": key,
            "label": cfg["label"],
            "description": cfg["description"],
            "source": cfg["source"],
            "demand_shock": _range_summary(cfg["demand_override"]),
            "supply_shock": _range_summary(cfg["supply_override"]),
        }
        for key, cfg in SCENARIOS.items()
    ]
