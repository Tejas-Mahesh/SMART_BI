
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
    return (
        str(column_name)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def find_column(dataframe, logical_name):
    if dataframe is None:
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

def safe_float(value):
    try:
        number = float(value)

        if not math.isfinite(number):
            return 0.0

        return number

    except (TypeError, ValueError):
        return 0.0


def round_value(value):
    return round(safe_float(value), 2)


def clean_numeric_series(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0)


def percentage_change(baseline, projected):
    baseline = safe_float(baseline)
    projected = safe_float(projected)

    if baseline == 0:
        if projected == 0:
            return 0.0

        return 100.0

    return round(
        ((projected - baseline) / abs(baseline)) * 100,
        2,
    )


# ============================================================
# BASELINE CALCULATION
# ============================================================

def calculate_baseline(dataframe):
    """
    Calculates the current business position from the
    selected cleaned DatasetVersion.
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

    # If no order identifier exists, use records as orders.
    if baseline["orders"] == 0:
        baseline["orders"] = int(
            len(dataframe)
        )

    # --------------------------------------------------------
    # DERIVED METRICS
    # --------------------------------------------------------

    baseline["average_order_value"] = (
        round_value(
            baseline["sales"]
            / baseline["orders"]
        )
        if baseline["orders"] > 0
        else 0.0
    )

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
# SCENARIO ASSUMPTIONS
# ============================================================

def normalize_assumptions(assumptions):
    """
    Normalizes user-provided scenario assumptions.

    Values represent percentage changes.
    Example:
        sales_growth = 10
    means sales increase by 10%.
    """

    if not isinstance(
        assumptions,
        dict,
    ):
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
            assumptions.get(
                field,
                0,
            )
        )

    return normalized


# ============================================================
# SCENARIO PROJECTION
# ============================================================

def apply_scenario(
    baseline,
    assumptions,
):
    """
    Applies scenario assumptions to the baseline.
    """

    assumptions = normalize_assumptions(
        assumptions
    )

    projected = dict(
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
            baseline.get(
                metric,
                0,
            )
        )

        change_percentage = safe_float(
            assumptions.get(
                assumption_key,
                0,
            )
        )

        projected_value = (
            baseline_value
            * (
                1
                + (
                    change_percentage
                    / 100
                )
            )
        )

        projected[metric] = round_value(
            projected_value
        )

        # Counts cannot become negative or fractional.
        if metric in [
            "customers",
            "orders",
        ]:
            projected[metric] = max(
                0,
                int(
                    round(
                        projected[metric]
                    )
                ),
            )

    # --------------------------------------------------------
    # DERIVED METRICS
    # --------------------------------------------------------

    projected["average_order_value"] = (
        round_value(
            projected["sales"]
            / projected["orders"]
        )
        if projected["orders"] > 0
        else 0.0
    )

    projected["profit_margin"] = (
        round_value(
            (
                projected["profit"]
                / projected["sales"]
            )
            * 100
        )
        if projected["sales"] != 0
        else 0.0
    )

    projected["return_rate"] = (
        round_value(
            (
                projected["returns"]
                / projected["sales"]
            )
            * 100
        )
        if projected["sales"] != 0
        else 0.0
    )

    return projected


# ============================================================
# SCENARIO COMPARISON
# ============================================================

def calculate_comparison(
    baseline,
    projected,
):
    """
    Compares baseline and projected results.
    """

    metrics = [
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

    comparison = {}

    for metric in metrics:

        baseline_value = safe_float(
            baseline.get(
                metric,
                0,
            )
        )

        projected_value = safe_float(
            projected.get(
                metric,
                0,
            )
        )

        absolute_change = (
            projected_value
            - baseline_value
        )

        comparison[metric] = {
            "baseline": round_value(
                baseline_value
            ),
            "projected": round_value(
                projected_value
            ),
            "absolute_change": round_value(
                absolute_change
            ),
            "percentage_change": percentage_change(
                baseline_value,
                projected_value,
            ),
        }

    return comparison


# ============================================================
# SCENARIO SUMMARY
# ============================================================

def build_scenario_summary(
    comparison,
):
    """
    Produces a concise summary that can be stored with
    the ScenarioPlanning record.
    """

    sales_change = comparison.get(
        "sales",
        {},
    )

    profit_change = comparison.get(
        "profit",
        {},
    )

    cost_change = comparison.get(
        "cost",
        {},
    )

    return {
        "sales_change": sales_change.get(
            "percentage_change",
            0,
        ),
        "profit_change": profit_change.get(
            "percentage_change",
            0,
        ),
        "cost_change": cost_change.get(
            "percentage_change",
            0,
        ),
        "sales_absolute_change": sales_change.get(
            "absolute_change",
            0,
        ),
        "profit_absolute_change": profit_change.get(
            "absolute_change",
            0,
        ),
        "cost_absolute_change": cost_change.get(
            "absolute_change",
            0,
        ),
    }


# ============================================================
# MAIN SCENARIO ENGINE
# ============================================================

def run_scenario(
    dataframe,
    assumptions=None,
):
    """
    Main public entry point for Scenario Planning.

    Returns:
        {
            "baseline": {...},
            "projected": {...},
            "comparison": {...},
            "summary": {...},
            "assumptions": {...},
        }
    """

    baseline = calculate_baseline(
        dataframe
    )

    normalized_assumptions = normalize_assumptions(
        assumptions or {}
    )

    projected = apply_scenario(
        baseline,
        normalized_assumptions,
    )

    comparison = calculate_comparison(
        baseline,
        projected,
    )

    summary = build_scenario_summary(
        comparison
    )

    return {
        "baseline": baseline,
        "projected": projected,
        "comparison": comparison,
        "summary": summary,
        "assumptions": normalized_assumptions,
    }
