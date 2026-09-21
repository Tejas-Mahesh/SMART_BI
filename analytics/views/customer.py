# analytics/views/customer.py

import json

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from analytics.metrics.customer_metrics import (
    calculate_customer_metrics,
    customer_registration_trend,
    customers_by_region,
    customers_by_segment,
    customers_by_status,
    customer_value_distribution,
    generate_customer_insights,
    prepare_customer_dataframe,
    repeat_customer_analysis,
)

from analytics.services.dataset_resolver import (
    get_user_datasets,
    resolve_dataset,
)

from analytics.services.date_filter import (
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
# HELPERS
# ============================================================

def get_customer_date_column(
    dataframe,
    columns,
):
    """
    Determine the best available Customer date column.

    Priority:
        1. Registration_Date
        2. Last_Order_Date
        3. None
    """

    registration_column = columns.get(
        "Registration_Date"
    )

    if (
        registration_column
        and registration_column in dataframe.columns
    ):
        return registration_column

    last_order_column = columns.get(
        "Last_Order_Date"
    )

    if (
        last_order_column
        and last_order_column in dataframe.columns
    ):
        return last_order_column

    return None


def get_available_customer_date_range(
    dataframe,
    date_column,
):
    """
    Return minimum and maximum valid dates
    available in the selected Customer dataset.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not date_column
        or date_column not in dataframe.columns
    ):
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
    range_key,
    latest_date,
):
    """
    Calculate relative Customer date ranges using
    the latest date in the selected dataset.

    This intentionally does NOT use today's system date.
    """

    if latest_date is None:
        return None, None

    latest = pd.Timestamp(
        latest_date
    ).normalize()

    if range_key == "all":
        return None, None

    if range_key == "7d":

        start = (
            latest
            - pd.Timedelta(days=6)
        )

    elif range_key == "30d":

        start = (
            latest
            - pd.Timedelta(days=29)
        )

    elif range_key == "3m":

        start = (
            latest
            - pd.DateOffset(months=3)
            + pd.Timedelta(days=1)
        )

    elif range_key == "6m":

        start = (
            latest
            - pd.DateOffset(months=6)
            + pd.Timedelta(days=1)
        )

    elif range_key == "12m":

        start = (
            latest
            - pd.DateOffset(months=12)
            + pd.Timedelta(days=1)
        )

    else:
        return None, None

    return (
        start.date(),
        latest.date(),
    )


def resolve_custom_dates(
    request,
):
    """
    Safely resolve custom date inputs.
    """

    from_date = request.GET.get(
        "from_date"
    )

    to_date = request.GET.get(
        "to_date"
    )

    if not from_date or not to_date:
        return None, None

    parsed_from = pd.to_datetime(
        from_date,
        errors="coerce",
    )

    parsed_to = pd.to_datetime(
        to_date,
        errors="coerce",
    )

    if (
        pd.isna(parsed_from)
        or pd.isna(parsed_to)
    ):
        return None, None

    if parsed_to < parsed_from:
        return None, None

    return (
        parsed_from.date(),
        parsed_to.date(),
    )


def json_safe(data):
    """
    Convert Python/Pandas data into JSON suitable
    for the frontend.
    """

    return json.dumps(
        data,
        default=str,
    )


# ============================================================
# CUSTOMER ID HELPERS
# ============================================================

def get_customer_ids(
    dataframe,
    customer_column,
):
    """
    Return unique valid customer IDs.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not customer_column
        or customer_column not in dataframe.columns
    ):
        return set()

    ids = (
        dataframe[customer_column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    ids = ids[
        ids != ""
    ]

    return set(
        ids.unique().tolist()
    )


def calculate_customer_period_growth(
    dataframe,
    columns,
    current_start,
    current_end,
):
    """
    Calculate Customer Growth by comparing the selected
    period with the immediately preceding period of the
    same length.

    Returns:
        percentage or None
    """

    customer_column = columns.get(
        "Customer_ID"
    )

    date_column = columns.get(
        "Registration_Date"
    )

    # --------------------------------------------------------
    # Growth is registration-based.
    # --------------------------------------------------------

    if not date_column:

        return None

    if not customer_column:

        return None

    if (
        dataframe is None
        or dataframe.empty
        or date_column not in dataframe.columns
        or customer_column not in dataframe.columns
    ):

        return None

    if (
        current_start is None
        or current_end is None
    ):

        return None

    current_start = pd.Timestamp(
        current_start
    ).normalize()

    current_end = pd.Timestamp(
        current_end
    ).normalize()

    if current_end < current_start:

        return None

    period_days = (
        current_end
        - current_start
    ).days + 1

    if period_days <= 0:

        return None

    # --------------------------------------------------------
    # Previous comparable period.
    # --------------------------------------------------------

    previous_end = (
        current_start
        - pd.Timedelta(days=1)
    )

    previous_start = (
        previous_end
        - pd.Timedelta(
            days=period_days - 1
        )
    )

    # --------------------------------------------------------
    # Parse registration dates.
    # --------------------------------------------------------

    registration_dates = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
        dayfirst=True,
    )

    valid_dates = registration_dates.notna()

    if not valid_dates.any():

        return None

    # --------------------------------------------------------
    # Current period.
    # --------------------------------------------------------

    current_mask = (
        valid_dates
        & (
            registration_dates
            >= current_start
        )
        & (
            registration_dates
            <= current_end
        )
    )

    current_ids = get_customer_ids(
        dataframe.loc[
            current_mask
        ],
        customer_column,
    )

    # --------------------------------------------------------
    # Previous period.
    # --------------------------------------------------------

    previous_mask = (
        valid_dates
        & (
            registration_dates
            >= previous_start
        )
        & (
            registration_dates
            <= previous_end
        )
    )

    previous_ids = get_customer_ids(
        dataframe.loc[
            previous_mask
        ],
        customer_column,
    )

    current_count = len(
        current_ids
    )

    previous_count = len(
        previous_ids
    )

    # --------------------------------------------------------
    # No previous customers means no valid percentage.
    # --------------------------------------------------------

    if previous_count <= 0:

        return None

    return round(
        (
            (
                current_count
                - previous_count
            )
            / previous_count
        )
        * 100,
        2,
    )


# ============================================================
# ACTIVE CUSTOMER CALCULATION
# ============================================================

def calculate_active_customers(
    dataframe,
    columns,
):
    """
    Calculate active customers using the strongest
    available activity information.

    Priority:

        1. Customer_Status
        2. Last_Order_Date
        3. Order_Count / Total_Orders

    Returns:
        integer or None
    """

    if (
        dataframe is None
        or dataframe.empty
    ):

        return None

    customer_column = columns.get(
        "Customer_ID"
    )

    if not customer_column:

        return None

    if customer_column not in dataframe.columns:

        return None

    # --------------------------------------------------------
    # CUSTOMER STATUS
    # --------------------------------------------------------

    status_column = columns.get(
        "Customer_Status"
    )

    if (
        status_column
        and status_column in dataframe.columns
    ):

        working = dataframe.copy()

        working["_customer_id"] = (
            working[
                customer_column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        working["_status"] = (
            working[
                status_column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        working = working[
            working["_customer_id"] != ""
        ]

        active_statuses = {
            "active",
            "current",
            "engaged",
            "retained",
            "1",
            "yes",
            "true",
        }

        active = working[
            working["_status"].isin(
                active_statuses
            )
        ]

        active_ids = set(
            active[
                "_customer_id"
            ].unique().tolist()
        )

        if active_ids:

            return len(
                active_ids
            )

    # --------------------------------------------------------
    # LAST ORDER DATE
    # --------------------------------------------------------

    last_order_column = columns.get(
        "Last_Order_Date"
    )

    if (
        last_order_column
        and last_order_column in dataframe.columns
    ):

        last_order_dates = pd.to_datetime(
            dataframe[
                last_order_column
            ],
            errors="coerce",
            dayfirst=True,
        )

        active = dataframe[
            last_order_dates.notna()
        ]

        active_ids = get_customer_ids(
            active,
            customer_column,
        )

        if active_ids:

            return len(
                active_ids
            )

    # --------------------------------------------------------
    # ORDER COUNT
    # --------------------------------------------------------

    order_count_column = (
        columns.get("Order_Count")
        or columns.get("Total_Orders")
    )

    if (
        order_count_column
        and order_count_column in dataframe.columns
    ):

        order_counts = pd.to_numeric(
            dataframe[
                order_count_column
            ],
            errors="coerce",
        )

        active = dataframe[
            order_counts > 0
        ]

        active_ids = get_customer_ids(
            active,
            customer_column,
        )

        if active_ids:

            return len(
                active_ids
            )

    # --------------------------------------------------------
    # No usable activity field.
    # --------------------------------------------------------

    return None


# ============================================================
# CUSTOMER INTELLIGENCE
# ============================================================

@login_required
def customer_intelligence(
    request,
):
    """
    Customer Intelligence dashboard.

    Uses the selected user's current Customer
    DatasetVersion.
    """

    # ========================================================
    # CUSTOMER DATASETS
    # ========================================================

    customer_datasets = (
        get_user_datasets(
            request.user,
            "Customers",
        )
    )

    selected_dataset_id = (
        request.GET.get("dataset")
        or request.GET.get("dataset_id")
    )

    selected_dataset = None

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

    if selected_dataset_id:

        selected_dataset = next(
            (
                dataset
                for dataset in customer_datasets
                if dataset.id
                == selected_dataset_id
            ),
            None,
        )

    if selected_dataset is None:

        if customer_datasets:

            selected_dataset = (
                customer_datasets.first()
            )

    # ========================================================
    # BASE CONTEXT
    # ========================================================

    context = {
        "customer_datasets": (
            customer_datasets
        ),

        "selected_dataset": (
            selected_dataset
        ),

        "date_range_options": (
            DATE_RANGE_OPTIONS
        ),

        "selected_range": (
            request.GET.get(
                "range",
                "all",
            )
        ),

        "analysis_from_date": None,

        "analysis_to_date": None,

        "available_from_date": None,

        "available_to_date": None,

        "metrics": {
            "total_customers": None,
            "new_customers": None,
            "active_customers": None,
            "repeat_customers": None,
            "average_customer_value": None,
            "average_orders_per_customer": None,
            "customer_growth": None,
        },

        "chart_data": {
            "registration_trend": [],
            "regions": [],
            "segments": [],
            "statuses": [],
            "value_distribution": [],
        },

        "insights": [],

        "missing_required_columns": [],

        "unavailable_charts": [],

        "error": None,

        "warning": None,
    }

    # ========================================================
    # NO DATASET
    # ========================================================

    if selected_dataset is None:

        context["error"] = (
            "Customer dataset required."
        )

        return render(
            request,
            "analytics/customer_intelligence.html",
            context,
        )

    # ========================================================
    # RESOLVE CURRENT DATASET VERSION
    # ========================================================

    try:

        resolved = resolve_dataset(
            request.user,
            "Customers",
            dataset_id=(
                selected_dataset.id
            ),
        )

    except Exception as exc:

        context["error"] = str(
            exc
        )

        return render(
            request,
            "analytics/customer_intelligence.html",
            context,
        )

    if resolved is None:

        context["error"] = (
            "Selected Customer dataset "
            "is not available."
        )

        return render(
            request,
            "analytics/customer_intelligence.html",
            context,
        )

    dataframe = resolved.dataframe

    context[
        "selected_version"
    ] = resolved.version

    # ========================================================
    # PREPARE DATAFRAME
    # ========================================================

    (
        prepared_dataframe,
        columns,
        missing_required_columns,
    ) = prepare_customer_dataframe(
        dataframe
    )

    context[
        "missing_required_columns"
    ] = missing_required_columns

    if missing_required_columns:

        context["error"] = (
            "Insufficient Customer data. "
            "Required column(s): "
            + ", ".join(
                missing_required_columns
            )
        )

        return render(
            request,
            "analytics/customer_intelligence.html",
            context,
        )

    # ========================================================
    # DATE INFORMATION
    # ========================================================

    date_column = (
        get_customer_date_column(
            prepared_dataframe,
            columns,
        )
    )

    (
        available_from_date,
        available_to_date,
    ) = get_available_customer_date_range(
        prepared_dataframe,
        date_column,
    )

    context[
        "available_from_date"
    ] = available_from_date

    context[
        "available_to_date"
    ] = available_to_date

    selected_range = (
        request.GET.get(
            "range",
            "all",
        )
    )

    # ========================================================
    # SELECTED DATE RANGE
    # ========================================================

    if selected_range == "custom":

        (
            analysis_from_date,
            analysis_to_date,
        ) = resolve_custom_dates(
            request
        )

        if (
            analysis_from_date is None
            or analysis_to_date is None
        ):

            context["warning"] = (
                "Please provide a valid "
                "custom date range."
            )

            # Use the complete available range
            # for the dashboard instead of leaving
            # the dataframe in an ambiguous state.

            analysis_from_date = (
                available_from_date
            )

            analysis_to_date = (
                available_to_date
            )

    elif selected_range == "all":

        analysis_from_date = (
            available_from_date
        )

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

    filtered_dataframe = (
        prepared_dataframe.copy()
    )

    if (
        analysis_from_date is not None
        or analysis_to_date is not None
    ):

        (
            filtered_dataframe,
            date_metadata,
        ) = apply_date_filter(
            prepared_dataframe,
            "Customers",
            analysis_from_date,
            analysis_to_date,
        )

        if date_metadata.get(
            "warning"
        ):

            context["warning"] = (
                date_metadata[
                    "warning"
                ]
            )

    # ========================================================
    # BASIC CUSTOMER METRICS
    # ========================================================

    metrics = calculate_customer_metrics(
        filtered_dataframe,
        columns,
    )

    # ========================================================
    # ACTIVE CUSTOMERS
    # ========================================================
    #
    # calculate_customer_metrics() may calculate this when
    # activity information is available. We explicitly
    # calculate it here as well so the dashboard always
    # receives the value from the selected date range.
    # ========================================================

    active_customers = (
        calculate_active_customers(
            filtered_dataframe,
            columns,
        )
    )

    if active_customers is not None:

        metrics[
            "active_customers"
        ] = active_customers

    # ========================================================
    # REPEAT CUSTOMER ANALYSIS
    # ========================================================

    repeat_analysis = (
        repeat_customer_analysis(
            filtered_dataframe,
            columns,
        )
    )

    if (
        repeat_analysis.get(
            "new_customers"
        )
        is not None
    ):

        metrics[
            "new_customers"
        ] = repeat_analysis[
            "new_customers"
        ]

    if (
        repeat_analysis.get(
            "repeat_customers"
        )
        is not None
    ):

        metrics[
            "repeat_customers"
        ] = repeat_analysis[
            "repeat_customers"
        ]

    # ========================================================
    # CUSTOMER GROWTH
    # ========================================================
    #
    # Growth is based on Registration_Date.
    #
    # For:
    #   7d   -> previous 7 days
    #   30d  -> previous 30 days
    #   3m   -> previous equivalent number of days
    #   6m   -> previous equivalent number of days
    #   12m  -> previous equivalent number of days
    #   custom -> previous equivalent number of days
    #
    # All Time has no meaningful previous period and therefore
    # intentionally returns None.
    # ========================================================

    metrics[
        "customer_growth"
    ] = None

    if (
        selected_range != "all"
        and date_column
        and columns.get(
            "Registration_Date"
        )
        and analysis_from_date is not None
        and analysis_to_date is not None
    ):

        metrics[
            "customer_growth"
        ] = calculate_customer_period_growth(
            prepared_dataframe,
            columns,
            analysis_from_date,
            analysis_to_date,
        )

    # ========================================================
    # STORE METRICS
    # ========================================================

    context[
        "metrics"
    ] = metrics

    # ========================================================
    # CHARTS
    # ========================================================

    registration_trend = (
        customer_registration_trend(
            filtered_dataframe,
            columns,
            aggregation="auto",
        )
    )

    regions = customers_by_region(
        filtered_dataframe,
        columns,
    )

    segments = customers_by_segment(
        filtered_dataframe,
        columns,
    )

    statuses = customers_by_status(
        filtered_dataframe,
        columns,
    )

    value_distribution = (
        customer_value_distribution(
            filtered_dataframe,
            columns,
        )
    )

    context[
        "chart_data"
    ] = {
        "registration_trend": (
            registration_trend
        ),

        "regions": regions,

        "segments": segments,

        "statuses": statuses,

        "value_distribution": (
            value_distribution
        ),
    }

    # ========================================================
    # INDIVIDUAL CHART AVAILABILITY
    # ========================================================

    unavailable_charts = []

    if not registration_trend:

        unavailable_charts.append(
            "Customer Registration Trend"
        )

    if not regions:

        unavailable_charts.append(
            "Customers by Region"
        )

    if not segments:

        unavailable_charts.append(
            "Customers by Segment"
        )

    if not statuses:

        unavailable_charts.append(
            "Customers by Status"
        )

    if not value_distribution:

        unavailable_charts.append(
            "Customer Value Distribution"
        )

    context[
        "unavailable_charts"
    ] = unavailable_charts

    # ========================================================
    # SMART INSIGHTS
    # ========================================================

    context[
        "insights"
    ] = generate_customer_insights(
        metrics,
        customer_segments=segments,
        regions=regions,
    )

    # ========================================================
    # JSON DATA
    # ========================================================

    context[
        "registration_trend_json"
    ] = json_safe(
        registration_trend
    )

    context[
        "regions_json"
    ] = json_safe(
        regions
    )

    context[
        "segments_json"
    ] = json_safe(
        segments
    )

    context[
        "statuses_json"
    ] = json_safe(
        statuses
    )

    context[
        "value_distribution_json"
    ] = json_safe(
        value_distribution
    )

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "analytics/customer_intelligence.html",
        context,
    )