import pandas as pd


def create_recommendation(
    title,
    category,
    priority,
    trigger,
    recommendation,
    reason,
    expected_impact,
    action_type,
    score=0,
):
    return {
        "title": title,
        "category": category,
        "priority": priority,
        "trigger": trigger,
        "recommendation": recommendation,
        "reason": reason,
        "expected_impact": expected_impact,
        "action_type": action_type,
        "score": round(float(score), 1),
    }


def generate_recommendations(
    opportunity_results=None,
    risk_results=None,
    anomaly_results=None,
    forecast_results=None,
    root_cause_results=None,
):
    """
    Converts Smart BI analytical results into
    business-oriented recommendations.
    """

    recommendations = []

    opportunity_results = opportunity_results or []
    risk_results = risk_results or []
    anomaly_results = anomaly_results or []
    forecast_results = forecast_results or []
    root_cause_results = root_cause_results or []

    # ---------------------------------------------------------
    # 1. OPPORTUNITY RECOMMENDATIONS
    # ---------------------------------------------------------

    for item in opportunity_results:

        level = str(
            item.get("opportunity_level", "")
        ).lower()

        growth = float(
            item.get("growth_percent", 0) or 0
        )

        category = item.get(
            "dimension",
            "Business"
        )

        area = item.get(
            "category",
            "Opportunity"
        )

        score = float(
            item.get("opportunity_score", 0) or 0
        )

        if level == "high" or score >= 75:

            recommendations.append(
                create_recommendation(
                    title=f"Scale {area}",
                    category="Opportunity",
                    priority="Critical",
                    trigger=f"{category} '{area}' is showing strong growth.",
                    recommendation=(
                        f"Increase focus on {area}. "
                        "Consider increasing inventory, "
                        "marketing exposure, and operational capacity."
                    ),
                    reason=(
                        f"The area recorded approximately "
                        f"{growth:.1f}% growth with a high "
                        "opportunity score of {score:.1f}."
                    ),
                    expected_impact=(
                        "Higher revenue potential and stronger "
                        "market capture."
                    ),
                    action_type="Scale",
                    score=score,
                )
            )

        elif level == "strong" or score >= 60:

            recommendations.append(
                create_recommendation(
                    title=f"Expand {area}",
                    category="Opportunity",
                    priority="High",
                    trigger=f"{category} '{area}' is performing above baseline.",
                    recommendation=(
                        f"Increase business attention toward {area} "
                        "and monitor its growth over the next period."
                    ),
                    reason=(
                        f"{growth:.1f}% growth indicates "
                        "positive business momentum."
                    ),
                    expected_impact=(
                        "Potential revenue growth and improved "
                        "performance."
                    ),
                    action_type="Expand",
                    score=score,
                )
            )

    # ---------------------------------------------------------
    # 2. CUSTOMER RISK RECOMMENDATIONS
    # ---------------------------------------------------------

    for item in risk_results:

        risk_level = str(
            item.get("risk_level", "")
        ).lower()

        risk_score = float(
            item.get("risk_score", 0) or 0
        )

        customer = item.get(
            "customer",
            "Customer"
        )

        monetary = float(
            item.get("monetary", 0) or 0
        )

        if risk_level == "high risk" or risk_score >= 75:

            recommendations.append(
                create_recommendation(
                    title=f"Retain {customer}",
                    category="Customer Risk",
                    priority="Critical",
                    trigger=(
                        f"{customer} has a high customer risk score."
                    ),
                    recommendation=(
                        "Launch a personalized retention campaign "
                        "with a relevant offer or direct engagement."
                    ),
                    reason=(
                        f"Customer risk score is {risk_score:.1f}. "
                        f"Historical customer value is "
                        f"{monetary:,.2f}."
                    ),
                    expected_impact=(
                        "Reduce churn risk and protect existing "
                        "customer revenue."
                    ),
                    action_type="Retain",
                    score=risk_score,
                )
            )

        elif risk_level == "at risk" or risk_score >= 55:

            recommendations.append(
                create_recommendation(
                    title=f"Re-engage {customer}",
                    category="Customer Risk",
                    priority="High",
                    trigger=(
                        f"{customer} shows elevated engagement risk."
                    ),
                    recommendation=(
                        "Send a targeted re-engagement message "
                        "and monitor the customer's next purchase."
                    ),
                    reason=(
                        f"Customer risk score is {risk_score:.1f}."
                    ),
                    expected_impact=(
                        "Improve customer engagement and repeat purchases."
                    ),
                    action_type="Re-engage",
                    score=risk_score,
                )
            )

    # ---------------------------------------------------------
    # 3. ANOMALY RECOMMENDATIONS
    # ---------------------------------------------------------

    for item in anomaly_results:

        severity = str(
            item.get("severity", "")
        ).lower()

        direction = str(
            item.get("direction", "")
        ).lower()

        anomaly_date = item.get(
            "date",
            "recent period"
        )

        value = item.get(
            "value",
            0
        )

        if severity == "critical":

            if direction == "spike":

                action = (
                    "Investigate the spike immediately and "
                    "identify whether it was caused by a "
                    "successful campaign, unusual demand, "
                    "pricing change, or data issue."
                )

            else:

                action = (
                    "Investigate the decline immediately. "
                    "Check product availability, customer demand, "
                    "pricing, operational issues, and data quality."
                )

            recommendations.append(
                create_recommendation(
                    title="Investigate Critical Anomaly",
                    category="Anomaly",
                    priority="Critical",
                    trigger=(
                        f"A critical {direction} anomaly was "
                        f"detected around {anomaly_date}."
                    ),
                    recommendation=action,
                    reason=(
                        f"Observed metric value: {value}."
                    ),
                    expected_impact=(
                        "Identify the underlying cause before "
                        "it materially affects business performance."
                    ),
                    action_type="Investigate",
                    score=90,
                )
            )

        elif severity in ["high", "warning"]:

            recommendations.append(
                create_recommendation(
                    title="Monitor Business Anomaly",
                    category="Anomaly",
                    priority="Medium",
                    trigger=(
                        f"An unusual {direction} pattern was detected."
                    ),
                    recommendation=(
                        "Monitor the affected metric and compare "
                        "it with operational and business events."
                    ),
                    reason=(
                        "The metric moved outside its expected pattern."
                    ),
                    expected_impact=(
                        "Early detection of emerging business problems."
                    ),
                    action_type="Monitor",
                    score=60,
                )
            )

    # ---------------------------------------------------------
    # 4. FORECAST RECOMMENDATIONS
    # ---------------------------------------------------------

    for item in forecast_results:

        forecast_change = float(
            item.get("change_percent", 0) or 0
        )

        forecast_value = item.get(
            "forecast_value",
            0
        )

        if forecast_change >= 15:

            recommendations.append(
                create_recommendation(
                    title="Prepare for Demand Growth",
                    category="Forecast",
                    priority="High",
                    trigger=(
                        f"Forecast indicates approximately "
                        f"{forecast_change:.1f}% future growth."
                    ),
                    recommendation=(
                        "Prepare inventory, staffing, logistics, "
                        "and marketing capacity before demand increases."
                    ),
                    reason=(
                        f"Forecasted metric value is approximately "
                        f"{forecast_value:,.2f}."
                    ),
                    expected_impact=(
                        "Reduce stockouts and operational bottlenecks "
                        "during the expected growth period."
                    ),
                    action_type="Prepare",
                    score=80,
                )
            )

        elif forecast_change <= -15:

            recommendations.append(
                create_recommendation(
                    title="Prepare for Demand Decline",
                    category="Forecast",
                    priority="High",
                    trigger=(
                        f"Forecast indicates approximately "
                        f"{abs(forecast_change):.1f}% decline."
                    ),
                    recommendation=(
                        "Review inventory commitments, promotional "
                        "strategy, and operating costs."
                    ),
                    reason=(
                        "Forecast indicates weakening future demand."
                    ),
                    expected_impact=(
                        "Reduce excess inventory and unnecessary costs."
                    ),
                    action_type="Protect",
                    score=80,
                )

            )

    # ---------------------------------------------------------
    # 5. ROOT CAUSE RECOMMENDATIONS
    # ---------------------------------------------------------

    for item in root_cause_results:

        change = float(
            item.get("change", 0) or 0
        )

        change_percent = float(
            item.get("change_percent", 0) or 0
        )

        dimension = item.get(
            "dimension",
            "Business"
        )

        category = item.get(
            "category",
            "Unknown"
        )

        if change < 0:

            recommendations.append(
                create_recommendation(
                    title=f"Address {category} Decline",
                    category="Root Cause",
                    priority="High",
                    trigger=(
                        f"{dimension} '{category}' contributed "
                        "to a negative performance change."
                    ),
                    recommendation=(
                        f"Investigate the operational factors affecting "
                        f"{category} and create a corrective action plan."
                    ),
                    reason=(
                        f"Performance changed by "
                        f"{change_percent:.1f}%."
                    ),
                    expected_impact=(
                        "Recover lost performance and reduce "
                        "the underlying business issue."
                    ),
                    action_type="Correct",
                    score=min(
                        95,
                        60 + abs(change_percent)
                    ),
                )
            )

    # ---------------------------------------------------------
    # REMOVE DUPLICATES
    # ---------------------------------------------------------

    unique = {}

    for recommendation in recommendations:

        key = (
            recommendation["title"],
            recommendation["category"],
        )

        if key not in unique:
            unique[key] = recommendation

    recommendations = list(
        unique.values()
    )

    # Highest priority first
    priority_order = {
        "Critical": 1,
        "High": 2,
        "Medium": 3,
        "Low": 4,
    }

    recommendations.sort(
        key=lambda item: (
            priority_order.get(
                item["priority"],
                5
            ),
            -item["score"],
        )
    )

    return recommendations


