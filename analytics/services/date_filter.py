import pandas as pd


# =========================================================
# DATASET DATE COLUMN MAPPING
# =========================================================

DATE_COLUMN_MAPPING = {
    "Sales": [
        "Order_Date",
        "Date",
    ],

    "Customers": [
        "Registration_Date",
        "Last_Order_Date",
        "Date",
    ],

    "Products": [
        "Date",
    ],

    "Regional": [
        "Date",
    ],

    "Marketing": [
        "Date",
    ],

    "Financial": [
        "Date",
    ],

    "Returns": [
        "Return_Date",
        "Date",
    ],
}


# =========================================================
# COLUMN NORMALIZATION
# =========================================================

def normalize_column_name(column):
    """
    Normalize a dataframe column name for comparison.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


# =========================================================
# DATE COLUMN RESOLUTION
# =========================================================

def find_date_column(dataframe, dataset_type):
    """
    Find the appropriate date column for a dataset.

    The search follows the dataset-specific mapping.
    """

    if dataframe is None or dataframe.empty:
        return None

    expected_columns = DATE_COLUMN_MAPPING.get(
        dataset_type,
        [],
    )

    if not expected_columns:
        return None

    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    for expected in expected_columns:

        normalized_expected = normalize_column_name(
            expected
        )

        actual_column = normalized_columns.get(
            normalized_expected
        )

        if actual_column:
            return actual_column

    return None


# =========================================================
# DATE PARSING
# =========================================================

def parse_date_series(series):
    """
    Convert a pandas Series to datetime safely.

    Product/Sales datasets may contain dates such as:

        05-01-2026
        31-08-2026
        05-09-2026

    Therefore dayfirst=True is intentionally used.

    ISO dates such as:

        2026-09-05

    are also handled correctly.
    """

    if series is None:
        return pd.Series(
            dtype="datetime64[ns]"
        )

    return pd.to_datetime(
        series,
        errors="coerce",
        dayfirst=True,
    )


def parse_single_date(value):
    """
    Convert one date value into a pandas Timestamp.

    Returns NaT when the value is invalid.
    """

    if value is None:
        return pd.NaT

    return pd.to_datetime(
        value,
        errors="coerce",
        dayfirst=True,
    )


# =========================================================
# APPLY DATE FILTER
# =========================================================

def apply_date_filter(
    dataframe,
    dataset_type,
    from_date=None,
    to_date=None,
):
    """
    Apply an optional date range to a dataframe.

    Returns:

        filtered_dataframe,
        metadata

    Metadata contains:

        date_column
        date_filter_applied
        from_date
        to_date
        warning
    """

    # -----------------------------------------------------
    # DATAFRAME UNAVAILABLE
    # -----------------------------------------------------

    if dataframe is None:

        return dataframe, {
            "date_column": None,
            "date_filter_applied": False,
            "from_date": from_date,
            "to_date": to_date,
            "warning": (
                "Dataset data is unavailable."
            ),
        }

    dataframe = dataframe.copy()

    # -----------------------------------------------------
    # FIND DATE COLUMN
    # -----------------------------------------------------

    date_column = find_date_column(
        dataframe,
        dataset_type,
    )

    metadata = {
        "date_column": date_column,
        "date_filter_applied": False,
        "from_date": from_date,
        "to_date": to_date,
        "warning": None,
    }

    # -----------------------------------------------------
    # DATE COLUMN NOT FOUND
    # -----------------------------------------------------

    if date_column is None:

        if from_date is not None or to_date is not None:

            metadata["warning"] = (
                "No compatible date column was found "
                "for this dataset."
            )

        return dataframe, metadata

    # -----------------------------------------------------
    # PARSE DATASET DATE COLUMN
    # -----------------------------------------------------

    dataframe[date_column] = parse_date_series(
        dataframe[date_column]
    )

    # -----------------------------------------------------
    # PARSE FROM DATE
    # -----------------------------------------------------

    from_timestamp = parse_single_date(
        from_date
    )

    # -----------------------------------------------------
    # PARSE TO DATE
    # -----------------------------------------------------

    to_timestamp = parse_single_date(
        to_date
    )

    # -----------------------------------------------------
    # INVALID FROM DATE
    # -----------------------------------------------------

    if from_date is not None and pd.isna(
        from_timestamp
    ):

        metadata["warning"] = (
            "The selected start date is invalid."
        )

        from_timestamp = pd.NaT

    # -----------------------------------------------------
    # INVALID TO DATE
    # -----------------------------------------------------

    if to_date is not None and pd.isna(
        to_timestamp
    ):

        metadata["warning"] = (
            "The selected end date is invalid."
        )

        to_timestamp = pd.NaT

    # =====================================================
    # APPLY FROM DATE
    # =====================================================

    if pd.notna(from_timestamp):

        # Normalize to beginning of selected day.
        from_timestamp = from_timestamp.normalize()

        dataframe = dataframe[
            dataframe[date_column]
            >= from_timestamp
        ]

        metadata["date_filter_applied"] = True

    # =====================================================
    # APPLY TO DATE
    # =====================================================

    if pd.notna(to_timestamp):

        # Include the complete selected day.
        #
        # Example:
        # 05-09-2026
        #
        # becomes:
        # 05-09-2026 23:59:59.999999
        #
        to_timestamp = (
            to_timestamp.normalize()
            + pd.Timedelta(days=1)
            - pd.Timedelta(microseconds=1)
        )

        dataframe = dataframe[
            dataframe[date_column]
            <= to_timestamp
        ]

        metadata["date_filter_applied"] = True

    # -----------------------------------------------------
    # RETURN FILTERED DATA
    # -----------------------------------------------------

    return (
        dataframe.reset_index(drop=True),
        metadata,
    )