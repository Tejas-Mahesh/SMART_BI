import numpy as np
import pandas as pd


# ============================================================
# FUTURE TRENDS SERVICE
# ============================================================


# ------------------------------------------------------------
# DATE COLUMN DETECTION
# ------------------------------------------------------------

def detect_date_columns(dataframe):
    """
    Detect columns that can reasonably be used as date/time
    dimensions for trend analysis.

    Detection uses:
    1. Existing datetime dtype
    2. Common date/time column names
    3. Successful datetime conversion
    """

    date_columns = []

    for column in dataframe.columns:

        series = dataframe[column]

        # Already datetime
        if pd.api.types.is_datetime64_any_dtype(series):

            date_columns.append(str(column))
            continue

        column_name = (
            str(column)
            .strip()
            .lower()
        )

        # Strong name-based indicators
        name_indicator = (
            "date" in column_name
            or
            "time" in column_name
            or
            "month" in column_name
            or
            "year" in column_name
        )

        if not name_indicator:
            continue

        converted = pd.to_datetime(
            series,
            errors="coerce"
        )

        valid_count = int(
            converted.notna().sum()
        )

        total_non_null = int(
            series.notna().sum()
        )

        if (
            valid_count > 0
            and
            (
                total_non_null == 0
                or
                valid_count / total_non_null >= 0.5
            )
        ):

            date_columns.append(str(column))

    return date_columns


# ------------------------------------------------------------
# NUMERIC METRIC DETECTION
# ------------------------------------------------------------

def detect_numeric_columns(dataframe):
    """
    Return numeric columns that can be used as trend metrics.
    """

    numeric_columns = []

    for column in dataframe.columns:

        series = dataframe[column]

        if pd.api.types.is_numeric_dtype(series):

            numeric_columns.append(
                str(column)
            )

    return numeric_columns


# ------------------------------------------------------------
# PREPARE TIME SERIES
# ------------------------------------------------------------

def prepare_time_series(
    dataframe,
    date_column,
    metric_column,
    frequency="M",
):
    """
    Convert the selected dataframe columns into an aggregated
    time series.

    Returns:
        pandas DataFrame with:
            period
            value
    """

    if dataframe is None:

        raise ValueError(
            "Dataset data was not provided."
        )

    if date_column not in dataframe.columns:

        raise ValueError(
            f"Date column '{date_column}' was not found."
        )

    if metric_column not in dataframe.columns:

        raise ValueError(
            f"Metric column '{metric_column}' was not found."
        )

    # --------------------------------------------------------
    # COPY
    # --------------------------------------------------------

    working_dataframe = dataframe[
        [
            date_column,
            metric_column,
        ]
    ].copy()

    # --------------------------------------------------------
    # DATE CONVERSION
    # --------------------------------------------------------

    working_dataframe[
        date_column
    ] = pd.to_datetime(
        working_dataframe[date_column],
        errors="coerce"
    )

    # --------------------------------------------------------
    # NUMERIC CONVERSION
    # --------------------------------------------------------

    working_dataframe[
        metric_column
    ] = pd.to_numeric(
        working_dataframe[metric_column],
        errors="coerce"
    )

    # --------------------------------------------------------
    # REMOVE INVALID VALUES
    # --------------------------------------------------------

    working_dataframe = (
        working_dataframe
        .dropna(
            subset=[
                date_column,
                metric_column,
            ]
        )
    )

    if working_dataframe.empty:

        raise ValueError(
            "No valid date and numeric values were found "
            "for the selected columns."
        )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    working_dataframe = (
        working_dataframe
        .sort_values(
            by=date_column
        )
    )

    # --------------------------------------------------------
    # NORMALIZE FREQUENCY
    # --------------------------------------------------------

    frequency = (
        str(frequency)
        .strip()
        .upper()
    )

    allowed_frequencies = {
        "D": "Daily",
        "W": "Weekly",
        "M": "Monthly",
        "Q": "Quarterly",
        "Y": "Yearly",
    }

    if frequency not in allowed_frequencies:

        raise ValueError(
            "Unsupported frequency. "
            "Use D, W, M, Q, or Y."
        )

    # --------------------------------------------------------
    # AGGREGATION
    # --------------------------------------------------------

    grouped = (
        working_dataframe
        .set_index(date_column)[metric_column]
        .resample(frequency)
        .sum()
        .dropna()
    )

    if grouped.empty:

        raise ValueError(
            "No time-series values could be generated "
            "for the selected frequency."
        )

    result = (
        grouped
        .reset_index()
        .rename(
            columns={
                date_column: "period",
                metric_column: "value",
            }
        )
    )

    # --------------------------------------------------------
    # REMOVE EMPTY / INVALID VALUES
    # --------------------------------------------------------

    result = result[
        result["value"].notna()
    ].copy()

    if result.empty:

        raise ValueError(
            "The generated time series contains no valid values."
        )

    return result


