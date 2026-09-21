from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.services.dashboard_service import (
    DASHBOARD_DATASET_TYPES,
    DATASET_TYPE_LABELS,
    get_available_dashboard_datasets,
    resolve_executive_dashboard,
)


logger = logging.getLogger(__name__)


# ============================================================
# DATE RANGE OPTIONS
# ============================================================

DATE_RANGE_OPTIONS = [
    ("all", "All Available Data"),
    ("7d", "Last 7 Days"),
    ("30d", "Last 30 Days"),
    ("3m", "Last 3 Months"),
    ("6m", "Last 6 Months"),
    ("12m", "Last 12 Months"),
    ("custom", "Custom Range"),
]


VALID_DATE_RANGES = {
    option[0]
    for option in DATE_RANGE_OPTIONS
}


# ============================================================
# APPROVAL
# ============================================================

def dashboard_user_is_approved(request) -> bool:
    """
    Executive Dashboard is available only to authenticated
    approved users.
    """

    if not request.user.is_authenticated:
        return False

    return (
        getattr(
            request.user,
            "approval_status",
            None,
        )
        == "Approved"
    )


# ============================================================
# DATE PARSER
# ============================================================

def parse_date(
    value: Optional[str],
) -> Optional[date]:
    """
    Convert YYYY-MM-DD into a date.

    Invalid values return None.
    """

    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()

    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# DATE RANGE RESOLUTION
# ============================================================

def resolve_date_range(
    request,
) -> tuple[
    str,
    Optional[date],
    Optional[date],
    Optional[str],
]:
    """
    Resolve the dashboard date-range controls.

    Returns:

        date_range
        from_date
        to_date
        date_error

    Date filtering itself is NOT performed here.

    The dates are passed to dashboard_service, and the
    dashboard metrics layer applies them to the dataframe.
    """

    date_range = request.GET.get(
        "date_range",
        "all",
    )

    if date_range not in VALID_DATE_RANGES:
        date_range = "all"

    # --------------------------------------------------------
    # ALL DATA
    # --------------------------------------------------------

    if date_range == "all":
        return (
            date_range,
            None,
            None,
            None,
        )

    # --------------------------------------------------------
    # CUSTOM
    # --------------------------------------------------------

    if date_range == "custom":

        from_date = parse_date(
            request.GET.get(
                "from_date"
            )
        )

        to_date = parse_date(
            request.GET.get(
                "to_date"
            )
        )

        if not from_date or not to_date:
            return (
                date_range,
                from_date,
                to_date,
                (
                    "Please provide both a start date "
                    "and an end date."
                ),
            )

        if from_date > to_date:
            return (
                date_range,
                from_date,
                to_date,
                (
                    "The start date cannot be later "
                    "than the end date."
                ),
            )

        return (
            date_range,
            from_date,
            to_date,
            None,
        )

    # --------------------------------------------------------
    # RELATIVE DATE RANGES
    # --------------------------------------------------------

    today = date.today()

    if date_range == "7d":

        from_date = today - timedelta(
            days=6
        )

    elif date_range == "30d":

        from_date = today - timedelta(
            days=29
        )

    elif date_range == "3m":

        from_date = today - timedelta(
            days=89
        )

    elif date_range == "6m":

        from_date = today - timedelta(
            days=179
        )

    elif date_range == "12m":

        from_date = today - timedelta(
            days=364
        )

    else:

        return (
            "all",
            None,
            None,
            None,
        )

    return (
        date_range,
        from_date,
        today,
        None,
    )


# ============================================================
# DASHBOARD DATASET OPTIONS
# ============================================================

