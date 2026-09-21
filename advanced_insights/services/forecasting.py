import numpy as np
import pandas as pd

from .future_trends import (
    prepare_time_series,
)


# ============================================================
# FORECAST FREQUENCY LABELS
# ============================================================

FREQUENCY_LABELS = {
    "D": "Daily",
    "W": "Weekly",
    "M": "Monthly",
    "Q": "Quarterly",
    "Y": "Yearly",
}


# ============================================================
# FORECAST METHODS
# ============================================================

FORECAST_METHODS = {
    "Linear Trend": "Linear Trend",
    "Moving Average": "Moving Average",
}


# ============================================================
# VALIDATION
# ============================================================

def validate_forecast_horizon(horizon):
    try:
        horizon = int(horizon)
    except (TypeError, ValueError):
        raise ValueError(
            "Forecast horizon must be a valid number."
        )

    if horizon < 1:
        raise ValueError(
            "Forecast horizon must be at least 1."
        )

    if horizon > 60:
        raise ValueError(
            "Forecast horizon cannot exceed 60 periods."
        )

    return horizon


def validate_forecast_method(method):
    method = str(method).strip()

    if method not in FORECAST_METHODS:
        raise ValueError(
            "Unsupported forecasting method."
        )

    return method


# ============================================================
# LINEAR TREND FORECAST
# ============================================================

def forecast_linear_trend(
    values,
    horizon,
):
    numeric_values = np.asarray(
        values,
        dtype=float
    )

    numeric_values = numeric_values[
        np.isfinite(numeric_values)
    ]

    if len(numeric_values) < 2:
        raise ValueError(
            "At least two historical periods are required "
            "for linear trend forecasting."
        )

    x = np.arange(
        len(numeric_values),
        dtype=float
    )

    coefficients = np.polyfit(
        x,
        numeric_values,
        1
    )

    slope = float(coefficients[0])
    intercept = float(coefficients[1])

    future_x = np.arange(
        len(numeric_values),
        len(numeric_values) + horizon,
        dtype=float
    )

    forecast_values = (
        slope * future_x
        + intercept
    )

    return forecast_values


# ============================================================
# MOVING AVERAGE FORECAST
# ============================================================

def forecast_moving_average(
    values,
    horizon,
    window=3,
):
    numeric_values = np.asarray(
        values,
        dtype=float
    )

    numeric_values = numeric_values[
        np.isfinite(numeric_values)
    ]

    if len(numeric_values) < 2:
        raise ValueError(
            "At least two historical periods are required "
            "for moving average forecasting."
        )

    window = max(
        2,
        int(window)
    )

    window = min(
        window,
        len(numeric_values)
    )

    working_values = list(
        numeric_values
    )

    forecasts = []

    for _ in range(horizon):

        recent_values = working_values[-window:]

        average_value = float(
            np.mean(recent_values)
        )

        forecasts.append(
            average_value
        )

        working_values.append(
            average_value
        )

    return np.asarray(
        forecasts,
        dtype=float
    )


# ============================================================
# FORECAST CONFIDENCE
# ============================================================

def calculate_confidence_level(
    actual_values,
    forecast_values,
):
    actual_values = np.asarray(
        actual_values,
        dtype=float
    )

    actual_values = actual_values[
        np.isfinite(actual_values)
    ]

    forecast_values = np.asarray(
        forecast_values,
        dtype=float
    )

    forecast_values = forecast_values[
        np.isfinite(forecast_values)
    ]

    if len(actual_values) < 3:
        return 50.0

    if len(forecast_values) == 0:
        return 50.0

    x = np.arange(
        len(actual_values),
        dtype=float
    )

    if np.std(actual_values) == 0:
        return 75.0

    correlation = np.corrcoef(
        x,
        actual_values
    )[0, 1]

    if not np.isfinite(correlation):
        return 50.0

    strength = abs(
        float(correlation)
    )

    confidence = (
        50.0
        + strength * 45.0
    )

    return round(
        min(
            max(confidence, 50.0),
            95.0
        ),
        2
    )


# ============================================================
# FORECAST PERCENTAGE CHANGE
# ============================================================

