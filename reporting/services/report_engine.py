from datetime import datetime

import numpy as np
import pandas as pd

from .dataset_service import load_reporting_dataset


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {
    "date": [
        "date",
        "order_date",
        "transaction_date",
        "invoice_date",
        "sale_date",
        "purchase_date",
        "created_at",
        "created_date",
    ],

    "sales": [
        "sales",
        "sale",
        "revenue",
        "total_sales",
        "sales_amount",
        "amount",
        "total_amount",
        "net_sales",
    ],

    "profit": [
        "profit",
        "gross_profit",
        "net_profit",
        "profit_amount",
    ],

    "cost": [
        "cost",
        "cost_amount",
        "total_cost",
        "expense",
        "expenses",
    ],

    "quantity": [
        "quantity",
        "qty",
        "units",
        "units_sold",
    ],

    "order": [
        "order",
        "order_id",
        "order_number",
        "invoice",
        "invoice_id",
        "transaction_id",
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

    "category": [
        "category",
        "product_category",
        "category_name",
        "segment",
    ],

    "region": [
        "region",
        "region_name",
        "state",
        "state_name",
        "country",
        "city",
        "location",
    ],

    "channel": [
        "channel",
        "sales_channel",
        "marketing_channel",
    ],

    "campaign": [
        "campaign",
        "campaign_name",
        "campaign_id",
    ],

    "spend": [
        "spend",
        "marketing_spend",
        "ad_spend",
        "advertising_spend",
        "cost",
    ],

    "conversions": [
        "conversions",
        "conversion",
        "converted",
    ],

    "return_amount": [
        "return_amount",
        "returns",
        "return_value",
        "refund",
        "refund_amount",
    ],

    "return_reason": [
        "return_reason",
        "reason",
        "return_type",
    ],

    "cash_flow": [
        "cash_flow",
        "cashflow",
        "net_cash_flow",
    ],
}


# ============================================================
# SAFE VALUE HELPERS
# ============================================================

def safe_float(value):
    """
    Convert a value to a JSON-safe float.
    """

    try:
        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return 0.0

        return round(value, 2)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def json_safe(value):
    """
    Convert pandas / numpy values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (
            np.integer,
            np.int64,
            np.int32,
        ),
    ):
        return int(value)

    if isinstance(
        value,
        (
            np.floating,
            np.float64,
            np.float32,
        ),
    ):
        return safe_float(value)

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
        ),
    ):
        return value.isoformat()

    if pd.isna(value):
        return None

    return value


# ============================================================
# COLUMN DETECTION
# ============================================================

def normalize_column_name(column):
    """
    Normalize a column name for comparison.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_column(dataframe, logical_name):
    """
    Find a real dataframe column using COLUMN_ALIASES.

    Returns the real column name or None.
    """

    if dataframe is None:
        return None

    columns = list(dataframe.columns)

    normalized_columns = {
        normalize_column_name(column): column
        for column in columns
    }

    aliases = COLUMN_ALIASES.get(
        logical_name,
        [],
    )

    for alias in aliases:
        normalized_alias = normalize_column_name(
            alias
        )

        if normalized_alias in normalized_columns:
            return normalized_columns[
                normalized_alias
            ]

    return None


# ============================================================
# DATASET SUMMARY
# ============================================================

def calculate_data_summary(dataframe):
    """
    Calculate structural information about the dataset.
    """

    if dataframe is None:
        return {
            "rows": 0,
            "columns": 0,
            "missing_values": 0,
            "duplicate_rows": 0,
            "numeric_columns": 0,
            "categorical_columns": 0,
            "datetime_columns": 0,
        }

    numeric_columns = dataframe.select_dtypes(
        include="number"
    ).columns

    datetime_columns = dataframe.select_dtypes(
        include=[
            "datetime",
            "datetimetz",
        ]
    ).columns

    categorical_columns = dataframe.select_dtypes(
        include=[
            "object",
            "category",
            "bool",
        ]
    ).columns

    return {
        "rows": int(
            len(dataframe)
        ),
        "columns": int(
            len(dataframe.columns)
        ),
        "missing_values": int(
            dataframe.isna().sum().sum()
        ),
        "duplicate_rows": int(
            dataframe.duplicated().sum()
        ),
        "numeric_columns": int(
            len(numeric_columns)
        ),
        "categorical_columns": int(
            len(categorical_columns)
        ),
        "datetime_columns": int(
            len(datetime_columns)
        ),
    }


# ============================================================
# KPI CREATION
# ============================================================

def make_kpi(
    name,
    value,
    label=None,
    format_type="number",
):
    """
    Create a standard KPI object.
    """

    return {
        "name": name,
        "value": json_safe(value),
        "label": label or name,
        "format": format_type,
    }


# ============================================================
# NUMERIC COLUMN SUMMARY
# ============================================================

def numeric_column_summary(dataframe):
    """
    Return summary information for numeric columns.
    """

    numeric_df = dataframe.select_dtypes(
        include="number"
    )

    result = []

    for column in numeric_df.columns:
        series = numeric_df[column]

        result.append(
            {
                "column": str(column),
                "count": int(
                    series.count()
                ),
                "sum": safe_float(
                    series.sum()
                ),
                "average": safe_float(
                    series.mean()
                ),
                "minimum": safe_float(
                    series.min()
                ),
                "maximum": safe_float(
                    series.max()
                ),
            }
        )

    return result


# ============================================================
# CATEGORICAL SUMMARY
# ============================================================

def categorical_column_summary(
    dataframe,
    limit=10,
):
    """
    Return the most common values for categorical columns.
    """

    categorical_df = dataframe.select_dtypes(
        include=[
            "object",
            "category",
            "bool",
        ]
    )

    result = []

    for column in categorical_df.columns:

        counts = (
            categorical_df[column]
            .value_counts(
                dropna=False
            )
            .head(limit)
        )

        values = []

        for value, count in counts.items():
            values.append(
                {
                    "value": json_safe(value),
                    "count": int(count),
                }
            )

        result.append(
            {
                "column": str(column),
                "values": values,
            }
        )

    return result


# ============================================================
# DATASET-SPECIFIC KPI GENERATION
# ============================================================

def generate_kpis(dataframe, dataset_type=None):
    """
    Generate general and dataset-aware KPIs.

    The function does not assume that every dataset contains
    every possible business column.
    """

    kpis = []

    # --------------------------------------------------------
    # General
    # --------------------------------------------------------

    kpis.append(
        make_kpi(
            "Total Records",
            len(dataframe),
            format_type="number",
        )
    )

    # --------------------------------------------------------
    # Sales
    # --------------------------------------------------------

    sales_column = find_column(
        dataframe,
        "sales",
    )

    if sales_column:
        sales_series = pd.to_numeric(
            dataframe[sales_column],
            errors="coerce",
        )

        total_sales = sales_series.sum()

        kpis.append(
            make_kpi(
                "Total Sales",
                total_sales,
                format_type="currency",
            )
        )

        kpis.append(
            make_kpi(
                "Average Sale",
                sales_series.mean(),
                format_type="currency",
            )
        )

    # --------------------------------------------------------
    # Profit
    # --------------------------------------------------------

    profit_column = find_column(
        dataframe,
        "profit",
    )

    if profit_column:
        profit_series = pd.to_numeric(
            dataframe[profit_column],
            errors="coerce",
        )

        kpis.append(
            make_kpi(
                "Total Profit",
                profit_series.sum(),
                format_type="currency",
            )
        )

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    quantity_column = find_column(
        dataframe,
        "quantity",
    )

    if quantity_column:
        quantity_series = pd.to_numeric(
            dataframe[quantity_column],
            errors="coerce",
        )

        kpis.append(
            make_kpi(
                "Total Units",
                quantity_series.sum(),
                format_type="number",
            )
        )

    # --------------------------------------------------------
    # Customers
    # --------------------------------------------------------

    customer_column = find_column(
        dataframe,
        "customer",
    )

    if customer_column:
        kpis.append(
            make_kpi(
                "Unique Customers",
                dataframe[
                    customer_column
                ].nunique(
                    dropna=True
                ),
                format_type="number",
            )
        )

    # --------------------------------------------------------
    # Products
    # --------------------------------------------------------

    product_column = find_column(
        dataframe,
        "product",
    )

    if product_column:
        kpis.append(
            make_kpi(
                "Unique Products",
                dataframe[
                    product_column
                ].nunique(
                    dropna=True
                ),
                format_type="number",
            )
        )

    # --------------------------------------------------------
    # Regions
    # --------------------------------------------------------

    region_column = find_column(
        dataframe,
        "region",
    )

    if region_column:
        kpis.append(
            make_kpi(
                "Regions",
                dataframe[
                    region_column
                ].nunique(
                    dropna=True
                ),
                format_type="number",
            )
        )

    # --------------------------------------------------------
    # Returns
    # --------------------------------------------------------

    return_column = find_column(
        dataframe,
        "return_amount",
    )

    if return_column:
        return_series = pd.to_numeric(
            dataframe[return_column],
            errors="coerce",
        )

        kpis.append(
            make_kpi(
                "Return Amount",
                return_series.sum(),
                format_type="currency",
            )
        )

    return kpis


# ============================================================
# TREND DATA
# ============================================================

def generate_trend_data(dataframe):
    """
    Generate a basic time-series dataset when both a date
    column and a sales/revenue column are available.
    """

    date_column = find_column(
        dataframe,
        "date",
    )

    sales_column = find_column(
        dataframe,
        "sales",
    )

    if not date_column or not sales_column:
        return []

    working_df = dataframe[
        [
            date_column,
            sales_column,
        ]
    ].copy()

    working_df[date_column] = pd.to_datetime(
        working_df[date_column],
        errors="coerce",
    )

    working_df[sales_column] = pd.to_numeric(
        working_df[sales_column],
        errors="coerce",
    )

    working_df = working_df.dropna(
        subset=[
            date_column,
            sales_column,
        ]
    )

    if working_df.empty:
        return []

    working_df["period"] = (
        working_df[date_column]
        .dt.to_period("M")
        .astype(str)
    )

    grouped = (
        working_df
        .groupby("period")[
            sales_column
        ]
        .sum()
        .reset_index()
    )

    return [
        {
            "period": str(row["period"]),
            "value": safe_float(
                row[sales_column]
            ),
        }
        for _, row in grouped.iterrows()
    ]


# ============================================================
# TOP DIMENSIONS
# ============================================================

def generate_dimension_tables(
    dataframe,
    limit=10,
):
    """
    Generate top-value tables for commonly useful dimensions.
    """

    tables = []

    dimensions = [
        (
            "Customer",
            "customer",
        ),
        (
            "Product",
            "product",
        ),
        (
            "Category",
            "category",
        ),
        (
            "Region",
            "region",
        ),
        (
            "Channel",
            "channel",
        ),
        (
            "Campaign",
            "campaign",
        ),
    ]

    sales_column = find_column(
        dataframe,
        "sales",
    )

    for title, logical_name in dimensions:

        dimension_column = find_column(
            dataframe,
            logical_name,
        )

        if not dimension_column:
            continue

        if sales_column:

            working_df = dataframe[
                [
                    dimension_column,
                    sales_column,
                ]
            ].copy()

            working_df[sales_column] = pd.to_numeric(
                working_df[sales_column],
                errors="coerce",
            )

            grouped = (
                working_df
                .groupby(
                    dimension_column,
                    dropna=False,
                )[sales_column]
                .sum()
                .sort_values(
                    ascending=False
                )
                .head(limit)
                .reset_index()
            )

            rows = []

            for _, row in grouped.iterrows():
                rows.append(
                    {
                        "dimension": json_safe(
                            row[dimension_column]
                        ),
                        "value": safe_float(
                            row[sales_column]
                        ),
                    }
                )

        else:

            counts = (
                dataframe[
                    dimension_column
                ]
                .value_counts(
                    dropna=False
                )
                .head(limit)
            )

            rows = [
                {
                    "dimension": json_safe(value),
                    "value": int(count),
                }
                for value, count
                in counts.items()
            ]

        tables.append(
            {
                "title": title,
                "column": dimension_column,
                "rows": rows,
            }
        )

    return tables


# ============================================================
# AUTOMATED REPORT
# ============================================================

def generate_automated_report(
    dataset,
    version=None,
):
    """
    Generate the standard automated report payload.

    This function reads the selected DatasetVersion and
    returns JSON-compatible report data.
    """

    loaded = load_reporting_dataset(
        dataset=dataset,
        version=version,
    )

    dataframe = loaded["dataframe"]

    dataset_obj = loaded["dataset"]
    version_obj = loaded["version"]

    summary = calculate_data_summary(
        dataframe
    )

    kpis = generate_kpis(
        dataframe,
        dataset_type=getattr(
            dataset_obj,
            "dataset_type",
            None,
        ),
    )

    trend_data = generate_trend_data(
        dataframe
    )

    dimension_tables = (
        generate_dimension_tables(
            dataframe
        )
    )

    return {
        "dataset": {
            "id": dataset_obj.id,
            "name": dataset_obj.name,
            "type": dataset_obj.dataset_type,
        },

        "version": {
            "id": version_obj.id,
            "number": version_obj.version_number,
            "type": version_obj.version_type,
            "file_name": (
                version_obj.file_name
                or version_obj.file.name
                or ""
            ),
        },

        "summary": summary,

        "kpis": kpis,

        "trends": trend_data,

        "dimension_tables": dimension_tables,

        "numeric_columns": (
            numeric_column_summary(
                dataframe
            )
        ),

        "categorical_columns": (
            categorical_column_summary(
                dataframe
            )
        ),

        "generated_at": (
            datetime.utcnow().isoformat()
        ),
    }