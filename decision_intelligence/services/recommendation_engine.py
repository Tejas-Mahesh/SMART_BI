"""
Smart BI Recommendation Engine

Consumes outputs from Advanced Insights and converts them
into actionable business recommendations.

Input:
    Opportunity Detection
    Customer Risk
    Anomaly Detection
    Forecasting
    Root Cause Analysis

Output:
    Prioritized business recommendations
"""

from typing import Any, Dict, List


# -------------------------------------------------------------------
# PRIORITY CONFIGURATION
# -------------------------------------------------------------------

PRIORITY_ORDER = {
    "Critical": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4,
}


# -------------------------------------------------------------------
# BASIC HELPERS
# -------------------------------------------------------------------

def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.replace("%", "").replace(",", "").strip()

        return float(value)

    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def clean_text(value, default=""):
    if value is None:
        return default

    return str(value).strip()


def normalize_list(value):
    """
    Ensures a value is always returned as a list.
    """

    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return [value]


# -------------------------------------------------------------------
# RECOMMENDATION CREATOR
# -------------------------------------------------------------------

def create_recommendation(
    title,
    category,
    priority,
    trigger,
    recommendation,
    reason="",
    expected_impact="",
    action_type="Review",
    score=0,
    source="Advanced Insights",
    metadata=None,
):
    """
    Creates one standardized recommendation object.
    """

    return {
        "title": clean_text(title, "Business Recommendation"),
        "category": clean_text(category, "General"),
        "priority": clean_text(priority, "Medium"),
        "trigger": clean_text(trigger),
        "recommendation": clean_text(recommendation),
        "reason": clean_text(reason),
        "expected_impact": clean_text(expected_impact),
        "action_type": clean_text(action_type, "Review"),
        "score": round(safe_float(score), 2),
        "source": clean_text(source, "Advanced Insights"),
        "metadata": metadata or {},
    }


# -------------------------------------------------------------------
# OPPORTUNITY RECOMMENDATIONS
# -------------------------------------------------------------------

def process_opportunities(opportunity_results):
    recommendations = []

    if not opportunity_results:
        return recommendations

    opportunities = (
        opportunity_results.get("opportunities")
        or opportunity_results.get("results")
        or opportunity_results.get("items")
        or []
    )

    for opportunity in normalize_list(opportunities):

        if not isinstance(opportunity, dict):
            continue

        area = (
            opportunity.get("name")
            or opportunity.get("product")
            or opportunity.get("customer")
            or opportunity.get("region")
            or opportunity.get("dimension_value")
            or opportunity.get("area")
            or "Business Area"
        )

        category = (
            opportunity.get("category")
            or opportunity.get("dataset_type")
            or "Business"
        )

        score = safe_float(
            opportunity.get("score")
            or opportunity.get("opportunity_score")
            or opportunity.get("rating")
        )

        growth = safe_float(
            opportunity.get("growth")
            or opportunity.get("growth_rate")
            or opportunity.get("change_percent")
            or opportunity.get("percentage_change")
        )

        classification = clean_text(
            opportunity.get("classification")
            or opportunity.get("status")
            or opportunity.get("class")
            or ""
        )

        revenue = safe_float(
            opportunity.get("revenue")
            or opportunity.get("sales")
            or opportunity.get("monetary")
        )

        # -----------------------------------------------------------
        # HIGH OPPORTUNITY
        # -----------------------------------------------------------

        if score >= 75 or classification.lower() == "high":

            recommendations.append(
                create_recommendation(
                    title=f"Scale {area}",
                    category=category,
                    priority="Critical",
                    trigger=f"Opportunity score {score:.0f}/100",
                    recommendation=(
                        f"Increase focus on {area}. "
                        f"Consider additional inventory, marketing exposure, "
                        f"sales resources, or operational capacity."
                    ),
                    reason=(
                        f"{area} is showing strong business potential"
                        f"{f' with approximately {growth:.1f}% growth' if growth else ''}."
                    ),
                    expected_impact=(
                        "Potential revenue growth and stronger business performance."
                    ),
                    action_type="Scale",
                    score=score,
                    source="Opportunity Detection",
                    metadata={
                        "growth": growth,
                        "revenue": revenue,
                        "classification": classification,
                    },
                )
            )

        # -----------------------------------------------------------
        # STRONG OPPORTUNITY
        # -----------------------------------------------------------

        elif score >= 60 or classification.lower() == "strong":

            recommendations.append(
                create_recommendation(
                    title=f"Expand {area}",
                    category=category,
                    priority="High",
                    trigger=f"Strong opportunity score {score:.0f}/100",
                    recommendation=(
                        f"Increase investment in {area} gradually "
                        f"and monitor whether the positive trend continues."
                    ),
                    reason=(
                        f"{area} is demonstrating positive business signals."
                    ),
                    expected_impact=(
                        "Improved revenue contribution and growth potential."
                    ),
                    action_type="Expand",
                    score=score,
                    source="Opportunity Detection",
                    metadata={
                        "growth": growth,
                        "revenue": revenue,
                        "classification": classification,
                    },
                )
            )

        # -----------------------------------------------------------
        # EMERGING OPPORTUNITY
        # -----------------------------------------------------------

        elif score >= 50 or classification.lower() == "emerging":

            recommendations.append(
                create_recommendation(
                    title=f"Monitor {area} Growth",
                    category=category,
                    priority="Medium",
                    trigger=f"Emerging opportunity score {score:.0f}/100",
                    recommendation=(
                        f"Monitor {area} closely and test targeted "
                        f"growth initiatives before making a larger investment."
                    ),
                    reason=(
                        f"{area} has emerging positive signals but requires "
                        f"additional validation."
                    ),
                    expected_impact=(
                        "Identify future growth opportunities with controlled risk."
                    ),
                    action_type="Monitor",
                    score=score,
                    source="Opportunity Detection",
                    metadata={
                        "growth": growth,
                        "revenue": revenue,
                        "classification": classification,
                    },
                )
            )

    return recommendations


