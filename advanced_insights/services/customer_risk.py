import numpy as np
import pandas as pd


# ============================================================
# COLUMN DETECTION
# ============================================================

def detect_column(df, candidates):
    """
    Detect a column using exact matching first,
    followed by partial matching.
    """

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    # Exact match
    for candidate in candidates:

        candidate = candidate.lower().strip()

        if candidate in normalized:
            return normalized[candidate]

    # Partial match
    for column in df.columns:

        column_name = str(column).strip().lower()

        for candidate in candidates:

            if candidate.lower().strip() in column_name:
                return column

    return None


# ============================================================
# PREPARE CUSTOMER DATA
# ============================================================

def prepare_customer_data(
    df,
    customer_column,
    date_column,
    metric_column=None,
    quantity_column=None,
):
    """
    Clean and prepare customer transaction data.
    """

    data = df.copy()

    if customer_column not in data.columns:
        return pd.DataFrame()

    if date_column not in data.columns:
        return pd.DataFrame()

    # Customer
    data[customer_column] = (
        data[customer_column]
        .astype(str)
        .str.strip()
    )

    data = data[
        (data[customer_column] != "")
        & (data[customer_column].str.lower() != "nan")
        & (data[customer_column].str.lower() != "none")
    ]

    # Date
    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce"
    )

    data = data.dropna(
        subset=[
            customer_column,
            date_column
        ]
    )

    # Revenue / sales
    if metric_column and metric_column in data.columns:

        data[metric_column] = pd.to_numeric(
            data[metric_column],
            errors="coerce"
        ).fillna(0)

    # Quantity
    if quantity_column and quantity_column in data.columns:

        data[quantity_column] = pd.to_numeric(
            data[quantity_column],
            errors="coerce"
        ).fillna(0)

    return data


# ============================================================
# CUSTOMER RFM CALCULATION
# ============================================================

def calculate_customer_rfm(
    data,
    customer_column,
    date_column,
    metric_column,
    quantity_column=None,
):
    """
    Calculate Recency, Frequency and Monetary values
    for every customer.
    """

    if data.empty:
        return pd.DataFrame()

    analysis_date = data[date_column].max().normalize()

    grouped = data.groupby(customer_column)

    rfm = grouped.agg(
        last_purchase=(date_column, "max"),
        frequency=(date_column, "count"),
    ).reset_index()

    # --------------------------------------------------------
    # Recency
    # --------------------------------------------------------

    rfm["recency"] = (
        analysis_date - rfm["last_purchase"]
    ).dt.days

    # --------------------------------------------------------
    # Monetary
    # --------------------------------------------------------

    if metric_column and metric_column in data.columns:

        monetary = (
            data.groupby(customer_column)[metric_column]
            .sum()
            .reset_index(name="monetary")
        )

        rfm = rfm.merge(
            monetary,
            on=customer_column,
            how="left"
        )

    else:

        rfm["monetary"] = 0

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    if quantity_column and quantity_column in data.columns:

        quantity = (
            data.groupby(customer_column)[quantity_column]
            .sum()
            .reset_index(name="total_quantity")
        )

        rfm = rfm.merge(
            quantity,
            on=customer_column,
            how="left"
        )

    else:

        rfm["total_quantity"] = 0

    # --------------------------------------------------------
    # First purchase
    # --------------------------------------------------------

    first_purchase = (
        data.groupby(customer_column)[date_column]
        .min()
        .reset_index(name="first_purchase")
    )

    rfm = rfm.merge(
        first_purchase,
        on=customer_column,
        how="left"
    )

    # --------------------------------------------------------
    # Average order value
    # --------------------------------------------------------

    rfm["average_order_value"] = np.where(
        rfm["frequency"] > 0,
        rfm["monetary"] / rfm["frequency"],
        0
    )

    return rfm


# ============================================================
# RFM SCORING
# ============================================================

