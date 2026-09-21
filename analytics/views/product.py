import json
from datetime import timedelta

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.metrics.product_metrics import (
    calculate_product_growth,
    calculate_product_metrics,
    generate_product_insights,
    prepare_product_dataframe,
    product_quantity_distribution,
    product_sales_trend,
    profit_by_product,
    sales_by_category,
    sales_by_product,
    units_by_product,
)

from analytics.services.dataset_resolver import (
    get_user_datasets,
    resolve_dataset,
)

from analytics.services.date_filter import (
    apply_date_filter,
    find_date_column,
)


# =========================================================
# DATE RANGE OPTIONS
# =========================================================

DATE_RANGE_OPTIONS = {
    "all": "All Time",
    "7d": "Last 7 Days",
    "30d": "Last 30 Days",
    "3m": "Last 3 Months",
    "6m": "Last 6 Months",
    "12m": "Last 12 Months",
    "custom": "Custom Range",
}


# =========================================================
# DATE HELPERS
# =========================================================

def get_product_date_column(dataframe):
    """
    Find the compatible date column for a Product dataset.
    """

    return find_date_column(
        dataframe,
        "Products",
    )


def get_available_product_date_range(dataframe):
    """
    Return the earliest and latest usable dates
    available in the selected Product dataset.

    Returns:
        (earliest_date, latest_date)
    """

    if dataframe is None or dataframe.empty:
        return None, None

    date_column = get_product_date_column(
        dataframe
    )

    if date_column is None:
        return None, None

    dates = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
        dayfirst=True,
    ).dropna()

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
    Calculate the date range for a preset option.

    The latest date in the selected dataset is treated
    as the end of the analysis period.
    """

    if latest_date is None:
        return None, None

    if selected_range == "all":
        return None, latest_date

    if selected_range == "7d":
        days = 6

    elif selected_range == "30d":
        days = 29

    elif selected_range == "3m":
        days = 89

    elif selected_range == "6m":
        days = 179

    elif selected_range == "12m":
        days = 364

    else:
        return None, latest_date

    return (
        latest_date - timedelta(days=days),
        latest_date,
    )


def resolve_custom_dates(
    from_date,
    to_date,
):
    """
    Parse custom date values safely.

    Supports both:

        DD-MM-YYYY

    and:

        YYYY-MM-DD
    """

    parsed_from = None
    parsed_to = None

    if from_date:

        parsed_from = pd.to_datetime(
            from_date,
            errors="coerce",
            dayfirst=True,
        )

    if to_date:

        parsed_to = pd.to_datetime(
            to_date,
            errors="coerce",
            dayfirst=True,
        )

    if (
        parsed_from is not None
        and pd.isna(parsed_from)
    ):
        parsed_from = None

    if (
        parsed_to is not None
        and pd.isna(parsed_to)
    ):
        parsed_to = None

    if parsed_from is not None:
        parsed_from = parsed_from.date()

    if parsed_to is not None:
        parsed_to = parsed_to.date()

    return (
        parsed_from,
        parsed_to,
    )


# =========================================================
# JSON SAFETY
# =========================================================

def json_safe(value):
    """
    Convert pandas / NumPy / nested values into
    JSON-safe Python values.
    """

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            tuple,
            set,
        ),
    ):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            pd.Timestamp,
            pd.Timedelta,
        ),
    ):
        return str(value)

    if hasattr(value, "item"):

        try:
            return value.item()

        except Exception:
            pass

    return value


# =========================================================
# EMPTY DEFAULTS
# =========================================================

def get_empty_metrics():
    """
    Default Product Intelligence metric structure.

    None is used when a metric cannot be calculated,
    rather than presenting an artificial zero.
    """

    return {
        "total_products": None,
        "active_products": None,
        "total_sales": None,
        "units_sold": None,
        "average_product_sales": None,
        "average_unit_price": None,
        "total_profit": None,
        "profit_margin": None,
        "top_product": None,
        "top_product_sales": None,
        "product_growth": None,
    }


def get_empty_chart_data():
    """
    Default Product Intelligence chart structure.
    """

    return {
        "sales_trend": [],
        "sales_by_product": [],
        "units_by_product": [],
        "sales_by_category": [],
        "profit_by_product": [],
        "quantity_distribution": [],
    }


# =========================================================
# MAIN VIEW
# =========================================================

@login_required
def product_intelligence(request):
    """
    Product Intelligence dashboard.

    Data source:
        Current DatasetVersion belonging to the
        authenticated user.

    Supports:
        - Multiple Product datasets
        - Dataset selection
        - Date presets
        - Custom date range
        - Product KPIs
        - Product charts
        - Product growth
        - Smart Product Insights

    Security:
        Dataset access is restricted through the
        owner-filtered dataset resolver.
    """

    context = {
        # -------------------------------------------------
        # DATASET
        # -------------------------------------------------

        "product_datasets": [],
        "selected_dataset": None,
        "selected_version": None,

        # -------------------------------------------------
        # DATE FILTER
        # -------------------------------------------------

        "selected_range": "30d",
        "date_range_options": DATE_RANGE_OPTIONS,

        "analysis_from_date": None,
        "analysis_to_date": None,

        "available_from_date": None,
        "available_to_date": None,

        # -------------------------------------------------
        # ANALYTICS
        # -------------------------------------------------

        "metrics": get_empty_metrics(),

        "chart_data": get_empty_chart_data(),

        "unavailable_charts": [],

        "insights": [],

        # -------------------------------------------------
        # CHART JSON
        # -------------------------------------------------

        "sales_trend_json": "[]",
        "sales_by_product_json": "[]",
        "units_by_product_json": "[]",
        "sales_by_category_json": "[]",
        "profit_by_product_json": "[]",
        "quantity_distribution_json": "[]",

        # -------------------------------------------------
        # MESSAGES
        # -------------------------------------------------

        "error": None,
        "warning": None,
    }

    # =====================================================
    # 1. LOAD USER'S PRODUCT DATASETS
    # =====================================================

    try:

        product_datasets = get_user_datasets(
            request.user,
            "Products",
        )

        context["product_datasets"] = (
            product_datasets
        )

    except Exception:

        context["error"] = (
            "Unable to load Product datasets."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # -----------------------------------------------------
    # NO PRODUCT DATASET
    # -----------------------------------------------------

    if not product_datasets.exists():

        context["error"] = (
            "Not available — Product dataset required."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # =====================================================
    # 2. SELECT PRODUCT DATASET
    # =====================================================

    requested_dataset_id = (
        request.GET.get("dataset")
        or request.GET.get("dataset_id")
    )

    selected_dataset = None

    if requested_dataset_id:

        try:

            requested_id = int(
                requested_dataset_id
            )

        except (
            TypeError,
            ValueError,
        ):

            requested_id = None

        if requested_id is not None:

            selected_dataset = (
                product_datasets
                .filter(
                    id=requested_id
                )
                .first()
            )

    # -----------------------------------------------------
    # DEFAULT TO NEWEST DATASET
    # -----------------------------------------------------

    if selected_dataset is None:

        selected_dataset = (
            product_datasets.first()
        )

    context["selected_dataset"] = (
        selected_dataset
    )

    # =====================================================
    # 3. RESOLVE CURRENT DATASET VERSION
    # =====================================================

    try:

        resolved = resolve_dataset(
            request.user,
            "Products",
            dataset_id=selected_dataset.id,
        )

    except ValueError as exc:

        context["error"] = str(exc)

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    except Exception:

        context["error"] = (
            "Unable to read the selected Product dataset."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # -----------------------------------------------------
    # DATASET COULD NOT BE RESOLVED
    # -----------------------------------------------------

    if resolved is None:

        context["error"] = (
            "Not available — Product dataset required."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    dataframe = resolved.dataframe

    context["selected_version"] = (
        resolved.version
    )

    # =====================================================
    # 4. PREPARE PRODUCT DATA
    # =====================================================

    (
        dataframe,
        resolved_columns,
        missing_required_columns,
    ) = prepare_product_dataframe(
        dataframe
    )

    # -----------------------------------------------------
    # REQUIRED DATA MISSING
    # -----------------------------------------------------

    if missing_required_columns:

        context["error"] = (
            "Insufficient Product data. "
            "Required column(s) missing: "
            + ", ".join(
                missing_required_columns
            )
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # =====================================================
    # 5. FIND AVAILABLE DATASET DATE RANGE
    # =====================================================

    (
        available_from_date,
        available_to_date,
    ) = get_available_product_date_range(
        dataframe
    )

    context[
        "available_from_date"
    ] = available_from_date

    context[
        "available_to_date"
    ] = available_to_date

    # =====================================================
    # 6. READ DATE RANGE FILTER
    # =====================================================

    selected_range = (
        request.GET.get(
            "range",
            "30d",
        )
        or "30d"
    )

    if selected_range not in DATE_RANGE_OPTIONS:

        selected_range = "30d"

    context["selected_range"] = (
        selected_range
    )

    analysis_from_date = None
    analysis_to_date = available_to_date

    # =====================================================
    # 7. CUSTOM DATE RANGE
    # =====================================================

    if selected_range == "custom":

        custom_from = request.GET.get(
            "from_date"
        )

        custom_to = request.GET.get(
            "to_date"
        )

        (
            analysis_from_date,
            analysis_to_date,
        ) = resolve_custom_dates(
            custom_from,
            custom_to,
        )

        # -------------------------------------------------
        # If only one custom date is provided, use the
        # available dataset boundary for the other side.
        # -------------------------------------------------

        if (
            analysis_from_date is None
            and analysis_to_date is not None
        ):

            analysis_from_date = (
                available_from_date
            )

        elif (
            analysis_from_date is not None
            and analysis_to_date is None
        ):

            analysis_to_date = (
                available_to_date
            )

        # -------------------------------------------------
        # Swap reversed dates instead of failing.
        # -------------------------------------------------

        if (
            analysis_from_date is not None
            and analysis_to_date is not None
            and analysis_from_date > analysis_to_date
        ):

            (
                analysis_from_date,
                analysis_to_date,
            ) = (
                analysis_to_date,
                analysis_from_date,
            )

    # =====================================================
    # 8. PRESET DATE RANGE
    # =====================================================

    else:

        (
            analysis_from_date,
            analysis_to_date,
        ) = calculate_preset_dates(
            available_to_date,
            selected_range,
        )

    context[
        "analysis_from_date"
    ] = analysis_from_date

    context[
        "analysis_to_date"
    ] = analysis_to_date

    # =====================================================
    # 9. APPLY DATE FILTER
    # =====================================================

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe,
            "Products",
            from_date=analysis_from_date,
            to_date=analysis_to_date,
        )
    )

    if date_metadata.get("warning"):

        context["warning"] = (
            date_metadata["warning"]
        )

    # =====================================================
    # 10. CHECK FILTERED DATA
    # =====================================================

    if (
        filtered_dataframe is None
        or filtered_dataframe.empty
    ):

        context["warning"] = (
            "No Product records are available "
            "for the selected date range."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # =====================================================
    # 11. PRODUCT KPI METRICS
    # =====================================================

    metrics = calculate_product_metrics(
        filtered_dataframe
    )

    if metrics is None:

        metrics = get_empty_metrics()

    # =====================================================
    # 12. PRODUCT GROWTH
    # =====================================================

    growth = calculate_product_growth(
        dataframe,
        current_from_date=analysis_from_date,
        current_to_date=analysis_to_date,
    )

    metrics["product_growth"] = growth

    context["metrics"] = metrics

    # =====================================================
    # 13. PRODUCT CHART DATA
    # =====================================================

    chart_data = {
        "sales_trend": product_sales_trend(
            filtered_dataframe
        ),

        "sales_by_product": sales_by_product(
            filtered_dataframe,
            limit=10,
        ),

        "units_by_product": units_by_product(
            filtered_dataframe,
            limit=10,
        ),

        "sales_by_category": sales_by_category(
            filtered_dataframe
        ),

        "profit_by_product": profit_by_product(
            filtered_dataframe,
            limit=10,
        ),

        "quantity_distribution": (
            product_quantity_distribution(
                filtered_dataframe
            )
        ),
    }

    context["chart_data"] = chart_data

    # =====================================================
    # 14. UNAVAILABLE CHARTS
    # =====================================================

    unavailable_charts = []

    if not chart_data["sales_trend"]:

        unavailable_charts.append(
            "Product Sales Trend"
        )

    if not chart_data["sales_by_product"]:

        unavailable_charts.append(
            "Sales by Product"
        )

    if not chart_data["units_by_product"]:

        unavailable_charts.append(
            "Units by Product"
        )

    if not chart_data["sales_by_category"]:

        unavailable_charts.append(
            "Sales by Category"
        )

    if not chart_data["profit_by_product"]:

        unavailable_charts.append(
            "Profit by Product"
        )

    if not chart_data["quantity_distribution"]:

        unavailable_charts.append(
            "Product Quantity Distribution"
        )

    context[
        "unavailable_charts"
    ] = unavailable_charts

    # =====================================================
    # 15. SMART PRODUCT INSIGHTS
    # =====================================================

    insights = generate_product_insights(
        metrics=metrics,

        sales_products=chart_data[
            "sales_by_product"
        ],

        category_sales=chart_data[
            "sales_by_category"
        ],

        profit_products=chart_data[
            "profit_by_product"
        ],

        growth=growth,
    )

    context["insights"] = insights

    # =====================================================
    # 16. SERIALIZE CHART DATA
    # =====================================================

    context[
        "sales_trend_json"
    ] = json.dumps(
        json_safe(
            chart_data["sales_trend"]
        )
    )

    context[
        "sales_by_product_json"
    ] = json.dumps(
        json_safe(
            chart_data["sales_by_product"]
        )
    )

    context[
        "units_by_product_json"
    ] = json.dumps(
        json_safe(
            chart_data["units_by_product"]
        )
    )

    context[
        "sales_by_category_json"
    ] = json.dumps(
        json_safe(
            chart_data["sales_by_category"]
        )
    )

    context[
        "profit_by_product_json"
    ] = json.dumps(
        json_safe(
            chart_data["profit_by_product"]
        )
    )

    context[
        "quantity_distribution_json"
    ] = json.dumps(
        json_safe(
            chart_data[
                "quantity_distribution"
            ]
        )
    )

    # =====================================================
    # 17. RENDER
    # =====================================================

    return render(
        request,
        "analytics/product_intelligence.html",
        context,
    )