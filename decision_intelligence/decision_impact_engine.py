
# ============================================================
# DECISION IMPACT ANALYSIS ENGINE
# ============================================================

import math

import pandas as pd


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {
    "date": [
        "date",
        "order_date",
        "transaction_date",
        "invoice_date",
        "purchase_date",
        "created_at",
    ],
    "sales": [
        "sales",
        "sale",
        "revenue",
        "total_sales",
        "total_revenue",
        "amount",
        "sales_amount",
        "revenue_amount",
    ],
    "profit": [
        "profit",
        "net_profit",
        "gross_profit",
        "profit_amount",
    ],
    "cost": [
        "cost",
        "total_cost",
        "cost_amount",
        "expense",
        "expenses",
    ],
    "quantity": [
        "quantity",
        "qty",
        "units",
        "units_sold",
        "sold_quantity",
    ],
    "customer": [
        "customer",
        "customer_id",
        "customer_name",
        "client",
        "client_id",
    ],
    "product": [
        "product",
        "product_id",
        "product_name",
        "item",
        "item_id",
    ],
    "order": [
        "order",
        "order_id",
        "invoice",
        "invoice_id",
        "transaction_id",
    ],
    "marketing_spend": [
        "marketing_spend",
        "marketing_cost",
        "ad_spend",
        "advertising_spend",
        "campaign_spend",
        "spend",
    ],
    "returns": [
        "return_amount",
        "returns",
        "returned_amount",
        "refund_amount",
        "refunds",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def normalize_column_name(value):
    """
    Normalize a dataframe column name for reliable matching.
    """
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_column(dataframe, aliases):
    """
    Find the first matching column from a list of aliases.
    """
    if dataframe is None or dataframe.empty:
        return None

    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    for alias in aliases:
        normalized_alias = normalize_column_name(alias)

        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    return None


def safe_float(value, default=0.0):
    """
    Convert a value to float safely.
    """
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.replace(",", "").strip()

        number = float(value)

        if math.isnan(number) or math.isinf(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def calculate_percentage_change(baseline, actual):
    """
    Calculate percentage change from baseline to actual.
    """
    baseline = safe_float(baseline)
    actual = safe_float(actual)

    if baseline == 0:
        if actual == 0:
            return 0.0

        return 100.0 if actual > 0 else -100.0

    return ((actual - baseline) / abs(baseline)) * 100


def calculate_expected_value(baseline, expected_change):
    """
    Calculate the expected value from a baseline and expected
    percentage change.
    """
    baseline = safe_float(baseline)
    expected_change = safe_float(expected_change)

    return baseline * (1 + expected_change / 100)


def calculate_impact_type(actual_change, expected_change):
    """
    Classify performance against the expected change.

    This classification describes whether the actual result
    met the expected target. It does not claim that increasing
    or decreasing a particular business metric is inherently
    good or bad.
    """
    actual_change = safe_float(actual_change)
    expected_change = safe_float(expected_change)

    tolerance = 0.000001

    difference = actual_change - expected_change

    if abs(difference) <= tolerance:
        return "Neutral"

    if difference > 0:
        return "Positive"

    return "Negative"


# ============================================================
# METRIC EXTRACTION
# ============================================================

def calculate_metric_value(dataframe, metric_name):
    """
    Calculate the actual value for the selected metric.

    Supported metrics:
        sales
        profit
        cost
        quantity
        customers
        orders
        marketing_spend
        returns
        average_order_value
        profit_margin
        return_rate
    """
    if dataframe is None:
        raise ValueError("No dataset was provided.")

    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("The provided dataset is not a valid dataframe.")

    if dataframe.empty:
        raise ValueError("The selected dataset contains no records.")

    metric = str(metric_name or "").strip().lower()

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    if metric == "sales":
        column = find_column(dataframe, COLUMN_ALIASES["sales"])

        if not column:
            raise ValueError(
                "A sales/revenue column could not be found in the dataset."
            )

        return float(
            pd.to_numeric(
                dataframe[column],
                errors="coerce",
            ).fillna(0).sum()
        )

    # --------------------------------------------------------
    # PROFIT
    # --------------------------------------------------------

    if metric == "profit":
        column = find_column(dataframe, COLUMN_ALIASES["profit"])

        if not column:
            raise ValueError(
                "A profit column could not be found in the dataset."
            )

        return float(
            pd.to_numeric(
                dataframe[column],
                errors="coerce",
            ).fillna(0).sum()
        )

    # --------------------------------------------------------
    # COST
    # --------------------------------------------------------

    if metric == "cost":
        column = find_column(dataframe, COLUMN_ALIASES["cost"])

        if not column:
            raise ValueError(
                "A cost/expense column could not be found in the dataset."
            )

        return float(
            pd.to_numeric(
                dataframe[column],
                errors="coerce",
            ).fillna(0).sum()
        )

    # --------------------------------------------------------
    # QUANTITY
    # --------------------------------------------------------

    if metric == "quantity":
        column = find_column(dataframe, COLUMN_ALIASES["quantity"])

        if not column:
            raise ValueError(
                "A quantity/units column could not be found in the dataset."
            )

        return float(
            pd.to_numeric(
                dataframe[column],
                errors="coerce",
            ).fillna(0).sum()
        )

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    if metric == "customers":
        column = find_column(dataframe, COLUMN_ALIASES["customer"])

        if column:
            return float(
                dataframe[column]
                .dropna()
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .nunique()
            )

        return float(len(dataframe))

    # --------------------------------------------------------
    # ORDERS
    # --------------------------------------------------------

    if metric == "orders":
        column = find_column(dataframe, COLUMN_ALIASES["order"])

        if column:
            return float(
                dataframe[column]
                .dropna()
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
                .dropna()
                .nunique()
            )

        return float(len(dataframe))

    # --------------------------------------------------------
    # MARKETING SPEND
    # --------------------------------------------------------

    if metric == "marketing_spend":
        column = find_column(
            dataframe,
            COLUMN_ALIASES["marketing_spend"],
        )

        if not column:
            raise ValueError(
                "A marketing spend column could not be found in the dataset."
            )

        return float(
            pd.to_numeric(
                dataframe[column],
                errors="coerce",
            ).fillna(0).sum()
        )

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    if metric == "returns":
        column = find_column(
            dataframe,
            COLUMN_ALIASES["returns"],
        )

        if not column:
            raise ValueError(
                "A returns/refund column could not be found in the dataset."
            )

        return float(
            pd.to_numeric(
                dataframe[column],
                errors="coerce",
            ).fillna(0).sum()
        )

    # --------------------------------------------------------
    # AVERAGE ORDER VALUE
    # --------------------------------------------------------

    if metric == "average_order_value":
        sales = calculate_metric_value(dataframe, "sales")
        orders = calculate_metric_value(dataframe, "orders")

        if orders == 0:
            return 0.0

        return sales / orders

    # --------------------------------------------------------
    # PROFIT MARGIN
    # --------------------------------------------------------

    if metric == "profit_margin":
        sales = calculate_metric_value(dataframe, "sales")
        profit = calculate_metric_value(dataframe, "profit")

        if sales == 0:
            return 0.0

        return (profit / sales) * 100

    # --------------------------------------------------------
    # RETURN RATE
    # --------------------------------------------------------

    if metric == "return_rate":
        sales = calculate_metric_value(dataframe, "sales")
        returns = calculate_metric_value(dataframe, "returns")

        if sales == 0:
            return 0.0

        return (returns / sales) * 100

    raise ValueError(
        f"Unsupported decision impact metric: {metric_name}"
    )


# ============================================================
# MAIN DECISION IMPACT ANALYSIS
# ============================================================

def analyze_decision_impact(
    dataframe,
    metric_name,
    baseline_value,
    expected_change,
    title="Decision Impact Analysis",
    category="General",
):
    """
    Analyze the actual impact of a decision.

    Inputs:
        dataframe:
            Cleaned DatasetVersion dataframe.

        metric_name:
            Metric to evaluate.

        baseline_value:
            Metric value before the decision.

        expected_change:
            Expected percentage change from baseline.

    Returns:
        A dictionary suitable for saving to
        DecisionImpactAnalysis.
    """

    if dataframe is None:
        raise ValueError("No dataset was provided.")

    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("The provided dataset is not a dataframe.")

    if dataframe.empty:
        raise ValueError("The selected dataset contains no records.")

    baseline = safe_float(baseline_value)
    expected_change_value = safe_float(expected_change)

    # --------------------------------------------------------
    # ACTUAL VALUE
    # --------------------------------------------------------

    actual = calculate_metric_value(
        dataframe,
        metric_name,
    )

    # --------------------------------------------------------
    # EXPECTED VALUE
    # --------------------------------------------------------

    expected = calculate_expected_value(
        baseline,
        expected_change_value,
    )

    # --------------------------------------------------------
    # ACTUAL CHANGE
    # --------------------------------------------------------

    actual_change = calculate_percentage_change(
        baseline,
        actual,
    )

    # --------------------------------------------------------
    # IMPACT
    # --------------------------------------------------------

    impact_value = actual - baseline

    impact_percentage = actual_change

    impact_type = calculate_impact_type(
        actual_change,
        expected_change_value,
    )

    # --------------------------------------------------------
    # GAP AGAINST EXPECTATION
    # --------------------------------------------------------

    expectation_gap = actual_change - expected_change_value

    # --------------------------------------------------------
    # RESULT SUMMARY
    # --------------------------------------------------------

    summary = {
        "metric_name": metric_name,
        "baseline_value": round(baseline, 4),
        "expected_value": round(expected, 4),
        "actual_value": round(actual, 4),
        "expected_change": round(expected_change_value, 4),
        "actual_change": round(actual_change, 4),
        "impact_value": round(impact_value, 4),
        "impact_percentage": round(impact_percentage, 4),
        "expectation_gap": round(expectation_gap, 4),
        "impact_type": impact_type,
    }

    # --------------------------------------------------------
    # ANALYSIS NOTES
    # --------------------------------------------------------

    if impact_type == "Positive":
        analysis_notes = (
            f"The actual {metric_name} change of "
            f"{actual_change:.2f}% exceeded the expected "
            f"change of {expected_change_value:.2f}%."
        )

    elif impact_type == "Negative":
        analysis_notes = (
            f"The actual {metric_name} change of "
            f"{actual_change:.2f}% was below the expected "
            f"change of {expected_change_value:.2f}%."
        )

    else:
        analysis_notes = (
            f"The actual {metric_name} change of "
            f"{actual_change:.2f}% matched the expected "
            f"change of {expected_change_value:.2f}%."
        )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {
        "title": title,
        "category": category,
        "metric_name": metric_name,

        "baseline_value": round(baseline, 4),
        "expected_value": round(expected, 4),
        "actual_value": round(actual, 4),

        "expected_change": round(
            expected_change_value,
            4,
        ),

        "actual_change": round(
            actual_change,
            4,
        ),

        "impact_value": round(
            impact_value,
            4,
        ),

        "impact_percentage": round(
            impact_percentage,
            4,
        ),

        "impact_type": impact_type,

        "status": "Monitoring",

        "analysis_notes": analysis_notes,

        "summary": summary,

        "metadata": {
            "records_analyzed": int(len(dataframe)),
            "expectation_gap": round(
                expectation_gap,
                4,
            ),
        },
    }


# ============================================================
# PUBLIC ENGINE FUNCTION
# ============================================================

def generate_decision_impact_analysis(
    dataframe,
    metric_name,
    baseline_value,
    expected_change,
    title="Decision Impact Analysis",
    category="General",
):
    """
    Public wrapper used by the Django view.
    """
    return analyze_decision_impact(
        dataframe=dataframe,
        metric_name=metric_name,
        baseline_value=baseline_value,
        expected_change=expected_change,
        title=title,
        category=category,
    )
