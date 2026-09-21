# analytics/views/marketing.py

import json
from datetime import datetime, timedelta

import pandas as pd
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.metrics.marketing_metrics import (
    calculate_marketing_growth,
    calculate_marketing_metrics,
    channel_performance,
    conversions_by_campaign,
    cost_by_campaign,
    generate_marketing_insights,
    marketing_by_region,
    marketing_funnel,
    marketing_sales_trend,
    roi_by_campaign,
    sales_by_campaign,
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
# DATE HELPERS
# ============================================================

def get_marketing_date_column(dataframe):
    """
    Return the compatible Marketing date column.
    """

    if dataframe is None or dataframe.empty:
        return None

    return find_date_column(
        dataframe,
        "Marketing",
    )


def get_available_marketing_date_range(dataframe):
    """
    Return the earliest and latest valid Marketing dates.
    """

    date_column = get_marketing_date_column(
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
    selected_range,
    latest_date,
):
    """
    Calculate the selected preset date range using the latest
    available date in the Marketing dataset.

    Returns:
        from_date,
        to_date
    """

    if latest_date is None:
        return None, None

    if isinstance(
        latest_date,
        datetime,
    ):
        latest_date = latest_date.date()

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
            latest_date - timedelta(days=89),
            latest_date,
        )

    if selected_range == "6m":

        return (
            latest_date - timedelta(days=179),
            latest_date,
        )

    if selected_range == "12m":

        return (
            latest_date - timedelta(days=364),
            latest_date,
        )

    return None, latest_date


def resolve_custom_dates(
    from_date,
    to_date,
):
    """
    Convert custom date values into Python date objects.
    """

    resolved_from = None
    resolved_to = None

    if from_date:

        try:

            resolved_from = datetime.strptime(
                from_date,
                "%Y-%m-%d",
            ).date()

        except (
            ValueError,
            TypeError,
        ):

            resolved_from = None

    if to_date:

        try:

            resolved_to = datetime.strptime(
                to_date,
                "%Y-%m-%d",
            ).date()

        except (
            ValueError,
            TypeError,
        ):

            resolved_to = None

    if (
        resolved_from
        and resolved_to
        and resolved_from > resolved_to
    ):

        resolved_from, resolved_to = (
            resolved_to,
            resolved_from,
        )

    return (
        resolved_from,
        resolved_to,
    )


# ============================================================
# JSON HELPER
# ============================================================

