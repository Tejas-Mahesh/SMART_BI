
import math

import pandas as pd


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {
    "sales": [
        "sales",
        "sale",
        "revenue",
        "total_sales",
        "total_revenue",
        "amount",
        "sales_amount",
        "revenue_amount",
        "net_sales",
    ],
    "profit": [
        "profit",
        "net_profit",
        "gross_profit",
        "profit_amount",
        "profit_value",
    ],
    "cost": [
        "cost",
        "total_cost",
        "cost_amount",
        "expense",
        "expenses",
        "operating_cost",
    ],
    "quantity": [
        "quantity",
        "qty",
        "units",
        "units_sold",
        "sales_quantity",
    ],
    "customer": [
        "customer",
        "customer_id",
        "customer_name",
        "client",
        "client_id",
    ],
    "order": [
        "order",
        "order_id",
        "order_number",
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
        "marketing_expense",
    ],
    "returns": [
        "returns",
        "return_amount",
        "returned_amount",
        "refund",
        "refund_amount",
        "return_value",
    ],
}


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize_column_name(value):
    """
    Convert a dataframe column name into a normalized format
    suitable for alias matching.
    """
    if value is None:
        return ""

    value = str(value).strip().lower()

    for character in [" ", "-", "/", "\\", ".", "(", ")", "[", "]"]:
        value = value.replace(character, "_")

    while "__" in value:
        value = value.replace("__", "_")

    return value.strip("_")


def find_column(dataframe, aliases):
    """
    Find the first dataframe column matching one of the
    supplied aliases.
    """
    if dataframe is None or dataframe.empty:
        return None

    normalized_columns = {}

    for column in dataframe.columns:
        normalized_columns[normalize_column_name(column)] = column

    for alias in aliases:
        normalized_alias = normalize_column_name(alias)

        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    # Partial matching as a fallback.
    for column in dataframe.columns:
        normalized_column = normalize_column_name(column)

        for alias in aliases:
            normalized_alias = normalize_column_name(alias)

            if (
                normalized_alias
                and normalized_alias in normalized_column
            ):
                return column

    return None


def get_column(dataframe, logical_name):
    """
    Resolve a logical metric name to an actual dataframe column.
    """
    aliases = COLUMN_ALIASES.get(logical_name, [])

    return find_column(dataframe, aliases)


def safe_float(value, default=0.0):
    """
    Convert a value safely to float.
    """
    try:
        if value is None:
            return float(default)

        if isinstance(value, bool):
            return float(default)

        numeric_value = float(value)

        if not math.isfinite(numeric_value):
            return float(default)

        return numeric_value

    except (TypeError, ValueError):
        return float(default)


def round_value(value, digits=2):
    """
    Safely round numeric values.
    """
    return round(safe_float(value), digits)


def clean_numeric_series(series):
    """
    Convert a pandas series to numeric values while ignoring
    invalid values.
    """
    if series is None:
        return pd.Series(dtype="float64")

    numeric = pd.to_numeric(series, errors="coerce")

    return numeric.dropna()


def unique_count(dataframe, column):
    """
    Count unique non-null values.
    """
    if dataframe is None or column is None:
        return 0

    try:
        return int(dataframe[column].dropna().nunique())
    except Exception:
        return 0


# ============================================================
# METRIC CALCULATIONS
# ============================================================