def get_dashboard_dataset_options(user):
    """
    Retrieve every active dataset available to the user.

    The selector contains:

        Overall Business Intelligence

    followed by every actual uploaded dataset.

    Multiple datasets in the same category are preserved.
    """

    datasets = []

    try:

        available = get_available_dashboard_datasets(
            user
        )

    except Exception:

        logger.exception(
            "Unable to retrieve dashboard datasets."
        )

        return datasets

    for dataset in available:

        dataset_type = getattr(
            dataset,
            "dataset_type",
            None,
        )

        if dataset_type not in DASHBOARD_DATASET_TYPES:
            continue

        datasets.append(
            {
                "dataset": dataset,

                "dataset_type": dataset_type,

                "dataset_type_label": (
                    DATASET_TYPE_LABELS.get(
                        dataset_type,
                        dataset_type,
                    )
                ),

                "id": dataset.id,

                "name": getattr(
                    dataset,
                    "name",
                    f"Dataset {dataset.id}",
                ),

                "uploaded_at": getattr(
                    dataset,
                    "uploaded_at",
                    None,
                ),
            }
        )

    # --------------------------------------------------------
    # Newest datasets first
    # --------------------------------------------------------

    def sort_key(item):

        uploaded_at = item.get(
            "uploaded_at"
        )

        if uploaded_at is None:
            return 0.0

        try:

            return uploaded_at.timestamp()

        except (
            AttributeError,
            OSError,
            OverflowError,
            ValueError,
        ):

            return 0.0

    datasets.sort(
        key=sort_key,
        reverse=True,
    )

    return datasets


# ============================================================
# SELECTED DATASET
# ============================================================

def get_selected_dataset_parameters(
    request,
):
    """
    Read dataset selector values from GET parameters.

    No dataset means:

        Overall Business Intelligence
    """

    dataset_id = request.GET.get(
        "dataset"
    )

    dataset_type = request.GET.get(
        "dataset_type"
    )

    if not dataset_id:
        dataset_id = None

    if dataset_type not in DASHBOARD_DATASET_TYPES:
        dataset_type = None

    return (
        dataset_id,
        dataset_type,
    )


# ============================================================
# SAFE DATA EXTRACTION
# ============================================================

def get_dashboard_kpis(
    dashboard_data: dict[str, Any],
) -> list:
    """
    Safely retrieve KPI data.

    KPI calculation belongs to dashboard_metrics.py.
    """

    kpis = dashboard_data.get(
        "kpis",
        [],
    )

    if not isinstance(kpis, list):
        return []

    return kpis


def get_dashboard_charts(
    dashboard_data: dict[str, Any],
) -> dict:
    """
    Safely retrieve chart data.

    Chart calculation belongs to dashboard_metrics.py.
    """

    charts = dashboard_data.get(
        "charts",
        {},
    )

    if not isinstance(charts, dict):
        return {}

    return charts


# ============================================================
# DATASET SUMMARY
# ============================================================

