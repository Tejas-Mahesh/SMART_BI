
"""
Returns Intelligence View
=========================

Django view for the Returns Intelligence dashboard.

Architecture:
    User
      ↓
    Owner-safe Returns Dataset
      ↓
    Current DatasetVersion
      ↓
    Prepared DataFrame
      ↓
    Date Range Filter
      ↓
    Returns Metrics
      ↓
    Chart Data
      ↓
    Smart Returns Insights
      ↓
    Template
"""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.metrics.returns_metrics import (
    calculate_returns_growth,
    calculate_returns_metrics,
    generate_returns_insights,
    prepare_returns_dataframe,
    return_value_distribution,
    returns_by_category,
    returns_by_product,
    returns_by_reason,
    returns_by_region,
    returns_by_status,
    returns_trend,
)

from analytics.services.dataset_resolver import (
    get_user_datasets,
    resolve_dataset,
)

from analytics.services.date_filter import (
    apply_date_filter,
    find_date_column,
)


# ============================================================================
# DATE RANGE OPTIONS
# ============================================================================

DATE_RANGE_OPTIONS = [
    ("all", "All Time"),
    ("7d", "Last 7 Days"),
    ("30d", "Last 30 Days"),
    ("3m", "Last 3 Months"),
    ("6m", "Last 6 Months"),
    ("12m", "Last 12 Months"),
    ("custom", "Custom Range"),
]


# ============================================================================
# DATE HELPERS
# ============================================================================

def get_returns_date_column(
    dataframe,
):
    """
    Find the compatible date column for Returns data.
    """

    if dataframe is None:
        return None

    return find_date_column(
        dataframe,
        "Returns",
    )


def get_available_returns_date_range(
    dataframe,
):
    """
    Return the earliest and latest valid return dates.
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return None, None

    date_column = get_returns_date_column(
        dataframe
    )

    if not date_column:
        return None, None

    dates = pd.to_datetime(
        dataframe[
            date_column
        ],
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
    available_from_date,
    available_to_date,
):
    """
    Calculate the requested date range from the actual dataset dates.

    The dataset's latest available date is used as the reference point.
    """

    if (
        available_from_date is None
        or available_to_date is None
    ):
        return None, None

    if selected_range == "all":
        return (
            available_from_date,
            available_to_date,
        )

    end_date = available_to_date

    if selected_range == "7d":

        start_date = (
            end_date
            - timedelta(days=6)
        )

    elif selected_range == "30d":

        start_date = (
            end_date
            - timedelta(days=29)
        )

    elif selected_range == "3m":

        start_date = (
            end_date
            - timedelta(days=89)
        )

    elif selected_range == "6m":

        start_date = (
            end_date
            - timedelta(days=179)
        )

    elif selected_range == "12m":

        start_date = (
            end_date
            - timedelta(days=364)
        )

    else:

        return (
            available_from_date,
            available_to_date,
        )

    if start_date < available_from_date:
        start_date = available_from_date

    return (
        start_date,
        end_date,
    )


def resolve_custom_dates(
    request,
    available_from_date,
    available_to_date,
):
    """
    Resolve custom from/to dates safely.

    Invalid values fall back to the available dataset range.
    """

    from_value = (
        request.GET.get(
            "from_date"
        )
        or ""
    ).strip()

    to_value = (
        request.GET.get(
            "to_date"
        )
        or ""
    ).strip()

    from_date = None
    to_date = None

    if from_value:

        parsed_from = pd.to_datetime(
            from_value,
            errors="coerce",
        )

        if pd.notna(parsed_from):
            from_date = parsed_from.date()

    if to_value:

        parsed_to = pd.to_datetime(
            to_value,
            errors="coerce",
        )

        if pd.notna(parsed_to):
            to_date = parsed_to.date()

    if from_date is None:
        from_date = available_from_date

    if to_date is None:
        to_date = available_to_date

    if (
        from_date is not None
        and to_date is not None
        and from_date > to_date
    ):

        from_date, to_date = (
            to_date,
            from_date,
        )

    return (
        from_date,
        to_date,
    )


# ============================================================================
# JSON SAFETY
# ============================================================================

def json_safe(value):
    """
    Convert pandas / numpy / Decimal values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (
            pd.Timestamp,
            pd.Timedelta,
        ),
    ):
        return str(value)

    if isinstance(
        value,
        Decimal,
    ):
        return float(value)

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
        (list, tuple),
    ):
        return [
            json_safe(item)
            for item in value
        ]

    try:

        if pd.isna(value):
            return None

    except (
        TypeError,
        ValueError,
    ):
        pass

    try:

        if hasattr(
            value,
            "item",
        ):
            return json_safe(
                value.item()
            )

    except Exception:
        pass

    return value


