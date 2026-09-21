
"""
Financial Intelligence View
============================

Connects the Financial Intelligence metrics layer with Django.

Architecture:
- Only authenticated users can access the page.
- Users can only access their own Financial datasets.
- Analytics always use the current DatasetVersion.
- Date filtering is applied to the resolved version.
- Missing datasets/columns produce an unavailable state instead of
  fabricated values.
"""

import json
from datetime import date, timedelta

import pandas as pd
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.metrics.financial_metrics import (
    calculate_financial_growth,
    calculate_financial_metrics,
    calculate_profit_growth,
    cash_flow_trend,
    expense_breakdown,
    financial_by_category,
    financial_by_region,
    financial_revenue_trend,
    generate_financial_insights,
    profit_by_category,
    revenue_vs_cost,
    transaction_distribution,
)

from analytics.services.dataset_resolver import (
    get_user_datasets,
    resolve_dataset,
)

from analytics.services.date_filter import (
    apply_date_filter,
    find_date_column,
)


# ---------------------------------------------------------------------------
# DATE RANGE OPTIONS
# ---------------------------------------------------------------------------

DATE_RANGE_OPTIONS = [
    ("all", "All Time"),
    ("7d", "Last 7 Days"),
    ("30d", "Last 30 Days"),
    ("3m", "Last 3 Months"),
    ("6m", "Last 6 Months"),
    ("12m", "Last 12 Months"),
    ("custom", "Custom Range"),
]


# ---------------------------------------------------------------------------
# DATE HELPERS
# ---------------------------------------------------------------------------

def get_financial_date_column(dataframe):
    """
    Find the compatible date column for Financial datasets.
    """

    return find_date_column(
        dataframe,
        "Financial",
    )