# -------------------------------------------------------------------
# CUSTOMER RISK RECOMMENDATIONS
# -------------------------------------------------------------------

def process_customer_risk(risk_results):
    recommendations = []

    if not risk_results:
        return recommendations

    customers = (
        risk_results.get("customers")
        or risk_results.get("results")
        or risk_results.get("customer_risk")
        or risk_results.get("items")
        or []
    )

    high_risk_count = 0
    at_risk_count = 0

    for customer in normalize_list(customers):

        if not isinstance(customer, dict):
            continue

        customer_name = (
            customer.get("customer_name")
            or customer.get("customer_id")
            or customer.get("name")
            or "Customer"
        )

        risk_level = clean_text(
            customer.get("risk_level")
            or customer.get("risk_class")
            or customer.get("classification")
            or customer.get("status")
            or ""
        )

        risk_score = safe_float(
            customer.get("risk_score")
            or customer.get("score")
        )

        recency = safe_float(
            customer.get("recency")
            or customer.get("recency_days")
        )

        if risk_level.lower() in ["high risk", "high"] or risk_score >= 75:
            high_risk_count += 1

            recommendations.append(
                create_recommendation(
                    title=f"Retain {customer_name}",
                    category="Customer",
                    priority="Critical",
                    trigger=f"High customer risk score {risk_score:.0f}/100",
                    recommendation=(
                        f"Launch a targeted retention action for {customer_name}. "
                        f"Review recent purchasing behavior and provide a "
                        f"personalized re-engagement offer."
                    ),
                    reason=(
                        f"The customer is classified as high risk"
                        f"{f' with {recency:.0f} days since last activity' if recency else ''}."
                    ),
                    expected_impact=(
                        "Reduce customer churn and protect existing revenue."
                    ),
                    action_type="Retain",
                    score=risk_score,
                    source="Customer Risk",
                    metadata={
                        "risk_score": risk_score,
                        "recency": recency,
                    },
                )
            )

        elif risk_level.lower() in ["at risk", "medium risk"] or risk_score >= 55:
            at_risk_count += 1

            recommendations.append(
                create_recommendation(
                    title=f"Re-engage {customer_name}",
                    category="Customer",
                    priority="High",
                    trigger=f"Customer risk score {risk_score:.0f}/100",
                    recommendation=(
                        f"Send a personalized re-engagement campaign to "
                        f"{customer_name} and monitor their next purchase."
                    ),
                    reason="Customer behavior indicates an increasing risk of inactivity.",
                    expected_impact=(
                        "Increase repeat purchases and improve customer retention."
                    ),
                    action_type="Re-engage",
                    score=risk_score,
                    source="Customer Risk",
                    metadata={
                        "risk_score": risk_score,
                        "recency": recency,
                    },
                )
            )

    # Aggregate recommendation
    if high_risk_count > 0:

        recommendations.append(
            create_recommendation(
                title="Launch Customer Retention Campaign",
                category="Customer",
                priority="Critical",
                trigger=f"{high_risk_count} high-risk customer(s) detected",
                recommendation=(
                    "Create a targeted retention campaign for high-risk "
                    "customers instead of using one generic campaign."
                ),
                reason=(
                    "Customer Risk Analysis identified customers with a "
                    "significant probability of disengagement."
                ),
                expected_impact=(
                    "Protect customer lifetime value and reduce churn."
                ),
                action_type="Campaign",
                score=min(100, 70 + high_risk_count),
                source="Customer Risk",
                metadata={
                    "high_risk_customers": high_risk_count,
                    "at_risk_customers": at_risk_count,
                },
            )
        )

    return recommendations


