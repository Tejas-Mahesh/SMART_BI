# analytics/views/regional.py

import json
from datetime import timedelta

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.metrics.regional_metrics import (
    calculate_regional_growth,
    calculate_regional_metrics,
    generate_regional_insights,
    prepare_regional_dataframe,
    profit_by_region,
    regional_performance_comparison,
    regional_sales_contribution,
    regional_sales_by_date,
    regional_sales_trend,
    sales_by_region,
    units_by_region,
)

from analytics.services.dataset_resolver import (
    get_user_datasets,
    resolve_dataset,
)

from analytics.services.date_filter import (
    apply_date_filter,
    find_date_column,
)


# ============================================================
# DATE RANGE OPTIONS
# ============================================================

DATE_RANGE_OPTIONS = {
    "all": "All Time",
    "7d": "Last 7 Days",
    "30d": "Last 30 Days",
    "3m": "Last 3 Months",
    "6m": "Last 6 Months",
    "12m": "Last 12 Months",
    "custom": "Custom Range",
}


# ============================================================
# DATE HELPERS
# ============================================================

def get_regional_date_column(dataframe):
    """
    Return the compatible Regional dataset date column.
    """

    return find_date_column(
        dataframe,
        "Regional",
    )


def get_available_regional_date_range(dataframe):
    """
    Return the earliest and latest valid dates available
    in the Regional dataset.

    Returns:
        (date, date)
        or
        (None, None)
    """

    if dataframe is None or dataframe.empty:
        return None, None

    date_column = get_regional_date_column(
        dataframe
    )

    if not date_column:
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

    The latest available dataset date is used as the
    reference point instead of today's date.
    """

    if not latest_date:
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
    Parse custom date parameters.

    HTML date inputs normally submit YYYY-MM-DD.
    dayfirst=True is retained for consistency with
    the project's dataset date handling.
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

    if pd.isna(parsed_from):
        parsed_from = None

    if pd.isna(parsed_to):
        parsed_to = None

    if parsed_from is not None:
        parsed_from = parsed_from.date()

    if parsed_to is not None:
        parsed_to = parsed_to.date()

    return (
        parsed_from,
        parsed_to,
    )


# ============================================================
# JSON SERIALIZATION
# ============================================================

def json_safe(value):
    """
    Convert pandas/numpy values into JSON-safe values.
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


# ============================================================
# MAIN VIEW
# ============================================================

