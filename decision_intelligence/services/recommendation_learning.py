import math


def safe_float(value, default=0.0):
    try:
        number = float(value)

        if math.isnan(number) or math.isinf(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def calculate_learning_score(
    success_count=0,
    failure_count=0,
    average_accuracy=0,
):
    """
    Calculates how strongly historical decision outcomes
    should influence future recommendations.
    """

    success_count = int(
        safe_float(success_count)
    )

    failure_count = int(
        safe_float(failure_count)
    )

    average_accuracy = safe_float(
        average_accuracy
    )

    total = success_count + failure_count

    if total == 0:
        return {
            "learning_score": 0,
            "success_rate": 0,
            "confidence": 0,
            "status": "Insufficient History",
        }

    success_rate = (
        success_count / total
    ) * 100

    learning_score = (
        success_rate * 0.60
        + average_accuracy * 0.40
    )

    learning_score = max(
        0,
        min(
            100,
            learning_score,
        ),
    )

    if learning_score >= 80:
        status = "Strong Learning"

    elif learning_score >= 60:
        status = "Moderate Learning"

    elif learning_score >= 40:
        status = "Weak Learning"

    else:
        status = "Poor Learning"

    return {
        "learning_score": round(
            learning_score,
            2,
        ),

        "success_rate": round(
            success_rate,
            2,
        ),

        "confidence": round(
            learning_score,
            2,
        ),

        "status": status,
    }


def calculate_recommendation_adjustment(
    base_score,
    learning_score,
    historical_success=False,
    historical_failure=False,
):
    """
    Adjusts a recommendation score using historical
    decision outcomes.
    """

    base_score = safe_float(
        base_score
    )

    learning_score = safe_float(
        learning_score
    )

    adjustment = 0

    if historical_success:
        adjustment += (
            learning_score * 0.15
        )

    if historical_failure:
        adjustment -= (
            learning_score * 0.15
        )

    adjusted_score = (
        base_score + adjustment
    )

    adjusted_score = max(
        0,
        min(
            100,
            adjusted_score,
        ),
    )

    return {
        "base_score": round(
            base_score,
            2,
        ),

        "adjustment": round(
            adjustment,
            2,
        ),

        "adjusted_score": round(
            adjusted_score,
            2,
        ),
    }


def build_learning_profile(impact_records):
    """
    Creates an overall historical learning profile
    from measured Decision Impact records.
    """

    if not impact_records:
        return {
            "total_measured": 0,
            "success_count": 0,
            "failure_count": 0,
            "neutral_count": 0,
            "average_accuracy": 0,
            "learning_score": 0,
            "success_rate": 0,
            "confidence": 0,
            "status": "Insufficient History",
        }

    success_count = 0
    failure_count = 0
    neutral_count = 0

    accuracy_values = []

    for record in impact_records:

        if not record.get("has_measurement"):
            continue

        status = record.get(
            "impact",
            "Neutral",
        )

        if status == "Positive":
            success_count += 1

        elif status == "Negative":
            failure_count += 1

        else:
            neutral_count += 1

        result = record.get(
            "result",
            {},
        )

        accuracy = result.get(
            "accuracy",
            {},
        )

        revenue_accuracy = safe_float(
            accuracy.get(
                "revenue",
                0,
            )
        )

        profit_accuracy = safe_float(
            accuracy.get(
                "profit",
                0,
            )
        )

        units_accuracy = safe_float(
            accuracy.get(
                "units",
                0,
            )
        )

        accuracy_values.append(
            (
                revenue_accuracy
                + profit_accuracy
                + units_accuracy
            ) / 3
        )

    measured_count = (
        success_count
        + failure_count
        + neutral_count
    )

    if accuracy_values:
        average_accuracy = (
            sum(accuracy_values)
            / len(accuracy_values)
        )
    else:
        average_accuracy = 0

    learning = calculate_learning_score(
        success_count=success_count,
        failure_count=failure_count,
        average_accuracy=average_accuracy,
    )

    return {
        "total_measured": measured_count,

        "success_count": success_count,

        "failure_count": failure_count,

        "neutral_count": neutral_count,

        "average_accuracy": round(
            average_accuracy,
            2,
        ),

        "learning_score": learning[
            "learning_score"
        ],

        "success_rate": learning[
            "success_rate"
        ],

        "confidence": learning[
            "confidence"
        ],

        "status": learning[
            "status"
        ],
    }

def apply_learning_to_recommendation(
    recommendation,
    learning_profile,
):
    """
    Adjust a recommendation using historical decision learning.

    The original recommendation is preserved.
    Only the score, priority and learning metadata are enhanced.
    """

    if not isinstance(recommendation, dict):
        return recommendation

    if not isinstance(learning_profile, dict):
        return recommendation

    result = recommendation.copy()

    base_score = safe_float(
        recommendation.get("score", 0)
    )

    learning_score = safe_float(
        learning_profile.get(
            "learning_score",
            0,
        )
    )

    success_rate = safe_float(
        learning_profile.get(
            "success_rate",
            0,
        )
    )

    historical_success = (
        success_rate >= 60
        and learning_score >= 60
    )

    historical_failure = (
        success_rate < 40
        and learning_score >= 40
    )

    adjustment_result = (
        calculate_recommendation_adjustment(
            base_score=base_score,
            learning_score=learning_score,
            historical_success=historical_success,
            historical_failure=historical_failure,
        )
    )

    adjusted_score = adjustment_result[
        "adjusted_score"
    ]

    result["base_score"] = (
        adjustment_result["base_score"]
    )

    result["learning_adjustment"] = (
        adjustment_result["adjustment"]
    )

    result["score"] = adjusted_score

    result["learning_score"] = learning_score

    result["learning_confidence"] = safe_float(
        learning_profile.get(
            "confidence",
            0,
        )
    )

    result["historical_success_rate"] = (
        success_rate
    )

    if (
        learning_score >= 80
        and historical_success
    ):
        result["learning_signal"] = (
            "Strong historical support"
        )

        result["learning_message"] = (
            "Historical decisions show strong "
            "support for similar strategies."
        )

        # Promote recommendation when learning
        # strongly supports it.
        if result.get("priority") == "Medium":
            result["priority"] = "High"

    elif (
        learning_score >= 60
        and historical_success
    ):
        result["learning_signal"] = (
            "Positive historical support"
        )

        result["learning_message"] = (
            "Historical decision outcomes support "
            "this recommendation."
        )

    elif historical_failure:
        result["learning_signal"] = (
            "Historical caution"
        )

        result["learning_message"] = (
            "Historical outcomes suggest caution "
            "with similar strategies."
        )

        if result.get("priority") == "Critical":
            result["priority"] = "High"

    elif learning_score > 0:
        result["learning_signal"] = (
            "Limited historical evidence"
        )

        result["learning_message"] = (
            "Historical decision evidence is "
            "available but not yet strong."
        )

    else:
        result["learning_signal"] = (
            "No historical evidence"
        )

        result["learning_message"] = (
            "More completed decisions are required "
            "before historical learning can influence "
            "this recommendation."
        )

    metadata = result.get(
        "metadata",
        {},
    )

    if not isinstance(metadata, dict):
        metadata = {}

    metadata = metadata.copy()

    metadata.update({
        "base_score": result.get(
            "base_score",
            0,
        ),

        "learning_adjustment": result.get(
            "learning_adjustment",
            0,
        ),

        "learning_score": learning_score,

        "learning_confidence": result.get(
            "learning_confidence",
            0,
        ),

        "historical_success_rate": success_rate,

        "learning_signal": result.get(
            "learning_signal",
            "",
        ),
    })

    result["metadata"] = metadata

    return result

def apply_learning_to_recommendations(
    recommendations,
    learning_profile,
):
    """
    Applies historical learning to every recommendation.
    """

    if not isinstance(recommendations, list):
        return []

    enhanced = []

    for recommendation in recommendations:

        try:
            enhanced_recommendation = (
                apply_learning_to_recommendation(
                    recommendation,
                    learning_profile,
                )
            )

            enhanced.append(
                enhanced_recommendation
            )

        except Exception:
            enhanced.append(
                recommendation
            )

    enhanced.sort(
        key=lambda item: (
            safe_float(
                item.get("score", 0)
            ),
            safe_float(
                item.get("learning_adjustment", 0)
            ),
        ),
        reverse=True,
    )

    return enhanced