# -------------------------------------------------------------------
# ANOMALY RECOMMENDATIONS
# -------------------------------------------------------------------

def process_anomalies(anomaly_results):
    recommendations = []

    if not anomaly_results:
        return recommendations

    anomalies = (
        anomaly_results.get("anomalies")
        or anomaly_results.get("results")
        or anomaly_results.get("items")
        or []
    )

    for anomaly in normalize_list(anomalies):

        if not isinstance(anomaly, dict):
            continue

        date = (
            anomaly.get("date")
            or anomaly.get("period")
            or anomaly.get("timestamp")
            or "Recent period"
        )

        anomaly_type = clean_text(
            anomaly.get("type")
            or anomaly.get("anomaly_type")
            or anomaly.get("direction")
            or "Unexpected change"
        )

        severity = clean_text(
            anomaly.get("severity")
            or anomaly.get("status")
            or ""
        )

        z_score = safe_float(
            anomaly.get("z_score")
            or anomaly.get("zscore")
        )

        impact = safe_float(
            anomaly.get("impact")
            or anomaly.get("difference")
            or anomaly.get("deviation")
        )

        critical = (
            severity.lower() == "critical"
            or z_score >= 3
        )

        if critical:

            recommendations.append(
                create_recommendation(
                    title="Investigate Critical Anomaly",
                    category="Operations",
                    priority="Critical",
                    trigger=f"{anomaly_type} detected on {date}",
                    recommendation=(
                        "Investigate the underlying transaction, operational, "
                        "marketing, pricing, or inventory cause immediately."
                    ),
                    reason=(
                        "The anomaly is statistically significant and may "
                        "represent an operational problem or an unusual business event."
                    ),
                    expected_impact=(
                        "Reduce the risk of recurring unexpected business losses."
                    ),
                    action_type="Investigate",
                    score=min(100, max(75, abs(z_score) * 20)),
                    source="Anomaly Detection",
                    metadata={
                        "date": str(date),
                        "anomaly_type": anomaly_type,
                        "z_score": z_score,
                        "impact": impact,
                    },
                )
            )

        elif severity.lower() in ["high", "warning"] or z_score >= 2:

            recommendations.append(
                create_recommendation(
                    title="Monitor Business Anomaly",
                    category="Operations",
                    priority="Medium",
                    trigger=f"Unusual {anomaly_type} detected",
                    recommendation=(
                        "Monitor the affected period and compare it with "
                        "historical business patterns."
                    ),
                    reason=(
                        "The observed value differs materially from the expected pattern."
                    ),
                    expected_impact=(
                        "Detect recurring problems before they become critical."
                    ),
                    action_type="Monitor",
                    score=min(100, max(50, abs(z_score) * 20)),
                    source="Anomaly Detection",
                    metadata={
                        "date": str(date),
                        "anomaly_type": anomaly_type,
                        "z_score": z_score,
                        "impact": impact,
                    },
                )
            )

    return recommendations


# -------------------------------------------------------------------
# FORECAST RECOMMENDATIONS
# -------------------------------------------------------------------