def calculate_rfm_scores(rfm):
    """
    Convert RFM values into 1-5 scores.
    """

    if rfm.empty:
        return rfm

    result = rfm.copy()

    # --------------------------------------------------------
    # Recency
    #
    # Lower recency is better.
    # --------------------------------------------------------

    try:

        result["recency_score"] = pd.qcut(
            result["recency"].rank(
                method="first"
            ),
            5,
            labels=[5, 4, 3, 2, 1]
        ).astype(int)

    except Exception:

        result["recency_score"] = 3

    # --------------------------------------------------------
    # Frequency
    # --------------------------------------------------------

    try:

        result["frequency_score"] = pd.qcut(
            result["frequency"].rank(
                method="first"
            ),
            5,
            labels=[1, 2, 3, 4, 5]
        ).astype(int)

    except Exception:

        result["frequency_score"] = 3

    # --------------------------------------------------------
    # Monetary
    # --------------------------------------------------------

    try:

        result["monetary_score"] = pd.qcut(
            result["monetary"].rank(
                method="first"
            ),
            5,
            labels=[1, 2, 3, 4, 5]
        ).astype(int)

    except Exception:

        result["monetary_score"] = 3

    # --------------------------------------------------------
    # RFM overall score
    # --------------------------------------------------------

    result["rfm_score"] = (
        result["recency_score"]
        + result["frequency_score"]
        + result["monetary_score"]
    )

    return result


# ============================================================
# CUSTOMER RISK SCORE
# ============================================================

def calculate_risk_scores(rfm):
    """
    Calculate a 0-100 customer risk score.

    Higher score = higher customer risk.
    """

    if rfm.empty:
        return rfm

    result = rfm.copy()

    # --------------------------------------------------------
    # Recency risk
    #
    # Recency score is 1-5 where:
    # 5 = very recent
    # 1 = very old
    #
    # Convert into risk:
    # 5 -> 0% risk
    # 1 -> 100% risk
    # --------------------------------------------------------

    result["recency_risk"] = (
        (5 - result["recency_score"]) / 4
    ) * 100

    # --------------------------------------------------------
    # Frequency risk
    # --------------------------------------------------------

    result["frequency_risk"] = (
        (5 - result["frequency_score"]) / 4
    ) * 100

    # --------------------------------------------------------
    # Monetary risk
    # --------------------------------------------------------

    result["monetary_risk"] = (
        (5 - result["monetary_score"]) / 4
    ) * 100

    # --------------------------------------------------------
    # Weighted risk
    #
    # Recency receives highest importance.
    # --------------------------------------------------------

    result["risk_score"] = (
        result["recency_risk"] * 0.50
        + result["frequency_risk"] * 0.30
        + result["monetary_risk"] * 0.20
    )

    result["risk_score"] = (
        result["risk_score"]
        .clip(0, 100)
        .round(1)
    )

    return result


# ============================================================
# RISK LEVEL
# ============================================================

def classify_risk(risk_score, recency):
    """
    Convert numerical risk into business-friendly levels.
    """

    # Very old customers are automatically elevated.
    if recency >= 90 or risk_score >= 75:
        return "High Risk"

    if recency >= 60 or risk_score >= 55:
        return "At Risk"

    if recency >= 30 or risk_score >= 35:
        return "Medium Risk"

    return "Low Risk"


# ============================================================
# APPLY RISK CLASSIFICATION
# ============================================================

def classify_customers(rfm):
    """
    Add customer risk level and recommended action.
    """

    if rfm.empty:
        return rfm

    result = rfm.copy()

    result["risk_level"] = result.apply(
        lambda row: classify_risk(
            row["risk_score"],
            row["recency"]
        ),
        axis=1
    )

    # --------------------------------------------------------
    # Recommended action
    # --------------------------------------------------------

    def action(row):

        level = row["risk_level"]

        if level == "High Risk":

            return (
                "Immediate retention campaign "
                "with personalized offer"
            )

        if level == "At Risk":

            return (
                "Send targeted re-engagement "
                "offer"
            )

        if level == "Medium Risk":

            return (
                "Monitor engagement and "
                "encourage repeat purchase"
            )

        return (
            "Maintain relationship and "
            "consider loyalty incentives"
        )

    result["recommended_action"] = result.apply(
        action,
        axis=1
    )

    return result


