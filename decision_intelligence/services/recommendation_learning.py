"""
Smart BI Context-Aware Recommendation Learning Engine

Learns from completed Decision Impact records while keeping
learning relevant to the recommendation category.

The engine supports:

    Opportunity
    Customer Risk
    Anomaly
    Forecast
    Root Cause

Learning is category-aware and does not invent analytical metrics.
"""


import math


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """

    try:
        number = float(value)

        if math.isnan(number) or math.isinf(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def clean_text(value, default=""):
    """
    Safely convert a value to clean text.
    """

    if value is None:
        return default

    text = str(value).strip()

    return text if text else default


# ============================================================
# CATEGORY NORMALIZATION
# ============================================================

def normalize_category(category):
    """
    Normalize recommendation categories so historical
    decisions can be compared consistently.
    """

    category = clean_text(category)

    aliases = {
        "opportunity": "Opportunity",
        "opportunities": "Opportunity",

        "customer risk": "Customer Risk",
        "customer-risk": "Customer Risk",
        "customer_risk": "Customer Risk",
        "risk": "Customer Risk",

        "anomaly": "Anomaly",
        "anomalies": "Anomaly",

        "forecast": "Forecast",
        "forecasting": "Forecast",

        "root cause": "Root Cause",
        "root-cause": "Root Cause",
        "root_cause": "Root Cause",

        "product": "Opportunity",
        "regional": "Opportunity",
        "marketing": "Opportunity",
    }

    normalized = aliases.get(
        category.lower()
    )

    if normalized:
        return normalized

    return category or "Unknown"


# ============================================================
# LEARNING SCORE
# ============================================================

def calculate_learning_score(
    success_count=0,
    failure_count=0,
    average_accuracy=0,
):
    """
    Calculate learning strength from historical outcomes.
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

    total = (
        success_count
        + failure_count
    )

    if total == 0:

        return {
            "learning_score": 0,
            "success_rate": 0,
            "confidence": 0,
            "status": "Insufficient History",
        }

    success_rate = (
        success_count
        / total
    ) * 100

    learning_score = (
        success_rate * 0.60
        +
        average_accuracy * 0.40
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


# ============================================================
# CATEGORY PROFILE
# ============================================================

def build_category_learning_profile(
    impact_records,
):
    """
    Build learning profiles separately for each recommendation
    category.

    Expected record structure:

        {
            "category": "Opportunity",
            "has_measurement": True,
            "impact": "Positive",
            "result": {
                "accuracy": {
                    "revenue": ...,
                    "profit": ...,
                    "units": ...
                }
            }
        }
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

        category = normalize_category(
            record.get(
                "category"
            )
        )

        if category not in profiles:

            profiles[category] = {
                "total_measured": 0,
                "success_count": 0,
                "failure_count": 0,
                "neutral_count": 0,
                "accuracy_values": [],
            }

        profile = profiles[category]

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

        average_accuracy = (
            revenue_accuracy
            +
            profit_accuracy
            +
            units_accuracy
        ) / 3

        profile[
            "accuracy_values"
        ].append(
            average_accuracy
        )

    # --------------------------------------------------------
    # Finalize profiles
    # --------------------------------------------------------

    finalized = {}

    for category, profile in profiles.items():

        accuracy_values = profile[
            "accuracy_values"
        ]

        if accuracy_values:

            average_accuracy = (
                sum(accuracy_values)
                /
                len(accuracy_values)
            )

        else:

            average_accuracy = 0

        learning = calculate_learning_score(
            success_count=profile[
                "success_count"
            ],
            failure_count=profile[
                "failure_count"
            ],
            average_accuracy=average_accuracy,
        )

        finalized[category] = {

            "category": category,

            "total_measured": profile[
                "total_measured"
            ],

            "success_count": profile[
                "success_count"
            ],

            "failure_count": profile[
                "failure_count"
            ],

            "neutral_count": profile[
                "neutral_count"
            ],

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

    return finalized


# ============================================================
# GLOBAL LEARNING PROFILE
# ============================================================

def build_learning_profile(
    impact_records,
):
    """
    Build the overall learning profile.

    This is retained for dashboard compatibility.
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

        if not isinstance(
            record,
            dict,
        ):
            continue

        if not record.get(
            "has_measurement"
        ):
            continue

        impact = clean_text(
            record.get(
                "impact"
            ),
            "Neutral",
        )

        if impact == "Positive":

            success_count += 1

        elif impact == "Negative":

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
                +
                profit_accuracy
                +
                units_accuracy
            ) / 3
        )

    total_measured = (
        success_count
        +
        failure_count
        +
        neutral_count
    )

    if accuracy_values:

        average_accuracy = (
            sum(accuracy_values)
            /
            len(accuracy_values)
        )

    else:

        average_accuracy = 0

    learning = calculate_learning_score(
        success_count=success_count,
        failure_count=failure_count,
        average_accuracy=average_accuracy,
    )

    return {

        "total_measured": total_measured,

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


# ============================================================
# FIND CATEGORY PROFILE
# ============================================================

def get_category_learning_profile(
    recommendation,
    category_profiles,
    global_profile=None,
):
    """
    Select the most relevant learning profile.

    Category-specific history is preferred.

    If no category-specific history exists,
    the global profile is returned only as
    background information and no automatic
    category adjustment is made.
    """

    if not isinstance(
        recommendation,
        dict,
    ):
        return {
            "category": "Unknown",
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

    category = normalize_category(
        recommendation.get(
            "category"
        )
    )

    category_profile = (
        category_profiles.get(
            category
        )
        if isinstance(
            category_profiles,
            dict,
        )
        else None
    )

    if category_profile:

        return category_profile

    return {
        "category": category,
        "total_measured": 0,
        "success_count": 0,
        "failure_count": 0,
        "neutral_count": 0,
        "average_accuracy": 0,
        "learning_score": 0,
        "success_rate": 0,
        "confidence": 0,
        "status": "No Category History",
    }


# ============================================================
# SCORE ADJUSTMENT
# ============================================================

def calculate_recommendation_adjustment(
    base_score,
    learning_score,
    historical_success=False,
    historical_failure=False,
):
    """
    Adjust a recommendation score using relevant
    historical category learning.

    The adjustment is intentionally conservative.
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

    elif historical_failure:

        adjustment -= (
            learning_score * 0.15
        )

    adjusted_score = (
        base_score
        +
        adjustment
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


# ============================================================
# APPLY CATEGORY-AWARE LEARNING
# ============================================================

def apply_learning_to_recommendation(
    recommendation,
    category_profiles,
    global_profile=None,
):
    """
    Apply category-specific historical learning.

    Important:

    A recommendation only receives an automatic
    score adjustment when relevant category history
    exists.

    This prevents unrelated decisions from influencing
    the recommendation.
    """

    if not isinstance(
        recommendation,
        dict,
    ):
        return recommendation

    result = recommendation.copy()

    category = normalize_category(
        recommendation.get(
            "category"
        )
    )

    category_profile = (
        get_category_learning_profile(
            recommendation,
            category_profiles,
            global_profile,
        )
    )

    base_score = safe_float(
        recommendation.get(
            "score",
            0,
        )
    )

    learning_score = safe_float(
        category_profile.get(
            "learning_score",
            0,
        )
    )

    success_rate = safe_float(
        category_profile.get(
            "success_rate",
            0,
        )
    )

    total_measured = int(
        safe_float(
            category_profile.get(
                "total_measured",
                0,
            )
        )
    )

    historical_success = (
        total_measured > 0
        and
        success_rate >= 60
        and
        learning_score >= 60
    )

    historical_failure = (
        total_measured > 0
        and
        success_rate < 40
        and
        learning_score >= 40
    )

    adjustment_result = (
        calculate_recommendation_adjustment(
            base_score=base_score,
            learning_score=learning_score,
            historical_success=historical_success,
            historical_failure=historical_failure,
        )
    )

    adjusted_score = (
        adjustment_result[
            "adjusted_score"
        ]
    )

    result["base_score"] = (
        adjustment_result[
            "base_score"
        ]
    )

    result["learning_adjustment"] = (
        adjustment_result[
            "adjustment"
        ]
    )

    result["score"] = adjusted_score

    # --------------------------------------------------------
    # Learning metadata
    # --------------------------------------------------------

    result["learning_score"] = (
        learning_score
    )

    result["learning_confidence"] = (
        safe_float(
            category_profile.get(
                "confidence",
                0,
            )
        )
    )

    result["historical_success_rate"] = (
        success_rate
    )

    result["learning_category"] = (
        category
    )

    result["learning_history_count"] = (
        total_measured
    )

    # --------------------------------------------------------
    # Learning signal
    # --------------------------------------------------------

    if historical_success:

        result["learning_signal"] = (
            "Strong category-specific historical support"
        )

        result["learning_message"] = (
            f"Previous {category} decisions "
            "show positive measurable outcomes. "
            "This recommendation received additional "
            "support from relevant historical decisions."
        )

        if result.get(
            "priority"
        ) == "Medium":

            result["priority"] = "High"

    elif historical_failure:

        result["learning_signal"] = (
            "Category-specific historical caution"
        )

        result["learning_message"] = (
            f"Previous {category} decisions "
            "show weaker measurable outcomes. "
            "Smart BI applied caution when prioritizing "
            "this recommendation."
        )

        if result.get(
            "priority"
        ) == "Critical":

            result["priority"] = "High"

    elif total_measured > 0:

        result["learning_signal"] = (
            "Limited category-specific evidence"
        )

        result["learning_message"] = (
            f"Smart BI has {total_measured} measured "
            f"{category} decision"
            f"{'s' if total_measured != 1 else ''}, "
            "but the historical evidence is not strong "
            "enough to change the recommendation score."
        )

    else:

        result["learning_signal"] = (
            "No category-specific evidence"
        )

        result["learning_message"] = (
            f"No completed measured {category} "
            "decisions are available yet. "
            "This recommendation is based on the current "
            "analytical evidence."
        )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

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

        "historical_success_rate": (
            success_rate
        ),

        "learning_category": category,

        "learning_history_count": (
            total_measured
        ),

        "learning_signal": result.get(
            "learning_signal",
            "",
        ),

    })

    result["metadata"] = metadata

    return result


# ============================================================
# APPLY TO ALL RECOMMENDATIONS
# ============================================================

def apply_learning_to_recommendations(
    recommendations,
    learning_profile,
    category_profiles=None,
):
    """
    Apply context-aware learning to every recommendation.

    Backward compatible:

        apply_learning_to_recommendations(
            recommendations,
            learning_profile,
        )

    New preferred usage:

        apply_learning_to_recommendations(
            recommendations,
            learning_profile,
            category_profiles,
        )
    """

    if not isinstance(
        recommendations,
        list,
    ):
        return []

    if not isinstance(
        category_profiles,
        dict,
    ):
        category_profiles = {}

    enhanced = []

    for recommendation in recommendations:

        try:

            enhanced_recommendation = (
                apply_learning_to_recommendation(
                    recommendation,
                    category_profiles,
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

    # --------------------------------------------------------
    # Final ranking
    # --------------------------------------------------------

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
                    "learning_adjustment",
                    0,
                )
            ),
        ),
        reverse=True,
    )

    return enhanced

# ============================================================
# MANAGER FEEDBACK LEARNING
# ============================================================

def calculate_feedback_learning_score(
    useful_count=0,
    partially_useful_count=0,
    not_useful_count=0,
    average_rating=0,
):
    """
    Calculate learning strength from explicit manager feedback.

    Feedback weighting:

        Useful            = positive signal
        Partially Useful  = neutral / moderate signal
        Not Useful        = negative signal

    Rating contributes to the overall confidence but does not
    override the explicit feedback decision.
    """

    useful_count = int(
        safe_float(
            useful_count
        )
    )

    partially_useful_count = int(
        safe_float(
            partially_useful_count
        )
    )

    not_useful_count = int(
        safe_float(
            not_useful_count
        )
    )

    average_rating = safe_float(
        average_rating
    )

    total = (
        useful_count
        +
        partially_useful_count
        +
        not_useful_count
    )

    if total == 0:

        return {
            "feedback_learning_score": 0,
            "feedback_success_rate": 0,
            "feedback_confidence": 0,
            "feedback_status": "Insufficient Feedback",
        }

    # --------------------------------------------------------
    # Weighted feedback score
    # --------------------------------------------------------

    weighted_score = (
        useful_count * 100
        +
        partially_useful_count * 50
        +
        not_useful_count * 0
    ) / total

    # --------------------------------------------------------
    # Rating contribution
    # --------------------------------------------------------

    rating_score = (
        average_rating
        / 5
    ) * 100

    feedback_learning_score = (
        weighted_score * 0.70
        +
        rating_score * 0.30
    )

    feedback_learning_score = max(
        0,
        min(
            100,
            feedback_learning_score,
        ),
    )

    # --------------------------------------------------------
    # Feedback success rate
    # --------------------------------------------------------

    feedback_success_rate = (
        (
            useful_count
            +
            (
                partially_useful_count
                * 0.5
            )
        )
        /
        total
    ) * 100

    feedback_success_rate = max(
        0,
        min(
            100,
            feedback_success_rate,
        ),
    )

    # --------------------------------------------------------
    # Confidence
    #
    # More feedback records = stronger confidence.
    # --------------------------------------------------------

    sample_confidence = min(
        100,
        total * 10,
    )

    feedback_confidence = (
        feedback_learning_score
        * 0.70
        +
        sample_confidence
        * 0.30
    )

    feedback_confidence = max(
        0,
        min(
            100,
            feedback_confidence,
        ),
    )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    if total < 2:

        status = "Early Feedback"

    elif feedback_learning_score >= 75:

        status = "Strong Positive Feedback"

    elif feedback_learning_score >= 55:

        status = "Moderate Feedback"

    elif feedback_learning_score >= 40:

        status = "Mixed Feedback"

    else:

        status = "Negative Feedback"

    return {

        "feedback_learning_score": round(
            feedback_learning_score,
            2,
        ),

        "feedback_success_rate": round(
            feedback_success_rate,
            2,
        ),

        "feedback_confidence": round(
            feedback_confidence,
            2,
        ),

        "status": status,
    }


# ============================================================
# BUILD CATEGORY FEEDBACK PROFILE
# ============================================================

def build_category_feedback_profile(
    feedback_records,
):
    """
    Build explicit manager feedback profiles by recommendation
    category.

    Expected record:

        {
            "category": "Opportunity",
            "feedback": "Useful",
            "rating": 5,
        }
    """

    profiles = {}

    if not isinstance(
        feedback_records,
        list,
    ):
        return profiles

    for record in feedback_records:

        if not isinstance(
            record,
            dict,
        ):
            continue

        category = normalize_category(
            record.get(
                "category"
            )
        )

        if category not in profiles:

            profiles[category] = {
                "category": category,
                "total_feedback": 0,
                "useful_count": 0,
                "partially_useful_count": 0,
                "not_useful_count": 0,
                "ratings": [],
            }

        profile = profiles[category]

        profile[
            "total_feedback"
        ] += 1

        feedback = clean_text(
            record.get(
                "feedback"
            ),
            "Partially Useful",
        )

        if feedback == "Useful":

            profile[
                "useful_count"
            ] += 1

        elif feedback == "Not Useful":

            profile[
                "not_useful_count"
            ] += 1

        else:

            profile[
                "partially_useful_count"
            ] += 1

        rating = safe_float(
            record.get(
                "rating",
                3,
            )
        )

        rating = max(
            1,
            min(
                5,
                rating,
            ),
        )

        profile[
            "ratings"
        ].append(
            rating
        )

    # --------------------------------------------------------
    # Finalize profiles
    # --------------------------------------------------------

    finalized = {}

    for category, profile in profiles.items():

        ratings = profile[
            "ratings"
        ]

        if ratings:

            average_rating = (
                sum(ratings)
                /
                len(ratings)
            )

        else:

            average_rating = 0

        learning = (
            calculate_feedback_learning_score(

                useful_count=profile[
                    "useful_count"
                ],

                partially_useful_count=profile[
                    "partially_useful_count"
                ],

                not_useful_count=profile[
                    "not_useful_count"
                ],

                average_rating=average_rating,
            )
        )

        finalized[category] = {

            "category": category,

            "total_feedback": profile[
                "total_feedback"
            ],

            "useful_count": profile[
                "useful_count"
            ],

            "partially_useful_count": profile[
                "partially_useful_count"
            ],

            "not_useful_count": profile[
                "not_useful_count"
            ],

            "average_rating": round(
                average_rating,
                2,
            ),

            "feedback_learning_score": (
                learning[
                    "feedback_learning_score"
                ]
            ),

            "feedback_success_rate": (
                learning[
                    "feedback_success_rate"
                ]
            ),

            "feedback_confidence": (
                learning[
                    "feedback_confidence"
                ]
            ),

            "status": learning[
                "status"
            ],
        }

    return finalized


# ============================================================
# GLOBAL FEEDBACK PROFILE
# ============================================================

def build_feedback_learning_profile(
    feedback_records,
):
    """
    Build an overall manager feedback learning profile.
    """

    if not isinstance(
        feedback_records,
        list,
    ):

        feedback_records = []

    useful_count = 0
    partially_useful_count = 0
    not_useful_count = 0
    ratings = []

    for record in feedback_records:

        if not isinstance(
            record,
            dict,
        ):
            continue

        feedback = clean_text(
            record.get(
                "feedback"
            ),
            "Partially Useful",
        )

        if feedback == "Useful":

            useful_count += 1

        elif feedback == "Not Useful":

            not_useful_count += 1

        else:

            partially_useful_count += 1

        rating = safe_float(
            record.get(
                "rating",
                3,
            )
        )

        rating = max(
            1,
            min(
                5,
                rating,
            ),
        )

        ratings.append(
            rating
        )

    total_feedback = (
        useful_count
        +
        partially_useful_count
        +
        not_useful_count
    )

    if ratings:

        average_rating = (
            sum(ratings)
            /
            len(ratings)
        )

    else:

        average_rating = 0

    learning = (
        calculate_feedback_learning_score(

            useful_count=useful_count,

            partially_useful_count=(
                partially_useful_count
            ),

            not_useful_count=(
                not_useful_count
            ),

            average_rating=average_rating,
        )
    )

    return {

        "total_feedback": total_feedback,

        "useful_count": useful_count,

        "partially_useful_count": (
            partially_useful_count
        ),

        "not_useful_count": (
            not_useful_count
        ),

        "average_rating": round(
            average_rating,
            2,
        ),

        "feedback_learning_score": (
            learning[
                "feedback_learning_score"
            ]
        ),

        "feedback_success_rate": (
            learning[
                "feedback_success_rate"
            ]
        ),

        "feedback_confidence": (
            learning[
                "feedback_confidence"
            ]
        ),

        "status": learning[
            "status"
        ],
    }


# ============================================================
# FEEDBACK PROFILE FOR RECOMMENDATION
# ============================================================

def get_category_feedback_profile(
    recommendation,
    feedback_profiles,
):
    """
    Return the feedback history relevant to the current
    recommendation category.
    """

    if not isinstance(
        recommendation,
        dict,
    ):

        return {
            "category": "Unknown",
            "total_feedback": 0,
            "useful_count": 0,
            "partially_useful_count": 0,
            "not_useful_count": 0,
            "average_rating": 0,
            "feedback_learning_score": 0,
            "feedback_success_rate": 0,
            "feedback_confidence": 0,
            "status": "Insufficient Feedback",
        }

    category = normalize_category(
        recommendation.get(
            "category"
        )
    )

    if not isinstance(
        feedback_profiles,
        dict,
    ):

        feedback_profiles = {}

    profile = feedback_profiles.get(
        category
    )

    if profile:

        return profile

    return {

        "category": category,

        "total_feedback": 0,

        "useful_count": 0,

        "partially_useful_count": 0,

        "not_useful_count": 0,

        "average_rating": 0,

        "feedback_learning_score": 0,

        "feedback_success_rate": 0,

        "feedback_confidence": 0,

        "status": "No Category Feedback",
    }


# ============================================================
# FEEDBACK SCORE ADJUSTMENT
# ============================================================

def calculate_feedback_adjustment(
    base_score,
    feedback_learning_score,
    feedback_success_rate,
    total_feedback,
):
    """
    Apply a conservative score adjustment based on manager
    feedback.

    No adjustment is made when there is insufficient history.
    """

    base_score = safe_float(
        base_score
    )

    feedback_learning_score = safe_float(
        feedback_learning_score
    )

    feedback_success_rate = safe_float(
        feedback_success_rate
    )

    total_feedback = int(
        safe_float(
            total_feedback
        )
    )

    adjustment = 0

    # --------------------------------------------------------
    # Minimum history requirement
    # --------------------------------------------------------

    if total_feedback >= 2:

        # Strong positive feedback
        if (
            feedback_success_rate >= 70
            and
            feedback_learning_score >= 65
        ):

            adjustment = (
                feedback_learning_score
                * 0.10
            )

        # Strong negative feedback
        elif (
            feedback_success_rate < 40
            and
            feedback_learning_score < 50
        ):

            adjustment = -(
                (
                    100
                    -
                    feedback_learning_score
                )
                * 0.10
            )

        # Mixed feedback
        else:

            adjustment = 0

    adjusted_score = (
        base_score
        +
        adjustment
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

        "feedback_adjustment": round(
            adjustment,
            2,
        ),

        "adjusted_score": round(
            adjusted_score,
            2,
        ),
    }


# ============================================================
# APPLY FEEDBACK TO RECOMMENDATION
# ============================================================

def apply_feedback_to_recommendation(
    recommendation,
    feedback_profiles,
):
    """
    Apply category-aware manager feedback learning to a
    recommendation.
    """

    if not isinstance(
        recommendation,
        dict,
    ):

        return recommendation

    result = recommendation.copy()

    feedback_profile = (
        get_category_feedback_profile(
            recommendation,
            feedback_profiles,
        )
    )

    total_feedback = int(
        safe_float(
            feedback_profile.get(
                "total_feedback",
                0,
            )
        )
    )

    feedback_learning_score = safe_float(
        feedback_profile.get(
            "feedback_learning_score",
            0,
        )
    )

    feedback_success_rate = safe_float(
        feedback_profile.get(
            "feedback_success_rate",
            0,
        )
    )

    average_rating = safe_float(
        feedback_profile.get(
            "average_rating",
            0,
        )
    )

    adjustment = (
        calculate_feedback_adjustment(

            base_score=safe_float(
                recommendation.get(
                    "score",
                    0,
                )
            ),

            feedback_learning_score=(
                feedback_learning_score
            ),

            feedback_success_rate=(
                feedback_success_rate
            ),

            total_feedback=total_feedback,
        )
    )

    result[
        "feedback_adjustment"
    ] = adjustment[
        "feedback_adjustment"
    ]

    result[
        "feedback_learning_score"
    ] = feedback_learning_score

    result[
        "feedback_confidence"
    ] = safe_float(
        feedback_profile.get(
            "feedback_confidence",
            0,
        )
    )

    result[
        "feedback_success_rate"
    ] = feedback_success_rate

    result[
        "feedback_average_rating"
    ] = average_rating

    result[
        "feedback_history_count"
    ] = total_feedback

    result[
        "feedback_category"
    ] = normalize_category(
        recommendation.get(
            "category"
        )
    )

    # --------------------------------------------------------
    # Feedback signal
    # --------------------------------------------------------

    if total_feedback == 0:

        result[
            "feedback_signal"
        ] = "No manager feedback yet"

        result[
            "feedback_message"
        ] = (
            "Smart BI has not received explicit manager "
            "feedback for this recommendation category yet."
        )

    elif total_feedback < 2:

        result[
            "feedback_signal"
        ] = "Early manager feedback"

        result[
            "feedback_message"
        ] = (
            f"Smart BI has received {total_feedback} "
            "feedback record. More feedback is needed "
            "before it influences recommendation scoring."
        )

    elif (
        feedback_success_rate >= 70
        and
        feedback_learning_score >= 65
    ):

        result[
            "feedback_signal"
        ] = "Strong positive manager feedback"

        result[
            "feedback_message"
        ] = (
            f"Managers have provided positive feedback "
            f"for {result['feedback_category']} recommendations. "
            "Smart BI increased support for this recommendation."
        )

        if result.get(
            "priority"
        ) == "Medium":

            result[
                "priority"
            ] = "High"

    elif (
        feedback_success_rate < 40
        and
        feedback_learning_score < 50
    ):

        result[
            "feedback_signal"
        ] = "Negative manager feedback"

        result[
            "feedback_message"
        ] = (
            f"Historical manager feedback for "
            f"{result['feedback_category']} recommendations "
            "has been weak. Smart BI applied a conservative "
            "score reduction."
        )

        if result.get(
            "priority"
        ) == "Critical":

            result[
                "priority"
            ] = "High"

    else:

        result[
            "feedback_signal"
        ] = "Mixed manager feedback"

        result[
            "feedback_message"
        ] = (
            f"Manager feedback for "
            f"{result['feedback_category']} recommendations "
            "is mixed. Smart BI did not apply a strong "
            "automatic adjustment."
        )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

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

        "feedback_adjustment": (
            result.get(
                "feedback_adjustment",
                0,
            )
        ),

        "feedback_learning_score": (
            feedback_learning_score
        ),

        "feedback_confidence": (
            result.get(
                "feedback_confidence",
                0,
            )
        ),

        "feedback_success_rate": (
            feedback_success_rate
        ),

        "feedback_average_rating": (
            average_rating
        ),

        "feedback_history_count": (
            total_feedback
        ),

        "feedback_category": (
            result.get(
                "feedback_category",
                "",
            )
        ),

        "feedback_signal": (
            result.get(
                "feedback_signal",
                "",
            )
        ),
    })

    result[
        "metadata"
    ] = metadata

    return result


# ============================================================
# APPLY FEEDBACK TO ALL RECOMMENDATIONS
# ============================================================

def apply_feedback_to_recommendations(
    recommendations,
    feedback_profiles,
):
    """
    Apply manager feedback learning to all recommendations.
    """

    if not isinstance(
        recommendations,
        list,
    ):

        return []

    if not isinstance(
        feedback_profiles,
        dict,
    ):

        feedback_profiles = {}

    enhanced = []

    for recommendation in recommendations:

        try:

            enhanced_recommendation = (
                apply_feedback_to_recommendation(
                    recommendation,
                    feedback_profiles,
                )
            )

            enhanced.append(
                enhanced_recommendation
            )

        except Exception:

            enhanced.append(
                recommendation
            )

    # --------------------------------------------------------
    # Re-rank recommendations
    # --------------------------------------------------------

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
                    "feedback_adjustment",
                    0,
                )
            ),

            safe_float(
                item.get(
                    "learning_adjustment",
                    0,
                )
            ),
        ),
        reverse=True,
    )

    return enhanced