def calculate_forecast_change_percentage(
    last_actual_value,
    latest_forecast_value,
):
    if last_actual_value is None:
        return None

    if latest_forecast_value is None:
        return None

    try:
        last_actual_value = float(
            last_actual_value
        )

        latest_forecast_value = float(
            latest_forecast_value
        )

    except (TypeError, ValueError):
        return None

    if not np.isfinite(last_actual_value):
        return None

    if not np.isfinite(latest_forecast_value):
        return None

    if last_actual_value == 0:
        return None

    percentage = (
        (
            latest_forecast_value
            - last_actual_value
        )
        /
        abs(last_actual_value)
    ) * 100

    return round(
        float(percentage),
        2
    )


# ============================================================
# FORECAST SUMMARY
# ============================================================

def generate_forecast_summary(
    metric_column,
    frequency_label,
    method,
    horizon,
    last_actual_value,
    first_forecast_value,
    latest_forecast_value,
    forecast_change_percentage,
    average_forecast_value,
    minimum_forecast_value,
    maximum_forecast_value,
    confidence_level,
):
    metric_name = str(
        metric_column
    )

    if forecast_change_percentage is None:

        change_text = (
            "The percentage change could not be "
            "calculated because the latest historical "
            "value was zero or unavailable."
        )

    elif forecast_change_percentage > 0:

        change_text = (
            f"The forecast increases by "
            f"{abs(forecast_change_percentage):.2f}% "
            f"from the latest historical value "
            f"to the final forecast period."
        )

    elif forecast_change_percentage < 0:

        change_text = (
            f"The forecast decreases by "
            f"{abs(forecast_change_percentage):.2f}% "
            f"from the latest historical value "
            f"to the final forecast period."
        )

    else:

        change_text = (
            "The final forecast value is unchanged "
            "from the latest historical value."
        )

    return (
        f"{metric_name} has been forecast using the "
        f"{method.lower()} method at "
        f"{frequency_label.lower()} frequency for "
        f"{horizon} future period(s). "
        f"The latest historical value was "
        f"{last_actual_value:.2f}, while the first "
        f"forecast value is "
        f"{first_forecast_value:.2f} and the final "
        f"forecast value is "
        f"{latest_forecast_value:.2f}. "
        f"{change_text} "
        f"The average forecast value is "
        f"{average_forecast_value:.2f}, with a minimum "
        f"of {minimum_forecast_value:.2f} and a maximum "
        f"of {maximum_forecast_value:.2f}. "
        f"The calculated trend confidence level is "
        f"{confidence_level:.2f}%."
    )


# ============================================================
# CHART DATA
# ============================================================

def build_forecast_chart_data(
    time_series,
    forecast_periods,
    forecast_values,
):
    chart_data = []

    for _, row in time_series.iterrows():

        period = row["period"]
        value = row["value"]

        if pd.isna(period):
            continue

        if pd.isna(value):
            continue

        if hasattr(period, "strftime"):
            period_value = period.strftime(
                "%Y-%m-%d"
            )
        else:
            period_value = str(period)

        chart_data.append(
            {
                "period": period_value,
                "actual": round(
                    float(value),
                    2
                ),
                "forecast": None,
            }
        )

    if time_series.empty:
        raise ValueError(
            "Historical time series is empty."
        )

    last_period = time_series[
        "period"
    ].iloc[-1]

    frequency = pd.infer_freq(
        time_series["period"]
    )

    if frequency is None:
        frequency = "M"

    future_index = pd.date_range(
        start=last_period,
        periods=len(forecast_periods) + 1,
        freq=frequency,
    )[1:]

    for period, value in zip(
        future_index,
        forecast_values,
    ):

        if hasattr(period, "strftime"):
            period_value = period.strftime(
                "%Y-%m-%d"
            )
        else:
            period_value = str(period)

        chart_data.append(
            {
                "period": period_value,
                "actual": None,
                "forecast": round(
                    float(value),
                    2
                ),
            }
        )

    if len(forecast_values) > 0:

        last_historical_period = (
            time_series["period"].iloc[-1]
        )

        last_historical_value = float(
            time_series["value"].iloc[-1]
        )

        first_forecast_period = future_index[0]

        if hasattr(
            last_historical_period,
            "strftime"
        ):
            historical_period_value = (
                last_historical_period.strftime(
                    "%Y-%m-%d"
                )
            )
        else:
            historical_period_value = str(
                last_historical_period
            )

        if hasattr(
            first_forecast_period,
            "strftime"
        ):
            forecast_period_value = (
                first_forecast_period.strftime(
                    "%Y-%m-%d"
                )
            )
        else:
            forecast_period_value = str(
                first_forecast_period
            )

        chart_data.insert(
            len(chart_data) - len(forecast_values),
            {
                "period": historical_period_value,
                "actual": round(
                    last_historical_value,
                    2
                ),
                "forecast": round(
                    float(forecast_values[0]),
                    2
                ),
            }
        )

    return chart_data