def calculate_metric_values(dataframe):
    """
    Calculate the business metrics required by the alert engine.
    """

    if dataframe is None:
        dataframe = pd.DataFrame()

    records = int(len(dataframe))

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    sales_column = get_column(dataframe, "sales")

    if sales_column:
        sales_series = clean_numeric_series(
            dataframe[sales_column]
        )
        sales = safe_float(sales_series.sum())
    else:
        sales = 0.0

    # --------------------------------------------------------
    # PROFIT
    # --------------------------------------------------------

    profit_column = get_column(dataframe, "profit")

    if profit_column:
        profit_series = clean_numeric_series(
            dataframe[profit_column]
        )
        profit = safe_float(profit_series.sum())
    else:
        profit = 0.0

    # --------------------------------------------------------
    # COST
    # --------------------------------------------------------

    cost_column = get_column(dataframe, "cost")

    if cost_column:
        cost_series = clean_numeric_series(
            dataframe[cost_column]
        )
        cost = safe_float(cost_series.sum())
    else:
        cost = 0.0

    # --------------------------------------------------------
    # QUANTITY
    # --------------------------------------------------------

    quantity_column = get_column(dataframe, "quantity")

    if quantity_column:
        quantity_series = clean_numeric_series(
            dataframe[quantity_column]
        )
        quantity = safe_float(quantity_series.sum())
    else:
        quantity = 0.0

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    customer_column = get_column(dataframe, "customer")

    if customer_column:
        customers = unique_count(
            dataframe,
            customer_column,
        )
    else:
        customers = 0

    # --------------------------------------------------------
    # ORDERS
    # --------------------------------------------------------

    order_column = get_column(dataframe, "order")

    if order_column:
        orders = unique_count(
            dataframe,
            order_column,
        )
    else:
        orders = records

    # --------------------------------------------------------
    # MARKETING SPEND
    # --------------------------------------------------------

    marketing_column = get_column(
        dataframe,
        "marketing_spend",
    )

    if marketing_column:
        marketing_series = clean_numeric_series(
            dataframe[marketing_column]
        )
        marketing_spend = safe_float(
            marketing_series.sum()
        )
    else:
        marketing_spend = 0.0

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    returns_column = get_column(dataframe, "returns")

    if returns_column:
        returns_series = clean_numeric_series(
            dataframe[returns_column]
        )
        returns = safe_float(returns_series.sum())
    else:
        returns = 0.0

    # --------------------------------------------------------
    # DERIVED METRICS
    # --------------------------------------------------------

    if orders > 0:
        average_order_value = sales / orders
    else:
        average_order_value = 0.0

    if sales != 0:
        profit_margin = (profit / sales) * 100
        return_rate = (returns / sales) * 100
    else:
        profit_margin = 0.0
        return_rate = 0.0

    return {
        "records": records,
        "sales": round_value(sales),
        "profit": round_value(profit),
        "cost": round_value(cost),
        "quantity": round_value(quantity),
        "customers": customers,
        "orders": orders,
        "marketing_spend": round_value(marketing_spend),
        "returns": round_value(returns),
        "average_order_value": round_value(
            average_order_value
        ),
        "profit_margin": round_value(
            profit_margin
        ),
        "return_rate": round_value(
            return_rate
        ),
    }


# ============================================================
# ALERT CREATION
# ============================================================

def create_alert(
    title,
    category,
    severity,
    description,
    trigger_type,
    metric_name,
    metric_value,
    threshold_value,
    comparison_operator,
    recommended_action,
    metadata=None,
):
    """
    Create a standardized alert dictionary.
    """

    return {
        "title": title,
        "category": category,
        "severity": severity,
        "description": description,
        "trigger_type": trigger_type,
        "metric_name": metric_name,
        "metric_value": round_value(metric_value),
        "threshold_value": round_value(
            threshold_value
        ),
        "comparison_operator": comparison_operator,
        "recommended_action": recommended_action,
        "metadata": metadata or {},
    }


# ============================================================
# SALES ALERT
# ============================================================

def detect_sales_alerts(metrics):
    alerts = []

    sales = safe_float(metrics.get("sales"))

    if sales <= 0:
        alerts.append(
            create_alert(
                title="Sales Activity Alert",
                category="Sales",
                severity="High",
                description=(
                    "The selected dataset does not show "
                    "positive sales activity."
                ),
                trigger_type="Zero or Negative Sales",
                metric_name="Sales",
                metric_value=sales,
                threshold_value=0,
                comparison_operator="<=",
                recommended_action=(
                    "Review the selected dataset, sales records, "
                    "and recent sales activity."
                ),
            )
        )

    return alerts


