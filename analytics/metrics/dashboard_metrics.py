from __future__ import annotations
from datetime import date, datetime
"""
Executive Dashboard Metrics Engine
===================================

This module contains ONLY Executive Dashboard calculations.

Architecture:

    Dataset
        ↓
    DatasetVersion (Cleaned)
        ↓
    dashboard_service.py
        ↓
    cleaned pandas DataFrame
        ↓
    dashboard_metrics.py
        ↓
    KPIs / Charts / Trends / Forecasts / Risks / Insights

IMPORTANT
---------
This module does NOT:
    - load Dataset objects
    - load DatasetVersion objects
    - read uploaded files
    - select datasets
    - access Dataset.file
    - access DatasetVersion.file
    - import business_metrics.py

The dashboard service is responsible for supplying cleaned dataframes.
This module only performs dashboard-specific calculations.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


# ============================================================================
# SUPPORTED DATASET TYPES
# ============================================================================

DASHBOARD_DATASET_TYPES = [
    "Sales",
    "Customers",
    "Products",
    "Regional",
    "Marketing",
    "Financial",
    "Returns",
]


DATASET_LABELS = {
    "Sales": "Sales Intelligence",
    "Customers": "Customer Intelligence",
    "Products": "Product Intelligence",
    "Regional": "Regional Intelligence",
    "Marketing": "Marketing Intelligence",
    "Financial": "Financial Intelligence",
    "Returns": "Returns Intelligence",
}


# ============================================================================
# COLUMN ALIASES
# ============================================================================

COLUMN_ALIASES = {
    # ------------------------------------------------------------------------
    # GENERAL
    # ------------------------------------------------------------------------

    "date": [
        "date",
        "datetime",
        "timestamp",
        "transaction_date",
        "order_date",
        "sale_date",
        "sales_date",
        "purchase_date",
        "invoice_date",
        "created_at",
        "created_date",
        "month",
        "year",
    ],

    "id": [
        "id",
        "record_id",
        "transaction_id",
        "order_id",
        "invoice_id",
        "reference_id",
    ],

    # ------------------------------------------------------------------------
    # SALES
    # ------------------------------------------------------------------------

    "sales": [
        "sales",
        "sale",
        "sales_amount",
        "sale_amount",
        "sales_value",
        "sale_value",
        "revenue",
        "revenue_amount",
        "total_sales",
        "total_revenue",
        "net_sales",
        "net_revenue",
        "amount",
        "total_amount",
        "order_value",
    ],

    "profit": [
        "profit",
        "profit_amount",
        "gross_profit",
        "net_profit",
        "operating_profit",
        "profit_value",
    ],

    "cost": [
        "cost",
        "cost_amount",
        "cost_value",
        "total_cost",
        "cogs",
        "cost_of_goods_sold",
    ],

    "quantity": [
        "quantity",
        "qty",
        "units",
        "unit_quantity",
        "sold_quantity",
        "sales_quantity",
        "order_quantity",
        "units_sold",
        "returned_quantity",
        "return_quantity",
    ],

    # ------------------------------------------------------------------------
    # CUSTOMER
    # ------------------------------------------------------------------------

    "customer": [
        "customer",
        "customer_id",
        "customerid",
        "client",
        "client_id",
        "buyer",
        "buyer_id",
        "account",
        "account_id",
    ],

    "customer_name": [
        "customer_name",
        "customername",
        "client_name",
        "buyer_name",
        "account_name",
        "name",
    ],

    "churn": [
        "churn",
        "churned",
        "is_churned",
        "customer_churn",
        "churn_flag",
        "churn_status",
    ],

    # ------------------------------------------------------------------------
    # PRODUCT
    # ------------------------------------------------------------------------

    "product": [
        "product",
        "product_id",
        "productid",
        "product_name",
        "productname",
        "item",
        "item_id",
        "item_name",
        "sku",
        "sku_id",
    ],

    "category": [
        "category",
        "product_category",
        "productcategory",
        "category_name",
        "segment",
        "product_segment",
    ],

    # ------------------------------------------------------------------------
    # REGION
    # ------------------------------------------------------------------------

    "region": [
        "region",
        "region_name",
        "regional",
        "territory",
        "area",
        "zone",
    ],

    "country": [
        "country",
        "country_name",
        "nation",
    ],

    "state": [
        "state",
        "state_name",
        "province",
    ],

    "city": [
        "city",
        "city_name",
    ],

    # ------------------------------------------------------------------------
    # MARKETING
    # ------------------------------------------------------------------------

    "spend": [
        "spend",
        "marketing_spend",
        "marketing_cost",
        "campaign_spend",
        "ad_spend",
        "advertising_spend",
        "cost",
        "budget",
    ],

    "campaign": [
        "campaign",
        "campaign_name",
        "campaign_id",
        "campaignname",
    ],

    "channel": [
        "channel",
        "marketing_channel",
        "channel_name",
        "source",
        "medium",
    ],

    "clicks": [
        "clicks",
        "click",
        "total_clicks",
    ],

    "impressions": [
        "impressions",
        "impression",
        "views",
        "ad_impressions",
    ],

    "conversions": [
        "conversions",
        "conversion",
        "leads",
        "orders",
        "converted",
    ],

    # ------------------------------------------------------------------------
    # FINANCIAL
    # ------------------------------------------------------------------------

    "income": [
        "income",
        "revenue",
        "sales",
        "total_income",
        "total_revenue",
        "gross_income",
        "operating_income",
    ],

    "expense": [
        "expense",
        "expenses",
        "cost",
        "costs",
        "total_expense",
        "total_expenses",
        "operating_expense",
        "operating_expenses",
    ],

    "tax": [
        "tax",
        "taxes",
        "tax_amount",
    ],

    "investment": [
        "investment",
        "investments",
        "investment_amount",
    ],

    "cash_flow": [
        "cash_flow",
        "cashflow",
        "net_cash_flow",
        "cash",
    ],

    # ------------------------------------------------------------------------
    # RETURNS
    # ------------------------------------------------------------------------

    "return": [
        "return",
        "returns",
        "return_amount",
        "returns_amount",
        "refund",
        "refund_amount",
        "refund_value",
        "returned_value",
    ],

    "return_reason": [
        "return_reason",
        "return_reason_name",
        "reason",
        "reason_name",
        "refund_reason",
        "refund_reason_name",
    ],
}


# ============================================================================
# BASIC DATAFRAME HELPERS
# ============================================================================

def safe_dataframe(dataframe: Any) -> pd.DataFrame:
    """
    Safely convert an input object into a pandas DataFrame.

    This function does not load data from disk.
    """

    if dataframe is None:
        return pd.DataFrame()

    if isinstance(dataframe, pd.DataFrame):
        return dataframe.copy()

    try:
        return pd.DataFrame(dataframe).copy()
    except Exception:
        return pd.DataFrame()


def normalize_column_name(value: Any) -> str:
    """
    Normalize a dataframe column name for matching.
    """

    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(".", "_")
    )


def prepare_dataframe(
    dataframe: Any,
) -> pd.DataFrame:
    """
    Prepare an already-loaded dataframe for dashboard analysis.

    No file access occurs here.
    """

    df = safe_dataframe(dataframe)

    if df.empty:
        return df

    df = df.copy()

    # Normalize duplicate column names while preserving
    # readable dashboard output.
    renamed = {}

    for column in df.columns:
        renamed[column] = normalize_column_name(column)

    df = df.rename(columns=renamed)

    # Remove completely empty rows.
    df = df.dropna(
        how="all"
    ).reset_index(
        drop=True
    )

    return df


def column_lookup(
    dataframe: pd.DataFrame,
) -> Dict[str, str]:
    """
    Return normalized-name -> actual-column mapping.
    """

    lookup = {}

    if dataframe is None:
        return lookup

    for column in dataframe.columns:
        normalized = normalize_column_name(
            column
        )

        if normalized not in lookup:
            lookup[normalized] = column

    return lookup


def find_column(
    dataframe: pd.DataFrame,
    aliases: Iterable[str],
) -> Optional[str]:
    """
    Find the first dataframe column matching any alias.
    """

    if dataframe is None or dataframe.empty:
        return None

    lookup = column_lookup(
        dataframe
    )

    for alias in aliases:
        normalized = normalize_column_name(
            alias
        )

        if normalized in lookup:
            return lookup[normalized]

    return None


def find_named_column(
    dataframe: pd.DataFrame,
    name: str,
) -> Optional[str]:
    """
    Find a semantic column using COLUMN_ALIASES.
    """

    aliases = COLUMN_ALIASES.get(
        name,
        [name],
    )

    return find_column(
        dataframe,
        aliases,
    )


# ============================================================================
# NUMERIC HELPERS
# ============================================================================

def numeric_series(
    dataframe: pd.DataFrame,
    column: Optional[str],
) -> pd.Series:
    """
    Return a numeric pandas Series.

    Invalid values become NaN and are excluded from calculations.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not column
        or column not in dataframe.columns
    ):
        return pd.Series(
            dtype=float
        )

    series = dataframe[column]

    if pd.api.types.is_numeric_dtype(
        series
    ):
        return pd.to_numeric(
            series,
            errors="coerce",
        )

    # Handle common currency / percentage formatting.
    cleaned = (
        series.astype(str)
        .str.replace(
            ",",
            "",
            regex=False,
        )
        .str.replace(
            "₹",
            "",
            regex=False,
        )
        .str.replace(
            "$",
            "",
            regex=False,
        )
        .str.replace(
            "€",
            "",
            regex=False,
        )
        .str.replace(
            "£",
            "",
            regex=False,
        )
        .str.replace(
            "%",
            "",
            regex=False,
        )
        .str.strip()
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce",
    )


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Convert a value safely to float.
    """

    try:
        if value is None:
            return default

        result = float(value)

        if not np.isfinite(result):
            return default

        return result

    except Exception:
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    Convert a value safely to int.
    """

    try:
        if value is None:
            return default

        return int(
            round(
                float(value)
            )
        )

    except Exception:
        return default