# ------------------------------------------------------------
# TREND DIRECTION
# ------------------------------------------------------------

def calculate_trend_direction(values):
    """
    Determine the overall direction using linear regression
    slope.

    Returns:
        Increasing
        Decreasing
        Stable
    """

    numeric_values = np.asarray(
        values,
        dtype=float
    )

    numeric_values = (
        numeric_values[
            np.isfinite(numeric_values)
        ]
    )

    if len(numeric_values) < 2:

        return "Stable"

    x = np.arange(
        len(numeric_values),
        dtype=float
    )

    slope = np.polyfit(
        x,
        numeric_values,
        1
    )[0]

    mean_value = float(
        np.mean(
            np.abs(
                numeric_values
            )
        )
    )

    # Avoid treating tiny numerical movements as trends.
    tolerance = max(
        mean_value * 0.001,
        1e-12
    )

    if slope > tolerance:

        return "Increasing"

    if slope < -tolerance:

        return "Decreasing"

    return "Stable"


# ------------------------------------------------------------
# TREND STRENGTH
# ------------------------------------------------------------

def calculate_trend_strength(values):
    """
    Calculate trend strength using the absolute correlation
    between time and metric values.

    Returns:
        Strong
        Moderate
        Weak
    """

    numeric_values = np.asarray(
        values,
        dtype=float
    )

    if len(numeric_values) < 3:

        return "Weak"

    x = np.arange(
        len(numeric_values),
        dtype=float
    )

    if np.std(numeric_values) == 0:

        return "Weak"

    correlation = np.corrcoef(
        x,
        numeric_values
    )[0, 1]

    if not np.isfinite(correlation):

        return "Weak"

    strength = abs(
        float(correlation)
    )

    if strength >= 0.70:

        return "Strong"

    if strength >= 0.40:

        return "Moderate"

    return "Weak"


# ------------------------------------------------------------
# PERCENTAGE CHANGE
# ------------------------------------------------------------