# ============================================================
# PROFIT ALERTS
# ============================================================

def detect_profit_alerts(metrics):
    alerts = []

    profit = safe_float(metrics.get("profit"))
    profit_margin = safe_float(
        metrics.get("profit_margin")
    )

    if profit < 0:
        alerts.append(
            create_alert(
                title="Negative Profit Detected",
                category="Financial",
                severity="Critical",
                description=(
                    "The selected dataset indicates an overall "
                    "negative profit position."
                ),
                trigger_type="Negative Profit",
                metric_name="Profit",
                metric_value=profit,
                threshold_value=0,
                comparison_operator="<",
                recommended_action=(
                    "Review pricing, cost structure, and "
                    "loss-making transactions."
                ),
            )
        )

    elif profit == 0:
        alerts.append(
            create_alert(
                title="Zero Profit Detected",
                category="Financial",
                severity="High",
                description=(
                    "The selected dataset indicates no positive "
                    "profit."
                ),
                trigger_type="Zero Profit",
                metric_name="Profit",
                metric_value=profit,
                threshold_value=0,
                comparison_operator="=",
                recommended_action=(
                    "Review revenue and cost drivers to determine "
                    "why profitability is not positive."
                ),
            )
        )

    if 0 < profit_margin < 10:
        alerts.append(
            create_alert(
                title="Low Profit Margin",
                category="Financial",
                severity="Medium",
                description=(
                    "The calculated profit margin is below 10%."
                ),
                trigger_type="Profit Margin Threshold",
                metric_name="Profit Margin",
                metric_value=profit_margin,
                threshold_value=10,
                comparison_operator="<",
                recommended_action=(
                    "Review pricing, operating costs, and "
                    "high-cost products or transactions."
                ),
            )
        )

    return alerts


# ============================================================
# COST ALERTS
# ============================================================

def detect_cost_alerts(metrics):
    alerts = []

    cost = safe_float(metrics.get("cost"))
    sales = safe_float(metrics.get("sales"))

    if cost > 0 and sales > 0:
        cost_ratio = (cost / sales) * 100

        if cost_ratio > 80:
            alerts.append(
                create_alert(
                    title="High Cost-to-Sales Ratio",
                    category="Financial",
                    severity="High",
                    description=(
                        "Costs represent more than 80% of "
                        "the recorded sales value."
                    ),
                    trigger_type="Cost-to-Sales Threshold",
                    metric_name="Cost Ratio",
                    metric_value=cost_ratio,
                    threshold_value=80,
                    comparison_operator=">",
                    recommended_action=(
                        "Review major cost drivers and identify "
                        "opportunities for cost control."
                    ),
                    metadata={
                        "sales": sales,
                        "cost": cost,
                    },
                )
            )

    return alerts


# ============================================================
# RETURNS ALERTS
# ============================================================

def detect_return_alerts(metrics):
    alerts = []

    return_rate = safe_float(
        metrics.get("return_rate")
    )

    returns = safe_float(
        metrics.get("returns")
    )

    if return_rate > 10:
        alerts.append(
            create_alert(
                title="High Return Rate",
                category="Returns",
                severity="High",
                description=(
                    "The return value represents more than "
                    "10% of recorded sales."
                ),
                trigger_type="Return Rate Threshold",
                metric_name="Return Rate",
                metric_value=return_rate,
                threshold_value=10,
                comparison_operator=">",
                recommended_action=(
                    "Investigate return reasons, products, "
                    "regions, and customer segments."
                ),
                metadata={
                    "returns": returns,
                },
            )
        )

    return alerts


# ============================================================
# MARKETING ALERTS
# ============================================================

