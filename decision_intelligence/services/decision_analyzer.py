import pandas as pd


# ============================================================
# COLUMN DETECTION
# ============================================================

def detect_column(df, candidates):
    """
    Detect a dataframe column using exact matching first,
    followed by partial matching.
    """

    if df is None or df.empty:
        return None

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    # Exact match
    for candidate in candidates:

        candidate = str(candidate).strip().lower()

        if candidate in normalized:
            return normalized[candidate]

    # Partial match
    for column in df.columns:

        column_name = str(column).strip().lower()

        for candidate in candidates:

            candidate = str(candidate).strip().lower()

            if candidate in column_name:
                return column

    return None


# ============================================================
# SAFE NUMBER
# ============================================================

def safe_number(value, default=0):
    """
    Safely convert a value to float.
    """

    try:

        if pd.isna(value):
            return default

        return float(value)

    except (ValueError, TypeError):

        return default


# ============================================================
# CREATE RECOMMENDATION
# ============================================================

def create_recommendation(
    title,
    category,
    priority,
    score,
    trigger,
    recommendation,
    reason,
    expected_impact,
    action_type="Monitor",
):
    """
    Standard recommendation structure used by
    the Decision Intelligence UI.
    """

    return {
        "title": str(title),
        "category": str(category),
        "priority": str(priority),
        "score": round(safe_number(score), 1),
        "trigger": str(trigger),
        "recommendation": str(recommendation),
        "reason": str(reason),
        "expected_impact": str(expected_impact),
        "action_type": str(action_type),
    }


# ============================================================
# PRIORITY FROM SCORE
# ============================================================

def priority_from_score(score):

    score = safe_number(score)

    if score >= 80:
        return "Critical"

    if score >= 65:
        return "High"

    if score >= 45:
        return "Medium"

    return "Low"


# ============================================================
# OPPORTUNITY RECOMMENDATIONS
# ============================================================

def recommendations_from_opportunities(opportunities):
    """
    Convert Opportunity Detection results into
    Decision Intelligence recommendations.
    """

    recommendations = []

    if not opportunities:
        return recommendations

    for item in opportunities:

        level = str(
            item.get(
                "opportunity_level",
                "Stable",
            )
        )

        score = safe_number(
            item.get(
                "opportunity_score",
                0,
            )
        )

        growth = safe_number(
            item.get(
                "growth_percent",
                0,
            )
        )

        category = str(
            item.get(
                "category",
                "Business Area",
            )
        )

        dimension = str(
            item.get(
                "dimension",
                "Business",
            )
        )

        action = str(
            item.get(
                "recommended_action",
                "Continue monitoring performance.",
            )
        )

        if level == "High Opportunity":

            priority = "Critical"

            expected_impact = (
                "Potential to accelerate revenue growth "
                "and capture additional demand."
            )

            action_type = "Scale"

        elif level == "Strong Opportunity":

            priority = "High"

            expected_impact = (
                "Potential to increase revenue by "
                "supporting an already positive growth trend."
            )

            action_type = "Expand"

        elif level == "Emerging Opportunity":

            priority = "Medium"

            expected_impact = (
                "Potential future growth if the positive "
                "signal continues."
            )

            action_type = "Test"

        else:

            continue

        recommendations.append(
            create_recommendation(

                title=(
                    f"Growth opportunity detected: "
                    f"{category}"
                ),

                category="Opportunity",

                priority=priority,

                score=score,

                trigger=(
                    f"{dimension} / {category} shows "
                    f"{growth:.1f}% recent revenue growth."
                ),

                recommendation=action,

                reason=(
                    f"Opportunity analysis classified "
                    f"this area as {level.lower()} "
                    f"with a score of {score:.1f}."
                ),

                expected_impact=expected_impact,

                action_type=action_type,
            )
        )

    return recommendations


# ============================================================
# CUSTOMER RISK RECOMMENDATIONS
# ============================================================