def json_safe(
    value: Any,
) -> Any:
    """
    Convert common pandas/numpy values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (
            np.integer,
        ),
    ):
        return int(value)

    if isinstance(
        value,
        (
            np.floating,
        ),
    ):
        if not np.isfinite(value):
            return None

        return float(value)

    if isinstance(
        value,
        (
            np.bool_,
        ),
    ):
        return bool(value)

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
            date,
        ),
    ):
        return value.isoformat()

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key): json_safe(
                item
            )
            for key, item in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return [
            json_safe(item)
            for item in value
        ]

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    return value


# ============================================================================
# DATE HELPERS
# ============================================================================

def get_date_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    """
    Detect a usable date column.
    """

    if dataframe is None or dataframe.empty:
        return None

    # Prefer semantic aliases first.
    for alias in COLUMN_ALIASES["date"]:
        column = find_column(
            dataframe,
            [alias],
        )

        if column:
            parsed = pd.to_datetime(
                dataframe[column],
                errors="coerce",
            )

            if parsed.notna().sum() >= 2:
                return column

    # Fallback: inspect columns with date-like names.
    for column in dataframe.columns:

        normalized = normalize_column_name(
            column
        )

        if any(
            token in normalized
            for token in (
                "date",
                "time",
                "month",
                "year",
            )
        ):
            parsed = pd.to_datetime(
                dataframe[column],
                errors="coerce",
            )

            if parsed.notna().sum() >= 2:
                return column

    return None


def prepare_date_dataframe(
    dataframe: pd.DataFrame,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Return a copy with a normalized datetime column.
    """

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return df, None

    date_column = get_date_column(
        df
    )

    if not date_column:
        return df, None

    df = df.copy()

    df["_dashboard_date"] = pd.to_datetime(
        df[date_column],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "_dashboard_date"
        ]
    ).sort_values(
        "_dashboard_date"
    )

    return (
        df,
        "_dashboard_date",
    )


def get_date_bounds(
    dataframe: pd.DataFrame,
) -> Optional[Dict[str, Any]]:
    """
    Return the earliest/latest usable date.
    """

    df, date_column = prepare_date_dataframe(
        dataframe
    )

    if (
        df.empty
        or not date_column
    ):
        return None

    return {
        "from": json_safe(
            df[date_column].min()
        ),
        "to": json_safe(
            df[date_column].max()
        ),
    }


def _normalize_filter_date(
    value: Any,
) -> Optional[pd.Timestamp]:

    if value is None:
        return None

    try:
        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if pd.isna(parsed):
            return None

        return pd.Timestamp(
            parsed
        )

    except Exception:
        return None


def apply_date_range(
    dataframe: pd.DataFrame,
    from_date: Any = None,
    to_date: Any = None,
) -> pd.DataFrame:
    """
    Apply an optional date range to a dataframe.

    This is the only place in dashboard_metrics.py
    where date filtering is performed.

    dashboard_service.py supplies the complete cleaned dataframe.
    """

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return df

    if (
        from_date is None
        and to_date is None
    ):
        return df

    date_column = get_date_column(
        df
    )

    if not date_column:
        return df

    dates = pd.to_datetime(
        df[date_column],
        errors="coerce",
    )

    start = _normalize_filter_date(
        from_date
    )

    end = _normalize_filter_date(
        to_date
    )

    mask = dates.notna()

    if start is not None:
        mask &= dates >= start

    if end is not None:
        # Include the complete end date.
        if (
            end.hour == 0
            and end.minute == 0
            and end.second == 0
        ):
            end = (
                end
                + pd.Timedelta(
                    days=1
                )
                - pd.Timedelta(
                    microseconds=1
                )
            )

        mask &= dates <= end

    return df.loc[
        mask
    ].copy().reset_index(
        drop=True
    )


# ============================================================================
# KPI HELPERS
# ============================================================================

def make_kpi(
    key: str,
    label: str,
    value: Any,
    *,
    format_type: str = "number",
    description: str = "",
) -> Dict[str, Any]:
    """
    Standard dashboard KPI object.
    """

    return {
        "key": key,
        "label": label,
        "name": label,
        "value": json_safe(
            value
        ),
        "format_type": format_type,
        "description": description,
    }


def calculate_growth(
    current: Any,
    previous: Any,
) -> Optional[float]:
    """
    Calculate percentage growth.
    """

    current_value = safe_float(
        current,
        default=0,
    )

    previous_value = safe_float(
        previous,
        default=0,
    )

    if previous_value == 0:
        return None

    return (
        (
            current_value
            - previous_value
        )
        / abs(previous_value)
    ) * 100


def period_growth(
    dataframe: pd.DataFrame,
    value_column: Optional[str],
) -> Optional[float]:
    """
    Calculate period-over-period growth.

    When a usable date field exists, the dataframe is split into
    two comparable chronological periods.

    Without a date field, growth is unavailable rather than fabricated.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not value_column
    ):
        return None

    df, date_column = prepare_date_dataframe(
        dataframe
    )

    if (
        df.empty
        or not date_column
    ):
        return None

    values = numeric_series(
        df,
        value_column,
    )

    work = pd.DataFrame(
        {
            "date": df[date_column],
            "value": values,
        }
    ).dropna()

    if len(work) < 4:
        return None

    work = work.sort_values(
        "date"
    )

    midpoint = len(work) // 2

    first = work.iloc[
        :midpoint
    ]["value"].sum()

    second = work.iloc[
        midpoint:
    ]["value"].sum()

    return calculate_growth(
        second,
        first,
    )


# ============================================================================
# CHART HELPERS
# ============================================================================

def build_chart(
    chart_id: str,
    title: str,
    labels: Iterable[Any],
    values: Iterable[Any],
    *,
    chart_type: str = "bar",
    series_name: str = "Value",
    description: str = "",
) -> Dict[str, Any]:
    """
    Build a standard Chart.js-compatible chart payload.
    """

    safe_labels = [
        json_safe(label)
        for label in labels
    ]

    safe_values = [
        safe_float(value)
        for value in values
    ]

    return {
        "id": chart_id,
        "title": title,
        "type": chart_type,
        "labels": safe_labels,
        "values": safe_values,
        "series_name": series_name,
        "description": description,
        "datasets": [
            {
                "label": series_name,
                "data": safe_values,
            }
        ],
    }


def grouped_chart(
    dataframe: pd.DataFrame,
    category_column: Optional[str],
    value_column: Optional[str],
    *,
    chart_id: str,
    title: str,
    series_name: str = "Value",
    limit: int = 10,
) -> Optional[Dict[str, Any]]:
    """
    Aggregate a numeric measure by category.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not category_column
        or not value_column
    ):
        return None

    if (
        category_column not in dataframe.columns
        or value_column not in dataframe.columns
    ):
        return None

    work = dataframe[
        [
            category_column,
            value_column,
        ]
    ].copy()

    work["_dashboard_value"] = numeric_series(
        work,
        value_column,
    )

    work = work.dropna(
        subset=[
            "_dashboard_value"
        ]
    )

    if work.empty:
        return None

    grouped = (
        work.groupby(
            category_column,
            dropna=False,
        )["_dashboard_value"]
        .sum()
        .sort_values(
            ascending=False
        )
        .head(limit)
    )

    if grouped.empty:
        return None

    return build_chart(
        chart_id,
        title,
        grouped.index.tolist(),
        grouped.values.tolist(),
        chart_type="bar",
        series_name=series_name,
    )


