from datetime import timedelta

import pandas as pd


DATE_RANGE_OPTIONS = {
    "30": "Last 30 Days",
    "90": "Last 3 Months",
    "180": "Last 6 Months",
    "365": "Last 12 Months",
    "all": "All Data",
}


def apply_date_filter(
    df,
    date_column,
    range_key="all",
    start_date=None,
    end_date=None,
):
    """
    Apply a common date filter to any analytics dataframe.

    Returns:
        filtered_df,
        metadata
    """

    result = df.copy()

    if not date_column or date_column not in result.columns:
        return result, {
            "range_key": "all",
            "range_label": "All Data",
            "start_date": None,
            "end_date": None,
            "days": None,
        }

    result[date_column] = pd.to_datetime(
        result[date_column],
        errors="coerce",
    )

    result = result.dropna(
        subset=[date_column]
    )

    if result.empty:
        return result, {
            "range_key": range_key,
            "range_label": DATE_RANGE_OPTIONS.get(
                range_key,
                "All Data",
            ),
            "start_date": None,
            "end_date": None,
            "days": 0,
        }

    min_date = result[date_column].min().normalize()
    max_date = result[date_column].max().normalize()

    # ---------------------------------------------------------
    # CUSTOM RANGE
    # ---------------------------------------------------------

    if range_key == "custom":

        try:
            requested_start = pd.to_datetime(
                start_date
            ).normalize()

            requested_end = pd.to_datetime(
                end_date
            ).normalize()

            if requested_start > requested_end:
                requested_start, requested_end = (
                    requested_end,
                    requested_start,
                )

            filter_start = max(
                requested_start,
                min_date,
            )

            filter_end = min(
                requested_end,
                max_date,
            )

            filtered = result[
                (result[date_column] >= filter_start)
                &
                (
                    result[date_column]
                    < filter_end + timedelta(days=1)
                )
            ].copy()

            return filtered, {
                "range_key": "custom",
                "range_label": "Custom Range",
                "start_date": filter_start,
                "end_date": filter_end,
                "days": (
                    filter_end - filter_start
                ).days + 1,
            }

        except (ValueError, TypeError):

            range_key = "all"

    # ---------------------------------------------------------
    # ALL DATA
    # ---------------------------------------------------------

    if range_key == "all":

        filtered = result.copy()

        return filtered, {
            "range_key": "all",
            "range_label": "All Data",
            "start_date": min_date,
            "end_date": max_date,
            "days": (
                max_date - min_date
            ).days + 1,
        }

    # ---------------------------------------------------------
    # PREDEFINED RANGES
    # ---------------------------------------------------------

    try:
        days = int(range_key)
    except (ValueError, TypeError):
        days = None

    if days is None:

        filtered = result.copy()

        return filtered, {
            "range_key": "all",
            "range_label": "All Data",
            "start_date": min_date,
            "end_date": max_date,
            "days": (
                max_date - min_date
            ).days + 1,
        }

    filter_end = max_date

    filter_start = max_date - timedelta(
        days=days - 1
    )

    filter_start = max(
        filter_start,
        min_date,
    )

    filtered = result[
        (result[date_column] >= filter_start)
        &
        (result[date_column] <= filter_end)
    ].copy()

    return filtered, {
        "range_key": str(days),
        "range_label": DATE_RANGE_OPTIONS.get(
            str(days),
            f"Last {days} Days",
        ),
        "start_date": filter_start,
        "end_date": filter_end,
        "days": (
            filter_end - filter_start
        ).days + 1,
    }


def get_previous_period(
    df,
    date_column,
    current_start,
    current_end,
):
    """
    Return the previous period having the same
    number of days as the selected period.
    """

    if (
        current_start is None
        or current_end is None
    ):
        return df.iloc[0:0].copy()

    current_start = pd.to_datetime(
        current_start
    ).normalize()

    current_end = pd.to_datetime(
        current_end
    ).normalize()

    period_days = (
        current_end - current_start
    ).days + 1

    previous_end = (
        current_start
        - timedelta(days=1)
    )

    previous_start = (
        previous_end
        - timedelta(days=period_days - 1)
    )

    dates = pd.to_datetime(
        df[date_column],
        errors="coerce",
    )

    return df[
        (dates >= previous_start)
        &
        (dates <= previous_end)
    ].copy()


def calculate_percentage_change(
    current_value,
    previous_value,
):
    """
    Calculate percentage change safely.
    """

    try:
        current_value = float(current_value)
        previous_value = float(previous_value)
    except (ValueError, TypeError):
        return 0

    if previous_value == 0:

        if current_value == 0:
            return 0

        return 100

    return (
        (
            current_value
            - previous_value
        )
        / previous_value
    ) * 100