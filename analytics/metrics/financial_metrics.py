
"""
Financial Intelligence Metrics
===============================

This module contains reusable financial analytics functions.

Architecture rules:
- Analytics consume the dataframe supplied by the current DatasetVersion.
- No database/storage logic belongs here.
- Missing columns produce unavailable metrics instead of fabricated zeroes.
- Common financial column aliases are supported.
- Functions are designed to work with the Financial Intelligence view.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# COLUMN DEFINITIONS
# ---------------------------------------------------------------------------

CORE_REQUIRED_COLUMNS = [
    "Date",
]


OPTIONAL_COLUMNS = [
    "Transaction_ID",
    "Order_ID",
    "Invoice_ID",
    "Customer_ID",

    "Revenue",
    "Sales",
    "Sales_Amount",
    "Revenue_Amount",

    "Cost",
    "Total_Cost",
    "Cost_Amount",

    "Profit",
    "Profit_Amount",
    "Gross_Profit",
    "Net_Profit",

    "Expenses",
    "Expense",
    "Operating_Expenses",

    "Tax",
    "Tax_Amount",

    "Cash_Inflow",
    "Cash_In",
    "Cash_Income",

    "Cash_Outflow",
    "Cash_Out",
    "Cash_Expense",

    "Payment_Amount",
    "Invoice_Amount",
    "Amount",

    "Category",
    "Expense_Category",
    "Account",

    "Region",
    "City",
    "State",
    "Country",

    "Payment_Status",
    "Transaction_Type",
]


# ---------------------------------------------------------------------------
# ALIASES
# ---------------------------------------------------------------------------

COLUMN_ALIASES = {
    "Date": [
        "Date",
        "Transaction_Date",
        "Financial_Date",
        "Invoice_Date",
        "Payment_Date",
        "Order_Date",
    ],

    "Transaction_ID": [
        "Transaction_ID",
        "Transaction_Id",
        "Transaction",
        "Transaction_Number",
    ],

    "Order_ID": [
        "Order_ID",
        "Order_Id",
        "Order",
        "Order_Number",
    ],

    "Invoice_ID": [
        "Invoice_ID",
        "Invoice_Id",
        "Invoice",
        "Invoice_Number",
    ],

    "Customer_ID": [
        "Customer_ID",
        "Customer_Id",
        "Customer",
        "Customer_Number",
    ],

    "Revenue": [
        "Revenue",
        "Sales",
        "Sales_Amount",
        "Revenue_Amount",
        "Total_Revenue",
        "Total_Sales",
        "Income",
    ],

    "Cost": [
        "Cost",
        "Total_Cost",
        "Cost_Amount",
        "Total_Cost_Amount",
        "COGS",
        "Cost_of_Goods_Sold",
    ],

    "Profit": [
        "Profit",
        "Profit_Amount",
        "Gross_Profit",
        "Net_Profit",
        "Total_Profit",
    ],

    "Expenses": [
        "Expenses",
        "Expense",
        "Operating_Expenses",
        "Operating_Expense",
        "Total_Expenses",
        "Expense_Amount",
    ],

    "Tax": [
        "Tax",
        "Tax_Amount",
        "Taxes",
        "Tax_Paid",
    ],

    "Cash_Inflow": [
        "Cash_Inflow",
        "Cash_In",
        "Cash_Income",
        "Cash_Received",
        "Cash_Receipts",
        "Cash_Received_Amount",
    ],

    "Cash_Outflow": [
        "Cash_Outflow",
        "Cash_Out",
        "Cash_Expense",
        "Cash_Paid",
        "Cash_Payments",
        "Cash_Paid_Amount",
    ],

    "Payment_Amount": [
        "Payment_Amount",
        "Payment",
        "Paid_Amount",
        "Amount_Paid",
    ],

    "Invoice_Amount": [
        "Invoice_Amount",
        "Invoice_Value",
        "Bill_Amount",
        "Billed_Amount",
        "Amount",
    ],

    "Category": [
        "Category",
        "Expense_Category",
        "Financial_Category",
        "Account_Category",
    ],

    "Account": [
        "Account",
        "Account_Name",
        "Ledger_Account",
        "Account_Type",
    ],

    "Region": [
        "Region",
        "Area",
        "Territory",
        "Sales_Region",
    ],

    "City": [
        "City",
        "Town",
    ],

    "State": [
        "State",
        "Province",
    ],

    "Country": [
        "Country",
        "Nation",
    ],

    "Payment_Status": [
        "Payment_Status",
        "PaymentState",
        "Payment_State",
        "Status",
    ],

    "Transaction_Type": [
        "Transaction_Type",
        "TransactionType",
        "Type",
    ],
}


# ---------------------------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------------------------

def normalize_column_name(column: Any) -> str:
    """
    Normalize a dataframe column name so aliases can be matched reliably.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def resolve_columns(
    dataframe: pd.DataFrame,
    aliases: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Optional[str]]:
    """
    Resolve canonical financial column names to actual dataframe columns.
    """

    if dataframe is None:
        return {}

    aliases = aliases or COLUMN_ALIASES

    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    resolved = {}

    for canonical_name, possible_names in aliases.items():

        actual_column = None

        for possible_name in possible_names:

            normalized_name = normalize_column_name(
                possible_name
            )

            if normalized_name in normalized_columns:
                actual_column = normalized_columns[
                    normalized_name
                ]
                break

        resolved[canonical_name] = actual_column

    return resolved


