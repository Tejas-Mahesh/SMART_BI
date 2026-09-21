import json

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..metrics.sales_metrics import (
    calculate_sales_growth,
    calculate_sales_metrics,
    generate_sales_insights,
    prepare_sales_dataframe,
    quantity_vs_sales,
    sales_by_category,
    sales_by_channel,
    sales_trend,
    salesperson_performance,
    top_products,
)

from ..services.dataset_resolver import (
    get_user_datasets,
    resolve_dataset,
)

from ..services.date_filter import (
    apply_date_filter,
)


# ============================================================
# DATE RANGE OPTIONS
# ============================================================

DATE_RANGE_OPTIONS = [
    ("all", "All Time"),
    ("7d", "Last 7 Days"),
    ("30d", "Last 30 Days"),
    ("3m", "Last 3 Months"),
    ("6m", "Last 6 Months"),
    ("12m", "Last 12 Months"),
    ("custom", "Custom Range"),
]


# ============================================================
# SALES DATE HELPERS
# ============================================================

def get_sales_date_column(dataframe):
    """
    Find the Sales date column.

    Supported columns:
        Order_Date
        Date

    Returns the actual dataframe column name or None.
    """

    if dataframe is None or dataframe.empty:
        return None

    expected_columns = [
        "Order_Date",
        "Date",
    ]

    normalized_columns = {
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_"): column
        for column in dataframe.columns
    }

    for expected in expected_columns:

        normalized_expected = (
            expected
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

        actual_column = normalized_columns.get(
            normalized_expected
        )

        if actual_column:
            return actual_column

    return None


def get_available_sales_date_range(dataframe):
    """
    Determine the earliest and latest usable Sales dates.

    Returns:

        {
            "min_date": date or None,
            "max_date": date or None,
        }
    """

    date_column = get_sales_date_column(
        dataframe
    )

    if date_column is None:
        return {
            "min_date": None,
            "max_date": None,
        }

    dates = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
    ).dropna()

    if dates.empty:
        return {
            "min_date": None,
            "max_date": None,
        }

    return {
        "min_date": dates.min().date(),
        "max_date": dates.max().date(),
    }


# ============================================================
# PRESET DATE CALCULATION
# ============================================================

def calculate_preset_dates(
    dataframe,
    range_key,
):
    """
    Calculate a date range relative to the latest
    available date in the selected Sales dataset.

    The dataset's latest date is used instead of
    today's system date.
    """

    available_range = get_available_sales_date_range(
        dataframe
    )

    min_date = available_range["min_date"]
    max_date = available_range["max_date"]

    if min_date is None or max_date is None:
        return None, None

    # --------------------------------------------------------
    # ALL TIME
    # --------------------------------------------------------

    if range_key == "all":

        return (
            min_date,
            max_date,
        )

    # --------------------------------------------------------
    # CUSTOM
    # --------------------------------------------------------

    if range_key == "custom":

        return None, None

    latest_timestamp = pd.Timestamp(
        max_date
    )

    # --------------------------------------------------------
    # LAST 7 DAYS
    # --------------------------------------------------------

    if range_key == "7d":

        start_timestamp = (
            latest_timestamp
            - pd.Timedelta(days=6)
        )

    # --------------------------------------------------------
    # LAST 30 DAYS
    # --------------------------------------------------------

    elif range_key == "30d":

        start_timestamp = (
            latest_timestamp
            - pd.Timedelta(days=29)
        )

    # --------------------------------------------------------
    # LAST 3 MONTHS
    # --------------------------------------------------------

    elif range_key == "3m":

        start_timestamp = (
            latest_timestamp
            - pd.DateOffset(months=3)
            + pd.Timedelta(days=1)
        )

    # --------------------------------------------------------
    # LAST 6 MONTHS
    # --------------------------------------------------------

    elif range_key == "6m":

        start_timestamp = (
            latest_timestamp
            - pd.DateOffset(months=6)
            + pd.Timedelta(days=1)
        )

    # --------------------------------------------------------
    # LAST 12 MONTHS
    # --------------------------------------------------------

    elif range_key == "12m":

        start_timestamp = (
            latest_timestamp
            - pd.DateOffset(months=12)
            + pd.Timedelta(days=1)
        )

    # --------------------------------------------------------
    # UNKNOWN RANGE
    # --------------------------------------------------------

    else:

        return (
            min_date,
            max_date,
        )

    start_date = start_timestamp.date()

    # --------------------------------------------------------
    # Do not go before dataset history.
    # --------------------------------------------------------

    if start_date < min_date:

        start_date = min_date

    return (
        start_date,
        max_date,
    )