# ============================================================
# MAIN FORECASTING ANALYSIS
# ============================================================

def analyze_forecast(
    dataframe,
    date_column,
    metric_column,
    frequency="M",
    method="Linear Trend",
    horizon=3,
):
    frequency = str(
        frequency
    ).strip().upper()

    if frequency not in FREQUENCY_LABELS:
        raise ValueError(
            "Invalid forecast frequency."
        )

    method = validate_forecast_method(
        method
    )

    horizon = validate_forecast_horizon(
        horizon
    )

    time_series = prepare_time_series(
        dataframe=dataframe,
        date_column=date_column,
        metric_column=metric_column,
        frequency=frequency,
    )

    if len(time_series) < 2:
        raise ValueError(
            "At least two historical periods are "
            "required for forecasting."
        )

    values = (
        time_series["value"]
        .astype(float)
        .tolist()
    )

    if method == "Linear Trend":

        forecast_values = forecast_linear_trend(
            values=values,
            horizon=horizon,
        )

    elif method == "Moving Average":

        forecast_values = forecast_moving_average(
            values=values,
            horizon=horizon,
        )

    else:
        raise ValueError(
            "Unsupported forecasting method."
        )

    forecast_values = np.asarray(
        forecast_values,
        dtype=float
    )

    forecast_values = forecast_values[
        np.isfinite(forecast_values)
    ]

    if len(forecast_values) != horizon:
        raise ValueError(
            "The forecasting engine did not generate "
            "the requested number of forecast periods."
        )

    last_actual_value = float(
        values[-1]
    )

    first_forecast_value = float(
        forecast_values[0]
    )

    latest_forecast_value = float(
        forecast_values[-1]
    )

    average_forecast_value = float(
        np.mean(forecast_values)
    )

    minimum_forecast_value = float(
        np.min(forecast_values)
    )

    maximum_forecast_value = float(
        np.max(forecast_values)
    )

    forecast_change_percentage = (
        calculate_forecast_change_percentage(
            last_actual_value=last_actual_value,
            latest_forecast_value=latest_forecast_value,
        )
    )

    confidence_level = (
        calculate_confidence_level(
            actual_values=values,
            forecast_values=forecast_values,
        )
    )

    frequency_label = FREQUENCY_LABELS[
        frequency
    ]

    future_periods = list(
        range(
            1,
            horizon + 1
        )
    )

    chart_data = build_forecast_chart_data(
        time_series=time_series,
        forecast_periods=future_periods,
        forecast_values=forecast_values,
    )

    summary = generate_forecast_summary(
        metric_column=metric_column,
        frequency_label=frequency_label,
        method=method,
        horizon=horizon,
        last_actual_value=last_actual_value,
        first_forecast_value=first_forecast_value,
        latest_forecast_value=latest_forecast_value,
        forecast_change_percentage=(
            forecast_change_percentage
        ),
        average_forecast_value=(
            average_forecast_value
        ),
        minimum_forecast_value=(
            minimum_forecast_value
        ),
        maximum_forecast_value=(
            maximum_forecast_value
        ),
        confidence_level=confidence_level,
    )

    return {
        "date_column": str(
            date_column
        ),

        "metric_column": str(
            metric_column
        ),

        "frequency": frequency,

        "frequency_label": frequency_label,

        "method": method,

        "horizon": horizon,

        "historical_periods": len(
            time_series
        ),

        "forecast_periods": horizon,

        "last_actual_value": round(
            last_actual_value,
            2
        ),

        "first_forecast_value": round(
            first_forecast_value,
            2
        ),

        "latest_forecast_value": round(
            latest_forecast_value,
            2
        ),

        "forecast_change_percentage": (
            forecast_change_percentage
        ),

        "average_forecast_value": round(
            average_forecast_value,
            2
        ),

        "minimum_forecast_value": round(
            minimum_forecast_value,
            2
        ),

        "maximum_forecast_value": round(
            maximum_forecast_value,
            2
        ),

        "confidence_level": confidence_level,

        "summary": summary,

        "chart_data": chart_data,
    }