def process_forecast(forecast_results):
    recommendations = []

    if not forecast_results:
        return recommendations

    summary = forecast_results.get("summary") or {}

    forecast_change = safe_float(
        summary.get("forecast_change")
        or summary.get("change")
        or summary.get("forecast_change_percent")
        or forecast_results.get("forecast_change")
    )

    direction = clean_text(
        summary.get("direction")
        or forecast_results.get("direction")
        or ""
    )

    forecast_avg = safe_float(
        summary.get("forecast_avg")
        or forecast_results.get("forecast_avg")
    )

    forecast_total = safe_float(
        summary.get("forecast_total")
        or forecast_results.get("forecast_total")
    )

    if forecast_change >= 15:

        recommendations.append(
            create_recommendation(
                title="Prepare for Forecasted Growth",
                category="Forecasting",
                priority="High",
                trigger=f"Forecast indicates {forecast_change:.1f}% growth",
                recommendation=(
                    "Prepare inventory, staffing, marketing capacity, "
                    "and operational resources for the expected increase."
                ),
                reason=(
                    "Forecasting indicates a meaningful positive future trend."
                ),
                expected_impact=(
                    "Reduce missed sales caused by insufficient capacity."
                ),
                action_type="Prepare",
                score=min(100, 60 + forecast_change),
                source="Forecasting",
                metadata={
                    "forecast_change": forecast_change,
                    "direction": direction,
                    "forecast_avg": forecast_avg,
                    "forecast_total": forecast_total,
                },
            )
        )

    elif forecast_change <= -15:

        recommendations.append(
            create_recommendation(
                title="Protect Against Forecasted Decline",
                category="Forecasting",
                priority="High",
                trigger=f"Forecast indicates {forecast_change:.1f}% decline",
                recommendation=(
                    "Review pricing, demand drivers, marketing performance, "
                    "inventory levels, and customer activity before the decline occurs."
                ),
                reason=(
                    "Forecasting indicates a meaningful negative future trend."
                ),
                expected_impact=(
                    "Reduce potential revenue loss and improve preparedness."
                ),
                action_type="Protect",
                score=min(100, 60 + abs(forecast_change)),
                source="Forecasting",
                metadata={
                    "forecast_change": forecast_change,
                    "direction": direction,
                    "forecast_avg": forecast_avg,
                    "forecast_total": forecast_total,
                },
            )
        )

    return recommendations


# -------------------------------------------------------------------
# ROOT CAUSE RECOMMENDATIONS
# -------------------------------------------------------------------

def process_root_cause(root_cause_results):
    recommendations = []

    if not root_cause_results:
        return recommendations

    causes = (
        root_cause_results.get("causes")
        or root_cause_results.get("root_causes")
        or root_cause_results.get("results")
        or root_cause_results.get("items")
        or []
    )

    for cause in normalize_list(causes):

        if not isinstance(cause, dict):
            continue

        dimension = (
            cause.get("dimension")
            or cause.get("category")
            or cause.get("field")
            or "Business Driver"
        )

        value = (
            cause.get("value")
            or cause.get("dimension_value")
            or cause.get("name")
            or "Unknown"
        )

        change = safe_float(
            cause.get("change")
            or cause.get("change_percent")
            or cause.get("percentage_change")
            or cause.get("growth")
        )

        contribution = safe_float(
            cause.get("contribution")
            or cause.get("contribution_percent")
        )

        if change < 0:

            recommendations.append(
                create_recommendation(
                    title=f"Correct Negative Driver: {value}",
                    category="Root Cause",
                    priority="High",
                    trigger=(
                        f"{dimension} '{value}' changed by {change:.1f}%"
                    ),
                    recommendation=(
                        f"Investigate {dimension} '{value}' and identify "
                        f"the operational or commercial factor causing the decline."
                    ),
                    reason=(
                        f"This driver is associated with a negative business change"
                        f"{f' and contributes approximately {contribution:.1f}% of the change' if contribution else ''}."
                    ),
                    expected_impact=(
                        "Address the underlying cause rather than only treating the symptom."
                    ),
                    action_type="Correct",
                    score=min(100, 60 + abs(change)),
                    source="Root Cause Analysis",
                    metadata={
                        "dimension": dimension,
                        "value": value,
                        "change": change,
                        "contribution": contribution,
                    },
                )
            )

    return recommendations