def get_available_financial_date_range(
    dataframe,
):
    """
    Return the minimum and maximum usable dates.
    """

    date_column = get_financial_date_column(
        dataframe
    )

    if not date_column:
        return None, None

    dates = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
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
    Calculate the selected preset period.

    The latest available date in the dataset is used as the endpoint.
    """

    if not latest_date:
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
            latest_date - pd.DateOffset(months=3),
            latest_date,
        )

    if selected_range == "6m":
        return (
            latest_date - pd.DateOffset(months=6),
            latest_date,
        )

    if selected_range == "12m":
        return (
            latest_date - pd.DateOffset(months=12),
            latest_date,
        )

    return None, latest_date


def resolve_custom_dates(
    from_date_value,
    to_date_value,
):
    """
    Parse custom date values supplied by the user.
    """

    parsed_from = None
    parsed_to = None

    if from_date_value:

        parsed_from = pd.to_datetime(
            from_date_value,
            errors="coerce",
        )

        if pd.isna(parsed_from):
            parsed_from = None
        else:
            parsed_from = parsed_from.date()

    if to_date_value:

        parsed_to = pd.to_datetime(
            to_date_value,
            errors="coerce",
        )

        if pd.isna(parsed_to):
            parsed_to = None
        else:
            parsed_to = parsed_to.date()

    return parsed_from, parsed_to


# ---------------------------------------------------------------------------
# JSON SAFETY
# ---------------------------------------------------------------------------

def json_safe(value):
    """
    Convert pandas/numpy/date values into JSON-safe values.
    """

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

    if isinstance(value, tuple):

        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        (
            pd.Timestamp,
            date,
        ),
    ):
        return value.isoformat()

    try:

        if pd.isna(value):
            return None

    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):

        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    return value


# ---------------------------------------------------------------------------
# MAIN VIEW
# ---------------------------------------------------------------------------

@login_required
def financial_intelligence(request):
    """
    Financial Intelligence dashboard.
    """

    financial_datasets = get_user_datasets(
        user=request.user,
        dataset_type="Financial",
    )

    selected_dataset = None
    selected_version = None

    selected_range = (
        request.GET.get(
            "range",
            "all",
        )
        or "all"
    )

    if selected_range not in {
        option[0]
        for option in DATE_RANGE_OPTIONS
    }:
        selected_range = "all"

    analysis_from_date = None
    analysis_to_date = None

    available_from_date = None
    available_to_date = None

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

    chart_data = {
        "revenue_trend": [],
        "revenue_vs_cost": [],
        "profit_by_category": [],
        "expense_breakdown": [],
        "cash_flow_trend": [],
        "financial_by_region": [],
        "transaction_distribution": [],
    }

    insights = []

    unavailable_charts = []

    error = None
    warning = None

    # ------------------------------------------------------------------
    # DATASET AVAILABILITY
    # ------------------------------------------------------------------

    if not financial_datasets.exists():

        error = (
            "Not available — Financial dataset required."
        )

    else:

        # --------------------------------------------------------------
        # DATASET SELECTION
        # --------------------------------------------------------------

        requested_dataset_id = (
            request.GET.get(
                "dataset"
            )
        )

        if requested_dataset_id:

            try:

                selected_dataset = (
                    financial_datasets
                    .filter(
                        id=int(
                            requested_dataset_id
                        )
                    )
                    .first()
                )

            except (
                TypeError,
                ValueError,
            ):

                selected_dataset = None

        # Invalid/non-owned dataset ID safely falls back to newest.
        if selected_dataset is None:

            selected_dataset = (
                financial_datasets
                .order_by(
                    "-uploaded_at",
                    "-id",
                )
                .first()
            )

        # --------------------------------------------------------------
        # CURRENT VERSION
        # --------------------------------------------------------------

        try:

            resolved = resolve_dataset(
                user=request.user,
                dataset_type="Financial",
                dataset_id=selected_dataset.id,
            )

            if resolved is None:

                error = (
                    "Not available — Financial dataset "
                    "could not be resolved."
                )

            else:

                selected_dataset = (
                    resolved.dataset
                )

                selected_version = (
                    resolved.version
                )

                dataframe = (
                    resolved.dataframe
                )

                # ------------------------------------------------------
                # PREPARE DATAFRAME
                # ------------------------------------------------------

                from analytics.metrics.financial_metrics import (
                    prepare_financial_dataframe,
                )

                dataframe = (
                    prepare_financial_dataframe(
                        dataframe
                    )
                )

                # ------------------------------------------------------
                # AVAILABLE DATE RANGE
                # ------------------------------------------------------

                (
                    available_from_date,
                    available_to_date,
                ) = get_available_financial_date_range(
                    dataframe
                )

                # ------------------------------------------------------
                # SELECT DATE RANGE
                # ------------------------------------------------------

                if (
                    selected_range == "custom"
                ):

                    custom_from = (
                        request.GET.get(
                            "from_date"
                        )
                    )

                    custom_to = (
                        request.GET.get(
                            "to_date"
                        )
                    )

                    (
                        analysis_from_date,
                        analysis_to_date,
                    ) = resolve_custom_dates(
                        custom_from,
                        custom_to,
                    )

                    if (
                        analysis_from_date is None
                        and available_from_date
                    ):
                        analysis_from_date = (
                            available_from_date
                        )

                    if (
                        analysis_to_date is None
                        and available_to_date
                    ):
                        analysis_to_date = (
                            available_to_date
                        )

                else:

                    (
                        analysis_from_date,
                        analysis_to_date,
                    ) = calculate_preset_dates(
                        available_to_date,
                        selected_range,
                    )

                # ------------------------------------------------------
                # DATE FILTER
                # ------------------------------------------------------

                filtered_dataframe, date_metadata = (
                    apply_date_filter(
                        dataframe,
                        "Financial",
                        analysis_from_date,
                        analysis_to_date,
                    )
                )

                if date_metadata.get(
                    "warning"
                ):
                    warning = date_metadata[
                        "warning"
                    ]

                # ------------------------------------------------------
                # EMPTY FILTERED DATA
                # ------------------------------------------------------

                if filtered_dataframe.empty:

                    warning = (
                        "No financial records are available "
                        "for the selected date range."
                    )

                else:

                    # --------------------------------------------------
                    # CORE METRICS
                    # --------------------------------------------------

                    metrics = (
                        calculate_financial_metrics(
                            filtered_dataframe
                        )
                    )

                    # --------------------------------------------------
                    # GROWTH
                    # --------------------------------------------------

                    revenue_growth = (
                        calculate_financial_growth(
                            dataframe,
                            analysis_from_date,
                            analysis_to_date,
                        )
                    )

                    profit_growth = (
                        calculate_profit_growth(
                            dataframe,
                            analysis_from_date,
                            analysis_to_date,
                        )
                    )

                    metrics[
                        "revenue_growth"
                    ] = revenue_growth

                    metrics[
                        "profit_growth"
                    ] = profit_growth

                    # --------------------------------------------------
                    # CHART DATA
                    # --------------------------------------------------

                    chart_data[
                        "revenue_trend"
                    ] = financial_revenue_trend(
                        filtered_dataframe
                    )

                    chart_data[
                        "revenue_vs_cost"
                    ] = revenue_vs_cost(
                        filtered_dataframe
                    )

                    chart_data[
                        "profit_by_category"
                    ] = profit_by_category(
                        filtered_dataframe
                    )

                    chart_data[
                        "expense_breakdown"
                    ] = expense_breakdown(
                        filtered_dataframe
                    )

                    chart_data[
                        "cash_flow_trend"
                    ] = cash_flow_trend(
                        filtered_dataframe
                    )

                    chart_data[
                        "financial_by_region"
                    ] = financial_by_region(
                        filtered_dataframe
                    )

                    chart_data[
                        "transaction_distribution"
                    ] = transaction_distribution(
                        filtered_dataframe
                    )

                    # --------------------------------------------------
                    # UNAVAILABLE CHARTS
                    # --------------------------------------------------

                    chart_labels = {
                        "revenue_trend": (
                            "Financial Revenue & Profit Trend"
                        ),
                        "revenue_vs_cost": (
                            "Revenue vs Cost"
                        ),
                        "profit_by_category": (
                            "Profit by Category"
                        ),
                        "expense_breakdown": (
                            "Expense Breakdown"
                        ),
                        "cash_flow_trend": (
                            "Cash Flow Trend"
                        ),
                        "financial_by_region": (
                            "Regional Financial Performance"
                        ),
                        "transaction_distribution": (
                            "Transaction Value Distribution"
                        ),
                    }

                    unavailable_charts = [
                        chart_labels[key]
                        for key, value
                        in chart_data.items()
                        if not value
                    ]

                    # --------------------------------------------------
                    # SMART INSIGHTS
                    # --------------------------------------------------

                    insights = (
                        generate_financial_insights(
                            metrics=metrics,
                            category_data=(
                                chart_data[
                                    "profit_by_category"
                                ]
                            ),
                            regional_data=(
                                chart_data[
                                    "financial_by_region"
                                ]
                            ),
                            revenue_trend=(
                                chart_data[
                                    "revenue_trend"
                                ]
                            ),
                            expense_data=(
                                chart_data[
                                    "expense_breakdown"
                                ]
                            ),
                            revenue_growth=(
                                revenue_growth
                            ),
                            profit_growth=(
                                profit_growth
                            ),
                        )
                    )

        except Exception as exc:

            error = (
                "Unable to process the Financial dataset."
            )

            # Keep a useful server-side message without exposing
            # implementation details to the browser.
            warning = str(exc)

    # ----------------------------------------------------------------------
    # JSON DATA
    # ----------------------------------------------------------------------

    chart_data = json_safe(
        chart_data
    )

    metrics = json_safe(
        metrics
    )

    insights = json_safe(
        insights
    )

    # ----------------------------------------------------------------------
    # CONTEXT
    # ----------------------------------------------------------------------

    context = {
        "financial_datasets": financial_datasets,
        "selected_dataset": selected_dataset,
        "selected_range": selected_range,
        "date_range_options": DATE_RANGE_OPTIONS,

        "analysis_from_date": (
            analysis_from_date
        ),
        "analysis_to_date": (
            analysis_to_date
        ),

        "available_from_date": (
            available_from_date
        ),
        "available_to_date": (
            available_to_date
        ),

        "selected_version": selected_version,

        "metrics": metrics,

        "chart_data": chart_data,

        "revenue_trend_json": json.dumps(
            chart_data[
                "revenue_trend"
            ]
        ),

        "revenue_vs_cost_json": json.dumps(
            chart_data[
                "revenue_vs_cost"
            ]
        ),

        "profit_by_category_json": json.dumps(
            chart_data[
                "profit_by_category"
            ]
        ),

        "expense_breakdown_json": json.dumps(
            chart_data[
                "expense_breakdown"
            ]
        ),

        "cash_flow_trend_json": json.dumps(
            chart_data[
                "cash_flow_trend"
            ]
        ),

        "financial_by_region_json": json.dumps(
            chart_data[
                "financial_by_region"
            ]
        ),

        "transaction_distribution_json": json.dumps(
            chart_data[
                "transaction_distribution"
            ]
        ),

        "insights": insights,

        "unavailable_charts": (
            unavailable_charts
        ),

        "error": error,
        "warning": warning,
    }

    return render(
        request,
        "analytics/financial_intelligence.html",
        context,
    )
