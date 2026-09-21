from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.metrics.business_metrics import (
    calculate_business_chart_data,
    calculate_business_metrics,
    generate_business_insights,
)

from analytics.metrics.sales_metrics import (
    calculate_sales_growth,
    calculate_sales_metrics,
    prepare_sales_dataframe,
    sales_trend,
    sales_by_category,
    top_products,
)

from analytics.metrics.customer_metrics import (
    calculate_customer_metrics,
    prepare_customer_dataframe,
    customer_registration_trend,
    customers_by_region,
    customers_by_segment,
)

from analytics.metrics.product_metrics import (
    calculate_product_metrics,
    product_sales_trend,
    sales_by_category as product_sales_by_category,
    sales_by_product,
)

from analytics.metrics.regional_metrics import (
    calculate_regional_growth,
    calculate_regional_metrics,
    regional_sales_trend,
    sales_by_region,
    units_by_region,
)

from analytics.metrics.marketing_metrics import (
    calculate_marketing_growth,
    calculate_marketing_metrics,
    marketing_sales_trend,
    sales_by_campaign,
    channel_performance,
)

from analytics.metrics.financial_metrics import (
    calculate_financial_metrics,
)

from analytics.metrics.returns_metrics import (
    calculate_returns_growth,
    calculate_returns_metrics,
    returns_trend,
    returns_by_reason,
    returns_by_product,
)

from analytics.services.dataset_resolver import (
    get_user_datasets,
    resolve_dataset,
)

from analytics.services.date_filter import (
    apply_date_filter,
    find_date_column,
)


# =====================================================================
# LOGGER
# =====================================================================

logger = logging.getLogger(__name__)


# =====================================================================
# DATE RANGE CONFIGURATION
# =====================================================================

DATE_RANGE_OPTIONS = [
    ("all", "All Time"),
    ("7d", "Last 7 Days"),
    ("30d", "Last 30 Days"),
    ("3m", "Last 3 Months"),
    ("6m", "Last 6 Months"),
    ("12m", "Last 12 Months"),
    ("custom", "Custom Range"),
]


# =====================================================================
# DATASET CONFIGURATION
# =====================================================================

BUSINESS_DATASET_TYPES = [
    "Sales",
    "Customers",
    "Products",
    "Regional",
    "Marketing",
    "Financial",
    "Returns",
]


# =====================================================================
# REQUEST PARAMETER CONFIGURATION
# =====================================================================

DATASET_PARAMETER_MAP = {
    "Sales": {
        "multiple": "sales_dataset_ids",
        "single": "sales_dataset_id",
    },
    "Customers": {
        "multiple": "customer_dataset_ids",
        "single": "customer_dataset_id",
    },
    "Products": {
        "multiple": "product_dataset_ids",
        "single": "product_dataset_id",
    },
    "Regional": {
        "multiple": "regional_dataset_ids",
        "single": "regional_dataset_id",
    },
    "Marketing": {
        "multiple": "marketing_dataset_ids",
        "single": "marketing_dataset_id",
    },
    "Financial": {
        "multiple": "financial_dataset_ids",
        "single": "financial_dataset_id",
    },
    "Returns": {
        "multiple": "returns_dataset_ids",
        "single": "returns_dataset_id",
    },
}


# =====================================================================
# COLUMN HELPERS
# =====================================================================

FINANCIAL_COLUMN_ALIASES = {
    "date": [
        "Date",
        "Transaction_Date",
        "Financial_Date",
    ],
    "revenue": [
        "Revenue",
        "Sales",
        "Sales_Amount",
        "Revenue_Amount",
    ],
    "cost": [
        "Cost",
        "Total_Cost",
        "Cost_Amount",
    ],
    "profit": [
        "Profit",
        "Profit_Amount",
        "Gross_Profit",
        "Net_Profit",
    ],
    "expense": [
        "Expenses",
        "Expense",
        "Operating_Expenses",
    ],
    "cash_inflow": [
        "Cash_Inflow",
        "Cash_In",
        "Cash_Income",
    ],
    "cash_outflow": [
        "Cash_Outflow",
        "Cash_Out",
        "Cash_Expense",
    ],
    "category": [
        "Category",
        "Account",
        "Transaction_Category",
    ],
}


