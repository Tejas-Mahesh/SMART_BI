
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
        "sales_amount",
        "revenue_amount",
        "amount",
        "net_sales",
        "net_revenue",
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
        "cogs",
        "cost_of_goods_sold",
    ],
    "quantity": [
        "quantity",
        "qty",
        "units",
        "units_sold",
        "volume",
    ],
    "customers": [
        "customer",
        "customer_id",
        "customer_name",
        "customers",
        "client",
        "client_id",
    ],
    "orders": [
        "order",
        "order_id",
        "order_number",
        "transaction",
        "transaction_id",
    ],
    "spend": [
        "spend",
        "marketing_spend",
        "ad_spend",
        "advertising_spend",
        "campaign_spend",
        "marketing_cost",
    ],
    "returns": [
        "return",
        "return_amount",
        "refund",
        "refund_amount",
        "returned_amount",
    ],
}


# ============================================================
# COLUMN HELPERS
# ============================================================

def normalize_column_name(column_name):
    """
    Normalize a dataframe column name so aliases can be matched
    consistently.
    """
    return (
        str(column_name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def find_column(dataframe, logical_name):
    """
    Find the first dataframe column matching a logical metric.
    """
    if dataframe is None or dataframe.empty:
        return None

    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    aliases = COLUMN_ALIASES.get(logical_name, [])

    for alias in aliases:
        normalized_alias = normalize_column_name(alias)

        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    return None


# ============================================================
# VALUE HELPERS
# ============================================================

def clean_numeric_series(series):
    """
    Convert a pandas series to numeric values.
    Invalid values become zero.
    """
    return pd.to_numeric(series, errors="coerce").fillna(0)


def safe_float(value):
    """
    Safely convert a value to a finite float.
    """
    try:
        number = float(value)

        if not math.isfinite(number):
            return 0.0

        return number

    except (TypeError, ValueError):
        return 0.0


def round_value(value):
    """
    Return a numeric value rounded to two decimal places.
    """
    return round(safe_float(value), 2)


def percentage_change(baseline, simulated):
    """
    Calculate percentage change from baseline to simulated value.
    """
    baseline = safe_float(baseline)
    simulated = safe_float(simulated)

    if baseline == 0:
        if simulated == 0:
            return 0.0

        return 100.0

    return round(
        ((simulated - baseline) / abs(baseline)) * 100,
        2,
    )


# ============================================================
# BASELINE CALCULATION
# ============================================================

def calculate_baseline(dataframe):
    """
    Calculate the baseline metrics from the selected cleaned
    DatasetVersion dataframe.
    """

    if dataframe is None:
        raise ValueError(
            "Dataset could not be loaded."
        )

    if dataframe.empty:
        raise ValueError(
            "The selected dataset contains no records."
        )

    sales_column = find_column(
        dataframe,
        "sales",
    )

    profit_column = find_column(
        dataframe,
        "profit",
    )

    cost_column = find_column(
        dataframe,
        "cost",
    )

    quantity_column = find_column(
        dataframe,
        "quantity",
    )

    customer_column = find_column(
        dataframe,
        "customers",
    )

    order_column = find_column(
        dataframe,
        "orders",
    )

    spend_column = find_column(
        dataframe,
        "spend",
    )

    return_column = find_column(
        dataframe,
        "returns",
    )

    baseline = {
        "records": int(len(dataframe)),
        "sales": 0.0,
        "profit": 0.0,
        "cost": 0.0,
        "quantity": 0.0,
        "customers": 0,
        "orders": 0,
        "marketing_spend": 0.0,
        "returns": 0.0,
    }

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    if sales_column:
        baseline["sales"] = round_value(
            clean_numeric_series(
                dataframe[sales_column]
            ).sum()
        )

    # --------------------------------------------------------
    # PROFIT
    # --------------------------------------------------------

    if profit_column:
        baseline["profit"] = round_value(
            clean_numeric_series(
                dataframe[profit_column]
            ).sum()
        )

    # --------------------------------------------------------
    # COST
    # --------------------------------------------------------

    if cost_column:
        baseline["cost"] = round_value(
            clean_numeric_series(
                dataframe[cost_column]
            ).sum()
        )

    # --------------------------------------------------------
    # QUANTITY
    # --------------------------------------------------------

    if quantity_column:
        baseline["quantity"] = round_value(
            clean_numeric_series(
                dataframe[quantity_column]
            ).sum()
        )

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    if customer_column:
        baseline["customers"] = int(
            dataframe[customer_column]
            .dropna()
            .nunique()
        )

    # --------------------------------------------------------
    # ORDERS
    # --------------------------------------------------------

    if order_column:
        baseline["orders"] = int(
            dataframe[order_column]
            .dropna()
            .nunique()
        )

    # --------------------------------------------------------
    # MARKETING SPEND
    # --------------------------------------------------------

    if spend_column:
        baseline["marketing_spend"] = round_value(
            clean_numeric_series(
                dataframe[spend_column]
            ).sum()
        )

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    if return_column:
        baseline["returns"] = round_value(
            clean_numeric_series(
                dataframe[return_column]
            ).sum()
        )

    # --------------------------------------------------------
    # FALLBACK ORDER COUNT
    # --------------------------------------------------------

    if baseline["orders"] == 0:
        baseline["orders"] = int(
            len(dataframe)
        )

    # --------------------------------------------------------
    # AVERAGE ORDER VALUE
    # --------------------------------------------------------

    baseline["average_order_value"] = (
        round_value(
            baseline["sales"]
            / baseline["orders"]
        )
        if baseline["orders"] > 0
        else 0.0
    )

    # --------------------------------------------------------
    # PROFIT MARGIN
    # --------------------------------------------------------

    baseline["profit_margin"] = (
        round_value(
            (
                baseline["profit"]
                / baseline["sales"]
            )
            * 100
        )
        if baseline["sales"] != 0
        else 0.0
    )

    # --------------------------------------------------------
    # RETURN RATE
    # --------------------------------------------------------

    baseline["return_rate"] = (
        round_value(
            (
                baseline["returns"]
                / baseline["sales"]
            )
            * 100
        )
        if baseline["sales"] != 0
        else 0.0
    )

    return baseline


# ============================================================
# ASSUMPTION NORMALIZATION
# ============================================================

def normalize_assumptions(assumptions):
    """
    Normalize the percentage assumptions accepted by the
    simulation engine.
    """

    if not isinstance(assumptions, dict):
        assumptions = {}

    supported_fields = [
        "sales_change",
        "profit_change",
        "cost_change",
        "quantity_change",
        "customer_change",
        "order_change",
        "marketing_spend_change",
        "returns_change",
    ]

    normalized = {}

    for field in supported_fields:
        normalized[field] = safe_float(
            assumptions.get(field, 0)
        )

    return normalized


# ============================================================
# APPLY SIMULATION
# ============================================================

def apply_simulation(
    baseline,
    assumptions,
):
    """
    Apply percentage-based assumptions to the baseline.
    """

    assumptions = normalize_assumptions(
        assumptions
    )

    simulated = dict(
        baseline
    )

    change_mapping = {
        "sales": "sales_change",
        "profit": "profit_change",
        "cost": "cost_change",
        "quantity": "quantity_change",
        "customers": "customer_change",
        "orders": "order_change",
        "marketing_spend": "marketing_spend_change",
        "returns": "returns_change",
    }

    for metric, assumption_key in change_mapping.items():

        baseline_value = safe_float(
            baseline.get(metric, 0)
        )

        change_percentage = assumptions.get(
            assumption_key,
            0,
        )

        simulated[metric] = round_value(
            baseline_value
            * (
                1
                + (
                    change_percentage
                    / 100
                )
            )
        )

        # Customers and orders cannot be negative
        # and are represented as whole numbers.
        if metric in [
            "customers",
            "orders",
        ]:
            simulated[metric] = max(
                0,
                int(
                    round(
                        simulated[metric]
                    )
                ),
            )

    # --------------------------------------------------------
    # RECALCULATE DERIVED METRICS
    # --------------------------------------------------------

    simulated["average_order_value"] = (
        round_value(
            simulated["sales"]
            / simulated["orders"]
        )
        if simulated["orders"] > 0
        else 0.0
    )

    simulated["profit_margin"] = (
        round_value(
            (
                simulated["profit"]
                / simulated["sales"]
            )
            * 100
        )
        if simulated["sales"] != 0
        else 0.0
    )

    simulated["return_rate"] = (
        round_value(
            (
                simulated["returns"]
                / simulated["sales"]
            )
            * 100
        )
        if simulated["sales"] != 0
        else 0.0
    )

    return simulated


# ============================================================
# RESULT SUMMARY
# ============================================================

def calculate_result_summary(
    baseline,
    simulated,
):
    """
    Create a metric-by-metric comparison between baseline
    and simulated values.
    """

    metrics = [
        "records",
        "sales",
        "profit",
        "cost",
        "quantity",
        "customers",
        "orders",
        "marketing_spend",
        "returns",
        "average_order_value",
        "profit_margin",
        "return_rate",
    ]

    changes = {}

    for metric in metrics:

        baseline_value = safe_float(
            baseline.get(metric, 0)
        )

        simulated_value = safe_float(
            simulated.get(metric, 0)
        )

        changes[metric] = {
            "baseline": round_value(
                baseline_value
            ),
            "simulated": round_value(
                simulated_value
            ),
            "absolute_change": round_value(
                simulated_value
                - baseline_value
            ),
            "percentage_change": percentage_change(
                baseline_value,
                simulated_value,
            ),
        }

    return changes


# ============================================================
# MAIN SIMULATION FUNCTION
# ============================================================

def run_what_if_simulation(
    dataframe,
    assumptions=None,
):
    """
    Complete What-If simulation pipeline.

    Returns:

    {
        "baseline": {...},
        "simulated": {...},
        "summary": {...},
        "assumptions": {...}
    }
    """

    baseline = calculate_baseline(
        dataframe
    )

    normalized_assumptions = (
        normalize_assumptions(
            assumptions or {}
        )
    )

    simulated = apply_simulation(
        baseline,
        normalized_assumptions,
    )

    summary = calculate_result_summary(
        baseline,
        simulated,
    )

    return {
        "baseline": baseline,
        "simulated": simulated,
        "summary": summary,
        "assumptions": normalized_assumptions,
    }