def calculate_percentage_change(
    first_value,
    latest_value,
):
    """
    Calculate percentage change from the first period
    to the latest period.
    """

    if first_value is None:
        return None

    if latest_value is None:
        return None

    try:

        first_value = float(
            first_value
        )

        latest_value = float(
            latest_value
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if not np.isfinite(first_value):

        return None

    if not np.isfinite(latest_value):

        return None

    if first_value == 0:

        return None

    percentage = (
        (
            latest_value
            -
            first_value
        )
        /
        abs(first_value)
    ) * 100

    return round(
        float(percentage),
        2
    )


# ------------------------------------------------------------
# RECENT DIRECTION
# ------------------------------------------------------------

def calculate_recent_direction(
    values,
    periods=3,
):
    """
    Compare the most recent periods to identify recent movement.
    """

    numeric_values = [
        float(value)
        for value in values
        if pd.notna(value)
    ]

    if len(numeric_values) < 2:

        return "Stable"

    periods = max(
        2,
        int(periods)
    )

    recent_values = numeric_values[
        -periods:
    ]

    if len(recent_values) < 2:

        return "Stable"

    first_value = recent_values[0]
    latest_value = recent_values[-1]

    difference = (
        latest_value
        -
        first_value
    )

    tolerance = max(
        abs(first_value) * 0.001,
        1e-12
    )

    if difference > tolerance:

        return "Increasing"

    if difference < -tolerance:

        return "Decreasing"

    return "Stable"


# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

def generate_trend_summary(
    metric_column,
    frequency_label,
    trend_direction,
    trend_strength,
    percentage_change,
    average_value,
    minimum_value,
    maximum_value,
    recent_direction,
):
    """
    Generate a human-readable summary for the trend result.
    """

    metric_name = str(
        metric_column
    )

    if percentage_change is None:

        change_text = (
            "The percentage change could not be "
            "calculated because the first period "
            "value was zero or unavailable."
        )

    elif percentage_change > 0:

        change_text = (
            f"The metric increased by "
            f"{abs(percentage_change):.2f}% "
            f"from the first period to the latest period."
        )

    elif percentage_change < 0:

        change_text = (
            f"The metric decreased by "
            f"{abs(percentage_change):.2f}% "
            f"from the first period to the latest period."
        )

    else:

        change_text = (
            "The first and latest period values "
            "are unchanged."
        )

    return (
        f"{metric_name} shows an overall "
        f"{trend_direction.lower()} trend with "
        f"{trend_strength.lower()} trend strength "
        f"at {frequency_label.lower()} frequency. "
        f"{change_text} "
        f"The average value was "
        f"{average_value:.2f}, with a minimum of "
        f"{minimum_value:.2f} and a maximum of "
        f"{maximum_value:.2f}. "
        f"Recent movement is "
        f"{recent_direction.lower()}."
    )


# ------------------------------------------------------------
# CHART DATA
# ------------------------------------------------------------

def build_chart_data(
    time_series
):
    """
    Convert the pandas time series into JSON-safe data
    suitable for Chart.js or another frontend chart library.
    """

    chart_data = []

    for _, row in time_series.iterrows():

        period = row["period"]
        value = row["value"]

        if pd.isna(period):
            continue

        if pd.isna(value):
            continue

        # Timestamp -> string
        if hasattr(
            period,
            "strftime"
        ):

            period_value = period.strftime(
                "%Y-%m-%d"
            )

        else:

            period_value = str(
                period
            )

        chart_data.append(
            {
                "period":
                    period_value,

                "value":
                    round(
                        float(value),
                        2
                    ),
            }
        )

    return chart_data


# ------------------------------------------------------------
# COMPLETE FUTURE TREND ANALYSIS
# ------------------------------------------------------------

def analyze_future_trend(
    dataframe,
    date_column,
    metric_column,
    frequency="M",
):
    """
    Complete Future Trends analysis.

    Returns a dictionary containing:
        - time series
        - trend direction
        - trend strength
        - percentage change
        - average
        - minimum
        - maximum
        - recent direction
        - summary
        - chart data
    """

    # --------------------------------------------------------
    # FREQUENCY LABELS
    # --------------------------------------------------------

    frequency_labels = {
        "D": "Daily",
        "W": "Weekly",
        "M": "Monthly",
        "Q": "Quarterly",
        "Y": "Yearly",
    }

    frequency = (
        str(frequency)
        .strip()
        .upper()
    )

    if frequency not in frequency_labels:

        raise ValueError(
            "Invalid trend frequency."
        )

    # --------------------------------------------------------
    # PREPARE TIME SERIES
    # --------------------------------------------------------

    time_series = prepare_time_series(
        dataframe=dataframe,
        date_column=date_column,
        metric_column=metric_column,
        frequency=frequency,
    )

    values = (
        time_series["value"]
        .astype(float)
        .tolist()
    )

    if not values:

        raise ValueError(
            "No values are available for trend analysis."
        )

    # --------------------------------------------------------
    # BASIC STATISTICS
    # --------------------------------------------------------

    average_value = float(
        np.mean(values)
    )

    minimum_value = float(
        np.min(values)
    )

    maximum_value = float(
        np.max(values)
    )

    first_period_value = float(
        values[0]
    )

    latest_period_value = float(
        values[-1]
    )

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    trend_direction = (
        calculate_trend_direction(
            values
        )
    )

    trend_strength = (
        calculate_trend_strength(
            values
        )
    )

    # --------------------------------------------------------
    # CHANGE
    # --------------------------------------------------------

    percentage_change = (
        calculate_percentage_change(
            first_period_value,
            latest_period_value,
        )
    )

    # --------------------------------------------------------
    # RECENT MOVEMENT
    # --------------------------------------------------------

    recent_direction = (
        calculate_recent_direction(
            values
        )
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = generate_trend_summary(
        metric_column=metric_column,
        frequency_label=frequency_labels[
            frequency
        ],
        trend_direction=trend_direction,
        trend_strength=trend_strength,
        percentage_change=percentage_change,
        average_value=average_value,
        minimum_value=minimum_value,
        maximum_value=maximum_value,
        recent_direction=recent_direction,
    )

    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    chart_data = build_chart_data(
        time_series
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "date_column":
            str(date_column),

        "metric_column":
            str(metric_column),

        "frequency":
            frequency,

        "frequency_label":
            frequency_labels[
                frequency
            ],

        "trend_direction":
            trend_direction,

        "trend_strength":
            trend_strength,

        "percentage_change":
            percentage_change,

        "average_value":
            round(
                average_value,
                2
            ),

        "minimum_value":
            round(
                minimum_value,
                2
            ),

        "maximum_value":
            round(
                maximum_value,
                2
            ),

        "first_period_value":
            round(
                first_period_value,
                2
            ),

        "latest_period_value":
            round(
                latest_period_value,
                2
            ),

        "recent_direction":
            recent_direction,

        "summary":
            summary,

        "chart_data":
            chart_data,

        "period_count":
            len(time_series),
    }