# ============================================================
# CUSTOM DATE VALIDATION
# ============================================================

def resolve_custom_dates(
    custom_from_date,
    custom_to_date,
):
    """
    Validate custom date input.

    Returns:

        (start_date, end_date)

    or:

        (None, None)
    """

    if not custom_from_date:
        return None, None

    if not custom_to_date:
        return None, None

    start_date = pd.to_datetime(
        custom_from_date,
        errors="coerce",
    )

    end_date = pd.to_datetime(
        custom_to_date,
        errors="coerce",
    )

    if pd.isna(start_date):
        return None, None

    if pd.isna(end_date):
        return None, None

    start_date = start_date.normalize()
    end_date = end_date.normalize()

    if end_date < start_date:
        return None, None

    return (
        start_date.date(),
        end_date.date(),
    )


# ============================================================
# DATE FORMAT HELPER
# ============================================================

def format_date_for_input(value):
    """
    Convert a date/datetime-like value into
    YYYY-MM-DD format.
    """

    if value is None:
        return ""

    if hasattr(value, "strftime"):

        return value.strftime(
            "%Y-%m-%d"
        )

    return str(value)


# ============================================================
# SALES INTELLIGENCE
# ============================================================

@login_required
def sales_intelligence(request):

    # ========================================================
    # GET USER SALES DATASETS
    # ========================================================

    sales_datasets = get_user_datasets(
        request.user,
        "Sales",
    )

    # ========================================================
    # SELECT DATASET
    # ========================================================

    selected_dataset_id = (
        request.GET.get("dataset")
        or request.GET.get("dataset_id")
    )

    if selected_dataset_id:

        try:

            selected_dataset_id = int(
                selected_dataset_id
            )

        except (
            TypeError,
            ValueError,
        ):

            selected_dataset_id = None

    # ========================================================
    # RESOLVE SELECTED DATASET
    # ========================================================

    resolved = None
    error = None

    try:

        resolved = resolve_dataset(
            request.user,
            "Sales",
            dataset_id=selected_dataset_id,
        )

    except Exception as exc:

        error = str(exc)

    # ========================================================
    # REQUESTED DATE RANGE
    # ========================================================

    requested_range = request.GET.get(
        "range",
        "all",
    )

    valid_range_keys = {
        key
        for key, label in DATE_RANGE_OPTIONS
    }

    if requested_range not in valid_range_keys:

        requested_range = "all"

    # ========================================================
    # CUSTOM DATE VALUES
    # ========================================================

    custom_from_date = request.GET.get(
        "from_date",
        "",
    )

    custom_to_date = request.GET.get(
        "to_date",
        "",
    )

    # ========================================================
    # BASE CONTEXT
    # ========================================================

    context = {

        "page_title": "Sales Intelligence",

        "dataset_available": False,

        "data_sufficient": False,

        "error": error,

        # ----------------------------------------------------
        # Dataset selector
        # ----------------------------------------------------

        "sales_datasets": sales_datasets,

        "selected_dataset_id": (
            resolved.dataset.id
            if resolved
            else selected_dataset_id
        ),

        # ----------------------------------------------------
        # Date selector
        # ----------------------------------------------------

        "date_range_options": (
            DATE_RANGE_OPTIONS
        ),

        "selected_range": (
            requested_range
        ),

        "from_date": "",

        "to_date": "",

        "custom_from_date": (
            custom_from_date
        ),

        "custom_to_date": (
            custom_to_date
        ),
    }

    # ========================================================
    # NO SALES DATASET
    # ========================================================

    if resolved is None:

        if not error:

            if sales_datasets.exists():

                context["error"] = (
                    "The selected Sales dataset "
                    "could not be found."
                )

            else:

                context["error"] = (
                    "Sales dataset required."
                )

        return render(
            request,
            "analytics/sales.html",
            context,
        )

    # ========================================================
    # CURRENT DATASET VERSION
    # ========================================================

    full_dataframe = resolved.dataframe

    # ========================================================
    # PREPARE SALES DATA
    # ========================================================

    (
        prepared_dataframe,
        columns,
        missing_core_columns,
        missing_optional_columns,
    ) = prepare_sales_dataframe(
        full_dataframe
    )

    # ========================================================
    # CORE DATA VALIDATION
    # ========================================================

    if missing_core_columns:

        context.update({

            "dataset_available": True,

            "data_sufficient": False,

            "dataset": resolved.dataset,

            "version": resolved.version,

            "missing_columns": (
                missing_core_columns
            ),

            "missing_core_columns": (
                missing_core_columns
            ),

            "missing_optional_columns": (
                missing_optional_columns
            ),
        })

        return render(
            request,
            "analytics/sales.html",
            context,
        )

    # ========================================================
    # AVAILABLE DATASET DATE RANGE
    # ========================================================

    available_date_range = (
        get_available_sales_date_range(
            prepared_dataframe
        )
    )

    available_min_date = (
        available_date_range["min_date"]
    )

    available_max_date = (
        available_date_range["max_date"]
    )

    # ========================================================
    # RESOLVE ANALYSIS PERIOD
    # ========================================================

    analysis_from_date = None
    analysis_to_date = None
    date_error = None

    # --------------------------------------------------------
    # CUSTOM
    # --------------------------------------------------------

    if requested_range == "custom":

        (
            analysis_from_date,
            analysis_to_date,
        ) = resolve_custom_dates(
            custom_from_date,
            custom_to_date,
        )

        if (
            analysis_from_date is None
            or analysis_to_date is None
        ):

            date_error = (
                "Please provide a valid custom "
                "date range."
            )

    # --------------------------------------------------------
    # PRESET
    # --------------------------------------------------------

    else:

        (
            analysis_from_date,
            analysis_to_date,
        ) = calculate_preset_dates(
            prepared_dataframe,
            requested_range,
        )

        if (
            analysis_from_date is None
            or analysis_to_date is None
        ):

            date_error = (
                "No valid Sales dates are available "
                "for the selected range."
            )

    # ========================================================
    # IF CUSTOM RANGE IS INVALID
    # ========================================================

    if date_error:

        context.update({

            "dataset_available": True,

            "data_sufficient": True,

            "dataset": resolved.dataset,

            "version": resolved.version,

            "columns": columns,

            "missing_core_columns": (
                missing_core_columns
            ),

            "missing_optional_columns": (
                missing_optional_columns
            ),

            "available_min_date": (
                format_date_for_input(
                    available_min_date
                )
            ),

            "available_max_date": (
                format_date_for_input(
                    available_max_date
                )
            ),

            "selected_range": (
                requested_range
            ),

            "error": date_error,

            "date_metadata": {
                "date_column": columns.get(
                    "Order_Date"
                ),
                "date_filter_applied": False,
                "from_date": None,
                "to_date": None,
                "analysis_from_date": None,
                "analysis_to_date": None,
                "selected_range": requested_range,
                "warning": date_error,
            },
        })

        return render(
            request,
            "analytics/sales.html",
            context,
        )

    # ========================================================
    # FORMAT ANALYSIS DATES
    # ========================================================

    from_date_for_filter = (
        format_date_for_input(
            analysis_from_date
        )
    )

    to_date_for_filter = (
        format_date_for_input(
            analysis_to_date
        )
    )

    # ========================================================
    # APPLY DATE FILTER
    # ========================================================

    (
        filtered_dataframe,
        date_metadata,
    ) = apply_date_filter(
        prepared_dataframe,
        "Sales",
        from_date_for_filter,
        to_date_for_filter,
    )

    # ========================================================
    # ADD ANALYSIS INFORMATION
    # ========================================================

    date_metadata["analysis_from_date"] = (
        from_date_for_filter
    )

    date_metadata["analysis_to_date"] = (
        to_date_for_filter
    )

    date_metadata["selected_range"] = (
        requested_range
    )

    # ========================================================
    # SALES KPI METRICS
    # ========================================================

    metrics = calculate_sales_metrics(
        filtered_dataframe,
        columns,
    )

    # ========================================================
    # SALES TREND
    # ========================================================

    trend = sales_trend(
        filtered_dataframe,
        columns,
    )

    # ========================================================
    # SALES BY CATEGORY
    # ========================================================

    category_data = sales_by_category(
        filtered_dataframe,
        columns,
    )

    # ========================================================
    # TOP PRODUCTS
    # ========================================================

    product_data = top_products(
        filtered_dataframe,
        columns,
    )

    # ========================================================
    # SALES BY CHANNEL
    # ========================================================

    channel_data = sales_by_channel(
        filtered_dataframe,
        columns,
    )

    # ========================================================
    # SALESPERSON PERFORMANCE
    # ========================================================

    salesperson_data = salesperson_performance(
        filtered_dataframe,
        columns,
    )

    # ========================================================
    # QUANTITY BAND
    # ========================================================

    quantity_data = quantity_vs_sales(
        filtered_dataframe,
        columns,
    )

    # ========================================================
    # SALES GROWTH
    # ========================================================
    #
    # IMPORTANT:
    #
    # Growth must use the FULL prepared dataset to find
    # the previous comparable period.
    #
    # The selected period is represented by:
    #
    #     analysis_from_date
    #     analysis_to_date
    #
    # We do NOT use request.GET directly here because
    # preset ranges do not have from_date/to_date values.
    # ========================================================

    growth = calculate_sales_growth(
        filtered_dataframe,
        prepared_dataframe,
        columns,
        analysis_from_date,
        analysis_to_date,
    )

    # --------------------------------------------------------
    # Store growth inside KPI metrics
    # --------------------------------------------------------

    metrics["sales_growth"] = growth

    # ========================================================
    # SMART SALES INSIGHTS
    # ========================================================

    insights = generate_sales_insights(
        metrics,
        category_data,
        product_data,
        channel_data,
        salesperson_data,
    )

    # ========================================================
    # FINAL CONTEXT
    # ========================================================

    context.update({

        "dataset_available": True,

        "data_sufficient": True,

        # ----------------------------------------------------
        # Dataset
        # ----------------------------------------------------

        "dataset": resolved.dataset,

        "version": resolved.version,

        # ----------------------------------------------------
        # Columns
        # ----------------------------------------------------

        "columns": columns,

        "missing_core_columns": (
            missing_core_columns
        ),

        "missing_optional_columns": (
            missing_optional_columns
        ),

        # ----------------------------------------------------
        # KPI metrics
        # ----------------------------------------------------

        "metrics": metrics,

        # ----------------------------------------------------
        # Chart data
        # ----------------------------------------------------

        "trend_data": json.dumps(
            trend
        ),

        "category_data": json.dumps(
            category_data
        ),

        "product_data": json.dumps(
            product_data
        ),

        "channel_data": json.dumps(
            channel_data
        ),

        "salesperson_data": json.dumps(
            salesperson_data
        ),

        "quantity_data": json.dumps(
            quantity_data
        ),

        # ----------------------------------------------------
        # Insights
        # ----------------------------------------------------

        "insights": insights,

        # ----------------------------------------------------
        # Date selector
        # ----------------------------------------------------

        "selected_range": (
            requested_range
        ),

        "from_date": (
            from_date_for_filter
        ),

        "to_date": (
            to_date_for_filter
        ),

        "custom_from_date": (
            custom_from_date
        ),

        "custom_to_date": (
            custom_to_date
        ),

        # ----------------------------------------------------
        # Dataset date limits
        # ----------------------------------------------------

        "available_min_date": (
            format_date_for_input(
                available_min_date
            )
        ),

        "available_max_date": (
            format_date_for_input(
                available_max_date
            )
        ),

        # ----------------------------------------------------
        # Date metadata
        # ----------------------------------------------------

        "date_metadata": (
            date_metadata
        ),

        # ----------------------------------------------------
        # Explicit analysis dates
        # ----------------------------------------------------

        "analysis_from_date": (
            from_date_for_filter
        ),

        "analysis_to_date": (
            to_date_for_filter
        ),
    })

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "analytics/sales.html",
        context,
    )