def normalize_column_name(column):
    """
    Normalize a dataframe column name.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_column(dataframe, candidates):
    """
    Find the first matching dataframe column from aliases.
    """

    if dataframe is None:
        return None

    try:
        columns = dataframe.columns
    except AttributeError:
        return None

    normalized = {
        normalize_column_name(column): column
        for column in columns
    }

    for candidate in candidates:
        actual = normalized.get(
            normalize_column_name(candidate)
        )

        if actual is not None:
            return actual

    return None


def get_financial_column(dataframe, field_name):
    return find_column(
        dataframe,
        FINANCIAL_COLUMN_ALIASES.get(
            field_name,
            [],
        ),
    )


def numeric_series(dataframe, column):
    """
    Safely convert a dataframe column to numeric.
    """

    if dataframe is None or column is None:
        return None

    try:
        return pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )
    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None


# =====================================================================
# JSON HELPERS
# =====================================================================

def json_safe(value: Any) -> Any:
    """
    Convert pandas / Decimal / datetime / numpy values into
    JSON-safe Python values.
    """

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
            date,
        ),
    ):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (
            ValueError,
            TypeError,
        ):
            pass

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    return value


def json_dumps(value: Any) -> str:
    return json.dumps(
        json_safe(value),
        ensure_ascii=False,
    )


# =====================================================================
# DATE HELPERS
# =====================================================================

def get_business_date_column(
    dataframe,
    dataset_type,
):
    """
    Resolve the appropriate date column.
    """

    if dataframe is None:
        return None

    try:
        return find_date_column(
            dataframe,
            dataset_type,
        )
    except Exception:
        return None


def get_available_business_date_range(
    dataframe,
    dataset_type,
):
    """
    Return minimum and maximum valid dates from one selected dataset.
    """

    if dataframe is None:
        return None, None

    try:
        if dataframe.empty:
            return None, None
    except AttributeError:
        return None, None

    date_column = get_business_date_column(
        dataframe,
        dataset_type,
    )

    if date_column is None:
        return None, None

    try:
        dates = pd.to_datetime(
            dataframe[date_column],
            errors="coerce",
            dayfirst=True,
        ).dropna()
    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None, None

    if dates.empty:
        return None, None

    return (
        dates.min().date(),
        dates.max().date(),
    )


def calculate_preset_dates(
    latest_date,
    selected_range,
):
    """
    Calculate the date range represented by a preset.
    """

    if latest_date is None:
        return None, None

    if selected_range == "all":
        return None, latest_date

    if selected_range == "7d":
        return (
            latest_date - timedelta(days=6),
            latest_date,
        )

    if selected_range == "30d":
        return (
            latest_date - timedelta(days=29),
            latest_date,
        )

    if selected_range == "3m":
        return (
            latest_date - pd.DateOffset(months=3)
        ).date(), latest_date

    if selected_range == "6m":
        return (
            latest_date - pd.DateOffset(months=6)
        ).date(), latest_date

    if selected_range == "12m":
        return (
            latest_date - pd.DateOffset(months=12)
        ).date(), latest_date

    return None, latest_date


def resolve_custom_dates(request):
    """
    Read and safely parse custom dates.
    """

    from_date = (
        request.GET.get("from_date")
        or None
    )

    to_date = (
        request.GET.get("to_date")
        or None
    )

    parsed_from = None
    parsed_to = None

    if from_date:

        parsed_from = pd.to_datetime(
            from_date,
            errors="coerce",
            dayfirst=True,
        )

        if pd.notna(parsed_from):
            parsed_from = parsed_from.date()
        else:
            parsed_from = None

    if to_date:

        parsed_to = pd.to_datetime(
            to_date,
            errors="coerce",
            dayfirst=True,
        )

        if pd.notna(parsed_to):
            parsed_to = parsed_to.date()
        else:
            parsed_to = None

    if (
        parsed_from is not None
        and parsed_to is not None
        and parsed_from > parsed_to
    ):
        parsed_from, parsed_to = (
            parsed_to,
            parsed_from,
        )

    return (
        parsed_from,
        parsed_to,
    )


# =====================================================================
# SINGLE DATASET SELECTION
# =====================================================================

def get_requested_dataset_ids(
    request,
    dataset_type,
):
    """
    Return at most ONE requested dataset ID.

    Singular parameter is primary.

    Legacy multiple parameters are supported only for compatibility,
    but only their first valid ID is accepted.
    """

    parameter_config = DATASET_PARAMETER_MAP.get(
        dataset_type
    )

    if not parameter_config:
        return []

    single_parameter = (
        parameter_config["single"]
    )

    multiple_parameter = (
        parameter_config["multiple"]
    )

    # -------------------------------------------------------------
    # Singular parameter.
    # -------------------------------------------------------------

    raw_single = request.GET.get(
        single_parameter
    )

    if raw_single:

        for value in str(
            raw_single
        ).split(","):

            value = value.strip()

            if not value:
                continue

            try:
                dataset_id = int(value)
            except (
                TypeError,
                ValueError,
            ):
                continue

            if dataset_id > 0:
                return [dataset_id]

    # -------------------------------------------------------------
    # Legacy multiple parameter.
    # -------------------------------------------------------------

    raw_values = request.GET.getlist(
        multiple_parameter
    )

    for raw_value in raw_values:

        if raw_value is None:
            continue

        for value in str(
            raw_value
        ).split(","):

            value = value.strip()

            if not value:
                continue

            try:
                dataset_id = int(value)
            except (
                TypeError,
                ValueError,
            ):
                continue

            if dataset_id > 0:
                return [dataset_id]

    return []


def get_requested_dataset_id(
    request,
    dataset_type,
):
    """
    Return one requested dataset ID or None.
    """

    dataset_ids = get_requested_dataset_ids(
        request,
        dataset_type,
    )

    if not dataset_ids:
        return None

    return dataset_ids[0]


def get_selected_dataset_id(
    request,
    dataset_type,
    available_queryset,
):
    """
    Resolve exactly ONE owner-safe selected dataset ID.

    Explicit valid selection wins.

    If there is no valid selection, newest active owner-safe
    dataset is selected automatically.
    """

    if available_queryset is None:
        return None

    requested_id = get_requested_dataset_id(
        request,
        dataset_type,
    )

    if requested_id is not None:

        try:
            exists = (
                available_queryset
                .filter(
                    id=requested_id
                )
                .exists()
            )

        except AttributeError:

            exists = any(
                getattr(
                    dataset,
                    "id",
                    None,
                ) == requested_id
                for dataset in available_queryset
            )

        if exists:
            return requested_id

    # -------------------------------------------------------------
    # Automatic newest dataset.
    # -------------------------------------------------------------

    try:
        newest_dataset = (
            available_queryset
            .order_by(
                "-uploaded_at",
                "-id",
            )
            .first()
        )

    except AttributeError:
        newest_dataset = None

    if newest_dataset is not None:
        return newest_dataset.id

    return None


# =====================================================================
# DATASET RESOLUTION
# =====================================================================

def resolve_business_dataset(
    user,
    dataset_type,
    dataset_id=None,
):
    """
    Resolve exactly ONE dataset through the central resolver.

    The returned object contains the current DatasetVersion.
    """

    if dataset_id is None:
        return None

    try:

        resolved = resolve_dataset(
            user=user,
            dataset_type=dataset_type,
            dataset_id=dataset_id,
        )

    except Exception:

        logger.exception(
            "Failed to resolve %s dataset id=%s for user id=%s",
            dataset_type,
            dataset_id,
            getattr(user, "id", None),
        )

        return None

    if resolved is None:
        return None

    return {
        "dataset": resolved.dataset,
        "version": resolved.version,
        "dataframe": resolved.dataframe,
    }


# =====================================================================
# DATASET STATUS BUILDER
# =====================================================================

def build_dataset_status(
    dataset_type,
    dataset=None,
    version=None,
    dataframe=None,
    available=True,
    message="Available",
    selected_id=None,
):
    """
    Build the complete dataset status object consumed by the
    Business Intelligence template.

    IMPORTANT:

    The template should use:

        source.dataset
        source.version
        source.rows
        source.columns
        source.version_type

    rather than attempting to get version information from
    Dataset objects inside source.datasets.
    """

    if dataset is None:

        return {
            "available": False,

            "selected": False,

            "message": message,

            "dataset": None,
            "version": None,
            "dataframe": None,

            "dataset_name": None,

            "selected_id": selected_id,

            "selected_ids": (
                [selected_id]
                if selected_id is not None
                else []
            ),

            "version_id": None,

            "version_number": None,

            "version_type": None,

            "version_type_display": None,

            "rows": 0,

            "columns": 0,

            "column_names": [],

            "file_name": None,

            # Compatibility fields.
            "datasets": [],
            "versions": [],

            "count": 0,
        }

    # -------------------------------------------------------------
    # Dataframe information.
    # -------------------------------------------------------------

    rows = 0
    columns_count = 0
    column_names = []

    if dataframe is not None:

        try:
            rows = int(
                len(dataframe.index)
            )
        except Exception:
            rows = 0

        try:
            columns_count = int(
                len(dataframe.columns)
            )
        except Exception:
            columns_count = 0

        try:
            column_names = [
                str(column)
                for column in dataframe.columns
            ]
        except Exception:
            column_names = []

    # -------------------------------------------------------------
    # Version information.
    # -------------------------------------------------------------

    version_number = getattr(
        version,
        "version_number",
        None,
    )

    version_type = getattr(
        version,
        "version_type",
        None,
    )

    version_type_display = None

    if version is not None:

        try:
            version_type_display = (
                version.get_version_type_display()
            )
        except Exception:

            version_type_display = (
                str(version_type)
                if version_type is not None
                else None
            )

    file_name = None

    if version is not None:

        try:
            if version.file:
                file_name = (
                    version.file.name
                )
        except Exception:
            file_name = None

    dataset_name = getattr(
        dataset,
        "name",
        None,
    )

    dataset_id = getattr(
        dataset,
        "id",
        selected_id,
    )

    version_id = getattr(
        version,
        "id",
        None,
    )

    return {
        "available": bool(available),

        "selected": True,

        "message": message,

        "dataset": dataset,

        "version": version,

        # Do NOT send dataframe to the template unless needed.
        "dataframe": None,

        "dataset_name": dataset_name,

        "selected_id": dataset_id,

        "selected_ids": [dataset_id],

        "version_id": version_id,

        "version_number": version_number,

        "version_type": version_type,

        "version_type_display": (
            version_type_display
        ),

        "rows": rows,

        "columns": columns_count,

        "column_names": column_names,

        "file_name": file_name,

        # Compatibility fields.
        "datasets": [dataset],

        "versions": [version],

        "count": 1,

        "dataset_type": dataset_type,
    }


# =====================================================================
# FINANCIAL CHART BUILDERS
# =====================================================================

def build_financial_revenue_trend(
    dataframe,
):
    """
    Build daily financial revenue trend.
    """

    if dataframe is None:
        return []

    try:
        if dataframe.empty:
            return []
    except AttributeError:
        return []

    date_column = get_financial_column(
        dataframe,
        "date",
    )

    revenue_column = get_financial_column(
        dataframe,
        "revenue",
    )

    if not date_column or not revenue_column:
        return []

    work = dataframe.copy()

    work["_business_date"] = pd.to_datetime(
        work[date_column],
        errors="coerce",
        dayfirst=True,
    )

    work["_business_revenue"] = pd.to_numeric(
        work[revenue_column],
        errors="coerce",
    )

    work = work.dropna(
        subset=[
            "_business_date",
            "_business_revenue",
        ]
    )

    if work.empty:
        return []

    grouped = (
        work
        .groupby(
            work["_business_date"].dt.date
        )["_business_revenue"]
        .sum()
        .reset_index()
    )

    return [
        {
            "date": row["_business_date"].isoformat(),
            "revenue": float(
                row["_business_revenue"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


def build_financial_revenue_vs_cost(
    dataframe,
):
    """
    Build daily revenue versus cost.
    """

    if dataframe is None:
        return []

    try:
        if dataframe.empty:
            return []
    except AttributeError:
        return []

    date_column = get_financial_column(
        dataframe,
        "date",
    )

    revenue_column = get_financial_column(
        dataframe,
        "revenue",
    )

    cost_column = get_financial_column(
        dataframe,
        "cost",
    )

    if not date_column:
        return []

    if (
        not revenue_column
        and not cost_column
    ):
        return []

    work = dataframe.copy()

    work["_business_date"] = pd.to_datetime(
        work[date_column],
        errors="coerce",
        dayfirst=True,
    )

    if revenue_column:

        work["_business_revenue"] = (
            pd.to_numeric(
                work[revenue_column],
                errors="coerce",
            )
        )

    else:

        work["_business_revenue"] = 0.0

    if cost_column:

        work["_business_cost"] = (
            pd.to_numeric(
                work[cost_column],
                errors="coerce",
            )
        )

    else:

        work["_business_cost"] = 0.0

    work = work.dropna(
        subset=[
            "_business_date",
        ]
    )

    if work.empty:
        return []

    grouped = (
        work
        .groupby(
            work["_business_date"].dt.date
        )[
            [
                "_business_revenue",
                "_business_cost",
            ]
        ]
        .sum()
        .reset_index()
    )

    return [
        {
            "date": row["_business_date"].isoformat(),
            "revenue": float(
                row["_business_revenue"]
            ),
            "cost": float(
                row["_business_cost"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


def build_financial_profit_by_category(
    dataframe,
):
    """
    Build profit grouped by financial category.
    """

    if dataframe is None:
        return []

    try:
        if dataframe.empty:
            return []
    except AttributeError:
        return []

    category_column = get_financial_column(
        dataframe,
        "category",
    )

    profit_column = get_financial_column(
        dataframe,
        "profit",
    )

    if (
        not category_column
        or not profit_column
    ):
        return []

    work = dataframe.copy()

    work["_business_profit"] = pd.to_numeric(
        work[profit_column],
        errors="coerce",
    )

    work = work.dropna(
        subset=[
            category_column,
            "_business_profit",
        ]
    )

    if work.empty:
        return []

    grouped = (
        work
        .groupby(
            category_column
        )["_business_profit"]
        .sum()
        .reset_index()
        .sort_values(
            "_business_profit",
            ascending=False,
        )
    )

    return [
        {
            "category": str(
                row[category_column]
            ),
            "profit": float(
                row["_business_profit"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


def build_financial_cash_flow(
    dataframe,
):
    """
    Build daily cash inflow/outflow trend.
    """

    if dataframe is None:
        return []

    try:
        if dataframe.empty:
            return []
    except AttributeError:
        return []

    date_column = get_financial_column(
        dataframe,
        "date",
    )

    inflow_column = get_financial_column(
        dataframe,
        "cash_inflow",
    )

    outflow_column = get_financial_column(
        dataframe,
        "cash_outflow",
    )

    if not date_column:
        return []

    if (
        not inflow_column
        and not outflow_column
    ):
        return []

    work = dataframe.copy()

    work["_business_date"] = pd.to_datetime(
        work[date_column],
        errors="coerce",
        dayfirst=True,
    )

    if inflow_column:

        work["_business_inflow"] = (
            pd.to_numeric(
                work[inflow_column],
                errors="coerce",
            )
        )

    else:

        work["_business_inflow"] = 0.0

    if outflow_column:

        work["_business_outflow"] = (
            pd.to_numeric(
                work[outflow_column],
                errors="coerce",
            )
        )

    else:

        work["_business_outflow"] = 0.0

    work = work.dropna(
        subset=[
            "_business_date",
        ]
    )

    if work.empty:
        return []

    grouped = (
        work
        .groupby(
            work["_business_date"].dt.date
        )[
            [
                "_business_inflow",
                "_business_outflow",
            ]
        ]
        .sum()
        .reset_index()
    )

    return [
        {
            "date": row["_business_date"].isoformat(),
            "cash_inflow": float(
                row["_business_inflow"]
            ),
            "cash_outflow": float(
                row["_business_outflow"]
            ),
            "net_cash_flow": float(
                row["_business_inflow"]
                - row["_business_outflow"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


# =====================================================================
# INDIVIDUAL ANALYTICS RESULT BUILDERS
# =====================================================================

def build_sales_result(
    dataframe,
    from_date=None,
    to_date=None,
):
    """
    Build exactly ONE Sales analytics result.

    Sales metrics and charts use the column mapping returned by
    prepare_sales_dataframe().
    """

    (
        prepared_dataframe,
        columns,
        missing_core_columns,
        missing_optional_columns,
    ) = prepare_sales_dataframe(
        dataframe
    )

    (
        filtered_dataframe,
        date_metadata,
    ) = apply_date_filter(
        prepared_dataframe,
        "Sales",
        from_date,
        to_date,
    )

    metrics = calculate_sales_metrics(
        filtered_dataframe,
        columns,
    )

    growth = calculate_sales_growth(
        filtered_dataframe,
        prepared_dataframe,
        columns,
        from_date,
        to_date,
    )

    if isinstance(metrics, dict):
        metrics["sales_growth"] = growth

    chart_data = {
        "sales_trend": sales_trend(
            filtered_dataframe,
            columns,
        ),

        "sales_by_category": sales_by_category(
            filtered_dataframe,
            columns,
        ),

        "top_products": top_products(
            filtered_dataframe,
            columns,
        ),
    }

    dataframe_available = (
        filtered_dataframe is not None
        and not filtered_dataframe.empty
        and not missing_core_columns
    )

    return {
        "metrics": metrics,

        "chart_data": chart_data,

        "date_metadata": date_metadata,

        "dataframe_available": (
            dataframe_available
        ),

        "missing_core_columns": (
            missing_core_columns
        ),

        "missing_optional_columns": (
            missing_optional_columns
        ),

        "columns": columns,
    }


def build_customer_result(
    dataframe,
    from_date=None,
    to_date=None,
):
    """
    Build exactly ONE Customer analytics result.

    Customer metrics and charts use the column mapping returned by
    prepare_customer_dataframe().
    """

    (
        prepared_dataframe,
        columns,
        missing_required,
    ) = prepare_customer_dataframe(
        dataframe
    )

    (
        filtered_dataframe,
        date_metadata,
    ) = apply_date_filter(
        prepared_dataframe,
        "Customers",
        from_date,
        to_date,
    )

    metrics = calculate_customer_metrics(
        filtered_dataframe,
        columns,
    )

    chart_data = {
        "registration_trend": (
            customer_registration_trend(
                filtered_dataframe,
                columns,
            )
        ),

        "customers_by_region": (
            customers_by_region(
                filtered_dataframe,
                columns,
            )
        ),

        "customers_by_segment": (
            customers_by_segment(
                filtered_dataframe,
                columns,
            )
        ),
    }

    dataframe_available = (
        filtered_dataframe is not None
        and not filtered_dataframe.empty
        and not missing_required
    )

    return {
        "metrics": metrics,

        "chart_data": chart_data,

        "date_metadata": date_metadata,

        "dataframe_available": (
            dataframe_available
        ),

        "missing_required_columns": (
            missing_required
        ),

        "columns": columns,
    }

def build_product_result(
    dataframe,
    from_date=None,
    to_date=None,
):
    """
    Build exactly ONE Product analytics result.
    """

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe,
            "Products",
            from_date,
            to_date,
        )
    )

    metrics = calculate_product_metrics(
        filtered_dataframe
    )

    chart_data = {
        "product_sales_trend": (
            product_sales_trend(
                filtered_dataframe
            )
        ),

        "sales_by_category": (
            product_sales_by_category(
                filtered_dataframe
            )
        ),

        "sales_by_product": (
            sales_by_product(
                filtered_dataframe
            )
        ),
    }

    if isinstance(metrics, dict):

        if (
            metrics.get("total_products")
            is None
            and metrics.get("product_count")
            is not None
        ):

            metrics["total_products"] = (
                metrics.get("product_count")
            )

    return {
        "metrics": metrics,

        "chart_data": chart_data,

        "date_metadata": date_metadata,

        "dataframe_available": (
            filtered_dataframe is not None
            and not filtered_dataframe.empty
        ),
    }


def build_regional_result(
    dataframe,
    from_date=None,
    to_date=None,
):
    """
    Build exactly ONE Regional analytics result.
    """

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe,
            "Regional",
            from_date,
            to_date,
        )
    )

    metrics = calculate_regional_metrics(
        filtered_dataframe
    )

    growth = calculate_regional_growth(
        dataframe,
        from_date,
        to_date,
    )

    if isinstance(metrics, dict):
        metrics["regional_growth"] = growth

    chart_data = {
        "sales_trend": regional_sales_trend(
            filtered_dataframe
        ),

        "sales_by_region": sales_by_region(
            filtered_dataframe
        ),

        "units_by_region": units_by_region(
            filtered_dataframe
        ),
    }

    return {
        "metrics": metrics,

        "chart_data": chart_data,

        "date_metadata": date_metadata,

        "dataframe_available": (
            filtered_dataframe is not None
            and not filtered_dataframe.empty
        ),
    }


def build_marketing_result(
    dataframe,
    from_date=None,
    to_date=None,
):
    """
    Build exactly ONE Marketing analytics result.
    """

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe,
            "Marketing",
            from_date,
            to_date,
        )
    )

    metrics = calculate_marketing_metrics(
        filtered_dataframe
    )

    growth = calculate_marketing_growth(
        dataframe,
        from_date,
        to_date,
    )

    if isinstance(metrics, dict):
        metrics["marketing_growth"] = growth

    chart_data = {
        "sales_trend": marketing_sales_trend(
            filtered_dataframe
        ),

        "sales_by_campaign": sales_by_campaign(
            filtered_dataframe
        ),

        "channel_performance": (
            channel_performance(
                filtered_dataframe
            )
        ),
    }

    return {
        "metrics": metrics,

        "chart_data": chart_data,

        "date_metadata": date_metadata,

        "dataframe_available": (
            filtered_dataframe is not None
            and not filtered_dataframe.empty
        ),
    }


def build_financial_result(
    dataframe,
    from_date=None,
    to_date=None,
):
    """
    Build exactly ONE Financial analytics result.
    """

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe,
            "Financial",
            from_date,
            to_date,
        )
    )

    metrics = calculate_financial_metrics(
        filtered_dataframe
    )

    chart_data = {
        "revenue_trend": (
            build_financial_revenue_trend(
                filtered_dataframe
            )
        ),

        "revenue_vs_cost": (
            build_financial_revenue_vs_cost(
                filtered_dataframe
            )
        ),

        "profit_by_category": (
            build_financial_profit_by_category(
                filtered_dataframe
            )
        ),

        "cash_flow_trend": (
            build_financial_cash_flow(
                filtered_dataframe
            )
        ),
    }

    return {
        "metrics": metrics,

        "chart_data": chart_data,

        "date_metadata": date_metadata,

        "dataframe_available": (
            filtered_dataframe is not None
            and not filtered_dataframe.empty
        ),
    }


def build_returns_result(
    dataframe,
    from_date=None,
    to_date=None,
):
    """
    Build exactly ONE Returns analytics result.
    """

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe,
            "Returns",
            from_date,
            to_date,
        )
    )

    metrics = calculate_returns_metrics(
        filtered_dataframe
    )

    growth = calculate_returns_growth(
        dataframe,
        from_date,
        to_date,
    )

    if isinstance(metrics, dict):
        metrics["return_growth"] = growth

    chart_data = {
        "returns_trend": returns_trend(
            filtered_dataframe
        ),

        "returns_by_reason": returns_by_reason(
            filtered_dataframe
        ),

        "returns_by_product": returns_by_product(
            filtered_dataframe
        ),
    }

    return {
        "metrics": metrics,

        "chart_data": chart_data,

        "date_metadata": date_metadata,

        "dataframe_available": (
            filtered_dataframe is not None
            and not filtered_dataframe.empty
        ),
    }


# =====================================================================
# RESULT BUILDER REGISTRY
# =====================================================================

RESULT_BUILDERS = {
    "Sales": build_sales_result,
    "Customers": build_customer_result,
    "Products": build_product_result,
    "Regional": build_regional_result,
    "Marketing": build_marketing_result,
    "Financial": build_financial_result,
    "Returns": build_returns_result,
}


# =====================================================================
# DEFAULT BUSINESS CHART KEYS
# =====================================================================

DEFAULT_BUSINESS_CHART_KEYS = [
    "sales_trend",
    "revenue_trend",
    "sales_by_region",
    "units_by_region",
    "sales_by_category",
    "top_products",
    "customer_segments",
    "customer_regions",
    "marketing_performance",
    "marketing_campaigns",
    "financial_trend",
    "profit_by_category",
    "cash_flow",
    "returns_trend",
    "returns_by_reason",
    "returns_by_product",
]


# =====================================================================
# MAIN BUSINESS INTELLIGENCE VIEW
# =====================================================================

@login_required
def business_intelligence(request):
    """
    Consolidated Business Intelligence dashboard.

    ARCHITECTURE
    ------------

    Exactly ONE dataset is selected per category.

    Example:

        Sales       -> Sales Final
        Customers   -> Customers Final
        Products    -> Products Final
        Regional    -> Regional Final
        Marketing   -> Marketing Final
        Financial   -> Financial Final
        Returns     -> Returns Final

    Same-category datasets are NEVER aggregated.

    Different categories are NEVER concatenated.

    Each selected dataset is resolved through the central resolver,
    which returns its current DatasetVersion.
    """

    # =================================================================
    # INITIAL CONTEXT
    # =================================================================

    context = {
        "business_dataset_types": (
            BUSINESS_DATASET_TYPES
        ),

        "dataset_parameter_map": (
            DATASET_PARAMETER_MAP
        ),

        "dataset_selections": {},

        "selected_dataset_ids": {},

        "selected_datasets": {},

        "selected_versions": {},

        "selected_range": "all",

        "date_range_options": (
            DATE_RANGE_OPTIONS
        ),

        "analysis_from_date": None,

        "analysis_to_date": None,

        "available_from_date": None,

        "available_to_date": None,

        "dataset_status": {},

        "metrics": {},

        "metric_sources": {},

        "chart_data": {
            key: []
            for key in DEFAULT_BUSINESS_CHART_KEYS
        },

        "sales_trend_json": "[]",

        "revenue_trend_json": "[]",

        "sales_by_region_json": "[]",

        "units_by_region_json": "[]",

        "sales_by_category_json": "[]",

        "top_products_json": "[]",

        "customer_segments_json": "[]",

        "customer_regions_json": "[]",

        "marketing_performance_json": "[]",

        "marketing_campaigns_json": "[]",

        "financial_trend_json": "[]",

        "profit_by_category_json": "[]",

        "cash_flow_json": "[]",

        "returns_trend_json": "[]",

        "returns_by_reason_json": "[]",

        "returns_by_product_json": "[]",

        "insights": [],

        "unavailable_charts": [],

        "available_dataset_count": 0,

        "available_dataset_types": [],

        "selected_dataset_count_by_type": {},

        "total_selected_dataset_count": 0,

        "error": None,

        "warning": None,
    }

    # =================================================================
    # DATE RANGE
    # =================================================================

    selected_range = (
        request.GET.get("range")
        or request.GET.get("date_range")
        or "all"
    )

    valid_ranges = {
        item[0]
        for item in DATE_RANGE_OPTIONS
    }

    if selected_range not in valid_ranges:
        selected_range = "all"

    context["selected_range"] = (
        selected_range
    )

    # =================================================================
    # LOAD OWNER-SAFE DATASETS
    # =================================================================

    dataset_lists = {}

    for dataset_type in BUSINESS_DATASET_TYPES:

        try:

            dataset_lists[dataset_type] = (
                get_user_datasets(
                    user=request.user,
                    dataset_type=dataset_type,
                )
            )

        except Exception:

            logger.exception(
                "Unable to load %s datasets for user id=%s",
                dataset_type,
                getattr(
                    request.user,
                    "id",
                    None,
                ),
            )

            dataset_lists[dataset_type] = []

            message = (
                f"Unable to load "
                f"{dataset_type} datasets."
            )

            if context["warning"]:

                context["warning"] += (
                    f" {message}"
                )

            else:

                context["warning"] = (
                    message
                )

    context["dataset_selections"] = (
        dataset_lists
    )

    # =================================================================
    # RESOLVE EXACTLY ONE DATASET PER CATEGORY
    # =================================================================

    resolved_datasets = {}

    for dataset_type in BUSINESS_DATASET_TYPES:

        queryset = dataset_lists.get(
            dataset_type
        )

        try:

            queryset_exists = (
                queryset.exists()
            )

        except AttributeError:

            queryset_exists = bool(
                queryset
            )

        # -------------------------------------------------------------
        # No dataset exists for this category.
        # -------------------------------------------------------------

        if not queryset_exists:

            message = (
                "Not available — "
                f"{dataset_type} dataset required."
            )

            context[
                "dataset_status"
            ][dataset_type] = (
                build_dataset_status(
                    dataset_type=dataset_type,
                    available=False,
                    message=message,
                    selected_id=None,
                )
            )

            context[
                "selected_dataset_ids"
            ][dataset_type] = None

            context[
                "selected_datasets"
            ][dataset_type] = None

            context[
                "selected_versions"
            ][dataset_type] = None

            continue

        # -------------------------------------------------------------
        # Select exactly ONE dataset.
        # -------------------------------------------------------------

        selected_id = (
            get_selected_dataset_id(
                request=request,
                dataset_type=dataset_type,
                available_queryset=queryset,
            )
        )

        context[
            "selected_dataset_ids"
        ][dataset_type] = selected_id

        # -------------------------------------------------------------
        # Resolve exactly ONE dataset.
        # -------------------------------------------------------------

        resolved = (
            resolve_business_dataset(
                user=request.user,
                dataset_type=dataset_type,
                dataset_id=selected_id,
            )
        )

        # -------------------------------------------------------------
        # Secure fallback to newest owner-safe dataset.
        # -------------------------------------------------------------

        if resolved is None:

            try:

                newest_dataset = (
                    queryset
                    .order_by(
                        "-uploaded_at",
                        "-id",
                    )
                    .first()
                )

            except AttributeError:

                newest_dataset = None

            if newest_dataset is not None:

                selected_id = (
                    newest_dataset.id
                )

                resolved = (
                    resolve_business_dataset(
                        user=request.user,
                        dataset_type=dataset_type,
                        dataset_id=selected_id,
                    )
                )

                if resolved is not None:

                    context[
                        "selected_dataset_ids"
                    ][dataset_type] = (
                        selected_id
                    )

        # -------------------------------------------------------------
        # Dataset could not be resolved.
        # -------------------------------------------------------------

        if resolved is None:

            message = (
                "Not available — "
                f"{dataset_type} dataset version required."
            )

            context[
                "dataset_status"
            ][dataset_type] = (
                build_dataset_status(
                    dataset_type=dataset_type,
                    available=False,
                    message=message,
                    selected_id=selected_id,
                )
            )

            context[
                "selected_datasets"
            ][dataset_type] = None

            context[
                "selected_versions"
            ][dataset_type] = None

            continue

        # -------------------------------------------------------------
        # Store exactly ONE resolved dataset.
        # -------------------------------------------------------------

        resolved_datasets[
            dataset_type
        ] = resolved

        dataset = resolved["dataset"]

        version = resolved["version"]

        dataframe = resolved["dataframe"]

        context[
            "selected_datasets"
        ][dataset_type] = dataset

        context[
            "selected_versions"
        ][dataset_type] = version

        # -------------------------------------------------------------
        # IMPORTANT:
        #
        # dataset_status now contains all information required by
        # the HTML without needing to inspect DatasetVersion through
        # a Dataset object.
        # -------------------------------------------------------------

        context[
            "dataset_status"
        ][dataset_type] = (
            build_dataset_status(
                dataset_type=dataset_type,
                dataset=dataset,
                version=version,
                dataframe=dataframe,
                available=True,
                message="Selected",
                selected_id=dataset.id,
            )
        )

    # =================================================================
    # NO RESOLVED DATASETS
    # =================================================================

    if not resolved_datasets:

        context["error"] = (
            "Not available — at least one "
            "business dataset is required."
        )

        return render(
            request,
            "analytics/business_intelligence.html",
            context,
        )

    # =================================================================
    # AVAILABLE DATE RANGE
    # =================================================================

    available_ranges = []

    for (
        dataset_type,
        resolved,
    ) in resolved_datasets.items():

        dataframe = resolved[
            "dataframe"
        ]

        (
            available_from,
            available_to,
        ) = get_available_business_date_range(
            dataframe,
            dataset_type,
        )

        if (
            available_from is not None
            and available_to is not None
        ):

            available_ranges.append(
                (
                    available_from,
                    available_to,
                )
            )

    if available_ranges:

        available_from_date = min(
            item[0]
            for item in available_ranges
        )

        available_to_date = max(
            item[1]
            for item in available_ranges
        )

    else:

        available_from_date = None

        available_to_date = None

    context[
        "available_from_date"
    ] = available_from_date

    context[
        "available_to_date"
    ] = available_to_date

    # =================================================================
    # ANALYSIS DATES
    # =================================================================

    if selected_range == "custom":

        (
            analysis_from_date,
            analysis_to_date,
        ) = resolve_custom_dates(
            request
        )

        if (
            analysis_from_date is None
            and analysis_to_date is None
        ):

            analysis_from_date = (
                available_from_date
            )

            analysis_to_date = (
                available_to_date
            )

    else:

        analysis_from_date = None

        analysis_to_date = (
            available_to_date
        )

        if available_to_date is not None:

            (
                analysis_from_date,
                analysis_to_date,
            ) = calculate_preset_dates(
                available_to_date,
                selected_range,
            )

    # =================================================================
    # CLAMP ANALYSIS DATES
    # =================================================================

    if (
        analysis_from_date is not None
        and available_from_date is not None
        and analysis_from_date
        < available_from_date
    ):

        analysis_from_date = (
            available_from_date
        )

    if (
        analysis_to_date is not None
        and available_to_date is not None
        and analysis_to_date
        > available_to_date
    ):

        analysis_to_date = (
            available_to_date
        )

    if (
        analysis_from_date is not None
        and analysis_to_date is not None
        and analysis_from_date
        > analysis_to_date
    ):

        (
            analysis_from_date,
            analysis_to_date,
        ) = (
            analysis_to_date,
            analysis_from_date,
        )

    context[
        "analysis_from_date"
    ] = analysis_from_date

    context[
        "analysis_to_date"
    ] = analysis_to_date

    # =================================================================
    # RUN INDIVIDUAL ANALYTICS
    # =================================================================

    source_results: Dict[
        str,
        Dict[str, Any],
    ] = {}

    for (
        dataset_type,
        resolved,
    ) in resolved_datasets.items():

        builder = RESULT_BUILDERS.get(
            dataset_type
        )

        if builder is None:
            continue

        dataframe = resolved[
            "dataframe"
        ]

        dataset = resolved[
            "dataset"
        ]

        version = resolved[
            "version"
        ]

        # -------------------------------------------------------------
        # Base result always contains selected dataset metadata.
        #
        # This is important because even if analytics fail,
        # the Data Sources table can still show:
        #
        # Dataset
        # Current Version
        # Version Type
        # Rows
        # Columns
        # -------------------------------------------------------------

        result = {
            "metrics": {},

            "chart_data": {},

            "date_metadata": {},

            "dataframe_available": False,

            "analytics_error": None,

            "_dataset": dataset,

            "_version": version,

            "_dataset_id": dataset.id,

            "_version_id": getattr(
                version,
                "id",
                None,
            ),

            "_dataset_name": (
                dataset.name
            ),

            "_dataset_type": (
                dataset_type
            ),
        }

        # -------------------------------------------------------------
        # Execute analytics builder.
        # -------------------------------------------------------------

        try:

            result = builder(
                dataframe=dataframe,
                from_date=analysis_from_date,
                to_date=analysis_to_date,
            )

            if not isinstance(
                result,
                dict,
            ):
                result = {
                    "metrics": {},
                    "chart_data": {},
                    "date_metadata": {},
                    "dataframe_available": False,
                    "analytics_error": (
                        "Analytics builder returned "
                        "an invalid result."
                    ),
                }

        except Exception as exc:

            # ---------------------------------------------------------
            # IMPORTANT:
            #
            # Log the REAL exception in Django console/log file.
            #
            # Do not expose traceback to the user.
            # ---------------------------------------------------------

            logger.exception(
                "Business Intelligence %s analytics failed "
                "for dataset id=%s name=%s version id=%s "
                "for user id=%s",
                dataset_type,
                getattr(
                    dataset,
                    "id",
                    None,
                ),
                getattr(
                    dataset,
                    "name",
                    None,
                ),
                getattr(
                    version,
                    "id",
                    None,
                ),
                getattr(
                    request.user,
                    "id",
                    None,
                ),
            )

            result = {
                "metrics": {},

                "chart_data": {},

                "date_metadata": {},

                "dataframe_available": False,

                "analytics_error": str(
                    exc
                ),
            }

            message = (
                f"{dataset_type} analytics could not "
                "be calculated for dataset "
                f"{dataset.name}."
            )

            if context.get("warning"):

                context["warning"] = (
                    f"{context['warning']} "
                    f"{message}"
                )

            else:

                context["warning"] = (
                    message
                )

        # -------------------------------------------------------------
        # Reattach selected dataset metadata.
        #
        # This is intentionally done AFTER the builder because
        # builders return analytics data only.
        # -------------------------------------------------------------

        result["_dataset"] = dataset

        result["_version"] = version

        result["_dataset_id"] = dataset.id

        result["_version_id"] = getattr(
            version,
            "id",
            None,
        )

        result["_dataset_name"] = (
            dataset.name
        )

        result["_dataset_type"] = (
            dataset_type
        )

        if not isinstance(
            result.get("metrics"),
            dict,
        ):

            result["metrics"] = {}

        if not isinstance(
            result.get("chart_data"),
            dict,
        ):

            result["chart_data"] = {}

        # -------------------------------------------------------------
        # Store exactly ONE result per category.
        # -------------------------------------------------------------

        source_results[
            dataset_type
        ] = result

    # =================================================================
    # BUSINESS METRICS
    # =================================================================

    try:

        business_result = (
            calculate_business_metrics(
                source_results
            )
        )

    except Exception as exc:

        logger.exception(
            "Business Intelligence metrics calculation failed "
            "for user id=%s",
            getattr(
                request.user,
                "id",
                None,
            ),
        )

        business_result = {
            "metrics": {},

            "metric_sources": {},

            "available_dataset_types": [],
        }

        warning = (
            "Business Intelligence metrics could "
            "not be calculated yet."
        )

        if context.get("warning"):

            context["warning"] = (
                f"{context['warning']} "
                f"{warning}"
            )

        else:

            context["warning"] = (
                warning
            )

    if not isinstance(
        business_result,
        dict,
    ):

        business_result = {
            "metrics": {},

            "metric_sources": {},

            "available_dataset_types": [],
        }

    business_metrics = (
        business_result.get(
            "metrics"
        )
        or {}
    )

    metric_sources = (
        business_result.get(
            "metric_sources"
        )
        or {}
    )

    context["metrics"] = (
        json_safe(
            business_metrics
        )
    )

    context["metric_sources"] = (
        json_safe(
            metric_sources
        )
    )

    # =================================================================
    # BUSINESS CHARTS
    # =================================================================

    try:

        chart_data = (
            calculate_business_chart_data(
                source_results
            )
        )

    except Exception:

        logger.exception(
            "Business Intelligence chart calculation failed "
            "for user id=%s",
            getattr(
                request.user,
                "id",
                None,
            ),
        )

        chart_data = {}

        warning = (
            "Some Business Intelligence charts "
            "could not be calculated."
        )

        if context.get("warning"):

            context["warning"] = (
                f"{context['warning']} "
                f"{warning}"
            )

        else:

            context["warning"] = (
                warning
            )

    if not isinstance(
        chart_data,
        dict,
    ):

        chart_data = {}

    # =================================================================
    # GUARANTEE ALL EXPECTED CHART KEYS
    # =================================================================

    for key in DEFAULT_BUSINESS_CHART_KEYS:

        if key not in chart_data:

            chart_data[key] = []

    # =================================================================
    # FINANCIAL COMPATIBILITY FALLBACK
    # =================================================================

    financial_result = (
        source_results.get(
            "Financial"
        )
    )

    if isinstance(
        financial_result,
        dict,
    ):

        financial_charts = (
            financial_result.get(
                "chart_data"
            )
            or {}
        )

        # Revenue trend.
        if (
            not chart_data.get(
                "revenue_trend"
            )
            and financial_charts.get(
                "revenue_trend"
            )
        ):

            chart_data[
                "revenue_trend"
            ] = financial_charts[
                "revenue_trend"
            ]

        # Financial trend.
        if (
            not chart_data.get(
                "financial_trend"
            )
            and financial_charts.get(
                "revenue_trend"
            )
        ):

            chart_data[
                "financial_trend"
            ] = financial_charts[
                "revenue_trend"
            ]

        # Profit by category.
        if (
            not chart_data.get(
                "profit_by_category"
            )
            and financial_charts.get(
                "profit_by_category"
            )
        ):

            chart_data[
                "profit_by_category"
            ] = financial_charts[
                "profit_by_category"
            ]

        # Cash flow.
        if (
            not chart_data.get(
                "cash_flow"
            )
            and financial_charts.get(
                "cash_flow_trend"
            )
        ):

            chart_data[
                "cash_flow"
            ] = financial_charts[
                "cash_flow_trend"
            ]

    # =================================================================
    # STORE CHART DATA
    # =================================================================

    context["chart_data"] = (
        json_safe(
            chart_data
        )
    )

    # =================================================================
    # CHART JSON
    # =================================================================

    context[
        "sales_trend_json"
    ] = json_dumps(
        chart_data.get(
            "sales_trend",
            [],
        )
    )

    context[
        "revenue_trend_json"
    ] = json_dumps(
        chart_data.get(
            "revenue_trend",
            [],
        )
    )

    context[
        "sales_by_region_json"
    ] = json_dumps(
        chart_data.get(
            "sales_by_region",
            [],
        )
    )

    context[
        "units_by_region_json"
    ] = json_dumps(
        chart_data.get(
            "units_by_region",
            [],
        )
    )

    context[
        "sales_by_category_json"
    ] = json_dumps(
        chart_data.get(
            "sales_by_category",
            [],
        )
    )

    context[
        "top_products_json"
    ] = json_dumps(
        chart_data.get(
            "top_products",
            [],
        )
    )

    context[
        "customer_segments_json"
    ] = json_dumps(
        chart_data.get(
            "customer_segments",
            [],
        )
    )

    context[
        "customer_regions_json"
    ] = json_dumps(
        chart_data.get(
            "customer_regions",
            [],
        )
    )

    context[
        "marketing_performance_json"
    ] = json_dumps(
        chart_data.get(
            "marketing_performance",
            [],
        )
    )

    context[
        "marketing_campaigns_json"
    ] = json_dumps(
        chart_data.get(
            "marketing_campaigns",
            [],
        )
    )

    context[
        "financial_trend_json"
    ] = json_dumps(
        chart_data.get(
            "financial_trend",
            [],
        )
    )

    context[
        "profit_by_category_json"
    ] = json_dumps(
        chart_data.get(
            "profit_by_category",
            [],
        )
    )

    context[
        "cash_flow_json"
    ] = json_dumps(
        chart_data.get(
            "cash_flow",
            [],
        )
    )

    context[
        "returns_trend_json"
    ] = json_dumps(
        chart_data.get(
            "returns_trend",
            [],
        )
    )

    context[
        "returns_by_reason_json"
    ] = json_dumps(
        chart_data.get(
            "returns_by_reason",
            [],
        )
    )

    context[
        "returns_by_product_json"
    ] = json_dumps(
        chart_data.get(
            "returns_by_product",
            [],
        )
    )

    # =================================================================
    # UNAVAILABLE CHARTS
    # =================================================================

    chart_labels = {
        "sales_trend": "Business Sales Trend",

        "revenue_trend": "Revenue Trend",

        "sales_by_region": "Sales by Region",

        "units_by_region": "Units by Region",

        "sales_by_category": "Sales by Category",

        "top_products": "Top Products",

        "customer_segments": "Customer Segments",

        "customer_regions": "Customer Regions",

        "marketing_performance": (
            "Marketing Performance"
        ),

        "marketing_campaigns": (
            "Marketing Campaign Performance"
        ),

        "financial_trend": (
            "Financial Performance"
        ),

        "profit_by_category": (
            "Profit by Category"
        ),

        "cash_flow": "Cash Flow Trend",

        "returns_trend": "Returns Trend",

        "returns_by_reason": (
            "Returns by Reason"
        ),

        "returns_by_product": (
            "Returns by Product"
        ),
    }

    unavailable_charts = []

    for key, label in chart_labels.items():

        value = chart_data.get(
            key
        )

        if (
            not isinstance(
                value,
                list,
            )
            or not value
        ):

            unavailable_charts.append(
                label
            )

    context[
        "unavailable_charts"
    ] = unavailable_charts

    # =================================================================
    # AVAILABLE DATASET TYPES
    # =================================================================

    available_dataset_types = []

    for dataset_type in BUSINESS_DATASET_TYPES:

        result = source_results.get(
            dataset_type
        )

        if not isinstance(
            result,
            dict,
        ):
            continue

        dataset = result.get(
            "_dataset"
        )

        if dataset is not None:

            available_dataset_types.append(
                dataset_type
            )

    context[
        "available_dataset_types"
    ] = available_dataset_types

    context[
        "available_dataset_count"
    ] = len(
        available_dataset_types
    )

    # =================================================================
    # SELECTED DATASET COUNTS
    # =================================================================

    selected_dataset_count_by_type = {}

    total_selected_dataset_count = 0

    for dataset_type in BUSINESS_DATASET_TYPES:

        selected_id = (
            context[
                "selected_dataset_ids"
            ].get(
                dataset_type
            )
        )

        count = (
            1
            if (
                selected_id is not None
                and dataset_type in resolved_datasets
            )
            else 0
        )

        selected_dataset_count_by_type[
            dataset_type
        ] = count

        total_selected_dataset_count += (
            count
        )

    context[
        "selected_dataset_count_by_type"
    ] = selected_dataset_count_by_type

    context[
        "total_selected_dataset_count"
    ] = total_selected_dataset_count

    # =================================================================
    # SMART BUSINESS INSIGHTS
    # =================================================================

    try:

        context["insights"] = (
            generate_business_insights(
                business_metrics
            )
            or []
        )

    except Exception:

        logger.exception(
            "Business Intelligence insights generation failed "
            "for user id=%s",
            getattr(
                request.user,
                "id",
                None,
            ),
        )

        context["insights"] = []

    # =================================================================
    # EMPTY FILTER WARNING
    # =================================================================

    if (
        analysis_from_date is not None
        or analysis_to_date is not None
    ):

        any_filtered_data = False

        for result in source_results.values():

            if not isinstance(
                result,
                dict,
            ):
                continue

            if result.get(
                "dataframe_available"
            ):

                any_filtered_data = True

                break

        if not any_filtered_data:

            # Do not overwrite an important analytics error.
            if not context.get(
                "warning"
            ):

                context["warning"] = (
                    "No records are available "
                    "for the selected analysis period."
                )

    # =================================================================
    # RENDER
    # =================================================================

    return render(
        request,
        "analytics/business_intelligence.html",
        context,
    )


# =====================================================================
# COMPATIBILITY ALIAS
# =====================================================================

business_dashboard = business_intelligence