def prepare_financial_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare a financial dataframe without changing the source dataframe.

    The resolved-column mapping is stored in dataframe.attrs so downstream
    functions can reuse the mapping without renaming the user's columns.
    """

    if dataframe is None:
        return pd.DataFrame()

    prepared = dataframe.copy()

    resolved = resolve_columns(prepared)

    prepared.attrs["_resolved_columns"] = resolved

    return prepared


def get_resolved_columns(
    dataframe: pd.DataFrame,
) -> Dict[str, Optional[str]]:
    """
    Return cached column mappings or resolve them when necessary.
    """

    if dataframe is None:
        return {}

    resolved = dataframe.attrs.get(
        "_resolved_columns"
    )

    if resolved:
        return resolved

    return resolve_columns(dataframe)


def get_column(
    dataframe: pd.DataFrame,
    canonical_name: str,
) -> Optional[str]:
    """
    Return the actual dataframe column for a canonical name.
    """

    resolved = get_resolved_columns(dataframe)

    return resolved.get(canonical_name)


def get_numeric_series(
    dataframe: pd.DataFrame,
    column: Optional[str],
) -> Optional[pd.Series]:
    """
    Return a numeric series for a dataframe column.

    Invalid numeric values are converted to NaN.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not column
        or column not in dataframe.columns
    ):
        return None

    return pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )


def safe_sum(
    dataframe: pd.DataFrame,
    column: Optional[str],
) -> Optional[float]:
    """
    Safely calculate a numeric column total.

    Returns None when the required column/data is unavailable.
    """

    series = get_numeric_series(
        dataframe,
        column,
    )

    if series is None:
        return None

    if series.notna().sum() == 0:
        return None

    return float(series.sum(skipna=True))


def safe_mean(
    dataframe: pd.DataFrame,
    column: Optional[str],
) -> Optional[float]:
    """
    Safely calculate a numeric column average.
    """

    series = get_numeric_series(
        dataframe,
        column,
    )

    if series is None:
        return None

    if series.notna().sum() == 0:
        return None

    return float(series.mean(skipna=True))


def round_value(
    value: Any,
    digits: int = 2,
) -> Optional[float]:
    """
    Safely round a numeric value.
    """

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def clean_text_series(
    series: pd.Series,
) -> pd.Series:
    """
    Normalize text values for grouping.
    """

    cleaned = (
        series
        .astype(str)
        .str.strip()
    )

    cleaned = cleaned.replace(
        {
            "": "Unknown",
            "nan": "Unknown",
            "None": "Unknown",
            "NaN": "Unknown",
        }
    )

    return cleaned


# ---------------------------------------------------------------------------
# COLUMN ACCESSORS
# ---------------------------------------------------------------------------

def get_date_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Date",
    )


def get_revenue_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Revenue",
    )


def get_cost_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Cost",
    )


def get_profit_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Profit",
    )


def get_expense_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Expenses",
    )


def get_tax_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Tax",
    )


def get_cash_inflow_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Cash_Inflow",
    )


def get_cash_outflow_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Cash_Outflow",
    )


def get_category_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Category",
    )


def get_region_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Region",
    )


# ---------------------------------------------------------------------------
# CORE FINANCIAL METRICS
# ---------------------------------------------------------------------------

