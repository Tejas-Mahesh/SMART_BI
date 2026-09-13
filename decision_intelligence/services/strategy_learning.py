import math


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        number = float(value)

        if math.isnan(number) or math.isinf(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def clean_text(value, default=""):
    if value is None:
        return default

    value = str(value).strip()

    return value if value else default


# ============================================================
# STRATEGY MAPPING
# ============================================================

STRATEGY_MAP = {
    "Opportunity": "Growth",
    "Customer Risk": "Retention",
    "Anomaly": "Anomaly Response",
    "Forecast": "Forecast Planning",
    "Root Cause": "Corrective Action",
    "Sales": "Sales Growth",
    "Product": "Product Growth",
    "Regional": "Regional Growth",
    "Marketing": "Marketing Optimization",
    "Financial": "Financial Optimization",
    "Returns": "Returns Reduction",
}


def normalize_strategy(
    category=None,
    source=None,
):
    """
    Convert recommendation category/source into a stable
    learning strategy.
    """

    category = clean_text(category)
    source = clean_text(source)

    if category in STRATEGY_MAP:
        return STRATEGY_MAP[category]

    if source in STRATEGY_MAP:
        return STRATEGY_MAP[source]

    category_lower = category.lower()
    source_lower = source.lower()

    if "customer" in category_lower or "risk" in category_lower:
        return "Retention"

    if "opportun" in category_lower or "growth" in category_lower:
        return "Growth"

    if "anomal" in category_lower:
        return "Anomaly Response"

    if "forecast" in category_lower:
        return "Forecast Planning"

    if "root" in category_lower or "cause" in category_lower:
        return "Corrective Action"

    if "product" in category_lower:
        return "Product Growth"

    if "regional" in category_lower:
        return "Regional Growth"

    if "marketing" in category_lower:
        return "Marketing Optimization"

    if "sales" in category_lower:
        return "Sales Growth"

    if source_lower:
        return source

    return "General Decision"


# ============================================================
# RECORD STRATEGY
# ============================================================

def get_record_strategy(record):
    """
    Determine the strategy represented by a historical
    decision/impact record.
    """

    if not isinstance(record, dict):
        return "General Decision"

    action = record.get("action")

    if action is not None:

        category = clean_text(
            getattr(action, "action_type", "")
        )

        title = clean_text(
            getattr(action, "title", "")
        )

        recommendation = clean_text(
            getattr(action, "recommendation", "")
        )

        text = (
            f"{category} "
            f"{title} "
            f"{recommendation}"
        ).lower()

        if "customer" in text or "retention" in text:
            return "Retention"

        if "anomaly" in text:
            return "Anomaly Response"

        if "forecast" in text:
            return "Forecast Planning"

        if "root cause" in text:
            return "Corrective Action"

        if "product" in text:
            return "Product Growth"

        if "regional" in text:
            return "Regional Growth"

        if "marketing" in text:
            return "Marketing Optimization"

        if "sales" in text:
            return "Sales Growth"

        if "growth" in text or "opportunity" in text:
            return "Growth"

    return clean_text(
        record.get("strategy"),
        "General Decision",
    )


# ============================================================
# STRATEGY PROFILE
# ============================================================

def build_strategy_profile(
    impact_records,
):
    """
    Build separate learning profiles for each decision
    strategy.
    """

    profiles = {}

    if not isinstance(
        impact_records,
        list,
    ):
        return profiles


    for record in impact_records:

        if not isinstance(
            record,
            dict,
        ):
            continue

        if not record.get(
            "has_measurement"
        ):
            continue


        strategy = get_record_strategy(
            record
        )


        if strategy not in profiles:

            profiles[strategy] = {
                "strategy": strategy,
                "total_measured": 0,
                "success_count": 0,
                "failure_count": 0,
                "neutral_count": 0,
                "accuracy_values": [],
            }


        profile = profiles[strategy]

        profile["total_measured"] += 1


        impact = clean_text(
            record.get(
                "impact"
            ),
            "Neutral",
        )


        if impact == "Positive":

            profile["success_count"] += 1

        elif impact == "Negative":

            profile["failure_count"] += 1

        else:

            profile["neutral_count"] += 1


        result = record.get(
            "result",
            {},
        )

        accuracy = (
            result.get(
                "accuracy",
                {}
            )
            if isinstance(
                result,
                dict,
            )
            else {}
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


        average_accuracy = (
            revenue_accuracy
            + profit_accuracy
            + units_accuracy
        ) / 3


        profile[
            "accuracy_values"
        ].append(
            average_accuracy
        )


    # ========================================================
    # FINALIZE PROFILES
    # ========================================================

    finalized = {}


    for strategy, profile in profiles.items():

        total = (
            profile["success_count"]
            + profile["failure_count"]
        )


        if total > 0:

            success_rate = (
                profile["success_count"]
                / total
            ) * 100

        else:

            success_rate = 0


        accuracy_values = (
            profile["accuracy_values"]
        )


        if accuracy_values:

            average_accuracy = (
                sum(accuracy_values)
                / len(accuracy_values)
            )

        else:

            average_accuracy = 0


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


        finalized[strategy] = {

            "strategy": strategy,

            "total_measured": (
                profile["total_measured"]
            ),

            "success_count": (
                profile["success_count"]
            ),

            "failure_count": (
                profile["failure_count"]
            ),

            "neutral_count": (
                profile["neutral_count"]
            ),

            "average_accuracy": round(
                average_accuracy,
                2,
            ),

            "success_rate": round(
                success_rate,
                2,
            ),

            "learning_score": round(
                learning_score,
                2,
            ),

            "confidence": round(
                learning_score,
                2,
            ),

            "status": status,
        }


    return finalized


# ============================================================
# SELECT RELEVANT PROFILE
# ============================================================

def get_strategy_learning(
    recommendation,
    strategy_profiles,
):
    """
    Select historical learning relevant to the current
    recommendation.
    """

    if not isinstance(
        recommendation,
        dict,
    ):
        return None


    if not isinstance(
        strategy_profiles,
        dict,
    ):
        return None


    strategy = normalize_strategy(
        category=recommendation.get(
            "category"
        ),
        source=recommendation.get(
            "source"
        ),
    )


    profile = strategy_profiles.get(
        strategy
    )


    if profile is None:

        return {
            "strategy": strategy,
            "total_measured": 0,
            "success_count": 0,
            "failure_count": 0,
            "neutral_count": 0,
            "average_accuracy": 0,
            "success_rate": 0,
            "learning_score": 0,
            "confidence": 0,
            "status": "No Strategy History",
        }


    return profile


# ============================================================
# STRATEGY-BASED ADJUSTMENT
# ============================================================

def calculate_strategy_adjustment(
    base_score,
    strategy_profile,
):
    base_score = safe_float(
        base_score
    )


    if not isinstance(
        strategy_profile,
        dict,
    ):

        return {
            "adjustment": 0,
            "adjusted_score": base_score,
            "signal": "No historical evidence",
        }


    learning_score = safe_float(
        strategy_profile.get(
            "learning_score",
            0,
        )
    )

    success_rate = safe_float(
        strategy_profile.get(
            "success_rate",
            0,
        )
    )

    measured = int(
        safe_float(
            strategy_profile.get(
                "total_measured",
                0,
            )
        )
    )


    if measured == 0:

        return {
            "adjustment": 0,
            "adjusted_score": base_score,
            "signal": "No strategy history",
        }


    adjustment = 0


    # --------------------------------------------------------
    # Strong positive history
    # --------------------------------------------------------

    if (
        learning_score >= 60
        and success_rate >= 60
    ):

        adjustment = (
            learning_score * 0.15
        )

        signal = (
            "Positive strategy history"
        )


    # --------------------------------------------------------
    # Weak / negative history
    # --------------------------------------------------------

    elif (
        learning_score >= 40
        and success_rate < 40
    ):

        adjustment = -(
            learning_score * 0.15
        )

        signal = (
            "Historical strategy caution"
        )


    else:

        adjustment = 0

        signal = (
            "Neutral strategy history"
        )


    adjusted_score = (
        base_score
        + adjustment
    )


    adjusted_score = max(
        0,
        min(
            100,
            adjusted_score,
        ),
    )


    return {
        "adjustment": round(
            adjustment,
            2,
        ),
        "adjusted_score": round(
            adjusted_score,
            2,
        ),
        "signal": signal,
    }


# ============================================================
# APPLY STRATEGY LEARNING
# ============================================================

def apply_strategy_learning(
    recommendation,
    strategy_profiles,
):
    if not isinstance(
        recommendation,
        dict,
    ):

        return recommendation


    result = recommendation.copy()


    strategy = normalize_strategy(
        category=recommendation.get(
            "category"
        ),
        source=recommendation.get(
            "source"
        ),
    )


    profile = get_strategy_learning(
        recommendation,
        strategy_profiles,
    )


    adjustment = calculate_strategy_adjustment(
        base_score=recommendation.get(
            "score",
            0,
        ),
        strategy_profile=profile,
    )


    result["strategy"] = strategy

    result["strategy_learning"] = (
        profile
    )

    result["strategy_adjustment"] = (
        adjustment["adjustment"]
    )

    result["strategy_learning_signal"] = (
        adjustment["signal"]
    )

    result["base_score"] = safe_float(
        recommendation.get(
            "score",
            0,
        )
    )

    result["score"] = (
        adjustment["adjusted_score"]
    )


    metadata = result.get(
        "metadata",
        {},
    )


    if not isinstance(
        metadata,
        dict,
    ):

        metadata = {}


    metadata = metadata.copy()


    metadata.update({

        "strategy": strategy,

        "strategy_learning_score": (
            profile.get(
                "learning_score",
                0,
            )
        ),

        "strategy_success_rate": (
            profile.get(
                "success_rate",
                0,
            )
        ),

        "strategy_confidence": (
            profile.get(
                "confidence",
                0,
            )
        ),

        "strategy_adjustment": (
            adjustment["adjustment"]
        ),

        "strategy_learning_signal": (
            adjustment["signal"]
        ),

    })


    result["metadata"] = metadata


    return result


# ============================================================
# APPLY TO ALL RECOMMENDATIONS
# ============================================================

def apply_strategy_learning_to_recommendations(
    recommendations,
    strategy_profiles,
):
    if not isinstance(
        recommendations,
        list,
    ):

        return []


    enhanced = []


    for recommendation in recommendations:

        try:

            enhanced.append(
                apply_strategy_learning(
                    recommendation,
                    strategy_profiles,
                )
            )

        except Exception:

            enhanced.append(
                recommendation
            )


    enhanced.sort(
        key=lambda item: (
            safe_float(
                item.get(
                    "score",
                    0,
                )
            ),

            safe_float(
                item.get(
                    "strategy_adjustment",
                    0,
                )
            ),
        ),
        reverse=True,
    )


    return enhanced