# ============================================================
# RISK SUMMARY
# ============================================================

def calculate_risk_summary(risk_data):
    """
    Calculate dashboard-level customer risk KPIs.
    """

    if risk_data.empty:

        return {
            "total_customers": 0,
            "high_risk_customers": 0,
            "at_risk_customers": 0,
            "medium_risk_customers": 0,
            "low_risk_customers": 0,
            "risk_rate": 0,
            "average_risk_score": 0,
        }

    total = len(risk_data)

    high_risk = (
        risk_data["risk_level"] == "High Risk"
    ).sum()

    at_risk = (
        risk_data["risk_level"] == "At Risk"
    ).sum()

    medium_risk = (
        risk_data["risk_level"] == "Medium Risk"
    ).sum()

    low_risk = (
        risk_data["risk_level"] == "Low Risk"
    ).sum()

    # At Risk includes both At Risk + High Risk.
    risk_rate = (
        ((high_risk + at_risk) / total) * 100
        if total
        else 0
    )

    return {
        "total_customers": total,
        "high_risk_customers": int(high_risk),
        "at_risk_customers": int(at_risk),
        "medium_risk_customers": int(medium_risk),
        "low_risk_customers": int(low_risk),
        "risk_rate": round(risk_rate, 2),
        "average_risk_score": round(
            risk_data["risk_score"].mean(),
            2
        ),
    }


# ============================================================
# RISK DISTRIBUTION
# ============================================================

def calculate_risk_distribution(risk_data):
    """
    Return counts and percentages for each risk level.
    """

    if risk_data.empty:
        return []

    total = len(risk_data)

    order = [
        "High Risk",
        "At Risk",
        "Medium Risk",
        "Low Risk",
    ]

    results = []

    for level in order:

        count = (
            risk_data["risk_level"] == level
        ).sum()

        percentage = (
            (count / total) * 100
            if total
            else 0
        )

        results.append({
            "name": level,
            "count": int(count),
            "percentage": round(
                percentage,
                2
            ),
        })

    return results


# ============================================================
# TOP RISKY CUSTOMERS
# ============================================================

def get_top_risky_customers(
    risk_data,
    limit=10
):
    """
    Return customers with the highest risk.
    """

    if risk_data.empty:
        return []

    columns = [
        "customer",
        "recency",
        "frequency",
        "monetary",
        "risk_score",
        "risk_level",
        "recommended_action",
        "last_purchase",
    ]

    # Customer column will be renamed before this function
    # if necessary.
    available = [
        column
        for column in columns
        if column in risk_data.columns
    ]

    result = (
        risk_data
        .sort_values(
            "risk_score",
            ascending=False
        )
        .head(limit)
    )

    customers = []

    for _, row in result.iterrows():

        customer_value = (
            row["customer"]
            if "customer" in row
            else ""
        )

        customers.append({
            "customer": str(customer_value),
            "recency": int(
                row["recency"]
            ),
            "frequency": int(
                row["frequency"]
            ),
            "monetary": round(
                float(row["monetary"]),
                2
            ),
            "risk_score": round(
                float(row["risk_score"]),
                1
            ),
            "risk_level": row["risk_level"],
            "recommended_action": row[
                "recommended_action"
            ],
            "last_purchase": row[
                "last_purchase"
            ],
        })

    return customers


# ============================================================
# AUTOMATED BUSINESS INSIGHTS
# ============================================================