@login_required
def regional_intelligence(request):
    """
    Regional Intelligence dashboard.

    Data flow:

        User
          ↓
        Regional Dataset
          ↓
        Current DatasetVersion
          ↓
        DataFrame
          ↓
        Date Filtering
          ↓
        Regional Metrics
          ↓
        Charts + Insights
    """

    # ========================================================
    # DEFAULT CONTEXT
    # ========================================================

    context = {

        "regional_datasets": [],

        "selected_dataset": None,

        "selected_range": "30d",

        "date_range_options": DATE_RANGE_OPTIONS,

        "analysis_from_date": None,

        "analysis_to_date": None,

        "available_from_date": None,

        "available_to_date": None,

        "selected_version": None,

        "metrics": {
            "total_regions": 0,
            "total_sales": None,
            "total_orders": None,
            "units_sold": None,
            "average_order_value": None,
            "average_sales_per_region": None,
            "total_profit": None,
            "profit_margin": None,
            "top_region": None,
            "top_region_sales": None,
            "regional_growth": None,
        },

        "chart_data": {

            "sales_trend": [],

            "sales_by_region": [],

            "units_by_region": [],

            "profit_by_region": [],

            "sales_contribution": [],

            "performance_comparison": [],

            "sales_by_date": [],
        },

        "sales_trend_json": "[]",

        "sales_by_region_json": "[]",

        "units_by_region_json": "[]",

        "profit_by_region_json": "[]",

        "sales_contribution_json": "[]",

        "performance_comparison_json": "[]",

        "sales_by_date_json": "[]",

        "insights": [],

        "unavailable_charts": [],

        "error": None,

        "warning": None,
    }


    # ========================================================
    # LOAD USER'S REGIONAL DATASETS
    # ========================================================

    try:

        regional_datasets = get_user_datasets(
            request.user,
            "Regional",
        )

        context["regional_datasets"] = (
            regional_datasets
        )

    except Exception:

        context["error"] = (
            "Unable to load Regional datasets."
        )

        return render(
            request,
            "analytics/regional_intelligence.html",
            context,
        )


    # ========================================================
    # DATASET REQUIRED
    # ========================================================

    if not regional_datasets:

        context["error"] = (
            "Not available — Regional dataset required."
        )

        return render(
            request,
            "analytics/regional_intelligence.html",
            context,
        )


    # ========================================================
    # DATASET SELECTION
    # ========================================================

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

            selected_dataset = (
                regional_datasets
                .filter(
                    id=requested_id
                )
                .first()
            )

        except (
            TypeError,
            ValueError,
        ):

            selected_dataset = None


    # Invalid/unavailable dataset selection falls back
    # to the newest dataset belonging to the user.

    if selected_dataset is None:

        selected_dataset = (
            regional_datasets.first()
        )


    context["selected_dataset"] = (
        selected_dataset
    )


    # ========================================================
    # RESOLVE CURRENT DATASET VERSION
    # ========================================================

    try:

        resolved = resolve_dataset(
            request.user,
            "Regional",
            dataset_id=selected_dataset.id,
        )

    except Exception as exc:

        context["error"] = str(exc)

        return render(
            request,
            "analytics/regional_intelligence.html",
            context,
        )


    if resolved is None:

        context["error"] = (
            "Not available — Regional dataset required."
        )

        return render(
            request,
            "analytics/regional_intelligence.html",
            context,
        )


    # ========================================================
    # RESOLVED DATA
    # ========================================================

    dataframe = resolved.dataframe

    selected_version = resolved.version

    context["selected_version"] = (
        selected_version
    )


    # ========================================================
    # PREPARE REGIONAL DATAFRAME
    # ========================================================

    (
        dataframe,
        resolved_columns,
        missing_required_columns,
    ) = prepare_regional_dataframe(
        dataframe
    )


    if missing_required_columns:

        context["error"] = (
            "Insufficient Regional data. "
            "Required column(s) missing: "
            + ", ".join(
                missing_required_columns
            )
        )

        return render(
            request,
            "analytics/regional_intelligence.html",
            context,
        )


    # ========================================================
    # AVAILABLE DATE RANGE
    # ========================================================

    (
        available_from_date,
        available_to_date,
    ) = get_available_regional_date_range(
        dataframe
    )

    context["available_from_date"] = (
        available_from_date
    )

    context["available_to_date"] = (
        available_to_date
    )


    # ========================================================
    # SELECTED DATE RANGE
    # ========================================================

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


    # ========================================================
    # ANALYSIS DATE RANGE
    # ========================================================

    analysis_from_date = None

    analysis_to_date = (
        available_to_date
    )


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


        # If only one custom date is supplied,
        # use the available dataset boundary for
        # the missing side.

        if (
            analysis_from_date is None
            and analysis_to_date is not None
            and available_from_date is not None
        ):

            analysis_from_date = (
                available_from_date
            )


        if (
            analysis_to_date is None
            and analysis_from_date is not None
            and available_to_date is not None
        ):

            analysis_to_date = (
                available_to_date
            )


        # Correct reversed custom ranges.

        if (
            analysis_from_date
            and analysis_to_date
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

    else:

        (
            analysis_from_date,
            analysis_to_date,
        ) = calculate_preset_dates(
            available_to_date,
            selected_range,
        )


    context["analysis_from_date"] = (
        analysis_from_date
    )

    context["analysis_to_date"] = (
        analysis_to_date
    )


    # ========================================================
    # APPLY DATE FILTER
    # ========================================================

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe,
            "Regional",
            from_date=analysis_from_date,
            to_date=analysis_to_date,
        )
    )


    if date_metadata.get("warning"):

        context["warning"] = (
            date_metadata["warning"]
        )


    # ========================================================
    # EMPTY FILTER RESULT
    # ========================================================

    if (
        filtered_dataframe is None
        or filtered_dataframe.empty
    ):

        context["warning"] = (
            "No Regional records are available "
            "for the selected date range."
        )

        return render(
            request,
            "analytics/regional_intelligence.html",
            context,
        )


    # ========================================================
    # CALCULATE REGIONAL METRICS
    # ========================================================

    metrics = calculate_regional_metrics(
        filtered_dataframe
    )


    # ========================================================
    # CALCULATE REGIONAL GROWTH
    # ========================================================

    growth = calculate_regional_growth(
        dataframe,
        current_from_date=analysis_from_date,
        current_to_date=analysis_to_date,
    )


    metrics["regional_growth"] = (
        growth
    )


    context["metrics"] = metrics


    # ========================================================
    # CHART DATA
    # ========================================================

    chart_data = {

        # 1. Overall regional sales trend
        "sales_trend": regional_sales_trend(
            filtered_dataframe
        ),

        # 2. Sales by region
        "sales_by_region": sales_by_region(
            filtered_dataframe,
            limit=10,
        ),

        # 3. Units by region
        "units_by_region": units_by_region(
            filtered_dataframe,
            limit=10,
        ),

        # 4. Profit by region
        "profit_by_region": profit_by_region(
            filtered_dataframe,
            limit=10,
        ),

        # 5. Sales contribution
        "sales_contribution": (
            regional_sales_contribution(
                filtered_dataframe
            )
        ),

        # 6. Regional comparison
        "performance_comparison": (
            regional_performance_comparison(
                filtered_dataframe,
                limit=10,
            )
        ),

        # 7. Sales by date and region
        "sales_by_date": regional_sales_by_date(
            filtered_dataframe,
            limit=5,
        ),
    }


    context["chart_data"] = (
        chart_data
    )


    # ========================================================
    # DETERMINE UNAVAILABLE CHARTS
    # ========================================================

    unavailable_charts = []


    if not chart_data["sales_trend"]:

        unavailable_charts.append(
            "Regional Sales Trend"
        )


    if not chart_data["sales_by_region"]:

        unavailable_charts.append(
            "Sales by Region"
        )


    if not chart_data["units_by_region"]:

        unavailable_charts.append(
            "Units by Region"
        )


    if not chart_data["profit_by_region"]:

        unavailable_charts.append(
            "Profit by Region"
        )


    if not chart_data["sales_contribution"]:

        unavailable_charts.append(
            "Regional Sales Contribution"
        )


    if not chart_data["performance_comparison"]:

        unavailable_charts.append(
            "Regional Performance Comparison"
        )


    if not chart_data["sales_by_date"]:

        unavailable_charts.append(
            "Regional Sales Comparison Trend"
        )


    context["unavailable_charts"] = (
        unavailable_charts
    )


    # ========================================================
    # SMART REGIONAL INSIGHTS
    # ========================================================

    insights = generate_regional_insights(
        metrics=metrics,

        sales_regions=(
            chart_data["sales_by_region"]
        ),

        profit_regions=(
            chart_data["profit_by_region"]
        ),

        growth=growth,
    )


    context["insights"] = insights


    # ========================================================
    # JSON DATA FOR CHART.JS
    # ========================================================

    context["sales_trend_json"] = json.dumps(
        json_safe(
            chart_data["sales_trend"]
        )
    )


    context["sales_by_region_json"] = json.dumps(
        json_safe(
            chart_data["sales_by_region"]
        )
    )


    context["units_by_region_json"] = json.dumps(
        json_safe(
            chart_data["units_by_region"]
        )
    )


    context["profit_by_region_json"] = json.dumps(
        json_safe(
            chart_data["profit_by_region"]
        )
    )


    context["sales_contribution_json"] = json.dumps(
        json_safe(
            chart_data["sales_contribution"]
        )
    )


    context["performance_comparison_json"] = (
        json.dumps(
            json_safe(
                chart_data[
                    "performance_comparison"
                ]
            )
        )
    )


    context["sales_by_date_json"] = json.dumps(
        json_safe(
            chart_data["sales_by_date"]
        )
    )


    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "analytics/regional_intelligence.html",
        context,
    )