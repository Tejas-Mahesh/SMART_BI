from math import isfinite


def safe_float(value, default=0.0):
    try:
        number = float(value)

        if not isfinite(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def percentage_change(current_value, previous_value):
    """
    Calculate percentage change between two values.
    """

    current_value = safe_float(current_value)
    previous_value = safe_float(previous_value)

    if previous_value == 0:
        if current_value == 0:
            return 0.0

        return 100.0

    return ((current_value - previous_value) / abs(previous_value)) * 100


def calculate_accuracy(expected, actual):
    """
    Calculate how closely the actual result matched
    the expected result.

    Example:
        Expected = 10%
        Actual   = 8%

        Accuracy = 80%
    """

    expected = safe_float(expected)
    actual = safe_float(actual)

    if expected == 0:
        if actual == 0:
            return 100.0

        return 0.0

    accuracy = 100 - (
        abs(actual - expected) / abs(expected) * 100
    )

    return max(0.0, min(100.0, accuracy))


def calculate_impact_score(
    revenue_accuracy,
    profit_accuracy,
    units_accuracy,
):
    """
    Overall Decision Impact score.

    Profit receives the highest weight because
    profitability is generally more important than
    volume alone.
    """

    revenue_accuracy = safe_float(revenue_accuracy)
    profit_accuracy = safe_float(profit_accuracy)
    units_accuracy = safe_float(units_accuracy)

    score = (
        revenue_accuracy * 0.30
        + profit_accuracy * 0.45
        + units_accuracy * 0.25
    )

    return round(
        max(0.0, min(100.0, score)),
        2,
    )


def classify_impact(
    actual_impact_score,
    actual_revenue_change,
    actual_profit_change,
):
    """
    Classify the final business impact.
    """

    score = safe_float(actual_impact_score)
    revenue_change = safe_float(actual_revenue_change)
    profit_change = safe_float(actual_profit_change)

    # Strong positive business result
    if score >= 75 and profit_change > 0:
        return "Positive"

    # Strong negative business result
    if score < 45 or profit_change < 0:
        return "Negative"

    # Everything between these ranges is considered neutral
    return "Neutral"


def build_decision_impact(
    expected_revenue_change=0,
    expected_profit_change=0,
    expected_units_change=0,
    actual_revenue_change=0,
    actual_profit_change=0,
    actual_units_change=0,
    expected_impact_score=0,
):
    """
    Build a complete Expected vs Actual Decision Impact result.
    """

    expected_revenue_change = safe_float(
        expected_revenue_change
    )

    expected_profit_change = safe_float(
        expected_profit_change
    )

    expected_units_change = safe_float(
        expected_units_change
    )

    actual_revenue_change = safe_float(
        actual_revenue_change
    )

    actual_profit_change = safe_float(
        actual_profit_change
    )

    actual_units_change = safe_float(
        actual_units_change
    )

    expected_impact_score = safe_float(
        expected_impact_score
    )

    revenue_accuracy = calculate_accuracy(
        expected_revenue_change,
        actual_revenue_change,
    )

    profit_accuracy = calculate_accuracy(
        expected_profit_change,
        actual_profit_change,
    )

    units_accuracy = calculate_accuracy(
        expected_units_change,
        actual_units_change,
    )

    actual_impact_score = calculate_impact_score(
        revenue_accuracy,
        profit_accuracy,
        units_accuracy,
    )

    impact_status = classify_impact(
        actual_impact_score,
        actual_revenue_change,
        actual_profit_change,
    )

    return {
        "expected": {
            "revenue_change": round(
                expected_revenue_change,
                2,
            ),
            "profit_change": round(
                expected_profit_change,
                2,
            ),
            "units_change": round(
                expected_units_change,
                2,
            ),
            "impact_score": round(
                expected_impact_score,
                2,
            ),
        },

        "actual": {
            "revenue_change": round(
                actual_revenue_change,
                2,
            ),
            "profit_change": round(
                actual_profit_change,
                2,
            ),
            "units_change": round(
                actual_units_change,
                2,
            ),
            "impact_score": round(
                actual_impact_score,
                2,
            ),
        },

        "accuracy": {
            "revenue": round(
                revenue_accuracy,
                2,
            ),
            "profit": round(
                profit_accuracy,
                2,
            ),
            "units": round(
                units_accuracy,
                2,
            ),
        },

        "impact_status": impact_status,
    }


def generate_impact_insights(result):
    """
    Generate business-friendly explanations
    from the Expected vs Actual results.
    """

    insights = []

    expected = result.get("expected", {})
    actual = result.get("actual", {})
    accuracy = result.get("accuracy", {})

    expected_profit = safe_float(
        expected.get("profit_change")
    )

    actual_profit = safe_float(
        actual.get("profit_change")
    )

    expected_revenue = safe_float(
        expected.get("revenue_change")
    )

    actual_revenue = safe_float(
        actual.get("revenue_change")
    )

    expected_units = safe_float(
        expected.get("units_change")
    )

    actual_units = safe_float(
        actual.get("units_change")
    )

    profit_accuracy = safe_float(
        accuracy.get("profit")
    )

    revenue_accuracy = safe_float(
        accuracy.get("revenue")
    )

    units_accuracy = safe_float(
        accuracy.get("units")
    )

    if actual_profit > expected_profit:
        insights.append(
            "Actual profit performance exceeded the expected impact."
        )

    elif actual_profit < expected_profit:
        insights.append(
            "Actual profit performance was below the expected impact."
        )

    else:
        insights.append(
            "Actual profit performance matched the expected impact."
        )

    if actual_revenue > expected_revenue:
        insights.append(
            "Revenue growth performed better than expected."
        )

    elif actual_revenue < expected_revenue:
        insights.append(
            "Revenue growth performed below expectations."
        )

    if actual_units > expected_units:
        insights.append(
            "Unit performance exceeded the expected level."
        )

    elif actual_units < expected_units:
        insights.append(
            "Unit performance was below the expected level."
        )

    if profit_accuracy >= 80:
        insights.append(
            "Profit impact prediction was highly accurate."
        )

    elif profit_accuracy < 50:
        insights.append(
            "Profit impact prediction should be reviewed for future decisions."
        )

    if revenue_accuracy >= 80:
        insights.append(
            "Revenue impact prediction was highly accurate."
        )

    if units_accuracy >= 80:
        insights.append(
            "Demand or unit impact prediction was highly accurate."
        )

    status = result.get(
        "impact_status",
        "Neutral",
    )

    if status == "Positive":
        insights.append(
            "Overall decision impact is positive. "
            "This type of action may be suitable for future use."
        )

    elif status == "Negative":
        insights.append(
            "Overall decision impact is negative. "
            "The business should review the action before repeating it."
        )

    else:
        insights.append(
            "Overall decision impact is neutral. "
            "Additional monitoring may be useful."
        )

    return insights


def build_complete_impact_analysis(**kwargs):
    """
    Convenience wrapper returning the complete
    Decision Impact analysis.
    """

    result = build_decision_impact(**kwargs)

    result["insights"] = generate_impact_insights(
        result
    )

    return result