def recommendations_from_customer_risk(
    risk_data,
    summary,
):
    """
    Convert Customer Risk Analysis into
    retention recommendations.
    """

    recommendations = []

    if risk_data is None or risk_data.empty:
        return recommendations

    high_risk = int(
        summary.get(
            "high_risk_customers",
            0,
        )
    )

    at_risk = int(
        summary.get(
            "at_risk_customers",
            0,
        )
    )

    risk_rate = safe_number(
        summary.get(
            "risk_rate",
            0,
        )
    )

    # --------------------------------------------------------
    # Overall customer risk
    # --------------------------------------------------------

    if high_risk > 0:

        score = min(
            100,
            70 + (risk_rate * 0.5),
        )

        recommendations.append(
            create_recommendation(

                title="Launch high-risk customer retention",

                category="Customer Risk",

                priority="Critical",

                score=score,

                trigger=(
                    f"{high_risk:,} customers are classified "
                    "as High Risk."
                ),

                recommendation=(
                    "Prioritize high-value high-risk customers "
                    "for personalized retention campaigns, "
                    "targeted offers and direct engagement."
                ),

                reason=(
                    f"Customer Risk Analysis identified "
                    f"{high_risk:,} high-risk customers."
                ),

                expected_impact=(
                    "Reduce potential customer loss and "
                    "protect existing customer revenue."
                ),

                action_type="Retain",
            )
        )

    # --------------------------------------------------------
    # At-risk population
    # --------------------------------------------------------

    if at_risk > 0:

        priority = (
            "High"
            if risk_rate >= 15
            else "Medium"
        )

        score = min(
            90,
            55 + risk_rate,
        )

        recommendations.append(
            create_recommendation(

                title="Re-engage at-risk customers",

                category="Customer Risk",

                priority=priority,

                score=score,

                trigger=(
                    f"{risk_rate:.1f}% of customers are "
                    "classified as At Risk or High Risk."
                ),

                recommendation=(
                    "Create a targeted re-engagement campaign "
                    "using personalized offers and customer "
                    "communication."
                ),

                reason=(
                    f"{at_risk:,} customers are classified "
                    "as At Risk."
                ),

                expected_impact=(
                    "Improve repeat purchasing and reduce "
                    "customer churn risk."
                ),

                action_type="Re-engage",
            )
        )

    # --------------------------------------------------------
    # High-value risky customers
    # --------------------------------------------------------

    try:

        monetary_threshold = (
            risk_data["monetary"]
            .quantile(0.75)
        )

        high_value_risky = risk_data[
            (
                risk_data["monetary"]
                >= monetary_threshold
            )
            &
            (
                risk_data["risk_level"].isin(
                    [
                        "At Risk",
                        "High Risk",
                    ]
                )
            )
        ]

        count = len(high_value_risky)

        if count > 0:

            recommendations.append(
                create_recommendation(

                    title="Protect high-value customers",

                    category="Customer Risk",

                    priority="Critical",

                    score=88,

                    trigger=(
                        f"{count:,} high-value customers "
                        "show elevated risk."
                    ),

                    recommendation=(
                        "Prioritize high-value customers with "
                        "personalized retention offers, "
                        "relationship outreach and loyalty incentives."
                    ),

                    reason=(
                        "These customers combine high monetary "
                        "value with elevated behavioral risk."
                    ),

                    expected_impact=(
                        "Protect high-value revenue and improve "
                        "customer lifetime value."
                    ),

                    action_type="Protect Revenue",
                )
            )

    except Exception:
        pass

    return recommendations


# ============================================================
# ANOMALY RECOMMENDATIONS
# ============================================================

