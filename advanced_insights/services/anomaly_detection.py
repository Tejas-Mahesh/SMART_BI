import numpy as np
import pandas as pd


def detect_column(df, candidates):
    """
    Detect a column using exact match first,
    then partial match.
    """
    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    # Exact match
    for candidate in candidates:
        candidate = candidate.lower()

        if candidate in normalized:
            return normalized[candidate]

    # Partial match
    for column in df.columns:
        column_lower = str(column).strip().lower()

        for candidate in candidates:
            if candidate.lower() in column_lower:
                return column

    return None


def prepare_daily_series(df, date_column, metric_column):
    """
    Convert transaction-level data into a daily time series.
    """

    data = df.copy()

    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce"
    )

    data[metric_column] = pd.to_numeric(
        data[metric_column],
        errors="coerce"
    )

    data = data.dropna(
        subset=[date_column, metric_column]
    )

    if data.empty:
        return pd.Series(dtype=float)

    daily = (
        data.groupby(
            data[date_column].dt.normalize()
        )[metric_column]
        .sum()
        .sort_index()
    )

    if daily.empty:
        return pd.Series(dtype=float)

    # Fill missing dates
    full_index = pd.date_range(
        start=daily.index.min(),
        end=daily.index.max(),
        freq="D"
    )

    daily = daily.reindex(
        full_index,
        fill_value=0
    )

    daily.index.name = "date"

    return daily.astype(float)


def detect_anomalies(series):
    """
    Detect unusual spikes and drops using
    rolling statistics and robust IQR logic.
    """

    if series.empty:
        return pd.DataFrame()

    data = pd.DataFrame({
        "date": series.index,
        "value": series.values
    })

    data["rolling_median"] = (
        data["value"]
        .rolling(
            window=7,
            center=True,
            min_periods=3
        )
        .median()
    )

    data["rolling_std"] = (
        data["value"]
        .rolling(
            window=7,
            center=True,
            min_periods=3
        )
        .std()
    )

    # Fill edge values
    data["rolling_median"] = (
        data["rolling_median"]
        .bfill()
        .ffill()
    )

    data["rolling_std"] = (
        data["rolling_std"]
        .fillna(0)
    )

    # Absolute deviation
    data["deviation"] = (
        data["value"]
        - data["rolling_median"]
    )

    data["deviation_percent"] = np.where(
        data["rolling_median"] != 0,
        (
            data["deviation"]
            / data["rolling_median"]
        ) * 100,
        0
    )

    # Robust IQR threshold
    q1 = data["value"].quantile(0.25)
    q3 = data["value"].quantile(0.75)

    iqr = q3 - q1

    lower_bound = q1 - (1.5 * iqr)
    upper_bound = q3 + (1.5 * iqr)

    data["iqr_anomaly"] = (
        (data["value"] < lower_bound)
        |
        (data["value"] > upper_bound)
    )

    # Rolling statistical anomaly
    data["z_score"] = np.where(
        data["rolling_std"] > 0,
        (
            data["value"]
            - data["rolling_median"]
        )
        / data["rolling_std"],
        0
    )

    data["statistical_anomaly"] = (
        data["z_score"].abs() >= 2
    )

    # Final anomaly decision
    data["is_anomaly"] = (
        data["iqr_anomaly"]
        |
        data["statistical_anomaly"]
    )

    # Direction
    data["direction"] = np.where(
        data["deviation"] >= 0,
        "Spike",
        "Drop"
    )

    # Severity
    absolute_z = data["z_score"].abs()

    data["severity"] = np.select(
        [
            absolute_z >= 3,
            absolute_z >= 2
        ],
        [
            "Critical",
            "Moderate"
        ],
        default="Low"
    )

    # Business impact
    data["impact"] = np.where(
        data["direction"] == "Spike",
        "Higher than expected",
        "Lower than expected"
    )

    return data


def calculate_anomaly_summary(
    series,
    anomaly_data
):
    """
    Generate dashboard-level anomaly statistics.
    """

    if series.empty or anomaly_data.empty:
        return {
            "total_days": 0,
            "anomaly_count": 0,
            "anomaly_rate": 0,
            "spike_count": 0,
            "drop_count": 0,
            "critical_count": 0,
            "largest_spike": 0,
            "largest_drop": 0,
            "largest_spike_date": None,
            "largest_drop_date": None,
        }

    anomaly_rows = anomaly_data[
        anomaly_data["is_anomaly"]
    ].copy()

    total_days = len(series)

    anomaly_count = len(anomaly_rows)

    anomaly_rate = (
        anomaly_count / total_days * 100
        if total_days
        else 0
    )

    spike_count = len(
        anomaly_rows[
            anomaly_rows["direction"] == "Spike"
        ]
    )

    drop_count = len(
        anomaly_rows[
            anomaly_rows["direction"] == "Drop"
        ]
    )

    critical_count = len(
        anomaly_rows[
            anomaly_rows["severity"] == "Critical"
        ]
    )

    largest_spike = 0
    largest_spike_date = None

    spike_rows = anomaly_rows[
        anomaly_rows["direction"] == "Spike"
    ]

    if not spike_rows.empty:

        largest_spike_row = spike_rows.loc[
            spike_rows["deviation_percent"].idxmax()
        ]

        largest_spike = float(
            largest_spike_row["deviation_percent"]
        )

        largest_spike_date = (
            largest_spike_row["date"]
        )

    largest_drop = 0
    largest_drop_date = None

    drop_rows = anomaly_rows[
        anomaly_rows["direction"] == "Drop"
    ]

    if not drop_rows.empty:

        largest_drop_row = drop_rows.loc[
            drop_rows["deviation_percent"].idxmin()
        ]

        largest_drop = abs(
            float(
                largest_drop_row["deviation_percent"]
            )
        )

        largest_drop_date = (
            largest_drop_row["date"]
        )

    return {
        "total_days": total_days,
        "anomaly_count": anomaly_count,
        "anomaly_rate": float(anomaly_rate),
        "spike_count": spike_count,
        "drop_count": drop_count,
        "critical_count": critical_count,
        "largest_spike": float(largest_spike),
        "largest_drop": float(largest_drop),
        "largest_spike_date": largest_spike_date,
        "largest_drop_date": largest_drop_date,
    }


def generate_anomaly_insights(
    summary,
    anomaly_data
):
    """
    Generate business-friendly anomaly explanations.
    """

    insights = []

    anomaly_count = summary["anomaly_count"]
    anomaly_rate = summary["anomaly_rate"]

    if anomaly_count == 0:

        insights.append(
            "No significant sales anomalies were detected "
            "in the analyzed period."
        )

    else:

        insights.append(
            f"{anomaly_count} unusual day(s) were detected "
            f"across {summary['total_days']} analyzed days."
        )

        if summary["spike_count"] > 0:

            insights.append(
                f"{summary['spike_count']} unusual sales spike(s) "
                "were detected and may indicate campaigns, "
                "seasonality, promotions or exceptional demand."
            )

        if summary["drop_count"] > 0:

            insights.append(
                f"{summary['drop_count']} unusual sales drop(s) "
                "were detected and may require investigation."
            )

        if summary["critical_count"] > 0:

            insights.append(
                f"{summary['critical_count']} critical anomaly/anomalies "
                "show unusually large deviations from normal activity."
            )

    if anomaly_rate >= 15:

        insights.append(
            "The anomaly rate is relatively high. "
            "Review promotions, inventory availability, "
            "pricing changes and operational disruptions."
        )

    elif anomaly_rate >= 5:

        insights.append(
            "The business shows occasional unusual activity. "
            "Investigate the most significant spike and drop periods."
        )

    return insights