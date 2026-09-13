from .recommendation_engine import safe_float


SEVERITY_ORDER = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
}


def create_alert(
    title,
    message,
    severity="Medium",
    source="System",
    category="",
    metric_name="",
    metric_value=None,
    threshold_value=None,
    recommendation="",
    metadata=None,
):
    return {
        "title": str(title),
        "message": str(message),
        "severity": severity,
        "source": source,
        "category": category,
        "metric_name": metric_name,
        "metric_value": (
            safe_float(metric_value)
            if metric_value is not None
            else None
        ),
        "threshold_value": (
            safe_float(threshold_value)
            if threshold_value is not None
            else None
        ),
        "recommendation": recommendation,
        "metadata": metadata or {},
    }


def process_forecast_alerts(forecast_results):
    alerts = []

    if not forecast_results:
        return alerts

    if isinstance(forecast_results, dict):
        results = [forecast_results]
    else:
        results = forecast_results

    for result in results:
        summary = result.get("summary", result)

        change = safe_float(
            summary.get(
                "forecast_change",
                summary.get("change", 0),
            )
        )

        direction = str(
            summary.get("direction", "")
        ).lower()

        if change <= -20:
            alerts.append(
                create_alert(
                    title="Significant revenue decline forecast",
                    message=(
                        f"Forecast analysis indicates a "
                        f"{abs(change):.1f}% decline."
                    ),
                    severity="Critical",
                    source="Forecasting",
                    category="Revenue",
                    metric_name="Forecast Change",
                    metric_value=change,
                    threshold_value=-20,
                    recommendation=(
                        "Review declining drivers and "
                        "prepare a corrective business strategy."
                    ),
                )
            )

        elif change <= -10:
            alerts.append(
                create_alert(
                    title="Revenue decline forecast",
                    message=(
                        f"Forecasted performance is expected "
                        f"to decline by {abs(change):.1f}%."
                    ),
                    severity="High",
                    source="Forecasting",
                    category="Revenue",
                    metric_name="Forecast Change",
                    metric_value=change,
                    threshold_value=-10,
                    recommendation=(
                        "Investigate the decline and identify "
                        "actions to protect revenue."
                    ),
                )
            )

        elif change >= 25:
            alerts.append(
                create_alert(
                    title="Strong revenue growth forecast",
                    message=(
                        f"Forecast indicates approximately "
                        f"{change:.1f}% growth."
                    ),
                    severity="Medium",
                    source="Forecasting",
                    category="Growth",
                    metric_name="Forecast Change",
                    metric_value=change,
                    threshold_value=25,
                    recommendation=(
                        "Prepare inventory, operations and "
                        "marketing capacity for expected growth."
                    ),
                )
            )

    return alerts


def process_anomaly_alerts(anomaly_results):
    alerts = []

    if not anomaly_results:
        return alerts

    results = (
        anomaly_results
        if isinstance(anomaly_results, list)
        else [anomaly_results]
    )

    for result in results:
        anomalies = result.get("anomalies", [])

        for anomaly in anomalies:
            z_score = safe_float(
                anomaly.get(
                    "z_score",
                    anomaly.get("zscore", 0),
                )
            )

            value = safe_float(
                anomaly.get("value", 0)
            )

            anomaly_type = str(
                anomaly.get(
                    "type",
                    anomaly.get("anomaly_type", "Anomaly"),
                )
            )

            if abs(z_score) >= 3:
                severity = "Critical"
            elif abs(z_score) >= 2:
                severity = "High"
            else:
                severity = "Medium"

            alerts.append(
                create_alert(
                    title=f"Business anomaly detected: {anomaly_type}",
                    message=(
                        f"An unusual business activity was detected "
                        f"with a z-score of {z_score:.2f}."
                    ),
                    severity=severity,
                    source="Anomaly Detection",
                    category="Anomaly",
                    metric_name="Anomaly Value",
                    metric_value=value,
                    threshold_value=z_score,
                    recommendation=(
                        "Investigate the affected period and "
                        "identify the underlying business driver."
                    ),
                    metadata=anomaly,
                )
            )

    return alerts


def process_customer_risk_alerts(risk_results):
    alerts = []

    if not risk_results:
        return alerts

    results = (
        risk_results
        if isinstance(risk_results, list)
        else [risk_results]
    )

    for result in results:
        summary = result.get("summary", {})

        high_risk = safe_float(
            summary.get(
                "high_risk_customers",
                summary.get("high_risk", 0),
            )
        )

        total_customers = safe_float(
            summary.get(
                "total_customers",
                summary.get("customers", 0),
            )
        )

        if total_customers <= 0:
            continue

        risk_percentage = (
            high_risk / total_customers
        ) * 100

        if risk_percentage >= 30:
            severity = "Critical"
        elif risk_percentage >= 20:
            severity = "High"
        elif risk_percentage >= 10:
            severity = "Medium"
        else:
            continue

        alerts.append(
            create_alert(
                title="High customer-risk concentration",
                message=(
                    f"{risk_percentage:.1f}% of analyzed customers "
                    f"are currently classified as high risk."
                ),
                severity=severity,
                source="Customer Risk",
                category="Customer Retention",
                metric_name="High Risk Customers %",
                metric_value=risk_percentage,
                threshold_value=10,
                recommendation=(
                    "Launch targeted retention and re-engagement "
                    "actions for high-risk customers."
                ),
            )
        )

    return alerts