def calculate_financial_metrics(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Calculate the main Financial Intelligence KPIs.

    Unsupported metrics return None rather than fabricated zeroes.
    """

    metrics = {
        "total_revenue": None,
        "total_cost": None,
        "gross_profit": None,
        "net_profit": None,
        "profit_margin": None,
        "total_expenses": None,
        "total_tax": None,
        "cash_inflow": None,
        "cash_outflow": None,
        "net_cash_flow": None,
        "average_transaction_value": None,
        "total_transactions": None,
        "average_transaction_count": None,
        "revenue_growth": None,
        "profit_growth": None,
        "top_category": None,
        "top_category_value": None,
        "top_region": None,
        "top_region_revenue": None,
    }

    if dataframe is None or dataframe.empty:
        return metrics

    revenue_column = get_revenue_column(dataframe)
    cost_column = get_cost_column(dataframe)
    profit_column = get_profit_column(dataframe)
    expense_column = get_expense_column(dataframe)
    tax_column = get_tax_column(dataframe)
    cash_inflow_column = get_cash_inflow_column(dataframe)
    cash_outflow_column = get_cash_outflow_column(dataframe)

    # ------------------------------------------------------------------
    # Revenue
    # ------------------------------------------------------------------

    total_revenue = safe_sum(
        dataframe,
        revenue_column,
    )

    metrics["total_revenue"] = round_value(
        total_revenue
    )

    # ------------------------------------------------------------------
    # Cost
    # ------------------------------------------------------------------

    total_cost = safe_sum(
        dataframe,
        cost_column,
    )

    metrics["total_cost"] = round_value(
        total_cost
    )

    # ------------------------------------------------------------------
    # Explicit profit
    # ------------------------------------------------------------------

    explicit_profit = safe_sum(
        dataframe,
        profit_column,
    )

    # Gross/profit fallback:
    # If explicit profit is unavailable but revenue and cost are available,
    # derive profit from revenue - cost.
    calculated_profit = None

    if (
        total_revenue is not None
        and total_cost is not None
    ):
        calculated_profit = (
            total_revenue - total_cost
        )

    profit_value = (
        explicit_profit
        if explicit_profit is not None
        else calculated_profit
    )

    metrics["gross_profit"] = round_value(
        profit_value
    )

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    total_expenses = safe_sum(
        dataframe,
        expense_column,
    )

    metrics["total_expenses"] = round_value(
        total_expenses
    )

    # ------------------------------------------------------------------
    # Net profit
    # ------------------------------------------------------------------

    net_profit = None

    if explicit_profit is not None:
        net_profit = explicit_profit

        if total_expenses is not None:
            net_profit -= total_expenses

        if (
            safe_sum(
                dataframe,
                tax_column,
            )
            is not None
        ):
            net_profit -= safe_sum(
                dataframe,
                tax_column,
            )

    elif calculated_profit is not None:
        net_profit = calculated_profit

        if total_expenses is not None:
            net_profit -= total_expenses

        tax_value = safe_sum(
            dataframe,
            tax_column,
        )

        if tax_value is not None:
            net_profit -= tax_value

    metrics["net_profit"] = round_value(
        net_profit
    )

    # ------------------------------------------------------------------
    # Tax
    # ------------------------------------------------------------------

    total_tax = safe_sum(
        dataframe,
        tax_column,
    )

    metrics["total_tax"] = round_value(
        total_tax
    )

    # ------------------------------------------------------------------
    # Profit margin
    # ------------------------------------------------------------------

    if (
        net_profit is not None
        and total_revenue is not None
        and total_revenue != 0
    ):
        metrics["profit_margin"] = round_value(
            (net_profit / total_revenue) * 100
        )

    # ------------------------------------------------------------------
    # Cash flow
    # ------------------------------------------------------------------

    cash_inflow = safe_sum(
        dataframe,
        cash_inflow_column,
    )

    cash_outflow = safe_sum(
        dataframe,
        cash_outflow_column,
    )

    metrics["cash_inflow"] = round_value(
        cash_inflow
    )

    metrics["cash_outflow"] = round_value(
        cash_outflow
    )

    if (
        cash_inflow is not None
        and cash_outflow is not None
    ):
        metrics["net_cash_flow"] = round_value(
            cash_inflow - cash_outflow
        )

    # ------------------------------------------------------------------
    # Transaction count
    # ------------------------------------------------------------------

    transaction_column = (
        get_column(
            dataframe,
            "Transaction_ID",
        )
        or get_column(
            dataframe,
            "Order_ID",
        )
        or get_column(
            dataframe,
            "Invoice_ID",
        )
    )

    if transaction_column:
        transaction_series = (
            dataframe[transaction_column]
            .dropna()
        )

        if not transaction_series.empty:
            metrics["total_transactions"] = int(
                transaction_series.nunique()
            )
    else:
        # If no transaction identifier exists, rows can still represent
        # financial transactions.
        if len(dataframe.index) > 0:
            metrics["total_transactions"] = int(
                len(dataframe.index)
            )

    # ------------------------------------------------------------------
    # Average transaction value
    # ------------------------------------------------------------------

    if (
        total_revenue is not None
        and metrics["total_transactions"]
        and metrics["total_transactions"] > 0
    ):
        metrics["average_transaction_value"] = round_value(
            total_revenue
            / metrics["total_transactions"]
        )

    # ------------------------------------------------------------------
    # Category performance
    # ------------------------------------------------------------------

    category_data = financial_by_category(
        dataframe
    )

    if category_data:
        first_category = category_data[0]

        metrics["top_category"] = (
            first_category.get("category")
        )

        metrics["top_category_value"] = round_value(
            first_category.get("revenue")
        )

    # ------------------------------------------------------------------
    # Regional performance
    # ------------------------------------------------------------------

    regional_data = financial_by_region(
        dataframe
    )

    if regional_data:
        first_region = regional_data[0]

        metrics["top_region"] = (
            first_region.get("region")
        )

        metrics["top_region_revenue"] = round_value(
            first_region.get("revenue")
        )

    return metrics


# ---------------------------------------------------------------------------
# REVENUE TREND
# ---------------------------------------------------------------------------

def financial_revenue_trend(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Return revenue and profit by date.
    """

    if dataframe is None or dataframe.empty:
        return []

    date_column = get_date_column(dataframe)

    revenue_column = get_revenue_column(dataframe)
    profit_column = get_profit_column(dataframe)
    cost_column = get_cost_column(dataframe)

    if not date_column:
        return []

    if not (
        revenue_column
        or profit_column
        or cost_column
    ):
        return []

    working = dataframe.copy()

    working["_financial_date"] = pd.to_datetime(
        working[date_column],
        errors="coerce",
    )

    working = working.dropna(
        subset=["_financial_date"]
    )

    if working.empty:
        return []

    grouping = (
        working
        .groupby(
            working["_financial_date"].dt.date
        )
    )

    result = []

    for date_value, group in grouping:

        item = {
            "date": str(date_value),
            "revenue": None,
            "cost": None,
            "profit": None,
        }

        if revenue_column:
            value = safe_sum(
                group,
                revenue_column,
            )
            item["revenue"] = round_value(value)

        if cost_column:
            value = safe_sum(
                group,
                cost_column,
            )
            item["cost"] = round_value(value)

        if profit_column:
            value = safe_sum(
                group,
                profit_column,
            )
            item["profit"] = round_value(value)

        elif (
            item["revenue"] is not None
            and item["cost"] is not None
        ):
            item["profit"] = round_value(
                item["revenue"]
                - item["cost"]
            )

        result.append(item)

    return result


# ---------------------------------------------------------------------------
# REVENUE VS COST
# ---------------------------------------------------------------------------

def revenue_vs_cost(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Compare total revenue and cost.
    """

    if dataframe is None or dataframe.empty:
        return []

    revenue_column = get_revenue_column(dataframe)
    cost_column = get_cost_column(dataframe)

    if not (
        revenue_column
        and cost_column
    ):
        return []

    revenue = safe_sum(
        dataframe,
        revenue_column,
    )

    cost = safe_sum(
        dataframe,
        cost_column,
    )

    if (
        revenue is None
        and cost is None
    ):
        return []

    return [
        {
            "metric": "Revenue",
            "value": round_value(revenue),
        },
        {
            "metric": "Cost",
            "value": round_value(cost),
        },
    ]


# ---------------------------------------------------------------------------
# PROFIT BY CATEGORY
# ---------------------------------------------------------------------------

def profit_by_category(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Return category-level revenue, cost and profit.
    """

    if dataframe is None or dataframe.empty:
        return []

    category_column = get_category_column(
        dataframe
    )

    if not category_column:
        return []

    revenue_column = get_revenue_column(
        dataframe
    )

    cost_column = get_cost_column(
        dataframe
    )

    profit_column = get_profit_column(
        dataframe
    )

    if not (
        revenue_column
        or cost_column
        or profit_column
    ):
        return []

    working = dataframe.copy()

    working["_category"] = clean_text_series(
        working[category_column]
    )

    grouped = (
        working
        .groupby("_category", dropna=False)
    )

    result = []

    for category, group in grouped:

        revenue = safe_sum(
            group,
            revenue_column,
        )

        cost = safe_sum(
            group,
            cost_column,
        )

        profit = safe_sum(
            group,
            profit_column,
        )

        if (
            profit is None
            and revenue is not None
            and cost is not None
        ):
            profit = revenue - cost

        result.append(
            {
                "category": str(category),
                "revenue": round_value(revenue),
                "cost": round_value(cost),
                "profit": round_value(profit),
            }
        )

    result.sort(
        key=lambda item: (
            item["profit"]
            if item["profit"] is not None
            else (
                item["revenue"]
                if item["revenue"] is not None
                else float("-inf")
            )
        ),
        reverse=True,
    )

    return result


# ---------------------------------------------------------------------------
# FINANCIAL BY CATEGORY
# ---------------------------------------------------------------------------

def financial_by_category(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Return category-level financial performance.

    This is intentionally similar to profit_by_category but focuses on
    revenue as the primary ranking metric.
    """

    data = profit_by_category(
        dataframe
    )

    data.sort(
        key=lambda item: (
            item["revenue"]
            if item["revenue"] is not None
            else float("-inf")
        ),
        reverse=True,
    )

    return data


# ---------------------------------------------------------------------------
# EXPENSE BREAKDOWN
# ---------------------------------------------------------------------------

def expense_breakdown(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Return expenses grouped by category.
    """

    if dataframe is None or dataframe.empty:
        return []

    expense_column = get_expense_column(
        dataframe
    )

    category_column = get_category_column(
        dataframe
    )

    if not (
        expense_column
        and category_column
    ):
        return []

    working = dataframe.copy()

    working["_category"] = clean_text_series(
        working[category_column]
    )

    working["_expense_value"] = pd.to_numeric(
        working[expense_column],
        errors="coerce",
    )

    working = working.dropna(
        subset=["_expense_value"]
    )

    if working.empty:
        return []

    grouped = (
        working
        .groupby("_category")["_expense_value"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    return [
        {
            "category": str(category),
            "expense": round_value(value),
        }
        for category, value in grouped.items()
    ]


# ---------------------------------------------------------------------------
# CASH FLOW TREND
# ---------------------------------------------------------------------------

def cash_flow_trend(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Return daily cash inflow, cash outflow and net cash flow.
    """

    if dataframe is None or dataframe.empty:
        return []

    date_column = get_date_column(dataframe)

    inflow_column = get_cash_inflow_column(
        dataframe
    )

    outflow_column = get_cash_outflow_column(
        dataframe
    )

    if not (
        date_column
        and inflow_column
        and outflow_column
    ):
        return []

    working = dataframe.copy()

    working["_financial_date"] = pd.to_datetime(
        working[date_column],
        errors="coerce",
    )

    working["_cash_inflow"] = pd.to_numeric(
        working[inflow_column],
        errors="coerce",
    )

    working["_cash_outflow"] = pd.to_numeric(
        working[outflow_column],
        errors="coerce",
    )

    working = working.dropna(
        subset=["_financial_date"]
    )

    if working.empty:
        return []

    grouped = (
        working
        .groupby(
            working["_financial_date"].dt.date
        )
    )

    result = []

    for date_value, group in grouped:

        inflow = (
            group["_cash_inflow"]
            .sum(min_count=1)
        )

        outflow = (
            group["_cash_outflow"]
            .sum(min_count=1)
        )

        inflow_value = (
            float(inflow)
            if pd.notna(inflow)
            else None
        )

        outflow_value = (
            float(outflow)
            if pd.notna(outflow)
            else None
        )

        net_value = None

        if (
            inflow_value is not None
            and outflow_value is not None
        ):
            net_value = (
                inflow_value
                - outflow_value
            )

        result.append(
            {
                "date": str(date_value),
                "cash_inflow": round_value(
                    inflow_value
                ),
                "cash_outflow": round_value(
                    outflow_value
                ),
                "net_cash_flow": round_value(
                    net_value
                ),
            }
        )

    return result


# ---------------------------------------------------------------------------
# REGIONAL FINANCIAL PERFORMANCE
# ---------------------------------------------------------------------------

def financial_by_region(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Return revenue, cost and profit by region.
    """

    if dataframe is None or dataframe.empty:
        return []

    region_column = get_region_column(
        dataframe
    )

    if not region_column:
        return []

    revenue_column = get_revenue_column(
        dataframe
    )

    cost_column = get_cost_column(
        dataframe
    )

    profit_column = get_profit_column(
        dataframe
    )

    if not (
        revenue_column
        or cost_column
        or profit_column
    ):
        return []

    working = dataframe.copy()

    working["_region"] = clean_text_series(
        working[region_column]
    )

    grouped = (
        working
        .groupby("_region", dropna=False)
    )

    result = []

    for region, group in grouped:

        revenue = safe_sum(
            group,
            revenue_column,
        )

        cost = safe_sum(
            group,
            cost_column,
        )

        profit = safe_sum(
            group,
            profit_column,
        )

        if (
            profit is None
            and revenue is not None
            and cost is not None
        ):
            profit = revenue - cost

        margin = None

        if (
            profit is not None
            and revenue is not None
            and revenue != 0
        ):
            margin = (
                profit / revenue
            ) * 100

        result.append(
            {
                "region": str(region),
                "revenue": round_value(revenue),
                "cost": round_value(cost),
                "profit": round_value(profit),
                "profit_margin": round_value(
                    margin
                ),
            }
        )

    result.sort(
        key=lambda item: (
            item["revenue"]
            if item["revenue"] is not None
            else float("-inf")
        ),
        reverse=True,
    )

    return result


# ---------------------------------------------------------------------------
# TRANSACTION DISTRIBUTION
# ---------------------------------------------------------------------------

def transaction_distribution(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Group transaction revenue into useful value bands.

    Bands:
        0–10K
        10K–50K
        50K–1L
        1L–5L
        5L+
    """

    if dataframe is None or dataframe.empty:
        return []

    revenue_column = get_revenue_column(
        dataframe
    )

    if not revenue_column:
        return []

    values = get_numeric_series(
        dataframe,
        revenue_column,
    )

    if values is None:
        return []

    values = values.dropna()

    if values.empty:
        return []

    bands = [
        (
            "0–10K",
            0,
            10_000,
        ),
        (
            "10K–50K",
            10_000,
            50_000,
        ),
        (
            "50K–1L",
            50_000,
            100_000,
        ),
        (
            "1L–5L",
            100_000,
            500_000,
        ),
        (
            "5L+",
            500_000,
            None,
        ),
    ]

    result = []

    for label, lower, upper in bands:

        if upper is None:
            mask = values >= lower
        else:
            mask = (
                (values >= lower)
                & (values < upper)
            )

        count = int(mask.sum())

        if count > 0:
            total_value = float(
                values[mask].sum()
            )

            result.append(
                {
                    "band": label,
                    "transactions": count,
                    "value": round_value(
                        total_value
                    ),
                }
            )

    return result


# ---------------------------------------------------------------------------
# REVENUE GROWTH
# ---------------------------------------------------------------------------

def calculate_financial_growth(
    dataframe: pd.DataFrame,
    current_from_date=None,
    current_to_date=None,
) -> Optional[float]:
    """
    Compare revenue in the selected period with the immediately preceding
    period of the same duration.

    Returns None when a meaningful comparison cannot be calculated.
    """

    if (
        dataframe is None
        or dataframe.empty
        or current_from_date is None
        or current_to_date is None
    ):
        return None

    date_column = get_date_column(
        dataframe
    )

    revenue_column = get_revenue_column(
        dataframe
    )

    if not (
        date_column
        and revenue_column
    ):
        return None

    dates = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
    )

    revenue = pd.to_numeric(
        dataframe[revenue_column],
        errors="coerce",
    )

    working = pd.DataFrame(
        {
            "_date": dates,
            "_revenue": revenue,
        }
    ).dropna(
        subset=[
            "_date",
            "_revenue",
        ]
    )

    if working.empty:
        return None

    current_start = pd.to_datetime(
        current_from_date,
        errors="coerce",
    )

    current_end = pd.to_datetime(
        current_to_date,
        errors="coerce",
    )

    if (
        pd.isna(current_start)
        or pd.isna(current_end)
    ):
        return None

    if current_end < current_start:
        return None

    period_length = (
        current_end - current_start
    ) + pd.Timedelta(days=1)

    previous_end = (
        current_start
        - pd.Timedelta(days=1)
    )

    previous_start = (
        previous_end
        - period_length
        + pd.Timedelta(days=1)
    )

    current_data = working[
        (working["_date"] >= current_start)
        & (working["_date"] <= current_end)
    ]

    previous_data = working[
        (working["_date"] >= previous_start)
        & (working["_date"] <= previous_end)
    ]

    if current_data.empty:
        return None

    if previous_data.empty:
        return None

    current_revenue = float(
        current_data["_revenue"].sum()
    )

    previous_revenue = float(
        previous_data["_revenue"].sum()
    )

    if previous_revenue == 0:
        return None

    growth = (
        (
            current_revenue
            - previous_revenue
        )
        / previous_revenue
    ) * 100

    return round_value(
        growth
    )


# ---------------------------------------------------------------------------
# PROFIT GROWTH
# ---------------------------------------------------------------------------

def calculate_profit_growth(
    dataframe: pd.DataFrame,
    current_from_date=None,
    current_to_date=None,
) -> Optional[float]:
    """
    Compare profit in the selected period with the immediately preceding
    period of equal duration.
    """

    if (
        dataframe is None
        or dataframe.empty
        or current_from_date is None
        or current_to_date is None
    ):
        return None

    date_column = get_date_column(
        dataframe
    )

    profit_column = get_profit_column(
        dataframe
    )

    revenue_column = get_revenue_column(
        dataframe
    )

    cost_column = get_cost_column(
        dataframe
    )

    if not date_column:
        return None

    if not (
        profit_column
        or (
            revenue_column
            and cost_column
        )
    ):
        return None

    dates = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
    )

    working = dataframe.copy()

    working["_financial_date"] = dates

    working = working.dropna(
        subset=["_financial_date"]
    )

    if working.empty:
        return None

    current_start = pd.to_datetime(
        current_from_date,
        errors="coerce",
    )

    current_end = pd.to_datetime(
        current_to_date,
        errors="coerce",
    )

    if (
        pd.isna(current_start)
        or pd.isna(current_end)
        or current_end < current_start
    ):
        return None

    period_length = (
        current_end - current_start
    ) + pd.Timedelta(days=1)

    previous_end = (
        current_start
        - pd.Timedelta(days=1)
    )

    previous_start = (
        previous_end
        - period_length
        + pd.Timedelta(days=1)
    )

    current_data = working[
        (working["_financial_date"] >= current_start)
        & (working["_financial_date"] <= current_end)
    ]

    previous_data = working[
        (working["_financial_date"] >= previous_start)
        & (working["_financial_date"] <= previous_end)
    ]

    if (
        current_data.empty
        or previous_data.empty
    ):
        return None

    def profit_for_period(
        period_dataframe,
    ):
        if profit_column:
            value = safe_sum(
                period_dataframe,
                profit_column,
            )

            if value is not None:
                return value

        revenue = safe_sum(
            period_dataframe,
            revenue_column,
        )

        cost = safe_sum(
            period_dataframe,
            cost_column,
        )

        if (
            revenue is not None
            and cost is not None
        ):
            return revenue - cost

        return None

    current_profit = profit_for_period(
        current_data
    )

    previous_profit = profit_for_period(
        previous_data
    )

    if (
        current_profit is None
        or previous_profit is None
        or previous_profit == 0
    ):
        return None

    growth = (
        (
            current_profit
            - previous_profit
        )
        / abs(previous_profit)
    ) * 100

    return round_value(
        growth
    )


# ---------------------------------------------------------------------------
# SMART FINANCIAL INSIGHTS
# ---------------------------------------------------------------------------

def generate_financial_insights(
    metrics: Dict[str, Any],
    category_data: Optional[List[Dict[str, Any]]] = None,
    regional_data: Optional[List[Dict[str, Any]]] = None,
    revenue_trend: Optional[List[Dict[str, Any]]] = None,
    expense_data: Optional[List[Dict[str, Any]]] = None,
    revenue_growth: Optional[float] = None,
    profit_growth: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Generate rule-based Financial Intelligence insights.

    The function returns factual, metric-driven observations.
    """

    insights = []

    metrics = metrics or {}
    category_data = category_data or []
    regional_data = regional_data or []
    expense_data = expense_data or []
    revenue_trend = revenue_trend or []

    # ------------------------------------------------------------------
    # Revenue growth
    # ------------------------------------------------------------------

    if revenue_growth is not None:

        if revenue_growth > 0:

            insights.append(
                {
                    "type": "positive",
                    "title": "Revenue Growth",
                    "message": (
                        f"Revenue increased by "
                        f"{revenue_growth:.2f}% "
                        f"compared with the previous "
                        f"comparable period."
                    ),
                }
            )

        elif revenue_growth < 0:

            insights.append(
                {
                    "type": "warning",
                    "title": "Revenue Decline",
                    "message": (
                        f"Revenue decreased by "
                        f"{abs(revenue_growth):.2f}% "
                        f"compared with the previous "
                        f"comparable period."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "info",
                    "title": "Revenue Stable",
                    "message": (
                        "Revenue remained unchanged "
                        "compared with the previous "
                        "comparable period."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Profit growth
    # ------------------------------------------------------------------

    if profit_growth is not None:

        if profit_growth > 0:

            insights.append(
                {
                    "type": "positive",
                    "title": "Profit Growth",
                    "message": (
                        f"Profit increased by "
                        f"{profit_growth:.2f}% "
                        f"compared with the previous "
                        f"comparable period."
                    ),
                }
            )

        elif profit_growth < 0:

            insights.append(
                {
                    "type": "warning",
                    "title": "Profit Decline",
                    "message": (
                        f"Profit decreased by "
                        f"{abs(profit_growth):.2f}% "
                        f"compared with the previous "
                        f"comparable period."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Profit margin
    # ------------------------------------------------------------------

    profit_margin = metrics.get(
        "profit_margin"
    )

    if profit_margin is not None:

        if profit_margin < 0:

            insights.append(
                {
                    "type": "warning",
                    "title": "Negative Profit Margin",
                    "message": (
                        f"The calculated net profit "
                        f"margin is {profit_margin:.2f}%."
                    ),
                }
            )

        elif profit_margin < 10:

            insights.append(
                {
                    "type": "warning",
                    "title": "Low Profit Margin",
                    "message": (
                        f"The calculated net profit "
                        f"margin is {profit_margin:.2f}%."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "positive",
                    "title": "Profit Margin",
                    "message": (
                        f"The calculated net profit "
                        f"margin is {profit_margin:.2f}%."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Cash flow
    # ------------------------------------------------------------------

    net_cash_flow = metrics.get(
        "net_cash_flow"
    )

    if net_cash_flow is not None:

        if net_cash_flow > 0:

            insights.append(
                {
                    "type": "positive",
                    "title": "Positive Cash Flow",
                    "message": (
                        f"Net cash flow is "
                        f"{net_cash_flow:,.2f}."
                    ),
                }
            )

        elif net_cash_flow < 0:

            insights.append(
                {
                    "type": "warning",
                    "title": "Negative Cash Flow",
                    "message": (
                        f"Net cash flow is "
                        f"{net_cash_flow:,.2f}."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "info",
                    "title": "Balanced Cash Flow",
                    "message": (
                        "Cash inflow and cash outflow "
                        "are equal for the selected data."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Top category
    # ------------------------------------------------------------------

    if category_data:

        top_category = category_data[0]

        category_name = top_category.get(
            "category"
        )

        category_revenue = top_category.get(
            "revenue"
        )

        if (
            category_name
            and category_revenue is not None
        ):

            insights.append(
                {
                    "type": "info",
                    "title": "Leading Financial Category",
                    "message": (
                        f"{category_name} has the highest "
                        f"revenue contribution at "
                        f"{category_revenue:,.2f}."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Top region
    # ------------------------------------------------------------------

    if regional_data:

        top_region = regional_data[0]

        region_name = top_region.get(
            "region"
        )

        region_revenue = top_region.get(
            "revenue"
        )

        if (
            region_name
            and region_revenue is not None
        ):

            insights.append(
                {
                    "type": "info",
                    "title": "Leading Region",
                    "message": (
                        f"{region_name} has the highest "
                        f"regional revenue at "
                        f"{region_revenue:,.2f}."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Expense concentration
    # ------------------------------------------------------------------

    if expense_data:

        total_expenses = sum(
            item.get("expense") or 0
            for item in expense_data
        )

        if total_expenses > 0:

            top_expense = expense_data[0]

            top_expense_value = (
                top_expense.get("expense")
                or 0
            )

            concentration = (
                top_expense_value
                / total_expenses
            ) * 100

            if concentration >= 50:

                insights.append(
                    {
                        "type": "warning",
                        "title": "Expense Concentration",
                        "message": (
                            f"{top_expense.get('category')} "
                            f"accounts for approximately "
                            f"{concentration:.2f}% of "
                            "recorded expenses."
                        ),
                    }
                )

    # ------------------------------------------------------------------
    # Revenue trend
    # ------------------------------------------------------------------

    if len(revenue_trend) >= 2:

        valid_revenue = [
            item.get("revenue")
            for item in revenue_trend
            if item.get("revenue") is not None
        ]

        if len(valid_revenue) >= 2:

            first_value = valid_revenue[0]
            last_value = valid_revenue[-1]

            if first_value != 0:

                trend_change = (
                    (
                        last_value
                        - first_value
                    )
                    / abs(first_value)
                ) * 100

                if trend_change > 0:

                    insights.append(
                        {
                            "type": "positive",
                            "title": "Revenue Trend",
                            "message": (
                                f"Revenue changed by "
                                f"{trend_change:.2f}% "
                                "from the first to the "
                                "last available date "
                                "in the selected data."
                            ),
                        }
                    )

                elif trend_change < 0:

                    insights.append(
                        {
                            "type": "warning",
                            "title": "Revenue Trend",
                            "message": (
                                f"Revenue changed by "
                                f"{trend_change:.2f}% "
                                "from the first to the "
                                "last available date "
                                "in the selected data."
                            ),
                        }
                    )

    # ------------------------------------------------------------------
    # Data availability notice
    # ------------------------------------------------------------------

    if not metrics.get("total_revenue"):

        insights.append(
            {
                "type": "info",
                "title": "Revenue Data Unavailable",
                "message": (
                    "Revenue could not be calculated "
                    "because a compatible revenue "
                    "column is unavailable or contains "
                    "no usable numeric values."
                ),
            }
        )

    return insights


# ---------------------------------------------------------------------------
# BACKWARD-COMPATIBILITY ALIASES
# ---------------------------------------------------------------------------

financial_revenue = financial_revenue_trend
financial_sales_trend = financial_revenue_trend
cashflow_trend = cash_flow_trend
profit_by_region = financial_by_region