def build_dataset_summary(
    dashboard_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Create lightweight dataset information for the template.

    No business metrics are calculated here.
    """

    datasets = dashboard_data.get(
        "datasets",
        {},
    )

    if not isinstance(datasets, dict):

        return {
            "count": 0,
            "types": [],
            "names": [],
        }

    types = []
    names = []

    for (
        dataset_type,
        dashboard_dataset,
    ) in datasets.items():

        if dataset_type not in types:
            types.append(
                dataset_type
            )

        dataset = getattr(
            dashboard_dataset,
            "dataset",
            None,
        )

        if dataset is not None:

            name = getattr(
                dataset,
                "name",
                None,
            )

            if name:
                names.append(name)

    return {
        "count": len(datasets),
        "types": types,
        "names": names,
    }


# ============================================================
# DATE RANGE PAYLOAD
# ============================================================

def build_date_range_payload(
    date_range: str,
    from_date: Optional[date],
    to_date: Optional[date],
    date_error: Optional[str],
) -> dict[str, Any]:
    """
    Build a template-friendly date range structure.
    """

    return {
        "value": date_range,

        "from_date": from_date,

        "to_date": to_date,

        "from_date_iso": (
            from_date.isoformat()
            if from_date
            else ""
        ),

        "to_date_iso": (
            to_date.isoformat()
            if to_date
            else ""
        ),

        "is_custom": (
            date_range == "custom"
        ),

        "has_error": (
            date_error is not None
        ),
    }


# ============================================================
# JSON SERIALIZATION
# ============================================================

def serialize_dashboard_json(
    value: Any,
) -> str:
    """
    Convert dashboard data into JSON for JavaScript.

    The dashboard metrics layer should already return
    JSON-compatible structures.

    default=str protects against pandas timestamps and
    other non-JSON-native values.
    """

    try:

        return json.dumps(
            value,
            default=str,
            allow_nan=False,
        )

    except (
        TypeError,
        ValueError,
    ):

        return "{}"


# ============================================================
# SAFE DASHBOARD FALLBACK
# ============================================================

def empty_dashboard_response(
    mode: str = "overall",
    error: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return a safe dashboard response when the service fails.
    """

    return {
        "mode": mode,
        "dataset_count": 0,
        "available_types": [],
        "datasets": {},
        "selected": None,
        "category_results": {},
        "kpis": [],
        "charts": {},
        "insights": [],
        "forecasts": [],
        "anomalies": [],
        "risks": [],
        "recommendations": [],
        "error": error,
    }


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

@login_required
def executive_dashboard(request):
    """
    Executive Business Intelligence Dashboard.

    --------------------------------------------------------
    MODE 1: OVERALL BUSINESS INTELLIGENCE
    --------------------------------------------------------

    /analytics/dashboard/

    No dataset parameter.

    The service selects the latest uploaded dataset from
    every available supported category.

    Example:

        Latest Sales
        Latest Customers
        Latest Products
        Latest Regional
        Latest Marketing
        Latest Financial
        Latest Returns

    Each selected dataset is analyzed from its CLEANED
    DatasetVersion.

    Missing categories are ignored.

    --------------------------------------------------------
    MODE 2: SINGLE DATASET INTELLIGENCE
    --------------------------------------------------------

    /analytics/dashboard/?dataset=15

    Only dataset 15 is analyzed.

    The dashboard does NOT combine it with other datasets.

    --------------------------------------------------------
    ARCHITECTURE
    --------------------------------------------------------

        View
          ↓
        dashboard_service
          ↓
        Cleaned DatasetVersion
          ↓
        dashboard_metrics.py
          ↓
        Template

    business_metrics.py is intentionally NOT used.
    """

    # ========================================================
    # APPROVAL
    # ========================================================

    if not dashboard_user_is_approved(request):

        return render(
            request,
            "analytics/executive_dashboard.html",
            {
                "dashboard_error": (
                    "Your account must be approved "
                    "before accessing the Executive Dashboard."
                ),

                "dashboard_datasets": [],

                "dashboard_mode": "overall",

                "is_overall_dashboard": True,

                "is_selected_dashboard": False,

                "kpis": [],

                "charts": {},

                "insights": [],

                "forecasts": [],

                "anomalies": [],

                "risks": [],

                "recommendations": [],

                "dashboard_data_json": "{}",

                "dashboard_charts_json": "{}",
            },
        )

    # ========================================================
    # DATE RANGE
    # ========================================================

    (
        date_range,
        from_date,
        to_date,
        date_error,
    ) = resolve_date_range(
        request
    )

    # ========================================================
    # DATASET SELECTOR
    # ========================================================

    dataset_options = (
        get_dashboard_dataset_options(
            request.user
        )
    )

    (
        dataset_id,
        dataset_type,
    ) = get_selected_dataset_parameters(
        request
    )

    # ========================================================
    # DASHBOARD MODE
    # ========================================================

    requested_mode = (
        "selected"
        if dataset_id
        else "overall"
    )

    # ========================================================
    # DASHBOARD RESOLUTION
    # ========================================================

    try:

        dashboard_data = (
            resolve_executive_dashboard(
                user=request.user,

                dataset_id=dataset_id,

                dataset_type=dataset_type,

                from_date=from_date,

                to_date=to_date,
            )
        )

    except Exception:

        logger.exception(
            "Executive Dashboard failed for user %s",
            request.user.pk,
        )

        dashboard_data = empty_dashboard_response(
            mode=requested_mode,
            error=(
                "The Executive Dashboard could not "
                "load the selected data."
            ),
        )

    # ========================================================
    # SAFETY
    # ========================================================

    if not isinstance(
        dashboard_data,
        dict,
    ):

        dashboard_data = empty_dashboard_response(
            mode=requested_mode,
            error=(
                "The Executive Dashboard returned "
                "an invalid response."
            ),
        )

    # ========================================================
    # DATE ERROR
    # ========================================================

    if date_error:

        dashboard_data["date_range_error"] = (
            date_error
        )

    # ========================================================
    # SERVICE ERROR
    # ========================================================

    dashboard_error = dashboard_data.get(
        "error"
    )

    # ========================================================
    # MODE
    # ========================================================

    dashboard_mode = dashboard_data.get(
        "mode",
        requested_mode,
    )

    if dashboard_mode not in {
        "overall",
        "selected",
    }:

        dashboard_mode = requested_mode

    is_overall_dashboard = (
        dashboard_mode == "overall"
    )

    is_selected_dashboard = (
        dashboard_mode == "selected"
    )

    # ========================================================
    # SELECTED DATASET
    # ========================================================

    selected_dashboard_dataset = (
        dashboard_data.get(
            "selected"
        )
    )

    selected_dataset = None

    selected_version = None

    if selected_dashboard_dataset:

        selected_dataset = getattr(
            selected_dashboard_dataset,
            "dataset",
            None,
        )

        selected_version = getattr(
            selected_dashboard_dataset,
            "version",
            None,
        )

    # ========================================================
    # DATASET SUMMARY
    # ========================================================

    dataset_summary = (
        build_dataset_summary(
            dashboard_data
        )
    )

    available_dataset_types = (
        dashboard_data.get(
            "available_types",
            [],
        )
    )

    if not isinstance(
        available_dataset_types,
        list,
    ):

        available_dataset_types = []

    # ========================================================
    # KPIs
    # ========================================================

    kpis = get_dashboard_kpis(
        dashboard_data
    )

    # ========================================================
    # CHARTS
    # ========================================================

    charts = get_dashboard_charts(
        dashboard_data
    )

    # ========================================================
    # INTELLIGENCE
    # ========================================================

    insights = dashboard_data.get(
        "insights",
        [],
    )

    if not isinstance(
        insights,
        list,
    ):

        insights = []

    forecasts = dashboard_data.get(
        "forecasts",
        [],
    )

    if not isinstance(
        forecasts,
        list,
    ):

        forecasts = []

    anomalies = dashboard_data.get(
        "anomalies",
        [],
    )

    if not isinstance(
        anomalies,
        list,
    ):

        anomalies = []

    risks = dashboard_data.get(
        "risks",
        [],
    )

    if not isinstance(
        risks,
        list,
    ):

        risks = []

    recommendations = (
        dashboard_data.get(
            "recommendations",
            [],
        )
    )

    if not isinstance(
        recommendations,
        list,
    ):

        recommendations = []

    # ========================================================
    # CATEGORY RESULTS
    # ========================================================

    category_results = (
        dashboard_data.get(
            "category_results",
            {},
        )
    )

    if not isinstance(
        category_results,
        dict,
    ):

        category_results = {}

    # ========================================================
    # OVERALL DATASETS
    # ========================================================

    overall_datasets = (
        dashboard_data.get(
            "datasets",
            {},
        )
    )

    if not isinstance(
        overall_datasets,
        dict,
    ):

        overall_datasets = {}

    # ========================================================
    # DATE RANGE PAYLOAD
    # ========================================================

    selected_date_range = (
        build_date_range_payload(
            date_range=date_range,
            from_date=from_date,
            to_date=to_date,
            date_error=date_error,
        )
    )

    # ========================================================
    # SELECTED DATASET ID
    # ========================================================

    selected_dataset_id = None

    if selected_dataset is not None:

        selected_dataset_id = getattr(
            selected_dataset,
            "id",
            None,
        )

    if selected_dataset_id is None:

        selected_dataset_id = dataset_id

    # ========================================================
    # NORMALIZE DATASET ID
    # ========================================================

    if selected_dataset_id is not None:

        selected_dataset_id = str(
            selected_dataset_id
        )

    # ========================================================
    # SELECTED DATASET TYPE
    # ========================================================

    selected_dataset_type = None

    if selected_dataset is not None:

        selected_dataset_type = getattr(
            selected_dataset,
            "dataset_type",
            None,
        )

    if selected_dataset_type is None:

        selected_dataset_type = dataset_type

    # ========================================================
    # DISPLAY LABEL
    # ========================================================

    selected_dataset_type_label = (
        DATASET_TYPE_LABELS.get(
            selected_dataset_type,
            selected_dataset_type,
        )
        if selected_dataset_type
        else None
    )

    # ========================================================
    # JSON
    # ========================================================

    dashboard_charts_json = (
        serialize_dashboard_json(
            charts
        )
    )

    dashboard_data_json = (
        serialize_dashboard_json(
            dashboard_data
        )
    )

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        # ----------------------------------------------------
        # Dataset selector
        # ----------------------------------------------------

        "dashboard_datasets": dataset_options,

        "selected_dataset": selected_dataset,

        "selected_dataset_id": selected_dataset_id,

        "selected_dataset_type": selected_dataset_type,

        "selected_dataset_type_label": (
            selected_dataset_type_label
        ),

        # ----------------------------------------------------
        # Dashboard mode
        # ----------------------------------------------------

        "dashboard_mode": dashboard_mode,

        "is_overall_dashboard": (
            is_overall_dashboard
        ),

        "is_selected_dashboard": (
            is_selected_dashboard
        ),

        # ----------------------------------------------------
        # Dataset summary
        # ----------------------------------------------------

        "dataset_summary": dataset_summary,

        "dataset_count": dashboard_data.get(
            "dataset_count",
            0,
        ),

        "available_dataset_types": (
            available_dataset_types
        ),

        # ----------------------------------------------------
        # Cleaned version
        # ----------------------------------------------------

        "current_version": selected_version,

        "selected_version": selected_version,

        # ----------------------------------------------------
        # Main dashboard data
        # ----------------------------------------------------

        "dashboard_data": dashboard_data,

        "dashboard_data_json": (
            dashboard_data_json
        ),

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        "kpis": kpis,

        # ----------------------------------------------------
        # Charts
        # ----------------------------------------------------

        "charts": charts,

        "dashboard_charts_json": (
            dashboard_charts_json
        ),

        # ----------------------------------------------------
        # Category results
        # ----------------------------------------------------

        "category_results": (
            category_results
        ),

        "overall_datasets": (
            overall_datasets
        ),

        # ----------------------------------------------------
        # Intelligence
        # ----------------------------------------------------

        "insights": insights,

        "forecasts": forecasts,

        "anomalies": anomalies,

        "risks": risks,

        "recommendations": recommendations,

        # ----------------------------------------------------
        # Date filtering
        # ----------------------------------------------------

        "date_range_options": (
            DATE_RANGE_OPTIONS
        ),

        "selected_date_range": (
            date_range
        ),

        "selected_from_date": (
            from_date
        ),

        "selected_to_date": (
            to_date
        ),

        "dashboard_date_range": (
            selected_date_range
        ),

        "date_error": (
            date_error
        ),

        # ----------------------------------------------------
        # Dashboard metadata
        # ----------------------------------------------------

        "dashboard_title": (
            "Executive Business Intelligence"
        ),

        "dashboard_subtitle": (
            "Overall Business Intelligence"
            if is_overall_dashboard
            else "Single Dataset Intelligence"
        ),

        # ----------------------------------------------------
        # Messages
        # ----------------------------------------------------

        "dashboard_error": (
            dashboard_error
            or date_error
        ),

        "dashboard_warning": (
            dashboard_data.get(
                "warning"
            )
        ),
    }

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "analytics/executive_dashboard.html",
        context,
    )