def detect_marketing_alerts(metrics):
    alerts = []

    marketing_spend = safe_float(
        metrics.get("marketing_spend")
    )

    sales = safe_float(
        metrics.get("sales")
    )

    if (
        marketing_spend > 0
        and sales > 0
        and marketing_spend > sales * 0.25
    ):
        spend_ratio = (
            marketing_spend / sales
        ) * 100

        alerts.append(
            create_alert(
                title="High Marketing Spend Ratio",
                category="Marketing",
                severity="Medium",
                description=(
                    "Marketing spend exceeds 25% of the "
                    "recorded sales value."
                ),
                trigger_type="Marketing Spend Threshold",
                metric_name="Marketing Spend Ratio",
                metric_value=spend_ratio,
                threshold_value=25,
                comparison_operator=">",
                recommended_action=(
                    "Review campaign efficiency, channel "
                    "performance, and marketing return."
                ),
                metadata={
                    "marketing_spend": marketing_spend,
                    "sales": sales,
                },
            )
        )

    return alerts


# ============================================================
# CUSTOMER ALERTS
# ============================================================

def detect_customer_alerts(metrics):
    alerts = []

    customers = int(
        safe_float(metrics.get("customers"))
    )

    if customers == 0:
        alerts.append(
            create_alert(
                title="No Customer Records Detected",
                category="Customer",
                severity="Medium",
                description=(
                    "No unique customer records were detected "
                    "in the selected dataset."
                ),
                trigger_type="Customer Record Check",
                metric_name="Customers",
                metric_value=customers,
                threshold_value=0,
                comparison_operator="=",
                recommended_action=(
                    "Verify that the dataset contains customer "
                    "information or a valid customer identifier."
                ),
            )
        )

    return alerts


# ============================================================
# OPERATIONAL ALERTS
# ============================================================

def detect_operational_alerts(metrics):
    alerts = []

    records = int(
        safe_float(metrics.get("records"))
    )

    if records == 0:
        alerts.append(
            create_alert(
                title="Empty Dataset",
                category="Operational",
                severity="Critical",
                description=(
                    "The selected dataset version contains "
                    "no records."
                ),
                trigger_type="Dataset Record Check",
                metric_name="Records",
                metric_value=records,
                threshold_value=0,
                comparison_operator="=",
                recommended_action=(
                    "Review the dataset version and Data "
                    "Management pipeline before making decisions."
                ),
            )
        )

    return alerts


# ============================================================
# GENERAL ALERTS
# ============================================================

def detect_general_alerts(metrics):
    alerts = []

    records = int(
        safe_float(metrics.get("records"))
    )

    if records > 0 and records < 10:
        alerts.append(
            create_alert(
                title="Limited Dataset Size",
                category="General",
                severity="Info",
                description=(
                    "The selected dataset contains fewer than "
                    "10 records, which may limit the usefulness "
                    "of business conclusions."
                ),
                trigger_type="Dataset Size Threshold",
                metric_name="Records",
                metric_value=records,
                threshold_value=10,
                comparison_operator="<",
                recommended_action=(
                    "Consider using a larger or more complete "
                    "dataset before making major business decisions."
                ),
            )
        )

    return alerts


# ============================================================
# MAIN ALERT ENGINE
# ============================================================

def generate_business_alerts(dataframe):
    """
    Analyze a dataframe and return detected business alerts.

    This function does not create database records.
    The view is responsible for saving the returned alerts.
    """

    if dataframe is None:
        dataframe = pd.DataFrame()

    metrics = calculate_metric_values(
        dataframe
    )

    alerts = []

    alerts.extend(
        detect_sales_alerts(metrics)
    )

    alerts.extend(
        detect_profit_alerts(metrics)
    )

    alerts.extend(
        detect_cost_alerts(metrics)
    )

    alerts.extend(
        detect_return_alerts(metrics)
    )

    alerts.extend(
        detect_marketing_alerts(metrics)
    )

    alerts.extend(
        detect_customer_alerts(metrics)
    )

    alerts.extend(
        detect_operational_alerts(metrics)
    )

    alerts.extend(
        detect_general_alerts(metrics)
    )

    return {
        "metrics": metrics,
        "alerts": alerts,
        "alert_count": len(alerts),
    }
