# ============================================================
# ANOMALY DETECTION SERVICE
# ============================================================

import math

import numpy as np
import pandas as pd


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=None):
    """
    Safely convert a value to float.
    """
    try:
        if value is None:
            return default

        value = float(value)

        if not math.isfinite(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def json_safe(value):
    """
    Convert pandas / NumPy values into JSON-safe Python values.
    """
    if value is None:
        return None

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

    return value


# ============================================================
# DATE COLUMN DETECTION
# ============================================================

def detect_date_columns(dataframe):
    """
    Detect columns that can reasonably be treated as dates.
    """

    date_columns = []

    for column in dataframe.columns:

        series = dataframe[column]

        if pd.api.types.is_datetime64_any_dtype(series):
            date_columns.append(column)
            continue

        if not (
            pd.api.types.is_object_dtype(series)
            or pd.api.types.is_string_dtype(series)
        ):
            continue

        converted = pd.to_datetime(
            series,
            errors="coerce",
        )

        valid_count = converted.notna().sum()

        if len(series) > 0:

            valid_ratio = valid_count / len(series)

            if valid_ratio >= 0.70:
                date_columns.append(column)

    return date_columns


# ============================================================
# NUMERIC COLUMN DETECTION
# ============================================================

def detect_numeric_columns(dataframe):
    """
    Return numeric columns suitable for anomaly detection.
    """

    numeric_columns = dataframe.select_dtypes(
        include=["number"]
    ).columns.tolist()

    return numeric_columns


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_metric_data(dataframe, metric_column):
    """
    Prepare a numeric metric series for anomaly detection.
    """

    if metric_column not in dataframe.columns:
        raise ValueError(
            f"Metric column '{metric_column}' was not found in the dataset."
        )

    working = dataframe.copy()

    working["_anomaly_value"] = pd.to_numeric(
        working[metric_column],
        errors="coerce",
    )

    working = working[
        working["_anomaly_value"].notna()
    ].copy()

    if working.empty:
        raise ValueError(
            f"No valid numeric values were found in '{metric_column}'."
        )

    return working


# ============================================================
# Z-SCORE ANOMALY DETECTION
# ============================================================

def detect_zscore_anomalies(
    dataframe,
    metric_column,
    threshold=2.5,
    date_column=None,
):
    """
    Detect anomalies using the Z-Score method.

    A value is considered anomalous when:

        abs(z_score) >= threshold

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Cleaned dataset.

    metric_column : str
        Numeric column to analyze.

    threshold : float
        Z-score threshold.

    date_column : str | None
        Optional date column for chart/table output.

    Returns
    -------
    dict
        Complete anomaly detection result.
    """

    # --------------------------------------------------------
    # Validate threshold
    # --------------------------------------------------------

    threshold = safe_float(threshold, 2.5)

    if threshold is None:
        threshold = 2.5

    if threshold <= 0:
        raise ValueError(
            "Anomaly threshold must be greater than 0."
        )

    # --------------------------------------------------------
    # Prepare data
    # --------------------------------------------------------

    working = prepare_metric_data(
        dataframe,
        metric_column,
    )

    values = working["_anomaly_value"].astype(float)

    total_records = len(values)

    if total_records == 0:
        raise ValueError(
            "The selected metric does not contain usable numeric values."
        )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    average_value = float(values.mean())

    standard_deviation = float(values.std(ddof=0))

    minimum_value = float(values.min())

    maximum_value = float(values.max())

    # --------------------------------------------------------
    # Constant-value dataset
    # --------------------------------------------------------

    if standard_deviation == 0 or not math.isfinite(
        standard_deviation
    ):

        working["_z_score"] = 0.0
        working["_is_anomaly"] = False
        working["_severity"] = "Normal"

    else:

        working["_z_score"] = (
            (values - average_value)
            / standard_deviation
        )

        working["_is_anomaly"] = (
            working["_z_score"].abs()
            >= threshold
        )

        # ----------------------------------------------------
        # Severity
        # ----------------------------------------------------

        absolute_z = working["_z_score"].abs()

        working["_severity"] = np.select(
            [
                absolute_z >= threshold * 1.5,
                absolute_z >= threshold,
            ],
            [
                "Critical",
                "High",
            ],
            default="Normal",
        )

    # --------------------------------------------------------
    # Counts
    # --------------------------------------------------------

    anomaly_mask = working["_is_anomaly"]

    anomaly_count = int(
        anomaly_mask.sum()
    )

    normal_records = (
        total_records - anomaly_count
    )

    anomaly_percentage = (
        anomaly_count / total_records * 100
        if total_records > 0
        else 0
    )

    # --------------------------------------------------------
    # Anomaly values
    # --------------------------------------------------------

    anomaly_rows = working[
        anomaly_mask
    ].copy()

    highest_anomaly_value = None
    lowest_anomaly_value = None

    if not anomaly_rows.empty:

        highest_anomaly_value = float(
            anomaly_rows["_anomaly_value"].max()
        )

        lowest_anomaly_value = float(
            anomaly_rows["_anomaly_value"].min()
        )

    # --------------------------------------------------------
    # Chart data
    # --------------------------------------------------------

    chart_data = []

    for index, row in working.iterrows():

        value = safe_float(
            row["_anomaly_value"]
        )

        z_score = safe_float(
            row["_z_score"]
        )

        is_anomaly = bool(
            row["_is_anomaly"]
        )

        label = index

        if date_column and date_column in working.columns:

            date_value = row[date_column]

            if pd.notna(date_value):

                if isinstance(
                    date_value,
                    pd.Timestamp,
                ):
                    label = date_value.strftime(
                        "%Y-%m-%d"
                    )
                else:
                    label = str(date_value)

        chart_data.append(
            {
                "index": json_safe(index),
                "label": json_safe(label),
                "value": json_safe(value),
                "z_score": json_safe(z_score),
                "is_anomaly": is_anomaly,
                "severity": str(
                    row["_severity"]
                ),
            }
        )

    # --------------------------------------------------------
    # Detailed anomaly records
    # --------------------------------------------------------

    anomaly_data = []

    for index, row in anomaly_rows.iterrows():

        value = safe_float(
            row["_anomaly_value"]
        )

        z_score = safe_float(
            row["_z_score"]
        )

        label = index

        if date_column and date_column in working.columns:

            date_value = row[date_column]

            if pd.notna(date_value):

                if isinstance(
                    date_value,
                    pd.Timestamp,
                ):
                    label = date_value.strftime(
                        "%Y-%m-%d"
                    )
                else:
                    label = str(date_value)

        direction = (
            "High"
            if value > average_value
            else "Low"
        )

        anomaly_data.append(
            {
                "index": json_safe(index),
                "date": json_safe(label),
                "value": json_safe(value),
                "z_score": json_safe(z_score),
                "direction": direction,
                "severity": str(
                    row["_severity"]
                ),
            }
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    if anomaly_count == 0:

        summary = (
            f"No anomalies were detected in "
            f"'{metric_column}' using a Z-Score threshold "
            f"of {threshold:.2f}. "
            f"All {total_records:,} analyzed records "
            f"fall within the normal range."
        )

    else:

        high_count = sum(
            1
            for item in anomaly_data
            if item["direction"] == "High"
        )

        low_count = (
            anomaly_count - high_count
        )

        summary = (
            f"{anomaly_count:,} anomalies were detected "
            f"among {total_records:,} analyzed records "
            f"({anomaly_percentage:.2f}%). "
            f"{high_count:,} are unusually high and "
            f"{low_count:,} are unusually low "
            f"relative to the dataset average."
        )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return {
        "date_column": date_column or "",
        "metric_column": metric_column,
        "detection_method": "Z-Score",
        "threshold": float(threshold),

        "total_records": total_records,
        "normal_records": normal_records,
        "anomaly_count": anomaly_count,
        "anomaly_percentage": float(
            anomaly_percentage
        ),

        "average_value": safe_float(
            average_value
        ),

        "standard_deviation": safe_float(
            standard_deviation
        ),

        "minimum_value": safe_float(
            minimum_value
        ),

        "maximum_value": safe_float(
            maximum_value
        ),

        "highest_anomaly_value": (
            safe_float(highest_anomaly_value)
        ),

        "lowest_anomaly_value": (
            safe_float(lowest_anomaly_value)
        ),

        "summary": summary,

        "chart_data": chart_data,

        "anomaly_data": anomaly_data,
    }


# ============================================================
# MAIN SERVICE FUNCTION
# ============================================================

def analyze_anomalies(
    dataframe,
    metric_column,
    threshold=2.5,
    date_column=None,
):
    """
    Main entry point used by the Django view.
    """

    if dataframe is None:
        raise ValueError(
            "Dataset could not be loaded."
        )

    if dataframe.empty:
        raise ValueError(
            "The selected dataset is empty."
        )

    return detect_zscore_anomalies(
        dataframe=dataframe,
        metric_column=metric_column,
        threshold=threshold,
        date_column=date_column,
    )