def time_series_chart(
    dataframe: pd.DataFrame,
    value_column: Optional[str],
    *,
    chart_id: str,
    title: str,
    series_name: str = "Value",
) -> Optional[Dict[str, Any]]:
    """
    Build a monthly time-series chart.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not value_column
    ):
        return None

    df, date_column = prepare_date_dataframe(
        dataframe
    )

    if (
        df.empty
        or not date_column
    ):
        return None

    values = numeric_series(
        df,
        value_column,
    )

    work = pd.DataFrame(
        {
            "date": df[date_column],
            "value": values,
        }
    ).dropna()

    if work.empty:
        return None

    monthly = (
        work.set_index(
            "date"
        )["value"]
        .resample("ME")
        .sum()
        .dropna()
    )

    if monthly.empty:
        return None

    return build_chart(
        chart_id,
        title,
        [
            value.strftime(
                "%Y-%m"
            )
            for value in monthly.index
        ],
        monthly.values.tolist(),
        chart_type="line",
        series_name=series_name,
    )


# ============================================================================
# SALES DASHBOARD
# ============================================================================

def calculate_sales_dashboard(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return empty_dataset_result(
            "Sales"
        )

    sales_column = find_named_column(
        df,
        "sales",
    )

    profit_column = find_named_column(
        df,
        "profit",
    )

    quantity_column = find_named_column(
        df,
        "quantity",
    )

    customer_column = find_named_column(
        df,
        "customer",
    )

    product_column = find_named_column(
        df,
        "product",
    )

    category_column = find_named_column(
        df,
        "category",
    )

    region_column = find_named_column(
        df,
        "region",
    )

    sales = (
        numeric_series(
            df,
            sales_column,
        ).sum()
        if sales_column
        else None
    )

    profit = (
        numeric_series(
            df,
            profit_column,
        ).sum()
        if profit_column
        else None
    )

    quantity = (
        numeric_series(
            df,
            quantity_column,
        ).sum()
        if quantity_column
        else None
    )

    kpis = [
        make_kpi(
            "sales_records",
            "Sales Records",
            len(df),
            description="Number of records in the Sales dataset.",
        )
    ]

    if sales is not None:
        kpis.append(
            make_kpi(
                "sales_revenue",
                "Sales Revenue",
                sales,
                format_type="currency",
                description="Total sales/revenue.",
            )
        )

    if profit is not None:
        kpis.append(
            make_kpi(
                "sales_profit",
                "Sales Profit",
                profit,
                format_type="currency",
                description="Total profit.",
            )
        )

    if quantity is not None:
        kpis.append(
            make_kpi(
                "sales_units",
                "Units Sold",
                quantity,
                description="Total quantity sold.",
            )
        )

    if customer_column:
        kpis.append(
            make_kpi(
                "sales_customers",
                "Customers",
                df[
                    customer_column
                ].nunique(),
                description="Unique customers represented in the Sales dataset.",
            )
        )

    if product_column:
        kpis.append(
            make_kpi(
                "sales_products",
                "Products",
                df[
                    product_column
                ].nunique(),
                description="Unique products represented in the Sales dataset.",
            )
        )

    charts = []

    chart = time_series_chart(
        df,
        sales_column,
        chart_id="sales_trend",
        title="Sales Trend",
        series_name="Sales",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        category_column,
        sales_column,
        chart_id="sales_by_category",
        title="Sales by Category",
        series_name="Sales",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        product_column,
        sales_column,
        chart_id="sales_by_product",
        title="Sales by Product",
        series_name="Sales",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        region_column,
        sales_column,
        chart_id="sales_by_region",
        title="Sales by Region",
        series_name="Sales",
    )

    if chart:
        charts.append(chart)

    return {
        "dataset_type": "Sales",
        "label": DATASET_LABELS["Sales"],
        "row_count": len(df),
        "kpis": kpis,
        "charts": charts,
        "primary_value_column": sales_column,
        "primary_value": sales,
        "growth": period_growth(
            df,
            sales_column,
        ),
    }


# ============================================================================
# CUSTOMER DASHBOARD
# ============================================================================

def _is_truthy_churn(
    value: Any,
) -> bool:
    """
    Interpret common churn representations.
    """

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        (int, float, np.integer, np.floating),
    ):
        return safe_float(
            value
        ) != 0

    normalized = (
        str(value)
        .strip()
        .lower()
    )

    return normalized in {
        "1",
        "true",
        "yes",
        "y",
        "churned",
        "churn",
    }


def calculate_customer_dashboard(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return empty_dataset_result(
            "Customers"
        )

    customer_column = find_named_column(
        df,
        "customer",
    )

    sales_column = find_named_column(
        df,
        "sales",
    )

    churn_column = find_named_column(
        df,
        "churn",
    )

    region_column = find_named_column(
        df,
        "region",
    )

    customer_count = (
        df[
            customer_column
        ].nunique()
        if customer_column
        else len(df)
    )

    revenue = (
        numeric_series(
            df,
            sales_column,
        ).sum()
        if sales_column
        else None
    )

    churn_rate = None

    if churn_column:
        churn_values = df[
            churn_column
        ].map(
            _is_truthy_churn
        )

        if len(churn_values):
            churn_rate = (
                churn_values.mean()
                * 100
            )

    kpis = [
        make_kpi(
            "customer_count",
            "Customers",
            customer_count,
            description="Unique customers represented in the dataset.",
        )
    ]

    if revenue is not None:
        kpis.append(
            make_kpi(
                "customer_revenue",
                "Customer Revenue",
                revenue,
                format_type="currency",
                description="Sales/revenue represented by the customer dataset.",
            )
        )

    if churn_rate is not None:
        kpis.append(
            make_kpi(
                "customer_churn_rate",
                "Churn Rate",
                churn_rate,
                format_type="percentage",
                description="Observed customer churn rate.",
            )
        )

    charts = []

    chart = time_series_chart(
        df,
        sales_column,
        chart_id="customer_revenue_trend",
        title="Customer Revenue Trend",
        series_name="Revenue",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        region_column,
        sales_column,
        chart_id="customer_revenue_by_region",
        title="Customer Revenue by Region",
        series_name="Revenue",
    )

    if chart:
        charts.append(chart)

    return {
        "dataset_type": "Customers",
        "label": DATASET_LABELS["Customers"],
        "row_count": len(df),
        "kpis": kpis,
        "charts": charts,
        "primary_value_column": sales_column,
        "primary_value": revenue,
        "growth": period_growth(
            df,
            sales_column,
        ),
    }


# ============================================================================
# PRODUCT DASHBOARD
# ============================================================================

def calculate_product_dashboard(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return empty_dataset_result(
            "Products"
        )

    product_column = find_named_column(
        df,
        "product",
    )

    category_column = find_named_column(
        df,
        "category",
    )

    sales_column = find_named_column(
        df,
        "sales",
    )

    quantity_column = find_named_column(
        df,
        "quantity",
    )

    product_count = (
        df[
            product_column
        ].nunique()
        if product_column
        else len(df)
    )

    sales = (
        numeric_series(
            df,
            sales_column,
        ).sum()
        if sales_column
        else None
    )

    quantity = (
        numeric_series(
            df,
            quantity_column,
        ).sum()
        if quantity_column
        else None
    )

    kpis = [
        make_kpi(
            "product_count",
            "Products",
            product_count,
            description="Unique products represented in the dataset.",
        )
    ]

    if sales is not None:
        kpis.append(
            make_kpi(
                "product_sales",
                "Product Sales",
                sales,
                format_type="currency",
                description="Sales associated with the product dataset.",
            )
        )

    if quantity is not None:
        kpis.append(
            make_kpi(
                "product_units",
                "Units",
                quantity,
                description="Total units represented in the product dataset.",
            )
        )

    charts = []

    chart = grouped_chart(
        df,
        product_column,
        sales_column,
        chart_id="product_sales_by_product",
        title="Sales by Product",
        series_name="Sales",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        category_column,
        sales_column,
        chart_id="product_sales_by_category",
        title="Sales by Category",
        series_name="Sales",
    )

    if chart:
        charts.append(chart)

    return {
        "dataset_type": "Products",
        "label": DATASET_LABELS["Products"],
        "row_count": len(df),
        "kpis": kpis,
        "charts": charts,
        "primary_value_column": sales_column,
        "primary_value": sales,
        "growth": period_growth(
            df,
            sales_column,
        ),
    }


# ============================================================================
# REGIONAL DASHBOARD
# ============================================================================

def calculate_regional_dashboard(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return empty_dataset_result(
            "Regional"
        )

    region_column = find_named_column(
        df,
        "region",
    )

    sales_column = find_named_column(
        df,
        "sales",
    )

    quantity_column = find_named_column(
        df,
        "quantity",
    )

    region_count = (
        df[
            region_column
        ].nunique()
        if region_column
        else None
    )

    sales = (
        numeric_series(
            df,
            sales_column,
        ).sum()
        if sales_column
        else None
    )

    quantity = (
        numeric_series(
            df,
            quantity_column,
        ).sum()
        if quantity_column
        else None
    )

    kpis = [
        make_kpi(
            "regional_records",
            "Regional Records",
            len(df),
            description="Number of records in the Regional dataset.",
        )
    ]

    if region_count is not None:
        kpis.append(
            make_kpi(
                "region_count",
                "Regions",
                region_count,
                description="Number of unique regions.",
            )
        )

    if sales is not None:
        kpis.append(
            make_kpi(
                "regional_sales",
                "Regional Sales",
                sales,
                format_type="currency",
                description="Total sales represented by the Regional dataset.",
            )
        )

    if quantity is not None:
        kpis.append(
            make_kpi(
                "regional_units",
                "Regional Units",
                quantity,
                description="Total quantity represented by the Regional dataset.",
            )
        )

    charts = []

    chart = grouped_chart(
        df,
        region_column,
        sales_column,
        chart_id="regional_sales",
        title="Sales by Region",
        series_name="Sales",
    )

    if chart:
        charts.append(chart)

    chart = time_series_chart(
        df,
        sales_column,
        chart_id="regional_sales_trend",
        title="Regional Sales Trend",
        series_name="Sales",
    )

    if chart:
        charts.append(chart)

    return {
        "dataset_type": "Regional",
        "label": DATASET_LABELS["Regional"],
        "row_count": len(df),
        "kpis": kpis,
        "charts": charts,
        "primary_value_column": sales_column,
        "primary_value": sales,
        "growth": period_growth(
            df,
            sales_column,
        ),
    }


# ============================================================================
# MARKETING DASHBOARD
# ============================================================================

def calculate_marketing_dashboard(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return empty_dataset_result(
            "Marketing"
        )

    spend_column = find_named_column(
        df,
        "spend",
    )

    sales_column = find_named_column(
        df,
        "sales",
    )

    campaign_column = find_named_column(
        df,
        "campaign",
    )

    channel_column = find_named_column(
        df,
        "channel",
    )

    clicks_column = find_named_column(
        df,
        "clicks",
    )

    impressions_column = find_named_column(
        df,
        "impressions",
    )

    conversions_column = find_named_column(
        df,
        "conversions",
    )

    spend = (
        numeric_series(
            df,
            spend_column,
        ).sum()
        if spend_column
        else None
    )

    revenue = (
        numeric_series(
            df,
            sales_column,
        ).sum()
        if sales_column
        else None
    )

    roas = None

    if (
        spend is not None
        and spend != 0
        and revenue is not None
    ):
        roas = (
            revenue
            / spend
        )

    clicks = (
        numeric_series(
            df,
            clicks_column,
        ).sum()
        if clicks_column
        else None
    )

    impressions = (
        numeric_series(
            df,
            impressions_column,
        ).sum()
        if impressions_column
        else None
    )

    conversions = (
        numeric_series(
            df,
            conversions_column,
        ).sum()
        if conversions_column
        else None
    )

    kpis = [
        make_kpi(
            "marketing_records",
            "Marketing Records",
            len(df),
            description="Number of records in the Marketing dataset.",
        )
    ]

    if spend is not None:
        kpis.append(
            make_kpi(
                "marketing_spend",
                "Marketing Spend",
                spend,
                format_type="currency",
                description="Total marketing spend.",
            )
        )

    if revenue is not None:
        kpis.append(
            make_kpi(
                "marketing_revenue",
                "Marketing Revenue",
                revenue,
                format_type="currency",
                description="Revenue attributed to the Marketing dataset.",
            )
        )

    if roas is not None:
        kpis.append(
            make_kpi(
                "marketing_roas",
                "Marketing ROAS",
                roas,
                format_type="ratio",
                description="Marketing revenue divided by marketing spend.",
            )
        )

    if clicks is not None:
        kpis.append(
            make_kpi(
                "marketing_clicks",
                "Clicks",
                clicks,
                description="Total clicks.",
            )
        )

    if impressions is not None:
        kpis.append(
            make_kpi(
                "marketing_impressions",
                "Impressions",
                impressions,
                description="Total impressions.",
            )
        )

    if conversions is not None:
        kpis.append(
            make_kpi(
                "marketing_conversions",
                "Conversions",
                conversions,
                description="Total conversions.",
            )
        )

    charts = []

    chart = time_series_chart(
        df,
        sales_column,
        chart_id="marketing_revenue_trend",
        title="Marketing Revenue Trend",
        series_name="Revenue",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        campaign_column,
        sales_column,
        chart_id="marketing_by_campaign",
        title="Revenue by Campaign",
        series_name="Revenue",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        channel_column,
        sales_column,
        chart_id="marketing_by_channel",
        title="Revenue by Channel",
        series_name="Revenue",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        campaign_column,
        spend_column,
        chart_id="marketing_spend_by_campaign",
        title="Spend by Campaign",
        series_name="Spend",
    )

    if chart:
        charts.append(chart)

    return {
        "dataset_type": "Marketing",
        "label": DATASET_LABELS["Marketing"],
        "row_count": len(df),
        "kpis": kpis,
        "charts": charts,
        "primary_value_column": (
            sales_column
            or spend_column
        ),
        "primary_value": (
            revenue
            if revenue is not None
            else spend
        ),
        "growth": period_growth(
            df,
            sales_column
            or spend_column,
        ),
    }


# ============================================================================
# FINANCIAL DASHBOARD
# ============================================================================

def calculate_financial_dashboard(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return empty_dataset_result(
            "Financial"
        )

    income_column = find_named_column(
        df,
        "income",
    )

    expense_column = find_named_column(
        df,
        "expense",
    )

    profit_column = find_named_column(
        df,
        "profit",
    )

    tax_column = find_named_column(
        df,
        "tax",
    )

    investment_column = find_named_column(
        df,
        "investment",
    )

    cash_flow_column = find_named_column(
        df,
        "cash_flow",
    )

    income = (
        numeric_series(
            df,
            income_column,
        ).sum()
        if income_column
        else None
    )

    expense = (
        numeric_series(
            df,
            expense_column,
        ).sum()
        if expense_column
        else None
    )

    profit = (
        numeric_series(
            df,
            profit_column,
        ).sum()
        if profit_column
        else None
    )

    if (
        profit is None
        and income is not None
        and expense is not None
    ):
        profit = (
            income
            - expense
        )

    tax = (
        numeric_series(
            df,
            tax_column,
        ).sum()
        if tax_column
        else None
    )

    investment = (
        numeric_series(
            df,
            investment_column,
        ).sum()
        if investment_column
        else None
    )

    cash_flow = (
        numeric_series(
            df,
            cash_flow_column,
        ).sum()
        if cash_flow_column
        else None
    )

    margin = None

    if (
        income is not None
        and income != 0
        and profit is not None
    ):
        margin = (
            profit
            / income
        ) * 100

    kpis = [
        make_kpi(
            "financial_records",
            "Financial Records",
            len(df),
            description="Number of records in the Financial dataset.",
        )
    ]

    if income is not None:
        kpis.append(
            make_kpi(
                "financial_income",
                "Income",
                income,
                format_type="currency",
                description="Total income/revenue.",
            )
        )

    if expense is not None:
        kpis.append(
            make_kpi(
                "financial_expense",
                "Expenses",
                expense,
                format_type="currency",
                description="Total expenses.",
            )
        )

    if profit is not None:
        kpis.append(
            make_kpi(
                "financial_profit",
                "Profit",
                profit,
                format_type="currency",
                description="Calculated or supplied profit.",
            )
        )

    if margin is not None:
        kpis.append(
            make_kpi(
                "financial_margin",
                "Profit Margin",
                margin,
                format_type="percentage",
                description="Profit as a percentage of income.",
            )
        )

    if tax is not None:
        kpis.append(
            make_kpi(
                "financial_tax",
                "Tax",
                tax,
                format_type="currency",
                description="Total tax.",
            )
        )

    if investment is not None:
        kpis.append(
            make_kpi(
                "financial_investment",
                "Investment",
                investment,
                format_type="currency",
                description="Total investment.",
            )
        )

    if cash_flow is not None:
        kpis.append(
            make_kpi(
                "financial_cash_flow",
                "Cash Flow",
                cash_flow,
                format_type="currency",
                description="Total cash flow.",
            )
        )

    charts = []

    chart = time_series_chart(
        df,
        income_column,
        chart_id="financial_income_trend",
        title="Income Trend",
        series_name="Income",
    )

    if chart:
        charts.append(chart)

    chart = time_series_chart(
        df,
        expense_column,
        chart_id="financial_expense_trend",
        title="Expense Trend",
        series_name="Expenses",
    )

    if chart:
        charts.append(chart)

    chart = time_series_chart(
        df,
        profit_column,
        chart_id="financial_profit_trend",
        title="Profit Trend",
        series_name="Profit",
    )

    if chart:
        charts.append(chart)

    return {
        "dataset_type": "Financial",
        "label": DATASET_LABELS["Financial"],
        "row_count": len(df),
        "kpis": kpis,
        "charts": charts,
        "primary_value_column": income_column,
        "primary_value": income,
        "growth": period_growth(
            df,
            income_column,
        ),
    }


# ============================================================================
# RETURNS DASHBOARD
# ============================================================================

def calculate_returns_dashboard(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return empty_dataset_result(
            "Returns"
        )

    return_column = find_named_column(
        df,
        "return",
    )

    quantity_column = find_named_column(
        df,
        "quantity",
    )

    sales_column = find_named_column(
        df,
        "sales",
    )

    product_column = find_named_column(
        df,
        "product",
    )

    reason_column = find_named_column(
        df,
        "return_reason",
    )

    return_amount = (
        numeric_series(
            df,
            return_column,
        ).sum()
        if return_column
        else None
    )

    returned_units = (
        numeric_series(
            df,
            quantity_column,
        ).sum()
        if quantity_column
        else None
    )

    sales_amount = (
        numeric_series(
            df,
            sales_column,
        ).sum()
        if sales_column
        else None
    )

    return_rate = None

    if (
        return_amount is not None
        and sales_amount not in (
            None,
            0,
        )
    ):
        return_rate = (
            abs(return_amount)
            / abs(sales_amount)
        ) * 100

    kpis = [
        make_kpi(
            "return_records",
            "Return Records",
            len(df),
            description="Number of records in the Returns dataset.",
        )
    ]

    if return_amount is not None:
        kpis.append(
            make_kpi(
                "return_amount",
                "Return / Refund Value",
                return_amount,
                format_type="currency",
                description="Total return/refund value.",
            )
        )

    if returned_units is not None:
        kpis.append(
            make_kpi(
                "returned_units",
                "Returned Units",
                returned_units,
                description="Total returned quantity.",
            )
        )

    if return_rate is not None:
        kpis.append(
            make_kpi(
                "return_rate",
                "Return Rate",
                return_rate,
                format_type="percentage",
                description="Return value relative to sales value.",
            )
        )

    charts = []

    chart = time_series_chart(
        df,
        return_column,
        chart_id="returns_trend",
        title="Returns Trend",
        series_name="Returns",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        reason_column,
        return_column,
        chart_id="returns_by_reason",
        title="Returns by Reason",
        series_name="Return Value",
    )

    if chart:
        charts.append(chart)

    chart = grouped_chart(
        df,
        product_column,
        return_column,
        chart_id="returns_by_product",
        title="Returns by Product",
        series_name="Return Value",
    )

    if chart:
        charts.append(chart)

    return {
        "dataset_type": "Returns",
        "label": DATASET_LABELS["Returns"],
        "row_count": len(df),
        "kpis": kpis,
        "charts": charts,
        "primary_value_column": return_column,
        "primary_value": return_amount,
        "growth": period_growth(
            df,
            return_column,
        ),
    }


# ============================================================================
# DATASET CALCULATOR REGISTRY
# ============================================================================

DATASET_CALCULATORS = {
    "Sales": calculate_sales_dashboard,
    "Customers": calculate_customer_dashboard,
    "Products": calculate_product_dashboard,
    "Regional": calculate_regional_dashboard,
    "Marketing": calculate_marketing_dashboard,
    "Financial": calculate_financial_dashboard,
    "Returns": calculate_returns_dashboard,
}


# ============================================================================
# EMPTY RESULT
# ============================================================================

def empty_dataset_result(
    dataset_type: str,
) -> Dict[str, Any]:

    return {
        "dataset_type": dataset_type,
        "label": DATASET_LABELS.get(
            dataset_type,
            dataset_type,
        ),
        "row_count": 0,
        "kpis": [],
        "charts": [],
        "primary_value_column": None,
        "primary_value": None,
        "growth": None,
        "available": False,
    }


# ============================================================================
# PRIMARY VALUE HELPER
# ============================================================================

def revenue_column_or_none(
    primary: Optional[str],
    fallback: Optional[str],
) -> Optional[str]:

    return primary or fallback


# ============================================================================
# SELECTED DATASET CALCULATION
# ============================================================================

def calculate_dataset_dashboard(
    dataframe: pd.DataFrame,
    dataset_type: str,
) -> Dict[str, Any]:
    """
    Calculate intelligence for exactly one dataset.

    No other dataset category is mixed into this calculation.
    """

    dataset_type = str(
        dataset_type or ""
    ).strip()

    if dataset_type not in DATASET_CALCULATORS:
        return {
            "dataset_type": dataset_type,
            "label": dataset_type,
            "row_count": 0,
            "kpis": [],
            "charts": [],
            "available": False,
            "error": (
                "Unsupported dashboard dataset type: "
                f"{dataset_type}"
            ),
        }

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return empty_dataset_result(
            dataset_type
        )

    calculator = DATASET_CALCULATORS[
        dataset_type
    ]

    result = calculator(
        df
    )

    result["available"] = True
    result["data_bounds"] = get_date_bounds(
        df
    )

    return result


# ============================================================================
# TREND ANALYSIS
# ============================================================================

def calculate_trend_direction(
    dataframe: pd.DataFrame,
    value_column: Optional[str],
) -> Dict[str, Any]:
    """
    Determine the general direction of a time series.

    Uses a simple transparent linear regression slope.
    """

    df, date_column = prepare_date_dataframe(
        dataframe
    )

    if (
        df.empty
        or not date_column
        or not value_column
    ):
        return {
            "available": False,
            "direction": None,
            "slope": None,
            "strength": None,
        }

    values = numeric_series(
        df,
        value_column,
    )

    work = pd.DataFrame(
        {
            "date": df[date_column],
            "value": values,
        }
    ).dropna()

    if len(work) < 3:
        return {
            "available": False,
            "direction": None,
            "slope": None,
            "strength": None,
        }

    y = work[
        "value"
    ].to_numpy(
        dtype=float
    )

    x = np.arange(
        len(y),
        dtype=float,
    )

    slope = np.polyfit(
        x,
        y,
        1,
    )[0]

    mean_abs = np.mean(
        np.abs(y)
    )

    normalized_slope = (
        slope / mean_abs
        if mean_abs
        else 0
    )

    if normalized_slope > 0.01:
        direction = "increasing"

    elif normalized_slope < -0.01:
        direction = "decreasing"

    else:
        direction = "stable"

    try:
        correlation = np.corrcoef(
            x,
            y,
        )[0, 1]
    except Exception:
        correlation = 0

    strength = abs(
        safe_float(
            correlation
        )
    )

    return {
        "available": True,
        "direction": direction,
        "slope": safe_float(
            slope
        ),
        "normalized_slope": safe_float(
            normalized_slope
        ),
        "strength": safe_float(
            strength
        ),
    }


# ============================================================================
# ANOMALY DETECTION
# ============================================================================

def detect_numeric_anomalies(
    dataframe: pd.DataFrame,
    value_column: Optional[str],
    *,
    z_threshold: float = 2.5,
) -> Dict[str, Any]:
    """
    Detect unusual observations using z-scores.
    """

    df, date_column = prepare_date_dataframe(
        dataframe
    )

    if (
        df.empty
        or not value_column
    ):
        return {
            "available": False,
            "count": 0,
            "items": [],
        }

    values = numeric_series(
        df,
        value_column,
    )

    work = pd.DataFrame(
        {
            "date": (
                df[date_column]
                if date_column
                else pd.Series(
                    range(
                        len(df)
                    ),
                    index=df.index,
                )
            ),
            "value": values,
        }
    ).dropna()

    if len(work) < 5:
        return {
            "available": False,
            "count": 0,
            "items": [],
        }

    mean = work[
        "value"
    ].mean()

    std = work[
        "value"
    ].std()

    if std == 0 or pd.isna(std):
        return {
            "available": True,
            "count": 0,
            "items": [],
        }

    work[
        "z_score"
    ] = (
        work["value"]
        - mean
    ) / std

    anomalies = work[
        work[
            "z_score"
        ].abs()
        >= z_threshold
    ].copy()

    anomalies = anomalies.sort_values(
        "z_score",
        key=lambda series: series.abs(),
        ascending=False,
    ).head(
        10
    )

    items = []

    for _, row in anomalies.iterrows():

        items.append(
            {
                "date": json_safe(
                    row["date"]
                ),
                "value": json_safe(
                    row["value"]
                ),
                "z_score": json_safe(
                    row["z_score"]
                ),
                "direction": (
                    "high"
                    if row["z_score"] > 0
                    else "low"
                ),
            }
        )

    return {
        "available": True,
        "count": len(items),
        "items": items,
    }


# ============================================================================
# FORECASTING
# ============================================================================

def forecast_numeric_series(
    dataframe: pd.DataFrame,
    value_column: Optional[str],
    *,
    periods: int = 6,
) -> Dict[str, Any]:
    """
    Simple transparent linear-trend forecast.

    Requirements:
        - usable date field
        - numeric value field
        - sufficient historical observations

    No external forecasting library is required.
    """

    df, date_column = prepare_date_dataframe(
        dataframe
    )

    if (
        df.empty
        or not date_column
        or not value_column
    ):
        return {
            "available": False,
            "reason": (
                "A date and numeric measure are required."
            ),
            "periods": [],
        }

    values = numeric_series(
        df,
        value_column,
    )

    work = pd.DataFrame(
        {
            "date": df[date_column],
            "value": values,
        }
    ).dropna()

    if len(work) < 6:
        return {
            "available": False,
            "reason": (
                "At least six historical observations "
                "are required for forecasting."
            ),
            "periods": [],
        }

    work = work.sort_values(
        "date"
    )

    # Aggregate monthly.
    monthly = (
        work.set_index(
            "date"
        )["value"]
        .resample("ME")
        .sum()
        .dropna()
    )

    if len(monthly) < 4:
        # Fall back to original observations.
        series = work[
            "value"
        ]

        last_date = work[
            "date"
        ].iloc[-1]

        frequency = "D"

    else:
        series = monthly

        last_date = monthly.index[-1]

        frequency = "M"

    if len(series) < 4:
        return {
            "available": False,
            "reason": (
                "Not enough historical observations."
            ),
            "periods": [],
        }

    y = np.asarray(
        series.values,
        dtype=float,
    )

    x = np.arange(
        len(y),
        dtype=float,
    )

    slope, intercept = np.polyfit(
        x,
        y,
        1,
    )

    future_x = np.arange(
        len(y),
        len(y) + periods,
        dtype=float,
    )

    predictions = (
        intercept
        + slope * future_x
    )

    # Business measures such as revenue, sales, spend,
    # quantities and returns should not receive negative
    # forecasts.
    predictions = np.maximum(
        predictions,
        0,
    )

    if frequency == "M":

        future_dates = pd.date_range(
            start=(
                last_date
                + pd.offsets.MonthEnd(
                    1
                )
            ),
            periods=periods,
            freq="ME",
        )

    else:

        future_dates = pd.date_range(
            start=(
                last_date
                + pd.Timedelta(
                    days=1
                )
            ),
            periods=periods,
            freq="D",
        )

    if slope > 0:
        trend = "increasing"

    elif slope < 0:
        trend = "decreasing"

    else:
        trend = "stable"

    return {
        "available": True,
        "method": "linear_trend",
        "frequency": frequency,
        "trend": trend,
        "slope": safe_float(
            slope
        ),
        "historical_points": len(
            series
        ),
        "periods": [
            {
                "date": json_safe(
                    forecast_date
                ),
                "value": safe_float(
                    value
                ),
            }
            for forecast_date, value
            in zip(
                future_dates,
                predictions,
            )
        ],
    }


# ============================================================================
# DATA-DRIVEN INSIGHTS
# ============================================================================

def generate_dataset_insights(
    dashboard_data: Dict[str, Any],
    dataframe: pd.DataFrame,
) -> Dict[str, List[str]]:
    """
    Generate four executive insight categories:

        What Happened?
        Why Did It Happen?
        What Is Going to Happen?
        What Should We Do?
    """

    dataset_type = dashboard_data.get(
        "dataset_type",
        "Dataset",
    )

    insights = {
        "what_happened": [],
        "why_happened": [],
        "going_to_happen": [],
        "what_to_do": [],
    }

    growth = dashboard_data.get(
        "growth"
    )

    primary_value = dashboard_data.get(
        "primary_value"
    )

    # ------------------------------------------------------------------------
    # WHAT HAPPENED?
    # ------------------------------------------------------------------------

    if primary_value is not None:
        insights[
            "what_happened"
        ].append(
            (
                f"{dataset_type} currently represents "
                f"{safe_float(primary_value):,.2f} "
                "of its primary measured value."
            )
        )

    if growth is not None:

        if growth > 5:
            message = (
                f"{dataset_type} shows positive "
                f"period-over-period growth of "
                f"{growth:.1f}%."
            )

        elif growth < -5:
            message = (
                f"{dataset_type} shows a "
                f"period-over-period decline of "
                f"{abs(growth):.1f}%."
            )

        else:
            message = (
                f"{dataset_type} is relatively stable, "
                f"with period growth of "
                f"{growth:.1f}%."
            )

        insights[
            "what_happened"
        ].append(
            message
        )

    # ------------------------------------------------------------------------
    # WHY DID IT HAPPEN?
    # ------------------------------------------------------------------------

    charts = dashboard_data.get(
        "charts",
        [],
    )

    for chart in charts[:3]:

        labels = chart.get(
            "labels",
            [],
        )

        values = chart.get(
            "values",
            [],
        )

        if not labels or not values:
            continue

        if len(labels) != len(values):
            continue

        numeric_values = [
            safe_float(
                value
            )
            for value in values
        ]

        if not numeric_values:
            continue

        try:
            index = max(
                range(
                    len(
                        numeric_values
                    )
                ),
                key=lambda i:
                    numeric_values[i],
            )

            if index < len(labels):

                top_label = labels[
                    index
                ]

                insights[
                    "why_happened"
                ].append(
                    (
                        f"{chart.get('title', 'Analysis')} "
                        f"indicates {top_label} as the "
                        "largest observed contributor."
                    )
                )

        except Exception:
            continue

    # ------------------------------------------------------------------------
    # WHAT IS GOING TO HAPPEN?
    # ------------------------------------------------------------------------

    forecast = dashboard_data.get(
        "forecast",
        {},
    )

    if forecast.get(
        "available"
    ):

        trend = forecast.get(
            "trend"
        )

        periods = forecast.get(
            "periods",
            [],
        )

        if periods:

            next_value = periods[
                0
            ].get(
                "value"
            )

            if trend == "increasing":

                insights[
                    "going_to_happen"
                ].append(
                    (
                        "The forecast indicates that the "
                        f"{dataset_type} measure is likely "
                        "to continue increasing, with the "
                        "first projected value around "
                        f"{safe_float(next_value):,.2f}."
                    )
                )

            elif trend == "decreasing":

                insights[
                    "going_to_happen"
                ].append(
                    (
                        "The forecast indicates a continuing "
                        f"downward direction for "
                        f"{dataset_type}. The projected trend "
                        "should be monitored."
                    )
                )

            else:

                insights[
                    "going_to_happen"
                ].append(
                    (
                        f"The forecast indicates a relatively "
                        f"stable {dataset_type} trajectory."
                    )
                )

    # ------------------------------------------------------------------------
    # ANOMALIES
    # ------------------------------------------------------------------------

    anomalies = dashboard_data.get(
        "anomalies",
        {},
    )

    anomaly_count = safe_int(
        anomalies.get(
            "count",
            0,
        )
    )

    if anomaly_count > 0:

        insights[
            "why_happened"
        ].append(
            (
                f"{anomaly_count} unusual observation(s) "
                "were detected and may explain part of the "
                "observed variation."
            )
        )

    # ------------------------------------------------------------------------
    # WHAT SHOULD WE DO?
    # ------------------------------------------------------------------------

    risks = dashboard_data.get(
        "risks",
        [],
    )

    for risk in risks[:3]:

        recommendation = risk.get(
            "recommendation"
        )

        if recommendation:
            insights[
                "what_to_do"
            ].append(
                recommendation
            )

    if not insights[
        "what_to_do"
    ]:

        insights[
            "what_to_do"
        ].append(
            (
                f"Continue monitoring the key "
                f"{dataset_type} KPIs, drivers, "
                "anomalies and forecast."
            )
        )

    # ------------------------------------------------------------------------
    # FALLBACKS
    # ------------------------------------------------------------------------

    if not insights[
        "what_happened"
    ]:

        insights[
            "what_happened"
        ].append(
            (
                f"The {dataset_type} dataset does not "
                "contain enough supported measures for "
                "a detailed historical summary."
            )
        )

    if not insights[
        "why_happened"
    ]:

        insights[
            "why_happened"
        ].append(
            (
                "Driver analysis becomes available when "
                "the dataset contains compatible category, "
                "region, product or campaign fields."
            )
        )

    if not insights[
        "going_to_happen"
    ]:

        insights[
            "going_to_happen"
        ].append(
            (
                "Forecasting requires a usable date field "
                "and sufficient historical numeric observations."
            )
        )

    return insights


# ============================================================================
# RISK ANALYSIS
# ============================================================================

def calculate_dataset_risks(
    dataframe: pd.DataFrame,
    dataset_type: str,
) -> List[Dict[str, Any]]:
    """
    Generate transparent data-driven risk signals.
    """

    risks = []

    df = prepare_dataframe(
        dataframe
    )

    if df.empty:
        return risks

    dataset_type = str(
        dataset_type or ""
    ).strip()

    # ------------------------------------------------------------------------
    # PRIMARY NUMERIC FIELD
    # ------------------------------------------------------------------------

    if dataset_type == "Sales":

        value_column = find_named_column(
            df,
            "sales",
        )

    elif dataset_type == "Financial":

        value_column = find_named_column(
            df,
            "income",
        )

    elif dataset_type == "Returns":

        value_column = find_named_column(
            df,
            "return",
        )

    elif dataset_type == "Marketing":

        value_column = find_named_column(
            df,
            "sales",
        )

    else:

        value_column = find_named_column(
            df,
            "sales",
        )

    # ------------------------------------------------------------------------
    # DECLINING TREND
    # ------------------------------------------------------------------------

    trend = calculate_trend_direction(
        df,
        value_column,
    )

    if (
        trend.get("available")
        and trend.get("direction")
        == "decreasing"
    ):

        risks.append(
            {
                "type": "declining_trend",
                "severity": "medium",
                "title": "Declining Trend",
                "message": (
                    f"{dataset_type} shows a "
                    "downward historical trend."
                ),
                "recommendation": (
                    "Investigate the strongest negative drivers "
                    "by period, product, region, customer or "
                    "campaign where available."
                ),
            }
        )

    # ------------------------------------------------------------------------
    # FINANCIAL MARGIN
    # ------------------------------------------------------------------------

    if dataset_type == "Financial":

        income_column = find_named_column(
            df,
            "income",
        )

        expense_column = find_named_column(
            df,
            "expense",
        )

        if income_column and expense_column:

            income = numeric_series(
                df,
                income_column,
            ).sum()

            expense = numeric_series(
                df,
                expense_column,
            ).sum()

            if income != 0:

                margin = (
                    (
                        income
                        - expense
                    )
                    / income
                ) * 100

                if margin < 0:

                    risks.append(
                        {
                            "type": "negative_margin",
                            "severity": "high",
                            "title": "Negative Financial Margin",
                            "message": (
                                "Expenses exceed income, "
                                f"resulting in a margin of "
                                f"{margin:.1f}%."
                            ),
                            "recommendation": (
                                "Review major expense categories "
                                "and the periods responsible for "
                                "the negative result."
                            ),
                        }
                    )

                elif margin < 10:

                    risks.append(
                        {
                            "type": "low_margin",
                            "severity": "medium",
                            "title": "Low Financial Margin",
                            "message": (
                                "The calculated financial "
                                f"margin is {margin:.1f}%."
                            ),
                            "recommendation": (
                                "Monitor operating expenses "
                                "and revenue drivers closely."
                            ),
                        }
                    )

    # ------------------------------------------------------------------------
    # MARKETING ROAS
    # ------------------------------------------------------------------------

    if dataset_type == "Marketing":

        spend_column = find_named_column(
            df,
            "spend",
        )

        sales_column = find_named_column(
            df,
            "sales",
        )

        if spend_column and sales_column:

            spend = numeric_series(
                df,
                spend_column,
            ).sum()

            revenue = numeric_series(
                df,
                sales_column,
            ).sum()

            if spend != 0:

                roas = (
                    revenue
                    / spend
                )

                if roas < 1:

                    risks.append(
                        {
                            "type": "low_roas",
                            "severity": "high",
                            "title": "Marketing Return Below Spend",
                            "message": (
                                f"Observed ROAS is "
                                f"{roas:.2f}."
                            ),
                            "recommendation": (
                                "Review campaign and channel "
                                "performance before increasing "
                                "marketing spend."
                            ),
                        }
                    )

    # ------------------------------------------------------------------------
    # RETURNS
    # ------------------------------------------------------------------------

    if dataset_type == "Returns":

        return_column = find_named_column(
            df,
            "return",
        )

        sales_column = find_named_column(
            df,
            "sales",
        )

        if return_column and sales_column:

            returns = numeric_series(
                df,
                return_column,
            ).sum()

            sales = numeric_series(
                df,
                sales_column,
            ).sum()

            if sales != 0:

                rate = (
                    abs(returns)
                    / abs(sales)
                ) * 100

                if rate > 10:

                    risks.append(
                        {
                            "type": "high_return_rate",
                            "severity": "high",
                            "title": "High Return Rate",
                            "message": (
                                "The observed return "
                                f"rate is {rate:.1f}%."
                            ),
                            "recommendation": (
                                "Investigate return reasons, "
                                "products and regions contributing "
                                "most to returned value."
                            ),
                        }
                    )

                elif rate > 5:

                    risks.append(
                        {
                            "type": "elevated_return_rate",
                            "severity": "medium",
                            "title": "Elevated Return Rate",
                            "message": (
                                "The observed return "
                                f"rate is {rate:.1f}%."
                            ),
                            "recommendation": (
                                "Monitor return drivers and "
                                "identify recurring product or "
                                "service issues."
                            ),
                        }
                    )

    return risks


# ============================================================================
# COMPLETE SELECTED DASHBOARD
# ============================================================================

def calculate_selected_dashboard(
    dataframe: pd.DataFrame,
    dataset_type: str,
    *,
    from_date: Any = None,
    to_date: Any = None,
) -> Dict[str, Any]:
    """
    Complete Executive Dashboard for EXACTLY ONE dataset.
    """

    original_df = prepare_dataframe(
        dataframe
    )

    if original_df.empty:

        result = empty_dataset_result(
            dataset_type
        )

        result.update(
            {
                "mode": "selected",
                "dataset_type": dataset_type,
                "insights": {
                    "what_happened": [],
                    "why_happened": [],
                    "going_to_happen": [],
                    "what_to_do": [],
                },
                "forecast": {
                    "available": False,
                    "periods": [],
                },
                "anomalies": {
                    "available": False,
                    "count": 0,
                    "items": [],
                },
                "risks": [],
                "recommendations": [],
                "data_bounds": get_date_bounds(
                    original_df
                ),
                "date_filter": {
                    "from": json_safe(
                        from_date
                    ),
                    "to": json_safe(
                        to_date
                    ),
                },
            }
        )

        return result

    df = apply_date_range(
        original_df,
        from_date,
        to_date,
    )

    if df.empty:

        result = empty_dataset_result(
            dataset_type
        )

        result.update(
            {
                "mode": "selected",
                "dataset_type": dataset_type,
                "insights": {
                    "what_happened": [
                        "No records match the selected date range."
                    ],
                    "why_happened": [],
                    "going_to_happen": [],
                    "what_to_do": [
                        "Expand the date range to include more historical records."
                    ],
                },
                "forecast": {
                    "available": False,
                    "periods": [],
                },
                "anomalies": {
                    "available": False,
                    "count": 0,
                    "items": [],
                },
                "risks": [],
                "recommendations": [
                    "Expand the date range to include more historical records."
                ],
                "data_bounds": get_date_bounds(
                    original_df
                ),
                "date_filter": {
                    "from": json_safe(
                        from_date
                    ),
                    "to": json_safe(
                        to_date
                    ),
                },
            }
        )

        return result

    dashboard = calculate_dataset_dashboard(
        df,
        dataset_type,
    )

    primary_column = dashboard.get(
        "primary_value_column"
    )

    trend = calculate_trend_direction(
        df,
        primary_column,
    )

    anomalies = detect_numeric_anomalies(
        df,
        primary_column,
    )

    forecast = forecast_numeric_series(
        df,
        primary_column,
    )

    risks = calculate_dataset_risks(
        df,
        dataset_type,
    )

    dashboard["mode"] = "selected"

    dashboard["trend"] = trend

    dashboard["anomalies"] = anomalies

    dashboard["forecast"] = forecast

    dashboard["risks"] = risks

    dashboard["data_bounds"] = get_date_bounds(
        df
    )

    dashboard["date_filter"] = {
        "from": json_safe(
            from_date
        ),
        "to": json_safe(
            to_date
        ),
    }

    dashboard["insights"] = (
        generate_dataset_insights(
            dashboard,
            df,
        )
    )

    dashboard["recommendations"] = (
        dashboard[
            "insights"
        ].get(
            "what_to_do",
            [],
        )
    )

    return json_safe(
        dashboard
    )


# ============================================================================
# OVERALL KPI HELPERS
# ============================================================================

def find_kpi_value(
    result: Dict[str, Any],
    keys: Iterable[str],
) -> Optional[float]:

    wanted = set(
        keys
    )

    for kpi in result.get(
        "kpis",
        [],
    ):

        if kpi.get(
            "key"
        ) in wanted:

            value = kpi.get(
                "value"
            )

            if value is not None:
                return safe_float(
                    value,
                    default=0,
                )

    return None


def overall_kpi(
    key: str,
    label: str,
    value: Optional[float],
    *,
    format_type: str = "number",
    description: str = "",
) -> Optional[Dict[str, Any]]:

    if value is None:
        return None

    return make_kpi(
        key,
        label,
        value,
        format_type=format_type,
        description=description,
    )


# ============================================================================
# OVERALL BUSINESS INTELLIGENCE
# ============================================================================

def calculate_overall_dashboard(
    datasets: Dict[str, Any],
    *,
    from_date: Any = None,
    to_date: Any = None,
) -> Dict[str, Any]:
    """
    Build Overall Business Intelligence.

    `datasets` should contain the latest available dataset
    for each available category.

    Dataset categories are analyzed independently.

    They are NEVER blindly concatenated.
    """

    if not datasets:

        return {
            "mode": "overall",
            "dataset_count": 0,
            "available_categories": [],
            "row_count": 0,
            "kpis": [],
            "charts": [],
            "categories": {},
            "insights": {
                "what_happened": [
                    "No dashboard datasets are currently available."
                ],
                "why_happened": [],
                "going_to_happen": [],
                "what_to_do": [],
            },
            "forecasts": [],
            "risks": [],
            "recommendations": [],
            "data_bounds": {},
            "error": None,
        }

    category_results = {}

    total_rows = 0

    # ------------------------------------------------------------------------
    # ANALYZE EACH CATEGORY INDEPENDENTLY
    # ------------------------------------------------------------------------

    for dataset_type in DASHBOARD_DATASET_TYPES:

        if dataset_type not in datasets:
            continue

        source = datasets.get(
            dataset_type
        )

        # dashboard_service may provide a DashboardDataset object.
        if hasattr(
            source,
            "dataframe",
        ):

            dataframe = source.dataframe

        elif isinstance(
            source,
            dict,
        ):

            dataframe = source.get(
                "dataframe"
            )

            if dataframe is None:
                dataframe = source.get(
                    "df"
                )

        else:

            dataframe = source

        df = prepare_dataframe(
            dataframe
        )

        if df.empty:
            continue

        filtered_df = apply_date_range(
            df,
            from_date,
            to_date,
        )

        if filtered_df.empty:
            continue

        result = calculate_selected_dashboard(
            filtered_df,
            dataset_type,
        )

        category_results[
            dataset_type
        ] = result

        total_rows += len(
            filtered_df
        )

    # ------------------------------------------------------------------------
    # CATEGORY RESULTS
    # ------------------------------------------------------------------------

    sales_result = category_results.get(
        "Sales"
    )

    customer_result = category_results.get(
        "Customers"
    )

    product_result = category_results.get(
        "Products"
    )

    regional_result = category_results.get(
        "Regional"
    )

    marketing_result = category_results.get(
        "Marketing"
    )

    financial_result = category_results.get(
        "Financial"
    )

    returns_result = category_results.get(
        "Returns"
    )

    # ------------------------------------------------------------------------
    # OVERALL KPIs
    #
    # IMPORTANT:
    # Do not add Sales revenue + Financial income.
    # That can double-count the same business activity.
    # ------------------------------------------------------------------------

    overall_kpis = []

    # ------------------------------------------------------------------------
    # REVENUE
    # ------------------------------------------------------------------------

    revenue = None

    if sales_result:

        revenue = find_kpi_value(
            sales_result,
            [
                "sales_revenue",
                "sales",
                "revenue",
            ],
        )

    if (
        revenue is None
        and financial_result
    ):

        revenue = find_kpi_value(
            financial_result,
            [
                "financial_income",
            ],
        )

    kpi = overall_kpi(
        "overall_revenue",
        "Business Revenue",
        revenue,
        format_type="currency",
        description=(
            "Revenue from the latest available Sales dataset, "
            "or Financial income when Sales data is unavailable."
        ),
    )

    if kpi:
        overall_kpis.append(
            kpi
        )

    # ------------------------------------------------------------------------
    # PROFIT
    # ------------------------------------------------------------------------

    profit = None

    if financial_result:

        profit = find_kpi_value(
            financial_result,
            [
                "financial_profit",
            ],
        )

    if (
        profit is None
        and sales_result
    ):

        profit = find_kpi_value(
            sales_result,
            [
                "sales_profit",
            ],
        )

    kpi = overall_kpi(
        "overall_profit",
        "Business Profit",
        profit,
        format_type="currency",
        description=(
            "Profit from the latest available Financial "
            "dataset, or Sales profit when Financial data "
            "is unavailable."
        ),
    )

    if kpi:
        overall_kpis.append(
            kpi
        )

    # ------------------------------------------------------------------------
    # CUSTOMERS
    # ------------------------------------------------------------------------

    customers = None

    if customer_result:

        customers = find_kpi_value(
            customer_result,
            [
                "customer_count",
            ],
        )

    elif sales_result:

        customers = find_kpi_value(
            sales_result,
            [
                "sales_customers",
            ],
        )

    kpi = overall_kpi(
        "overall_customers",
        "Customers",
        customers,
        description=(
            "Customers from the latest available "
            "Customer Intelligence data."
        ),
    )

    if kpi:
        overall_kpis.append(
            kpi
        )

    # ------------------------------------------------------------------------
    # PRODUCTS
    # ------------------------------------------------------------------------

    products = None

    if product_result:

        products = find_kpi_value(
            product_result,
            [
                "product_count",
            ],
        )

    elif sales_result:

        products = find_kpi_value(
            sales_result,
            [
                "sales_products",
            ],
        )

    kpi = overall_kpi(
        "overall_products",
        "Products",
        products,
        description=(
            "Products from the latest available "
            "Product Intelligence data."
        ),
    )

    if kpi:
        overall_kpis.append(
            kpi
        )

    # ------------------------------------------------------------------------
    # MARKETING SPEND
    # ------------------------------------------------------------------------

    marketing_spend = None

    if marketing_result:

        marketing_spend = find_kpi_value(
            marketing_result,
            [
                "marketing_spend",
            ],
        )

    kpi = overall_kpi(
        "overall_marketing_spend",
        "Marketing Spend",
        marketing_spend,
        format_type="currency",
        description=(
            "Marketing spend from the latest available "
            "Marketing dataset."
        ),
    )

    if kpi:
        overall_kpis.append(
            kpi
        )

    # ------------------------------------------------------------------------
    # ROAS
    # ------------------------------------------------------------------------

    roas = None

    if marketing_result:

        roas = find_kpi_value(
            marketing_result,
            [
                "marketing_roas",
            ],
        )

    kpi = overall_kpi(
        "overall_roas",
        "Marketing ROAS",
        roas,
        format_type="ratio",
        description=(
            "Marketing revenue divided by marketing spend."
        ),
    )

    if kpi:
        overall_kpis.append(
            kpi
        )

    # ------------------------------------------------------------------------
    # RETURN RATE
    # ------------------------------------------------------------------------

    return_rate = None

    if returns_result:

        return_rate = find_kpi_value(
            returns_result,
            [
                "return_rate",
            ],
        )

    kpi = overall_kpi(
        "overall_return_rate",
        "Return Rate",
        return_rate,
        format_type="percentage",
        description=(
            "Return rate from the latest available "
            "Returns dataset."
        ),
    )

    if kpi:
        overall_kpis.append(
            kpi
        )

    # ------------------------------------------------------------------------
    # REGIONS
    # ------------------------------------------------------------------------

    regions = None

    if regional_result:

        regions = find_kpi_value(
            regional_result,
            [
                "region_count",
            ],
        )

    kpi = overall_kpi(
        "overall_regions",
        "Regions",
        regions,
        description=(
            "Regions represented in the latest "
            "Regional dataset."
        ),
    )

    if kpi:
        overall_kpis.append(
            kpi
        )

    # =========================================================================
    # OVERALL CHARTS
    # =========================================================================

    charts = []

    for dataset_type, result in category_results.items():

        for chart in result.get(
            "charts",
            [],
        ):

            chart_copy = dict(
                chart
            )

            chart_copy[
                "dataset_type"
            ] = dataset_type

            charts.append(
                chart_copy
            )

    # Keep dashboard payload manageable.
    charts = charts[:25]

    # =========================================================================
    # FORECASTS
    # =========================================================================

    forecasts = []

    for dataset_type, result in category_results.items():

        forecast = result.get(
            "forecast"
        )

        if (
            forecast
            and forecast.get(
                "available"
            )
        ):

            forecasts.append(
                {
                    "dataset_type": dataset_type,
                    "label": DATASET_LABELS.get(
                        dataset_type,
                        dataset_type,
                    ),
                    **forecast,
                }
            )

    # =========================================================================
    # RISKS
    # =========================================================================

    risks = []

    for dataset_type, result in category_results.items():

        for risk in result.get(
            "risks",
            [],
        ):

            risk_copy = dict(
                risk
            )

            risk_copy[
                "dataset_type"
            ] = dataset_type

            risks.append(
                risk_copy
            )

    # =========================================================================
    # INSIGHTS
    # =========================================================================

    overall_insights = {
        "what_happened": [],
        "why_happened": [],
        "going_to_happen": [],
        "what_to_do": [],
    }

    for dataset_type, result in category_results.items():

        insights = result.get(
            "insights",
            {},
        )

        prefix = DATASET_LABELS.get(
            dataset_type,
            dataset_type,
        )

        for key in overall_insights:

            for message in insights.get(
                key,
                [],
            ):

                overall_insights[
                    key
                ].append(
                    f"{prefix}: {message}"
                )

    available = list(
        category_results.keys()
    )

    if available:

        overall_insights[
            "what_happened"
        ].insert(
            0,
            (
                "Overall Business Intelligence is based "
                "on the latest available dataset from: "
                + ", ".join(
                    available
                )
                + "."
            ),
        )

    if len(
        available
    ) > 1:

        overall_insights[
            "why_happened"
        ].insert(
            0,
            (
                "The dashboard keeps Sales, Customer, Product, "
                "Regional, Marketing, Financial and Returns "
                "datasets independent so their measures are "
                "not incorrectly combined."
            ),
        )

    if forecasts:

        overall_insights[
            "going_to_happen"
        ].insert(
            0,
            (
                "Forecasts are available for "
                f"{len(forecasts)} dataset "
                "category/categories."
            ),
        )

    if risks:

        overall_insights[
            "what_to_do"
        ].insert(
            0,
            (
                f"{len(risks)} data-driven risk signal(s) "
                "require monitoring across the available "
                "business datasets."
            ),
        )

    # ------------------------------------------------------------------------
    # REMOVE DUPLICATES
    # ------------------------------------------------------------------------

    for key in overall_insights:

        unique = []

        for message in overall_insights[
            key
        ]:

            if message not in unique:
                unique.append(
                    message
                )

        overall_insights[
            key
        ] = unique[:10]

    # ------------------------------------------------------------------------
    # FALLBACKS
    # ------------------------------------------------------------------------

    if not overall_insights[
        "what_happened"
    ]:

        overall_insights[
            "what_happened"
        ].append(
            (
                "The available datasets do not yet contain "
                "enough supported measures for an overall summary."
            )
        )

    if not overall_insights[
        "why_happened"
    ]:

        overall_insights[
            "why_happened"
        ].append(
            (
                "Driver analysis becomes available when the "
                "available datasets contain compatible "
                "categorical and numeric fields."
            )
        )

    if not overall_insights[
        "going_to_happen"
    ]:

        overall_insights[
            "going_to_happen"
        ].append(
            (
                "Forecasting becomes available when sufficient "
                "historical date and numeric data exists."
            )
        )

    if not overall_insights[
        "what_to_do"
    ]:

        overall_insights[
            "what_to_do"
        ].append(
            (
                "Review the category-level KPIs, trends, "
                "risks and forecasts before taking action."
            )
        )

    return json_safe(
        {
            "mode": "overall",
            "dataset_count": len(
                category_results
            ),
            "available_categories": list(
                category_results.keys()
            ),
            "row_count": total_rows,
            "kpis": overall_kpis,
            "charts": charts,
            "categories": category_results,
            "insights": overall_insights,
            "forecasts": forecasts,
            "risks": risks,
            "recommendations": overall_insights[
                "what_to_do"
            ],
            "data_bounds": {
                dataset_type: result.get(
                    "data_bounds"
                )
                for dataset_type, result
                in category_results.items()
            },
            "date_filter": {
                "from": json_safe(
                    from_date
                ),
                "to": json_safe(
                    to_date
                ),
            },
            "error": None,
        }
    )


# ============================================================================
# PUBLIC EXECUTIVE DASHBOARD API
# ============================================================================

def calculate_executive_dashboard(
    dataframe: Optional[pd.DataFrame] = None,
    dataset_type: Optional[str] = None,
    *,
    mode: str = "selected",
    datasets: Optional[Dict[str, Any]] = None,
    from_date: Any = None,
    to_date: Any = None,
) -> Dict[str, Any]:
    """
    Main public Executive Dashboard API.

    SELECTED MODE
    -------------

    Exactly one dataset is analyzed.

    OVERALL MODE
    ------------

    Each available category is analyzed independently.

    This function performs calculations only.
    Dataset selection and cleaned DatasetVersion resolution
    belong to dashboard_service.py.
    """

    normalized_mode = str(
        mode or "selected"
    ).lower().strip()

    if normalized_mode == "overall":

        return calculate_overall_dashboard(
            datasets or {},
            from_date=from_date,
            to_date=to_date,
        )

    # ------------------------------------------------------------------------
    # SELECTED MODE
    # ------------------------------------------------------------------------

    if not dataset_type:

        return {
            "mode": "selected",
            "dataset_type": None,
            "row_count": 0,
            "kpis": [],
            "charts": [],
            "insights": {
                "what_happened": [
                    "No dataset has been selected."
                ],
                "why_happened": [],
                "going_to_happen": [],
                "what_to_do": [],
            },
            "forecast": {
                "available": False,
                "periods": [],
            },
            "anomalies": {
                "available": False,
                "count": 0,
                "items": [],
            },
            "risks": [],
            "recommendations": [],
            "date_filter": {
                "from": json_safe(
                    from_date
                ),
                "to": json_safe(
                    to_date
                ),
            },
            "error": None,
        }

    return calculate_selected_dashboard(
        dataframe=(
            dataframe
            if dataframe is not None
            else pd.DataFrame()
        ),
        dataset_type=dataset_type,
        from_date=from_date,
        to_date=to_date,
    )


# ============================================================================
# BACKWARD-COMPATIBILITY HELPERS
# ============================================================================

def calculate_dashboard_metrics(
    dataframe: pd.DataFrame,
    dataset_type: str,
) -> Dict[str, Any]:
    """
    Compatibility wrapper for existing dashboard callers.
    """

    return calculate_selected_dashboard(
        dataframe,
        dataset_type,
    )


def calculate_dashboard_insights(
    dataframe: pd.DataFrame,
    dataset_type: str,
) -> Dict[str, List[str]]:
    """
    Compatibility wrapper for insight generation.
    """

    result = calculate_selected_dashboard(
        dataframe,
        dataset_type,
    )

    return result.get(
        "insights",
        {
            "what_happened": [],
            "why_happened": [],
            "going_to_happen": [],
            "what_to_do": [],
        },
    )


def calculate_dashboard_forecast(
    dataframe: pd.DataFrame,
    dataset_type: str,
) -> Dict[str, Any]:
    """
    Compatibility wrapper for forecasting.
    """

    result = calculate_selected_dashboard(
        dataframe,
        dataset_type,
    )

    return result.get(
        "forecast",
        {
            "available": False,
            "periods": [],
        },
    )


def calculate_dashboard_risks(
    dataframe: pd.DataFrame,
    dataset_type: str,
) -> List[Dict[str, Any]]:
    """
    Compatibility wrapper for risk analysis.
    """

    return calculate_dataset_risks(
        dataframe,
        dataset_type,
    )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Dataset configuration
    "DASHBOARD_DATASET_TYPES",
    "DATASET_LABELS",
    "COLUMN_ALIASES",

    # General helpers
    "safe_dataframe",
    "prepare_dataframe",
    "normalize_column_name",
    "column_lookup",
    "find_column",
    "find_named_column",
    "numeric_series",
    "safe_float",
    "safe_int",
    "json_safe",

    # Date helpers
    "get_date_column",
    "prepare_date_dataframe",
    "get_date_bounds",
    "apply_date_range",

    # KPI helpers
    "make_kpi",
    "calculate_growth",
    "period_growth",

    # Chart helpers
    "build_chart",
    "grouped_chart",
    "time_series_chart",

    # Dataset calculations
    "calculate_sales_dashboard",
    "calculate_customer_dashboard",
    "calculate_product_dashboard",
    "calculate_regional_dashboard",
    "calculate_marketing_dashboard",
    "calculate_financial_dashboard",
    "calculate_returns_dashboard",
    "calculate_dataset_dashboard",

    # Intelligence
    "calculate_trend_direction",
    "detect_numeric_anomalies",
    "forecast_numeric_series",
    "generate_dataset_insights",
    "calculate_dataset_risks",

    # Executive dashboard
    "calculate_selected_dashboard",
    "calculate_overall_dashboard",
    "calculate_executive_dashboard",

    # Compatibility
    "calculate_dashboard_metrics",
    "calculate_dashboard_insights",
    "calculate_dashboard_forecast",
    "calculate_dashboard_risks",
]