def process_opportunity_alerts(opportunity_results):
    alerts = []

    if not opportunity_results:
        return alerts

    results = (
        opportunity_results
        if isinstance(opportunity_results, list)
        else [opportunity_results]
    )

    for result in results:
        opportunities = result.get(
            "opportunities",
            result.get("results", []),
        )

        for opportunity in opportunities:
            score = safe_float(
                opportunity.get("score", 0)
            )

            classification = str(
                opportunity.get(
                    "classification",
                    opportunity.get("class", ""),
                )
            )

            name = (
                opportunity.get("name")
                or opportunity.get("label")
                or opportunity.get("entity")
                or "Business Area"
            )

            if score >= 75:
                severity = "High"
            elif score >= 60:
                severity = "Medium"
            else:
                continue

            alerts.append(
                create_alert(
                    title=f"Growth opportunity: {name}",
                    message=(
                        f"{name} has an opportunity score of "
                        f"{score:.1f} and is classified as "
                        f"{classification or 'high potential'}."
                    ),
                    severity=severity,
                    source="Opportunity Detection",
                    category="Opportunity",
                    metric_name="Opportunity Score",
                    metric_value=score,
                    threshold_value=60,
                    recommendation=(
                        f"Evaluate expansion and investment "
                        f"opportunities for {name}."
                    ),
                    metadata=opportunity,
                )
            )

    return alerts


def process_recommendation_alerts(recommendation_results):
    alerts = []

    if not recommendation_results:
        return alerts

    results = (
        recommendation_results
        if isinstance(recommendation_results, list)
        else [recommendation_results]
    )

    for recommendation in results:
        priority = str(
            recommendation.get(
                "priority",
                "",
            )
        )

        if priority not in {"Critical", "High"}:
            continue

        title = recommendation.get(
            "title",
            "Important business recommendation",
        )

        message = recommendation.get(
            "reason",
            recommendation.get(
                "recommendation",
                "An important business recommendation requires attention.",
            ),
        )

        alerts.append(
            create_alert(
                title=title,
                message=message,
                severity=priority,
                source="Recommendation Engine",
                category=recommendation.get(
                    "category",
                    "Decision",
                ),
                recommendation=recommendation.get(
                    "recommendation",
                    "",
                ),
                metadata=recommendation,
            )
        )

    return alerts


def deduplicate_alerts(alerts):
    unique = {}

    for alert in alerts:
        key = (
            alert.get("title", "").strip().lower(),
            alert.get("source", "").strip().lower(),
        )

        existing = unique.get(key)

        if not existing:
            unique[key] = alert
            continue

        current_rank = SEVERITY_ORDER.get(
            alert.get("severity", "Low"),
            1,
        )

        existing_rank = SEVERITY_ORDER.get(
            existing.get("severity", "Low"),
            1,
        )

        if current_rank > existing_rank:
            unique[key] = alert

    return list(unique.values())


def rank_alerts(alerts):
    return sorted(
        alerts,
        key=lambda item: (
            SEVERITY_ORDER.get(
                item.get("severity", "Low"),
                1,
            ),
            item.get("metric_value") or 0,
        ),
        reverse=True,
    )


def generate_business_alerts(
    forecast_results=None,
    anomaly_results=None,
    risk_results=None,
    opportunity_results=None,
    recommendation_results=None,
):
    alerts = []

    alerts.extend(
        process_forecast_alerts(
            forecast_results
        )
    )

    alerts.extend(
        process_anomaly_alerts(
            anomaly_results
        )
    )

    alerts.extend(
        process_customer_risk_alerts(
            risk_results
        )
    )

    alerts.extend(
        process_opportunity_alerts(
            opportunity_results
        )
    )

    alerts.extend(
        process_recommendation_alerts(
            recommendation_results
        )
    )

    alerts = deduplicate_alerts(alerts)

    return rank_alerts(alerts)


def calculate_alert_summary(alerts):
    summary = {
        "total": len(alerts),
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for alert in alerts:
        severity = str(
            alert.get("severity", "Low")
        ).lower()

        key = severity

        if key in summary:
            summary[key] += 1

    return summary