def recommendations_from_anomalies(
    summary,
):
    """
    Convert Anomaly Detection findings into
    operational recommendations.
    """

    recommendations = []

    if not summary:
        return recommendations

    anomaly_count = int(
        summary.get(
            "anomaly_count",
            0,
        )
    )

    critical_count = int(
        summary.get(
            "critical_count",
            0,
        )
    )

    anomaly_rate = safe_number(
        summary.get(
            "anomaly_rate",
            0,
        )
    )

    spike_count = int(
        summary.get(
            "spike_count",
            0,
        )
    )

    drop_count = int(
        summary.get(
            "drop_count",
            0,
        )
    )

    # --------------------------------------------------------
    # Critical anomalies
    # --------------------------------------------------------

    if critical_count > 0:

        recommendations.append(
            create_recommendation(

                title="Investigate critical business anomalies",

                category="Anomaly",

                priority="Critical",

                score=min(
                    100,
                    80 + critical_count * 2,
                ),

                trigger=(
                    f"{critical_count} critical anomaly "
                    "event(s) were detected."
                ),

                recommendation=(
                    "Investigate the affected dates and "
                    "cross-check inventory, pricing, promotions, "
                    "marketing activity and operational events."
                ),

                reason=(
                    "Critical anomalies indicate unusually "
                    "large deviations from normal business activity."
                ),

                expected_impact=(
                    "Identify operational issues quickly and "
                    "prevent repeated abnormal performance."
                ),

                action_type="Investigate",
            )
        )

    # --------------------------------------------------------
    # Significant drops
    # --------------------------------------------------------

    if drop_count > 0:

        priority = (
            "High"
            if anomaly_rate >= 5
            else "Medium"
        )

        recommendations.append(
            create_recommendation(

                title="Investigate unusual sales drops",

                category="Anomaly",

                priority=priority,

                score=min(
                    90,
                    60 + anomaly_rate,
                ),

                trigger=(
                    f"{drop_count} unusual sales drop(s) "
                    "were detected."
                ),

                recommendation=(
                    "Review inventory availability, pricing, "
                    "customer demand, campaigns and operational "
                    "disruptions around the affected dates."
                ),

                reason=(
                    "Sales were materially below expected "
                    "normal activity."
                ),

                expected_impact=(
                    "Recover lost sales and reduce the chance "
                    "of repeated performance drops."
                ),

                action_type="Investigate",
            )
        )

    # --------------------------------------------------------
    # Spikes
    # --------------------------------------------------------

    if spike_count > 0:

        recommendations.append(
            create_recommendation(

                title="Identify and replicate sales spikes",

                category="Anomaly",

                priority="Medium",

                score=60,

                trigger=(
                    f"{spike_count} unusual sales spike(s) "
                    "were detected."
                ),

                recommendation=(
                    "Investigate promotions, campaigns, "
                    "pricing and product availability that "
                    "coincided with the strongest spikes."
                ),

                reason=(
                    "Unusual positive deviations may reveal "
                    "successful business activities."
                ),

                expected_impact=(
                    "Identify repeatable growth drivers and "
                    "potentially reproduce successful outcomes."
                ),

                action_type="Optimize",
            )
        )

    # --------------------------------------------------------
    # General anomaly activity
    # --------------------------------------------------------

    if anomaly_count > 0 and anomaly_rate >= 15:

        recommendations.append(
            create_recommendation(

                title="Review business volatility",

                category="Anomaly",

                priority="High",

                score=72,

                trigger=(
                    f"{anomaly_rate:.1f}% of analyzed days "
                    "contain unusual activity."
                ),

                recommendation=(
                    "Review operational, pricing, inventory "
                    "and marketing changes that may be increasing "
                    "business volatility."
                ),

                reason=(
                    "The anomaly rate is relatively high."
                ),

                expected_impact=(
                    "Improve business stability and make "
                    "future planning more reliable."
                ),

                action_type="Stabilize",
            )
        )

    return recommendations


# ============================================================
# FORECAST RECOMMENDATIONS
# ============================================================

def recommendations_from_forecast(
    forecast_summary,
):
    """
    Convert forecasting output into
    forward-looking recommendations.
    """

    recommendations = []

    if not forecast_summary:
        return recommendations

    change = safe_number(
        forecast_summary.get(
            "forecast_change",
            0,
        )
    )

    direction = str(
        forecast_summary.get(
            "forecast_direction",
            "Stable",
        )
    )

    forecast_average = safe_number(
        forecast_summary.get(
            "forecast_average",
            0,
        )
    )

    # --------------------------------------------------------
    # Strong growth
    # --------------------------------------------------------

    if change >= 15:

        recommendations.append(
            create_recommendation(

                title="Prepare for forecasted growth",

                category="Forecast",

                priority="High",

                score=min(
                    95,
                    65 + abs(change) * 0.5,
                ),

                trigger=(
                    f"Forecast average is {change:.1f}% "
                    "above the recent historical average."
                ),

                recommendation=(
                    "Prepare inventory, staffing, marketing "
                    "capacity and operational resources to "
                    "support the expected increase in demand."
                ),

                reason=(
                    f"The forecasting model indicates "
                    f"{direction.lower()} future performance."
                ),

                expected_impact=(
                    "Capture additional demand while reducing "
                    "the risk of stockouts or capacity constraints."
                ),

                action_type="Prepare",
            )
        )

    # --------------------------------------------------------
    # Strong decline
    # --------------------------------------------------------

    elif change <= -15:

        recommendations.append(
            create_recommendation(

                title="Protect against forecasted decline",

                category="Forecast",

                priority="High",

                score=min(
                    95,
                    65 + abs(change) * 0.5,
                ),

                trigger=(
                    f"Forecast average is {abs(change):.1f}% "
                    "below the recent historical average."
                ),

                recommendation=(
                    "Review pricing, demand drivers, inventory "
                    "levels and marketing strategy before the "
                    "forecasted decline occurs."
                ),

                reason=(
                    f"The forecasting model indicates "
                    f"{direction.lower()} future performance."
                ),

                expected_impact=(
                    "Reduce revenue downside and improve "
                    "preparedness for weaker demand."
                ),

                action_type="Protect",
            )
        )

    # --------------------------------------------------------
    # Moderate growth
    # --------------------------------------------------------

    elif change >= 5:

        recommendations.append(
            create_recommendation(

                title="Monitor positive demand trend",

                category="Forecast",

                priority="Medium",

                score=58,

                trigger=(
                    f"Forecast average is {change:.1f}% "
                    "above recent historical activity."
                ),

                recommendation=(
                    "Monitor demand and prepare controlled "
                    "capacity or inventory increases."
                ),

                reason=(
                    "The forecast indicates a positive "
                    "near-term direction."
                ),

                expected_impact=(
                    "Capture growth without overcommitting resources."
                ),

                action_type="Monitor",
            )
        )

    elif change <= -5:

        recommendations.append(
            create_recommendation(

                title="Monitor weakening demand trend",

                category="Forecast",

                priority="Medium",

                score=58,

                trigger=(
                    f"Forecast average is {abs(change):.1f}% "
                    "below recent historical activity."
                ),

                recommendation=(
                    "Monitor demand closely and review "
                    "pricing, promotions and customer engagement."
                ),

                reason=(
                    "The forecast indicates weakening "
                    "near-term performance."
                ),

                expected_impact=(
                    "Enable earlier corrective action if "
                    "the decline continues."
                ),

                action_type="Monitor",
            )
        )

    return recommendations


