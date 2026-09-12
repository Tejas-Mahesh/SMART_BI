import numpy as np
import pandas as pd

from statsmodels.tsa.holtwinters import ExponentialSmoothing


def detect_column(df, candidates):
    """
    Detect a column using exact and partial matching.
    """

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    # Exact match
    for candidate in candidates:

        candidate_lower = candidate.lower()

        if candidate_lower in normalized:
            return normalized[candidate_lower]

    # Partial match
    for column in df.columns:

        column_lower = str(column).strip().lower()

        for candidate in candidates:

            if candidate.lower() in column_lower:
                return column

    return None


def prepare_time_series(
    df,
    date_column,
    metric_column,
):
    """
    Convert raw cleaned data into a daily
    time-series suitable for forecasting.
    """

    data = df.copy()

    data[date_column] = pd.to_datetime(
        data[date_column],
        errors="coerce",
    )

    data[metric_column] = pd.to_numeric(
        data[metric_column],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            date_column,
            metric_column,
        ]
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

    # Fill missing calendar dates.
    full_index = pd.date_range(
        start=daily.index.min(),
        end=daily.index.max(),
        freq="D",
    )

    daily = daily.reindex(
        full_index,
        fill_value=0,
    )

    daily.index.name = "date"

    return daily.astype(float)


def calculate_trend(series):
    """
    Calculate simple statistical trend using
    linear regression.
    """

    if series.empty:
        return {
            "direction": "Unknown",
            "slope": 0,
            "strength": 0,
        }

    values = series.values.astype(float)

    if len(values) < 2:
        return {
            "direction": "Stable",
            "slope": 0,
            "strength": 0,
        }

    x = np.arange(len(values))

    slope = np.polyfit(
        x,
        values,
        1,
    )[0]

    mean_value = np.mean(values)

    if mean_value == 0:
        strength = 0
    else:
        strength = abs(
            slope / mean_value
        ) * 100

    if slope > 0:
        direction = "Increasing"

    elif slope < 0:
        direction = "Decreasing"

    else:
        direction = "Stable"

    return {
        "direction": direction,
        "slope": float(slope),
        "strength": float(strength),
    }


def forecast_series(
    series,
    periods=30,
):
    """
    Forecast future values using Holt-Winters
    Exponential Smoothing.

    Returns:
        historical,
        forecast,
        confidence information,
        model status
    """

    if series.empty:
        return {
            "forecast": pd.Series(dtype=float),
            "model": "Unavailable",
            "confidence": "Low",
        }

    series = series.astype(float)

    # Very small datasets should not be
    # forced through a statistical model.
    if len(series) < 10:

        return {
            "forecast": pd.Series(
                [series.iloc[-1]] * periods,
                index=pd.date_range(
                    series.index[-1]
                    + pd.Timedelta(days=1),
                    periods=periods,
                    freq="D",
                ),
            ),
            "model": "Baseline",
            "confidence": "Low",
        }

    try:

        seasonal_periods = None

        # Use weekly seasonality when enough
        # historical observations exist.
        if len(series) >= 21:
            seasonal_periods = 7

        if seasonal_periods:

            model = ExponentialSmoothing(
                series,
                trend="add",
                seasonal="add",
                seasonal_periods=seasonal_periods,
                initialization_method="estimated",
            )

        else:

            model = ExponentialSmoothing(
                series,
                trend="add",
                initialization_method="estimated",
            )

        fitted_model = model.fit(
            optimized=True
        )

        forecast = fitted_model.forecast(
            periods
        )

        forecast = forecast.clip(
            lower=0
        )

        if len(series) >= 60:
            confidence = "High"

        elif len(series) >= 30:
            confidence = "Medium"

        else:
            confidence = "Low"

        return {
            "forecast": forecast,
            "model": "Holt-Winters Exponential Smoothing",
            "confidence": confidence,
        }

    except Exception:

        # Safe fallback
        last_value = float(
            series.iloc[-1]
        )

        forecast_index = pd.date_range(
            series.index[-1]
            + pd.Timedelta(days=1),
            periods=periods,
            freq="D",
        )

        forecast = pd.Series(
            [last_value] * periods,
            index=forecast_index,
        )

        return {
            "forecast": forecast,
            "model": "Baseline Fallback",
            "confidence": "Low",
        }


def calculate_forecast_summary(
    historical,
    forecast,
):
    """
    Generate business-friendly forecast metrics.
    """

    if historical.empty or forecast.empty:

        return {
            "historical_average": 0,
            "forecast_average": 0,
            "forecast_total": 0,
            "forecast_change": 0,
            "forecast_direction": "Unknown",
        }

    historical_average = float(
        historical.tail(30).mean()
    )

    forecast_average = float(
        forecast.mean()
    )

    forecast_total = float(
        forecast.sum()
    )

    if historical_average == 0:

        forecast_change = 0

    else:

        forecast_change = (
            (
                forecast_average
                -
                historical_average
            )
            /
            historical_average
        ) * 100

    if forecast_change > 5:
        direction = "Increasing"

    elif forecast_change < -5:
        direction = "Decreasing"

    else:
        direction = "Stable"

    return {
        "historical_average":
            historical_average,

        "forecast_average":
            forecast_average,

        "forecast_total":
            forecast_total,

        "forecast_change":
            float(forecast_change),

        "forecast_direction":
            direction,
    }