"""
Smart BI Recommendation Explainability Engine

Converts a recommendation produced by the Decision Intelligence engine
into a human-readable explanation.

The engine does not create or invent analytical metrics.
It only uses information already available inside the recommendation.
"""


def safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """
    try:
        number = float(value)

        if number != number:
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


def get_source_explanation(source, category):
    """
    Explain where the recommendation came from.
    """

    source_text = clean_text(source)

    category_text = clean_text(
        category,
        "Smart BI Analysis",
    )

    explanations = {
        "Opportunity Detection": (
            "Smart BI identified a business opportunity by analyzing "
            "growth and performance signals in the selected dataset."
        ),

        "Customer Risk": (
            "Smart BI identified customer-related risk using behavioral "
            "and customer-value signals available in the analysis."
        ),

        "Anomaly Detection": (
            "Smart BI detected an unusual business pattern that differs "
            "from the normal behavior identified by the anomaly engine."
        ),

        "Forecasting": (
            "Smart BI used historical business behavior and forecasting "
            "signals to identify a potential future change."
        ),

        "Root Cause": (
            "Smart BI identified a business dimension that contributes "
            "to a measured change in performance."
        ),

        "Decision Engine": (
            "Smart BI combined signals from the analytical engines and "
            "converted them into a prioritized business decision."
        ),
    }

    if source_text in explanations:
        return explanations[source_text]

    category_explanations = {
        "Opportunity": (
            "The recommendation is based on an opportunity signal "
            "identified in the business data."
        ),

        "Customer Risk": (
            "The recommendation is based on customer behavior and "
            "risk-related signals."
        ),

        "Anomaly": (
            "The recommendation is based on an unusual pattern "
            "detected in the business data."
        ),

        "Forecast": (
            "The recommendation is based on a forecast of future "
            "business performance."
        ),

        "Root Cause": (
            "The recommendation is based on a contributing factor "
            "identified through root-cause analysis."
        ),
    }

    if category_text in category_explanations:
        return category_explanations[category_text]

    if source_text:
        return (
            f"The recommendation was generated from the "
            f"{source_text} intelligence signal."
        )

    return (
        "The recommendation was generated from the available "
        "Smart BI analytical signals."
    )


def build_evidence(recommendation):
    """
    Build evidence items from information already present
    in the recommendation.

    No new analytical values are generated here.
    """

    evidence = []

    trigger = clean_text(
        recommendation.get("trigger")
    )

    if trigger:
        evidence.append({
            "label": "Detected signal",
            "value": trigger,
        })

    reason = clean_text(
        recommendation.get("reason")
    )

    if reason:
        evidence.append({
            "label": "Business evidence",
            "value": reason,
        })

    expected_impact = clean_text(
        recommendation.get("expected_impact")
    )

    if expected_impact:
        evidence.append({
            "label": "Expected impact",
            "value": expected_impact,
        })

    source = clean_text(
        recommendation.get("source")
    )

    if source:
        evidence.append({
            "label": "Analysis source",
            "value": source,
        })

    category = clean_text(
        recommendation.get("category")
    )

    if category:
        evidence.append({
            "label": "Decision category",
            "value": category,
        })

    metadata = recommendation.get(
        "metadata",
        {},
    )

    if isinstance(metadata, dict):

        metadata_labels = {
            "growth": "Growth signal",
            "change": "Performance change",
            "percent_change": "Percentage change",
            "revenue": "Revenue signal",
            "quantity": "Quantity signal",
            "transactions": "Transaction signal",
            "risk_score": "Risk score",
            "recency": "Customer recency",
            "frequency": "Customer frequency",
            "monetary": "Customer monetary value",
            "z_score": "Anomaly score",
            "impact": "Detected impact",
            "forecast_change": "Forecast change",
        }

        for key, label in metadata_labels.items():

            if key not in metadata:
                continue

            value = metadata.get(key)

            if value is None:
                continue

            if isinstance(value, str) and not value.strip():
                continue

            evidence.append({
                "label": label,
                "value": value,
            })

    if not evidence:
        evidence.append({
            "label": "Evidence",
            "value": (
                "Evidence is not available in the current "
                "analysis output."
            ),
        })

    return evidence


def build_business_reason(recommendation):
    """
    Build the business-level explanation.
    """

    reason = clean_text(
        recommendation.get("reason")
    )

    if reason:
        return reason

    category = clean_text(
        recommendation.get("category"),
        "business",
    )

    return (
        f"Smart BI identified a {category.lower()} signal "
        "that may require management attention."
    )


def build_decision_logic(recommendation):
    """
    Explain how the recommendation was prioritized.
    """

    category = clean_text(
        recommendation.get("category"),
        "Smart BI",
    )

    priority = clean_text(
        recommendation.get("priority"),
        "Medium",
    )

    score = safe_float(
        recommendation.get("score", 0)
    )

    category_logic_map = {

        "Opportunity": (
            "The Decision Engine evaluates the opportunity signal "
            "using the performance evidence produced by Opportunity "
            "Detection."
        ),

        "Customer Risk": (
            "The Decision Engine evaluates the customer risk signal "
            "using customer behavior and risk evidence produced by "
            "Customer Risk analysis."
        ),

        "Anomaly": (
            "The Decision Engine evaluates the unusual signal and "
            "prioritizes it according to the severity produced by "
            "Anomaly Detection."
        ),

        "Forecast": (
            "The Decision Engine evaluates the projected business "
            "direction and prioritizes the recommendation according "
            "to the forecast signal."
        ),

        "Root Cause": (
            "The Decision Engine evaluates the identified contributing "
            "factor and prioritizes it according to the performance "
            "change detected by Root Cause Analysis."
        ),
    }

    category_logic = category_logic_map.get(
        category,
        (
            "The Decision Engine combines the available analytical "
            "signals before assigning a recommendation priority."
        ),
    )

    if score >= 80:
        score_logic = (
            f"The recommendation received a high decision score "
            f"of {score:.1f}/100."
        )

    elif score >= 60:
        score_logic = (
            f"The recommendation received a moderate-to-high "
            f"decision score of {score:.1f}/100."
        )

    elif score > 0:
        score_logic = (
            f"The recommendation received a decision score of "
            f"{score:.1f}/100."
        )

    else:
        score_logic = (
            "A numerical decision score is not available from the "
            "current analysis output."
        )

    priority_logic = (
        f"The final recommendation priority is {priority}. "
        "Priority reflects the decision engine's assessment of "
        "the available business signal."
    )

    return {
        "category_logic": category_logic,
        "score_logic": score_logic,
        "priority_logic": priority_logic,
    }


def build_confidence(recommendation):
    """
    Build a transparent confidence explanation.

    The score is used as the primary decision confidence indicator.
    Historical learning confidence is shown separately when available.
    """

    score = safe_float(
        recommendation.get("score", 0)
    )

    learning_confidence = safe_float(
        recommendation.get(
            "learning_confidence",
            0,
        )
    )

    if score >= 80:
        level = "High"

        message = (
            "The recommendation has a strong decision score based "
            "on the analytical evidence currently available."
        )

    elif score >= 60:
        level = "Moderate"

        message = (
            "The recommendation has meaningful analytical support, "
            "but additional evidence can strengthen confidence."
        )

    elif score > 0:
        level = "Developing"

        message = (
            "The recommendation has some analytical support, "
            "but the available evidence is not yet strong."
        )

    else:
        level = "Limited"

        message = (
            "A reliable numerical confidence level is not available "
            "from the current recommendation output."
        )

    if learning_confidence > 0:

        message += (
            f" Historical learning confidence is "
            f"{learning_confidence:.1f}/100."
        )

    return {
        "score": round(score, 2),
        "level": level,
        "message": message,
    }


def build_learning_explanation(recommendation):
    """
    Explain how historical decision learning affected
    this recommendation.
    """

    adjustment = safe_float(
        recommendation.get(
            "learning_adjustment",
            0,
        )
    )

    learning_score = safe_float(
        recommendation.get(
            "learning_score",
            0,
        )
    )

    learning_signal = clean_text(
        recommendation.get(
            "learning_signal"
        )
    )

    learning_message = clean_text(
        recommendation.get(
            "learning_message"
        )
    )

    if adjustment > 0:

        effect = "Historical support increased confidence"

        summary = (
            f"Historical decision learning increased the "
            f"recommendation score by {adjustment:.1f} points."
        )

    elif adjustment < 0:

        effect = "Historical caution reduced confidence"

        summary = (
            f"Historical decision learning reduced the "
            f"recommendation score by {abs(adjustment):.1f} points."
        )

    else:

        effect = "No historical score adjustment"

        summary = (
            "Historical decision learning did not change the "
            "recommendation score."
        )

    if learning_score > 0:

        summary += (
            f" The current learning score is "
            f"{learning_score:.1f}/100."
        )

    if not learning_message:

        if learning_signal:

            learning_message = learning_signal

        else:

            learning_message = (
                "No additional historical learning explanation "
                "is available."
            )

    return {
        "effect": effect,
        "adjustment": round(adjustment, 2),
        "learning_score": round(
            learning_score,
            2,
        ),
        "summary": summary,
        "message": learning_message,
    }


def build_recommendation_summary(
    recommendation,
    confidence,
    learning,
):
    """
    Create the short executive explanation shown first.
    """

    title = clean_text(
        recommendation.get("title"),
        "This recommendation",
    )

    category = clean_text(
        recommendation.get("category"),
        "business",
    )

    priority = clean_text(
        recommendation.get("priority"),
        "Medium",
    )

    trigger = clean_text(
        recommendation.get("trigger")
    )

    if trigger:

        summary = (
            f"{title} was generated because Smart BI detected "
            f"{trigger}."
        )

    else:

        summary = (
            f"{title} was generated from the available "
            f"{category.lower()} intelligence signals."
        )

    summary += (
        f" The decision is classified as {priority} priority "
        f"with {confidence['level'].lower()} confidence."
    )

    if learning["adjustment"] > 0:

        summary += (
            " Historical decision learning provided additional "
            "support for this recommendation."
        )

    elif learning["adjustment"] < 0:

        summary += (
            " Historical decision learning introduced caution "
            "when prioritizing this recommendation."
        )

    return summary


def build_recommendation_explanation(
    recommendation
):
    """
    Main explainability function.

    Returns a structured explanation that can be directly
    consumed by the Django template.
    """

    if not isinstance(
        recommendation,
        dict,
    ):
        recommendation = {}

    category = clean_text(
        recommendation.get("category"),
        "Smart BI Insight",
    )

    source = clean_text(
        recommendation.get("source"),
        category,
    )

    trigger = clean_text(
        recommendation.get("trigger"),
        "No specific trigger was provided by the analysis engine.",
    )

    business_reason = build_business_reason(
        recommendation
    )

    decision_logic = build_decision_logic(
        recommendation
    )

    confidence = build_confidence(
        recommendation
    )

    learning = build_learning_explanation(
        recommendation
    )

    evidence = build_evidence(
        recommendation
    )

    source_explanation = get_source_explanation(
        source,
        category,
    )

    recommended_action = clean_text(
        recommendation.get("recommendation"),
        "Review the available evidence before taking action.",
    )

    summary = build_recommendation_summary(
        recommendation,
        confidence,
        learning,
    )

    return {
        "source": source,
        "source_explanation": source_explanation,

        "trigger": trigger,

        "business_reason": business_reason,

        "decision_logic": decision_logic,

        "evidence": evidence,

        "confidence": confidence,

        "learning": learning,

        "recommended_action": recommended_action,

        "summary": summary,
    }


def add_explanations_to_recommendations(
    recommendations
):
    """
    Add an explanation object to every recommendation.
    """

    if not isinstance(
        recommendations,
        list,
    ):
        return []

    enhanced = []

    for recommendation in recommendations:

        if not isinstance(
            recommendation,
            dict,
        ):
            continue

        result = recommendation.copy()

        result["explanation"] = (
            build_recommendation_explanation(
                result
            )
        )

        enhanced.append(result)

    return enhanced