# ============================================================
# ROOT CAUSE RECOMMENDATIONS
# ============================================================

def recommendations_from_root_causes(
    results,
    overall_change,
):
    """
    Convert root-cause findings into
    corrective or scaling recommendations.
    """

    recommendations = []

    if not results:
        return recommendations

    overall_change = safe_number(
        overall_change
    )

    # Only the strongest contributors are useful
    # to the decision layer.

    for item in results[:5]:

        change = safe_number(
            item.get(
                "change",
                0,
            )
        )

        change_percent = safe_number(
            item.get(
                "change_percent",
                0,
            )
        )

        dimension = str(
            item.get(
                "dimension",
                "Business Area",
            )
        )

        category = str(
            item.get(
                "category",
                "Unknown",
            )
        )

        contribution = safe_number(
            item.get(
                "contribution",
                0,
            )
        )

        # ----------------------------------------------------
        # Negative contributor
        # ----------------------------------------------------

        if change < 0:

            score = min(
                95,
                60 + abs(contribution) * 0.3,
            )

            priority = (
                "High"
                if abs(change_percent) >= 15
                else "Medium"
            )

            recommendations.append(
                create_recommendation(

                    title=(
                        f"Address decline in "
                        f"{category}"
                    ),

                    category="Root Cause",

                    priority=priority,

                    score=score,

                    trigger=(
                        f"{dimension} = {category} recorded "
                        f"a {abs(change_percent):.1f}% decline."
                    ),

                    recommendation=(
                        f"Investigate the drivers affecting "
                        f"{category}, including pricing, demand, "
                        "inventory, marketing and operational factors."
                    ),

                    reason=(
                        f"This area is a significant contributor "
                        "to the observed performance change."
                    ),

                    expected_impact=(
                        "Reduce the negative performance driver "
                        "and recover lost business value."
                    ),

                    action_type="Correct",
                )
            )

        # ----------------------------------------------------
        # Positive contributor
        # ----------------------------------------------------

        elif change > 0 and overall_change > 0:

            score = min(
                90,
                55 + abs(contribution) * 0.3,
            )

            recommendations.append(
                create_recommendation(

                    title=(
                        f"Scale positive driver: "
                        f"{category}"
                    ),

                    category="Root Cause",

                    priority="Medium",

                    score=score,

                    trigger=(
                        f"{dimension} = {category} recorded "
                        f"a {change_percent:.1f}% increase."
                    ),

                    recommendation=(
                        f"Investigate what is driving growth "
                        f"in {category} and consider scaling "
                        "the successful strategy."
                    ),

                    reason=(
                        "The area is contributing positively "
                        "to overall business performance."
                    ),

                    expected_impact=(
                        "Increase the likelihood of sustaining "
                        "and extending current growth."
                    ),

                    action_type="Scale",
                )
            )

    return recommendations


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate_recommendations(
    recommendations
):
    """
    Remove duplicate recommendations while
    preserving the strongest score.
    """

    if not recommendations:
        return []

    grouped = {}

    for recommendation in recommendations:

        key = (
            recommendation.get("title", ""),
            recommendation.get("category", ""),
        )

        existing = grouped.get(key)

        if existing is None:

            grouped[key] = recommendation

        else:

            if (
                safe_number(
                    recommendation.get("score", 0)
                )
                >
                safe_number(
                    existing.get("score", 0)
                )
            ):

                grouped[key] = recommendation

    return list(
        grouped.values()
    )