def generate_customer_risk_insights(
    risk_data,
    summary
):
    """
    Generate business-friendly explanations.
    """

    insights = []

    if risk_data.empty:
        return [
            "No customer risk insights could be generated."
        ]

    total = summary["total_customers"]
    high_risk = summary["high_risk_customers"]
    at_risk = summary["at_risk_customers"]
    risk_rate = summary["risk_rate"]

    # --------------------------------------------------------
    # Overall risk
    # --------------------------------------------------------

    if risk_rate >= 30:

        insights.append(
            f"{risk_rate:.1f}% of analyzed customers "
            "are currently classified as At Risk or "
            "High Risk. Customer retention should be "
            "treated as a priority."
        )

    elif risk_rate >= 15:

        insights.append(
            f"{risk_rate:.1f}% of analyzed customers "
            "show elevated churn risk. A targeted "
            "retention strategy could reduce customer loss."
        )

    else:

        insights.append(
            f"Customer risk is relatively controlled, "
            f"with {risk_rate:.1f}% of customers classified "
            "as At Risk or High Risk."
        )

    # --------------------------------------------------------
    # High risk
    # --------------------------------------------------------

    if high_risk > 0:

        insights.append(
            f"{high_risk:,} customers are classified as "
            "High Risk and should receive immediate "
            "retention attention."
        )

    # --------------------------------------------------------
    # Recent behavior
    # --------------------------------------------------------

    average_recency = risk_data["recency"].mean()

    if average_recency >= 60:

        insights.append(
            f"Average customer recency is "
            f"{average_recency:.0f} days, indicating "
            "weaker recent engagement across the customer base."
        )

    elif average_recency <= 30:

        insights.append(
            f"Average customer recency is only "
            f"{average_recency:.0f} days, suggesting "
            "relatively healthy recent purchasing activity."
        )

    # --------------------------------------------------------
    # High-value risky customers
    # --------------------------------------------------------

    if not risk_data.empty:

        monetary_threshold = (
            risk_data["monetary"].quantile(.75)
        )

        high_value_risky = risk_data[
            (
                risk_data["monetary"]
                >= monetary_threshold
            )
            &
            (
                risk_data["risk_level"].isin(
                    ["At Risk", "High Risk"]
                )
            )
        ]

        if len(high_value_risky) > 0:

            insights.append(
                f"{len(high_value_risky):,} high-value "
                "customers are showing elevated risk. "
                "These customers should receive personalized "
                "retention campaigns first."
            )

    return insights


# ============================================================
# FINAL PIPELINE
# ============================================================

def run_customer_risk_analysis(
    df,
    customer_column,
    date_column,
    metric_column=None,
    quantity_column=None,
):
    """
    Complete customer risk analysis pipeline.

    Returns:
        risk_data
        summary
        distribution
        insights
    """

    data = prepare_customer_data(
        df=df,
        customer_column=customer_column,
        date_column=date_column,
        metric_column=metric_column,
        quantity_column=quantity_column,
    )

    if data.empty:

        return (
            pd.DataFrame(),
            calculate_risk_summary(
                pd.DataFrame()
            ),
            [],
            [
                "No valid customer transaction data "
                "was available for analysis."
            ]
        )

    rfm = calculate_customer_rfm(
        data=data,
        customer_column=customer_column,
        date_column=date_column,
        metric_column=metric_column,
        quantity_column=quantity_column,
    )

    if rfm.empty:

        return (
            pd.DataFrame(),
            calculate_risk_summary(
                pd.DataFrame()
            ),
            [],
            [
                "Customer RFM analysis could not "
                "be calculated."
            ]
        )

    rfm = calculate_rfm_scores(rfm)

    rfm = calculate_risk_scores(rfm)

    rfm = classify_customers(rfm)

    # Standardize customer column for templates.
    if customer_column != "customer":

        rfm = rfm.rename(
            columns={
                customer_column: "customer"
            }
        )

    summary = calculate_risk_summary(
        rfm
    )

    distribution = calculate_risk_distribution(
        rfm
    )

    insights = generate_customer_risk_insights(
        rfm,
        summary
    )

    return (
        rfm,
        summary,
        distribution,
        insights,
    )