def json_safe(value):
    """
    Convert common pandas/Python values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (
            pd.Timestamp,
            datetime,
        ),
    ):

        return value.isoformat()

    if hasattr(
        value,
        "item",
    ):

        try:
            return value.item()

        except (
            ValueError,
            TypeError,
        ):
            pass

    if isinstance(
        value,
        float,
    ):

        if pd.isna(value):
            return None

    if isinstance(
        value,
        dict,
    ):

        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(
        value,
        list,
    ):

        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        tuple,
    ):

        return [
            json_safe(item)
            for item in value
        ]

    return value


# ============================================================
# MARKETING INTELLIGENCE
# ============================================================

@login_required
def marketing_intelligence(request):
    """
    Marketing Intelligence dashboard.

    Architecture:
        User
          ↓
        Marketing Dataset
          ↓
        Current DatasetVersion
          ↓
        Data Preparation
          ↓
        Date Filtering
          ↓
        Marketing Metrics
          ↓
        Charts + Smart Insights
    """

    # ========================================================
    # INITIAL CONTEXT
    # ========================================================

    context = {

        "marketing_datasets": [],

        "selected_dataset": None,

        "selected_range": "all",

        "date_range_options":
            DATE_RANGE_OPTIONS,

        "analysis_from_date": None,

        "analysis_to_date": None,

        "available_from_date": None,

        "available_to_date": None,

        "selected_version": None,


        # ----------------------------------------------------
        # KPI METRICS
        # ----------------------------------------------------

        "metrics": {
            "total_campaigns": 0,
            "total_impressions": None,
            "total_clicks": None,
            "total_conversions": None,
            "total_leads": None,
            "total_sales": None,
            "total_marketing_cost": None,
            "total_profit": None,
            "average_ctr": None,
            "conversion_rate": None,
            "cost_per_click": None,
            "cost_per_conversion": None,
            "cost_per_lead": None,
            "roi": None,
            "roas": None,
            "customers_acquired": None,
            "average_campaign_sales": None,
            "top_campaign": None,
            "top_campaign_sales": None,
            "marketing_growth": None,
        },


        # ----------------------------------------------------
        # CHART DATA
        # ----------------------------------------------------

        "chart_data": {

            "sales_trend": [],

            "sales_by_campaign": [],

            "cost_by_campaign": [],

            "conversions_by_campaign": [],

            "channel_performance": [],

            "roi_by_campaign": [],

            "marketing_funnel": [],

            "marketing_by_region": [],
        },


        # ----------------------------------------------------
        # JSON VARIABLES
        # ----------------------------------------------------

        "sales_trend_json": "[]",

        "sales_by_campaign_json": "[]",

        "cost_by_campaign_json": "[]",

        "conversions_by_campaign_json": "[]",

        "channel_performance_json": "[]",

        "roi_by_campaign_json": "[]",

        "marketing_funnel_json": "[]",

        "marketing_by_region_json": "[]",


        # ----------------------------------------------------
        # INSIGHTS
        # ----------------------------------------------------

        "insights": [],

        "unavailable_charts": [],

        "error": None,

        "warning": None,
    }


    # ========================================================
    # LOAD USER MARKETING DATASETS
    # ========================================================

    marketing_datasets = get_user_datasets(
        user=request.user,
        dataset_type="Marketing",
    )

    context[
        "marketing_datasets"
    ] = marketing_datasets


    # ========================================================
    # NO MARKETING DATASET
    # ========================================================

    if not marketing_datasets.exists():

        context["error"] = (
            "Not available — Marketing dataset required."
        )

        return render(
            request,
            "analytics/marketing_intelligence.html",
            context,
        )


    # ========================================================
    # DATASET SELECTION
    # ========================================================

    requested_dataset_id = (
        request.GET.get(
            "dataset"
        )
        or request.GET.get(
            "dataset_id"
        )
    )


    selected_dataset = None


    if requested_dataset_id:

        try:

            requested_dataset_id = int(
                requested_dataset_id
            )

        except (
            ValueError,
            TypeError,
        ):

            requested_dataset_id = None


    if requested_dataset_id:

        selected_dataset = (
            marketing_datasets
            .filter(
                id=requested_dataset_id
            )
            .first()
        )


    # Invalid or unauthorized dataset IDs safely fall back
    # to the newest Marketing dataset.

    if selected_dataset is None:

        selected_dataset = (
            marketing_datasets
            .order_by(
                "-uploaded_at",
                "-id",
            )
            .first()
        )


    context[
        "selected_dataset"
    ] = selected_dataset


    if selected_dataset is None:

        context["error"] = (
            "Not available — Marketing dataset required."
        )

        return render(
            request,
            "analytics/marketing_intelligence.html",
            context,
        )


    # ========================================================
    # RESOLVE CURRENT DATASET VERSION
    # ========================================================

    try:

        resolved_dataset = resolve_dataset(
            user=request.user,
            dataset_type="Marketing",
            dataset_id=selected_dataset.id,
        )

    except Exception as exc:

        context["error"] = str(exc)

        return render(
            request,
            "analytics/marketing_intelligence.html",
            context,
        )


    if resolved_dataset is None:

        context["error"] = (
            "Not available — Marketing dataset "
            "version required."
        )

        return render(
            request,
            "analytics/marketing_intelligence.html",
            context,
        )


    dataframe = (
        resolved_dataset.dataframe
    )

    selected_version = (
        resolved_dataset.version
    )


    context[
        "selected_version"
    ] = selected_version


    # ========================================================
    # PREPARE DATAFRAME
    # ========================================================

    if dataframe is None:

        context["error"] = (
            "Marketing dataset data is unavailable."
        )

        return render(
            request,
            "analytics/marketing_intelligence.html",
            context,
        )


    dataframe = dataframe.copy()


    # ========================================================
    # DATE RANGE
    # ========================================================

    selected_range = (
        request.GET.get(
            "range",
            "all",
        )
    )


    valid_ranges = {
        option[0]
        for option in DATE_RANGE_OPTIONS
    }


    if selected_range not in valid_ranges:

        selected_range = "all"


    context[
        "selected_range"
    ] = selected_range


    # ========================================================
    # AVAILABLE DATE RANGE
    # ========================================================

    available_from_date, available_to_date = (
        get_available_marketing_date_range(
            dataframe
        )
    )


    context[
        "available_from_date"
    ] = available_from_date

    context[
        "available_to_date"
    ] = available_to_date


    # ========================================================
    # SELECT ANALYSIS DATE RANGE
    # ========================================================

    analysis_from_date = None
    analysis_to_date = None


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


        if custom_from and not analysis_from_date:

            context["warning"] = (
                "The custom start date is invalid."
            )


        if custom_to and not analysis_to_date:

            context["warning"] = (
                "The custom end date is invalid."
            )


        if (
            analysis_from_date is None
            and available_from_date is not None
        ):

            analysis_from_date = (
                available_from_date
            )


        if (
            analysis_to_date is None
            and available_to_date is not None
        ):

            analysis_to_date = (
                available_to_date
            )


    else:

        (
            analysis_from_date,
            analysis_to_date,
        ) = calculate_preset_dates(
            selected_range,
            available_to_date,
        )


    context[
        "analysis_from_date"
    ] = analysis_from_date

    context[
        "analysis_to_date"
    ] = analysis_to_date


    # ========================================================
    # APPLY DATE FILTER
    # ========================================================

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe=dataframe,
            dataset_type="Marketing",
            from_date=analysis_from_date,
            to_date=analysis_to_date,
        )
    )


    # ========================================================
    # DATE WARNING
    # ========================================================

    if date_metadata.get(
        "warning"
    ):

        context["warning"] = (
            date_metadata[
                "warning"
            ]
        )


    # ========================================================
    # EMPTY FILTERED DATA
    # ========================================================

    if filtered_dataframe.empty:

        context["warning"] = (
            "No Marketing data is available "
            "for the selected date range."
        )

        context[
            "chart_data"
        ] = {
            "sales_trend": [],
            "sales_by_campaign": [],
            "cost_by_campaign": [],
            "conversions_by_campaign": [],
            "channel_performance": [],
            "roi_by_campaign": [],
            "marketing_funnel": [],
            "marketing_by_region": [],
        }

        return render(
            request,
            "analytics/marketing_intelligence.html",
            context,
        )


    # ========================================================
    # CALCULATE CORE METRICS
    # ========================================================

    metrics = calculate_marketing_metrics(
        filtered_dataframe
    )


    # ========================================================
    # MARKETING GROWTH
    # ========================================================

    marketing_growth = (
        calculate_marketing_growth(
            dataframe=dataframe,
            current_from_date=analysis_from_date,
            current_to_date=analysis_to_date,
        )
    )


    metrics[
        "marketing_growth"
    ] = marketing_growth


    context[
        "metrics"
    ] = json_safe(
        metrics
    )


    # ========================================================
    # CHART DATA
    # ========================================================

    sales_trend_data = (
        marketing_sales_trend(
            filtered_dataframe
        )
    )


    sales_by_campaign_data = (
        sales_by_campaign(
            filtered_dataframe,
            limit=10,
        )
    )


    cost_by_campaign_data = (
        cost_by_campaign(
            filtered_dataframe,
            limit=10,
        )
    )


    conversions_by_campaign_data = (
        conversions_by_campaign(
            filtered_dataframe,
            limit=10,
        )
    )


    channel_performance_data = (
        channel_performance(
            filtered_dataframe,
            limit=10,
        )
    )


    roi_by_campaign_data = (
        roi_by_campaign(
            filtered_dataframe,
            limit=10,
        )
    )


    marketing_funnel_data = (
        marketing_funnel(
            filtered_dataframe
        )
    )


    marketing_by_region_data = (
        marketing_by_region(
            filtered_dataframe,
            limit=10,
        )
    )


    # ========================================================
    # STORE CHART DATA
    # ========================================================

    context[
        "chart_data"
    ] = {

        "sales_trend":
            json_safe(
                sales_trend_data
            ),

        "sales_by_campaign":
            json_safe(
                sales_by_campaign_data
            ),

        "cost_by_campaign":
            json_safe(
                cost_by_campaign_data
            ),

        "conversions_by_campaign":
            json_safe(
                conversions_by_campaign_data
            ),

        "channel_performance":
            json_safe(
                channel_performance_data
            ),

        "roi_by_campaign":
            json_safe(
                roi_by_campaign_data
            ),

        "marketing_funnel":
            json_safe(
                marketing_funnel_data
            ),

        "marketing_by_region":
            json_safe(
                marketing_by_region_data
            ),
    }


    # ========================================================
    # UNAVAILABLE CHARTS
    # ========================================================

    unavailable_charts = []


    if not sales_trend_data:

        unavailable_charts.append(
            "Marketing Sales Trend"
        )


    if not sales_by_campaign_data:

        unavailable_charts.append(
            "Sales by Campaign"
        )


    if not cost_by_campaign_data:

        unavailable_charts.append(
            "Marketing Cost by Campaign"
        )


    if not conversions_by_campaign_data:

        unavailable_charts.append(
            "Conversions by Campaign"
        )


    if not channel_performance_data:

        unavailable_charts.append(
            "Channel Performance"
        )


    if not roi_by_campaign_data:

        unavailable_charts.append(
            "Campaign ROI / ROAS"
        )


    if not marketing_funnel_data:

        unavailable_charts.append(
            "Marketing Funnel"
        )


    if not marketing_by_region_data:

        unavailable_charts.append(
            "Marketing Performance by Region"
        )


    context[
        "unavailable_charts"
    ] = unavailable_charts


    # ========================================================
    # SMART MARKETING INSIGHTS
    # ========================================================

    insights = (
        generate_marketing_insights(
            metrics=metrics,
            campaigns=sales_by_campaign_data,
            channels=channel_performance_data,
            roi_campaigns=roi_by_campaign_data,
            growth=marketing_growth,
        )
    )


    context[
        "insights"
    ] = json_safe(
        insights
    )


    # ========================================================
    # JSON VARIABLES FOR CHART.JS
    # ========================================================

    context[
        "sales_trend_json"
    ] = json.dumps(
        json_safe(
            sales_trend_data
        )
    )


    context[
        "sales_by_campaign_json"
    ] = json.dumps(
        json_safe(
            sales_by_campaign_data
        )
    )


    context[
        "cost_by_campaign_json"
    ] = json.dumps(
        json_safe(
            cost_by_campaign_data
        )
    )


    context[
        "conversions_by_campaign_json"
    ] = json.dumps(
        json_safe(
            conversions_by_campaign_data
        )
    )


    context[
        "channel_performance_json"
    ] = json.dumps(
        json_safe(
            channel_performance_data
        )
    )


    context[
        "roi_by_campaign_json"
    ] = json.dumps(
        json_safe(
            roi_by_campaign_data
        )
    )


    context[
        "marketing_funnel_json"
    ] = json.dumps(
        json_safe(
            marketing_funnel_data
        )
    )


    context[
        "marketing_by_region_json"
    ] = json.dumps(
        json_safe(
            marketing_by_region_data
        )
    )


    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "analytics/marketing_intelligence.html",
        context,
    )