# ============================================================
# SORT
# ============================================================

def sort_recommendations(
    recommendations
):

    priority_order = {
        "Critical": 0,
        "High": 1,
        "Medium": 2,
        "Low": 3,
    }

    return sorted(
        recommendations,
        key=lambda item: (
            priority_order.get(
                item.get(
                    "priority",
                    "Low",
                ),
                4,
            ),
            -safe_number(
                item.get(
                    "score",
                    0,
                )
            ),
        ),
    )


# ============================================================
# SUMMARY
# ============================================================

def summarize_signals(
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

    critical = sum(
        item["priority"] == "Critical"
        for item in recommendations
    )

    high = sum(
        item["priority"] == "High"
        for item in recommendations
    )

    medium = sum(
        item["priority"] == "Medium"
        for item in recommendations
    )

    low = sum(
        item["priority"] == "Low"
        for item in recommendations
    )

    scores = [
        safe_number(
            item.get(
                "score",
                0,
            )
        )
        for item in recommendations
    ]

    return {
        "total": len(recommendations),
        "critical": int(critical),
        "high": int(high),
        "medium": int(medium),
        "low": int(low),
        "average_score": round(
            sum(scores) / len(scores),
            1,
        ),
    }


# ============================================================
# INSIGHTS
# ============================================================

def generate_decision_insights(
    recommendations,
    summary,
):
    """
    Generate high-level management messages.
    """

    insights = []

    if not recommendations:

        return [
            "No significant decision signals were identified "
            "from the selected dataset."
        ]

    if summary["critical"] > 0:

        insights.append(
            f"{summary['critical']} critical decision signal(s) "
            "require immediate management attention."
        )

    if summary["high"] > 0:

        insights.append(
            f"{summary['high']} high-priority recommendation(s) "
            "should be reviewed and actioned soon."
        )

    opportunity_count = sum(
        item.get("category") == "Opportunity"
        for item in recommendations
    )

    risk_count = sum(
        item.get("category") == "Customer Risk"
        for item in recommendations
    )

    anomaly_count = sum(
        item.get("category") == "Anomaly"
        for item in recommendations
    )

    forecast_count = sum(
        item.get("category") == "Forecast"
        for item in recommendations
    )

    if opportunity_count > 0:

        insights.append(
            "Positive opportunity signals were identified. "
            "Management should evaluate where additional "
            "investment can accelerate growth."
        )

    if risk_count > 0:

        insights.append(
            "Customer risk signals indicate that retention "
            "actions should be considered before revenue is lost."
        )

    if anomaly_count > 0:

        insights.append(
            "Unusual business activity was detected. "
            "Investigating the underlying operational drivers "
            "can prevent repeated performance deviations."
        )

    if forecast_count > 0:

        insights.append(
            "Forecast signals provide forward-looking guidance "
            "for capacity, inventory, marketing and planning decisions."
        )

    return insights


# ============================================================
# FINAL DECISION ANALYSIS
# ============================================================

def build_decision_recommendations(
    opportunity_results=None,
    customer_risk_data=None,
    customer_risk_summary=None,
    anomaly_summary=None,
    forecast_summary=None,
    root_cause_results=None,
    root_cause_change=0,
):
    """
    Central Decision Intelligence aggregation layer.

    It receives results from the actual Advanced Insights
    engines and converts them into business recommendations.
    """

    recommendations = []

    # Opportunity Detection
    recommendations.extend(
        recommendations_from_opportunities(
            opportunity_results or []
        )
    )

    # Customer Risk
    recommendations.extend(
        recommendations_from_customer_risk(
            customer_risk_data,
            customer_risk_summary or {},
        )
    )

    # Anomaly Detection
    recommendations.extend(
        recommendations_from_anomalies(
            anomaly_summary or {}
        )
    )

    # Forecasting
    recommendations.extend(
        recommendations_from_forecast(
            forecast_summary or {}
        )
    )

    # Root Cause Analysis
    recommendations.extend(
        recommendations_from_root_causes(
            root_cause_results or [],
            root_cause_change,
        )
    )

    recommendations = deduplicate_recommendations(
        recommendations
    )

    recommendations = sort_recommendations(
        recommendations
    )

    # Keep the dashboard manageable.
    recommendations = recommendations[:30]

    summary = summarize_signals(
        recommendations
    )

    insights = generate_decision_insights(
        recommendations,
        summary,
    )

    return {
        "recommendations": recommendations,
        "summary": summary,
        "insights": insights,
    }