# -------------------------------------------------------------------
# MAIN ENGINE
# -------------------------------------------------------------------

def generate_recommendations(
    opportunity_results=None,
    risk_results=None,
    anomaly_results=None,
    forecast_results=None,
    root_cause_results=None,
):
    """
    Main Recommendation Engine.

    All recommendations are generated from actual Advanced Insights
    outputs.
    """

    recommendations = []

    # Advanced Insights → Recommendation Engine
    recommendations.extend(
        process_opportunities(opportunity_results)
    )

    recommendations.extend(
        process_customer_risk(risk_results)
    )

    recommendations.extend(
        process_anomalies(anomaly_results)
    )

    recommendations.extend(
        process_forecast(forecast_results)
    )

    recommendations.extend(
        process_root_cause(root_cause_results)
    )

    # ---------------------------------------------------------------
    # REMOVE DUPLICATES
    # ---------------------------------------------------------------

    unique = {}

    for recommendation in recommendations:

        key = (
            recommendation.get("title", "").lower(),
            recommendation.get("category", "").lower(),
        )

        if key not in unique:

            unique[key] = recommendation

        else:

            existing = unique[key]

            if (
                PRIORITY_ORDER.get(
                    recommendation["priority"],
                    99
                )
                <
                PRIORITY_ORDER.get(
                    existing["priority"],
                    99
                )
            ):
                unique[key] = recommendation

            elif recommendation["score"] > existing["score"]:
                unique[key] = recommendation

    recommendations = list(unique.values())

    # ---------------------------------------------------------------
    # PRIORITY SORT
    # ---------------------------------------------------------------

    recommendations.sort(
        key=lambda item: (
            PRIORITY_ORDER.get(
                item.get("priority"),
                99
            ),
            -safe_float(item.get("score")),
        )
    )

    return recommendations


# -------------------------------------------------------------------
# SUMMARY
# -------------------------------------------------------------------

def calculate_recommendation_summary(recommendations):
    recommendations = recommendations or []

    critical = sum(
        1
        for item in recommendations
        if item.get("priority") == "Critical"
    )

    high = sum(
        1
        for item in recommendations
        if item.get("priority") == "High"
    )

    medium = sum(
        1
        for item in recommendations
        if item.get("priority") == "Medium"
    )

    low = sum(
        1
        for item in recommendations
        if item.get("priority") == "Low"
    )

    scores = [
        safe_float(item.get("score"))
        for item in recommendations
    ]

    average_score = (
        sum(scores) / len(scores)
        if scores
        else 0
    )

    return {
        "total": len(recommendations),
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "average_score": round(average_score, 1),
    }


# -------------------------------------------------------------------
# INSIGHTS
# -------------------------------------------------------------------

def generate_recommendation_insights(recommendations):
    recommendations = recommendations or []

    insights = []

    if not recommendations:
        return [
            {
                "type": "info",
                "title": "No Immediate Actions",
                "message": (
                    "The current analysis did not identify any major "
                    "actionable business signals."
                ),
            }
        ]

    critical_count = sum(
        1
        for item in recommendations
        if item.get("priority") == "Critical"
    )

    high_count = sum(
        1
        for item in recommendations
        if item.get("priority") == "High"
    )

    if critical_count:

        insights.append(
            {
                "type": "critical",
                "title": "Immediate Attention Required",
                "message": (
                    f"{critical_count} critical recommendation(s) "
                    f"require immediate business attention."
                ),
            }
        )

    if high_count:

        insights.append(
            {
                "type": "warning",
                "title": "High-Priority Actions",
                "message": (
                    f"{high_count} high-priority recommendation(s) "
                    f"should be reviewed by the business team."
                ),
            }
        )

    categories = {}

    for item in recommendations:

        category = item.get(
            "category",
            "General"
        )

        categories[category] = (
            categories.get(category, 0) + 1
        )

    if categories:

        top_category = max(
            categories,
            key=categories.get
        )

        insights.append(
            {
                "type": "info",
                "title": "Main Decision Area",
                "message": (
                    f"{top_category} currently contains the largest "
                    f"number of generated recommendations."
                ),
            }
        )

    return insights