def calculate_recommendation_summary(
    recommendations
):
    if not recommendations:
        return {
            "total": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "average_score": 0,
        }

    total = len(recommendations)

    critical = sum(
        1
        for item in recommendations
        if item["priority"] == "Critical"
    )

    high = sum(
        1
        for item in recommendations
        if item["priority"] == "High"
    )

    medium = sum(
        1
        for item in recommendations
        if item["priority"] == "Medium"
    )

    low = sum(
        1
        for item in recommendations
        if item["priority"] == "Low"
    )

    average_score = sum(
        item["score"]
        for item in recommendations
    ) / total

    return {
        "total": total,
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "average_score": round(
            average_score,
            1
        ),
    }


def generate_recommendation_insights(
    recommendations
):
    if not recommendations:
        return [
            "No actionable recommendations were generated from the available analytics."
        ]

    insights = []

    critical = [
        item
        for item in recommendations
        if item["priority"] == "Critical"
    ]

    high = [
        item
        for item in recommendations
        if item["priority"] == "High"
    ]

    categories = {}

    for item in recommendations:
        category = item["category"]

        categories[category] = (
            categories.get(category, 0) + 1
        )

    if critical:
        insights.append(
            f"{len(critical)} critical action(s) require immediate management attention."
        )

    if high:
        insights.append(
            f"{len(high)} high-priority action(s) should be addressed in the near term."
        )

    if categories:
        dominant_category = max(
            categories,
            key=categories.get
        )

        insights.append(
            f"{dominant_category} currently generates "
            f"the largest number of recommended actions."
        )

    top = recommendations[0]

    insights.append(
        f"Highest-priority recommendation: {top['title']}."
    )

    return insights