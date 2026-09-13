from .what_if import calculate_scenario


def safe_float(value, default=0.0):
    try:
        number = float(value)

        if number != number:
            return default

        return number

    except (TypeError, ValueError):
        return default


def build_scenario_result(
    baseline,
    price_change=0,
    discount_change=0,
    marketing_change=0,
    demand_change=0,
):
    """
    Run one business scenario using the existing
    What-If calculation engine.
    """

    baseline_revenue = safe_float(
        baseline.get("revenue", 0)
    )

    baseline_profit = safe_float(
        baseline.get("profit", 0)
    )

    baseline_units = safe_float(
        baseline.get("units", 0)
    )

    return calculate_scenario(
        base_revenue=baseline_revenue,
        base_profit=baseline_profit,
        base_units=baseline_units,
        price_change=safe_float(price_change),
        discount_change=safe_float(discount_change),
        marketing_change=safe_float(marketing_change),
        demand_change=safe_float(demand_change),
    )


def scenario_summary(name, result):
    """
    Convert the What-If result into a
    Scenario Planning-friendly structure.
    """

    baseline = result.get("baseline", {})
    scenario = result.get("scenario", {})
    changes = result.get("changes", {})

    return {
        "name": name,

        "baseline_revenue": safe_float(
            baseline.get("revenue", 0)
        ),

        "baseline_profit": safe_float(
            baseline.get("profit", 0)
        ),

        "baseline_units": safe_float(
            baseline.get("units", 0)
        ),

        "scenario_revenue": safe_float(
            scenario.get("revenue", 0)
        ),

        "scenario_profit": safe_float(
            scenario.get("profit", 0)
        ),

        "scenario_units": safe_float(
            scenario.get("units", 0)
        ),

        "revenue_change": safe_float(
            changes.get("revenue", 0)
        ),

        "profit_change": safe_float(
            changes.get("profit", 0)
        ),

        "units_change": safe_float(
            changes.get("units", 0)
        ),

        "score": safe_float(
            result.get("score", 0)
        ),

        "decision": result.get(
            "decision",
            "Review"
        ),

        "insights": result.get(
            "insights",
            []
        ),
    }


def rank_scenarios(scenarios):
    """
    Rank scenarios primarily by score,
    then profit impact,
    then revenue impact.
    """

    ranked = list(scenarios)

    ranked.sort(
        key=lambda item: (
            safe_float(
                item.get("score", 0)
            ),
            safe_float(
                item.get("profit_change", 0)
            ),
            safe_float(
                item.get("revenue_change", 0)
            ),
        ),
        reverse=True,
    )

    for index, scenario in enumerate(
        ranked,
        start=1
    ):
        scenario["rank"] = index

    return ranked


def get_best_scenario(scenarios):
    """
    Return the highest-ranked scenario.
    """

    ranked = rank_scenarios(
        scenarios
    )

    if not ranked:
        return None

    return ranked[0]