# ============================================================================
# MAIN VIEW
# ============================================================================

@login_required
def returns_intelligence(
    request,
):
    """
    Returns Intelligence dashboard.
    """

    # ------------------------------------------------------------------
    # Default context
    # ------------------------------------------------------------------

    context = {

        "returns_datasets": [],

        "selected_dataset": None,

        "selected_range": (
            request.GET.get(
                "range"
            )
            or "all"
        ),

        "date_range_options": (
            DATE_RANGE_OPTIONS
        ),

        "analysis_from_date": None,

        "analysis_to_date": None,

        "available_from_date": None,

        "available_to_date": None,

        "selected_version": None,

        "metrics": {

            "total_returns": None,

            "returned_units": None,

            "return_value": None,

            "total_sales": None,

            "return_rate": None,

            "average_return_value": None,

            "average_return_units": None,

            "returning_customers": None,

            "return_customer_rate": None,

            "top_return_reason": None,

            "top_return_reason_count": None,

            "top_return_product": None,

            "top_return_product_count": None,

            "top_return_region": None,

            "top_return_region_count": None,

            "return_growth": None,
        },

        "chart_data": {

            "returns_trend": [],

            "returns_by_reason": [],

            "returns_by_product": [],

            "returns_by_category": [],

            "returns_by_region": [],

            "return_status": [],

            "return_value_distribution": [],
        },

        "returns_trend_json": "[]",

        "returns_by_reason_json": "[]",

        "returns_by_product_json": "[]",

        "returns_by_category_json": "[]",

        "returns_by_region_json": "[]",

        "return_status_json": "[]",

        "return_value_distribution_json": "[]",

        "insights": [],

        "unavailable_charts": [],

        "error": None,

        "warning": None,
    }

    # ------------------------------------------------------------------
    # Load owner-safe Returns datasets
    # ------------------------------------------------------------------

    returns_datasets = get_user_datasets(
        user=request.user,
        dataset_type="Returns",
    )

    context[
        "returns_datasets"
    ] = returns_datasets

    if not returns_datasets.exists():

        context[
            "error"
        ] = (
            "Not available — Returns dataset required."
        )

        return render(
            request,
            "analytics/returns_intelligence.html",
            context,
        )

    # ------------------------------------------------------------------
    # Resolve selected dataset
    # ------------------------------------------------------------------

    dataset_id = (
        request.GET.get(
            "dataset"
        )
        or request.GET.get(
            "dataset_id"
        )
    )

    selected_dataset = None

    if dataset_id:

        try:

            selected_dataset = (
                returns_datasets
                .filter(
                    id=int(
                        dataset_id
                    )
                )
                .first()
            )

        except (
            TypeError,
            ValueError,
        ):

            selected_dataset = None

    # Invalid / missing dataset selection:
    # safely fall back to newest owner-owned dataset.
    if selected_dataset is None:

        selected_dataset = (
            returns_datasets
            .order_by(
                "-uploaded_at",
                "-id",
            )
            .first()
        )

    context[
        "selected_dataset"
    ] = selected_dataset

    # ------------------------------------------------------------------
    # Resolve current DatasetVersion
    # ------------------------------------------------------------------

    try:

        resolved = resolve_dataset(
            user=request.user,
            dataset_type="Returns",
            dataset_id=selected_dataset.id,
        )

    except Exception as exc:

        context[
            "error"
        ] = str(exc)

        return render(
            request,
            "analytics/returns_intelligence.html",
            context,
        )

    if resolved is None:

        context[
            "error"
        ] = (
            "Not available — Returns dataset required."
        )

        return render(
            request,
            "analytics/returns_intelligence.html",
            context,
        )

    dataframe = resolved.dataframe

    selected_version = (
        resolved.version
    )

    context[
        "selected_version"
    ] = selected_version

    # ------------------------------------------------------------------
    # Prepare dataframe
    # ------------------------------------------------------------------

    try:

        dataframe = prepare_returns_dataframe(
            dataframe
        )

    except Exception as exc:

        context[
            "error"
        ] = (
            "Unable to prepare the Returns dataset: "
            f"{exc}"
        )

        return render(
            request,
            "analytics/returns_intelligence.html",
            context,
        )

    if dataframe is None or dataframe.empty:

        context[
            "warning"
        ] = (
            "The selected Returns dataset contains "
            "no records."
        )

        return render(
            request,
            "analytics/returns_intelligence.html",
            context,
        )

    # ------------------------------------------------------------------
    # Determine available date range
    # ------------------------------------------------------------------

    (
        available_from_date,
        available_to_date,
    ) = get_available_returns_date_range(
        dataframe
    )

    context[
        "available_from_date"
    ] = available_from_date

    context[
        "available_to_date"
    ] = available_to_date

    selected_range = context[
        "selected_range"
    ]

    # ------------------------------------------------------------------
    # Resolve requested date range
    # ------------------------------------------------------------------

    if selected_range == "custom":

        (
            analysis_from_date,
            analysis_to_date,
        ) = resolve_custom_dates(
            request,
            available_from_date,
            available_to_date,
        )

    else:

        (
            analysis_from_date,
            analysis_to_date,
        ) = calculate_preset_dates(
            selected_range,
            available_from_date,
            available_to_date,
        )

    context[
        "analysis_from_date"
    ] = analysis_from_date

    context[
        "analysis_to_date"
    ] = analysis_to_date

    # ------------------------------------------------------------------
    # Apply date filter
    # ------------------------------------------------------------------

    filtered_dataframe, date_metadata = (
        apply_date_filter(
            dataframe,
            "Returns",
            from_date=analysis_from_date,
            to_date=analysis_to_date,
        )
    )

    if date_metadata.get(
        "warning"
    ):

        context[
            "warning"
        ] = date_metadata[
            "warning"
        ]

    # ------------------------------------------------------------------
    # Handle empty filtered result
    # ------------------------------------------------------------------

    if (
        filtered_dataframe is None
        or filtered_dataframe.empty
    ):

        context[
            "warning"
        ] = (
            "No return records are available "
            "for the selected date range."
        )

        return render(
            request,
            "analytics/returns_intelligence.html",
            context,
        )

    # ------------------------------------------------------------------
    # Re-prepare after filtering so attrs remain available
    # ------------------------------------------------------------------

    filtered_dataframe = (
        prepare_returns_dataframe(
            filtered_dataframe
        )
    )

    # ------------------------------------------------------------------
    # Calculate metrics
    # ------------------------------------------------------------------

    try:

        metrics = calculate_returns_metrics(
            filtered_dataframe
        )

    except Exception as exc:

        context[
            "error"
        ] = (
            "Unable to calculate Returns metrics: "
            f"{exc}"
        )

        return render(
            request,
            "analytics/returns_intelligence.html",
            context,
        )

    # ------------------------------------------------------------------
    # Calculate return growth
    # ------------------------------------------------------------------

    return_growth = (
        calculate_returns_growth(
            dataframe=filtered_dataframe,
            current_from_date=analysis_from_date,
            current_to_date=analysis_to_date,
        )
    )

    metrics[
        "return_growth"
    ] = return_growth

    context[
        "metrics"
    ] = metrics

    # ------------------------------------------------------------------
    # Generate chart data
    # ------------------------------------------------------------------

    unavailable_charts = []

    # Returns trend
    try:

        chart_data = returns_trend(
            filtered_dataframe
        )

        if chart_data:

            context[
                "chart_data"
            ][
                "returns_trend"
            ] = chart_data

        else:

            unavailable_charts.append(
                "Returns Trend"
            )

    except Exception:

        unavailable_charts.append(
            "Returns Trend"
        )

    # Returns by reason
    try:

        chart_data = returns_by_reason(
            filtered_dataframe
        )

        if chart_data:

            context[
                "chart_data"
            ][
                "returns_by_reason"
            ] = chart_data

        else:

            unavailable_charts.append(
                "Returns by Reason"
            )

    except Exception:

        unavailable_charts.append(
            "Returns by Reason"
        )

    # Returns by product
    try:

        chart_data = returns_by_product(
            filtered_dataframe
        )

        if chart_data:

            context[
                "chart_data"
            ][
                "returns_by_product"
            ] = chart_data

        else:

            unavailable_charts.append(
                "Returns by Product"
            )

    except Exception:

        unavailable_charts.append(
            "Returns by Product"
        )

    # Returns by category
    try:

        chart_data = returns_by_category(
            filtered_dataframe
        )

        if chart_data:

            context[
                "chart_data"
            ][
                "returns_by_category"
            ] = chart_data

        else:

            unavailable_charts.append(
                "Returns by Category"
            )

    except Exception:

        unavailable_charts.append(
            "Returns by Category"
        )

    # Returns by region
    try:

        chart_data = returns_by_region(
            filtered_dataframe
        )

        if chart_data:

            context[
                "chart_data"
            ][
                "returns_by_region"
            ] = chart_data

        else:

            unavailable_charts.append(
                "Returns by Region"
            )

    except Exception:

        unavailable_charts.append(
            "Returns by Region"
        )

    # Return status
    try:

        chart_data = returns_by_status(
            filtered_dataframe
        )

        if chart_data:

            context[
                "chart_data"
            ][
                "return_status"
            ] = chart_data

        else:

            unavailable_charts.append(
                "Return Status Distribution"
            )

    except Exception:

        unavailable_charts.append(
            "Return Status Distribution"
        )

    # Return value distribution
    try:

        chart_data = return_value_distribution(
            filtered_dataframe
        )

        if chart_data:

            context[
                "chart_data"
            ][
                "return_value_distribution"
            ] = chart_data

        else:

            unavailable_charts.append(
                "Return Value Distribution"
            )

    except Exception:

        unavailable_charts.append(
            "Return Value Distribution"
        )

    # ------------------------------------------------------------------
    # Remove duplicate unavailable chart names
    # ------------------------------------------------------------------

    context[
        "unavailable_charts"
    ] = list(
        dict.fromkeys(
            unavailable_charts
        )
    )

    # ------------------------------------------------------------------
    # Smart Returns Insights
    # ------------------------------------------------------------------

    try:

        insights = generate_returns_insights(
            metrics=metrics,

            reasons=context[
                "chart_data"
            ][
                "returns_by_reason"
            ],

            products=context[
                "chart_data"
            ][
                "returns_by_product"
            ],

            categories=context[
                "chart_data"
            ][
                "returns_by_category"
            ],

            regions=context[
                "chart_data"
            ][
                "returns_by_region"
            ],

            statuses=context[
                "chart_data"
            ][
                "return_status"
            ],

            return_growth=return_growth,
        )

        context[
            "insights"
        ] = insights

    except Exception as exc:

        context[
            "warning"
        ] = (
            context.get(
                "warning"
            )
            or
            f"Smart Returns Insights unavailable: {exc}"
        )

    # ------------------------------------------------------------------
    # JSON chart variables
    # ------------------------------------------------------------------

    context[
        "returns_trend_json"
    ] = json.dumps(
        json_safe(
            context[
                "chart_data"
            ][
                "returns_trend"
            ]
        )
    )

    context[
        "returns_by_reason_json"
    ] = json.dumps(
        json_safe(
            context[
                "chart_data"
            ][
                "returns_by_reason"
            ]
        )
    )

    context[
        "returns_by_product_json"
    ] = json.dumps(
        json_safe(
            context[
                "chart_data"
            ][
                "returns_by_product"
            ]
        )
    )

    context[
        "returns_by_category_json"
    ] = json.dumps(
        json_safe(
            context[
                "chart_data"
            ][
                "returns_by_category"
            ]
        )
    )

    context[
        "returns_by_region_json"
    ] = json.dumps(
        json_safe(
            context[
                "chart_data"
            ][
                "returns_by_region"
            ]
        )
    )

    context[
        "return_status_json"
    ] = json.dumps(
        json_safe(
            context[
                "chart_data"
            ][
                "return_status"
            ]
        )
    )

    context[
        "return_value_distribution_json"
    ] = json.dumps(
        json_safe(
            context[
                "chart_data"
            ][
                "return_value_distribution"
            ]
        )
    )

    # ------------------------------------------------------------------
    # Render dashboard
    # ------------------------------------------------------------------

    return render(
        request,
        "analytics/returns_intelligence.html",
        context,
    )
