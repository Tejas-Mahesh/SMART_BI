import pandas as pd

from .decision_impact import (
    build_complete_impact_analysis,
    safe_float,
)


def detect_column(df, candidates):
    """
    Find the first matching column from a list of possible names.
    """

    if df is None or df.empty:
        return None

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:
        candidate_key = str(candidate).strip().lower()

        if candidate_key in normalized:
            return normalized[candidate_key]

    # Partial matching
    for column in df.columns:
        column_name = str(column).strip().lower()

        for candidate in candidates:
            candidate_key = str(candidate).strip().lower()

            if (
                candidate_key in column_name
                or column_name in candidate_key
            ):
                return column

    return None


def detect_business_columns(df):
    """
    Automatically detect the important business columns.
    """

    date_column = detect_column(
        df,
        [
            "date",
            "order_date",
            "sales_date",
            "transaction_date",
            "invoice_date",
            "created_at",
        ],
    )

    revenue_column = detect_column(
        df,
        [
            "revenue",
            "sales",
            "sales_amount",
            "total_sales",
            "total_amount",
            "order_value",
            "amount",
        ],
    )

    profit_column = detect_column(
        df,
        [
            "profit",
            "profit_amount",
            "net_profit",
            "gross_profit",
        ],
    )

    units_column = detect_column(
        df,
        [
            "units",
            "quantity",
            "qty",
            "units_sold",
            "quantity_sold",
        ],
    )

    return {
        "date": date_column,
        "revenue": revenue_column,
        "profit": profit_column,
        "units": units_column,
    }


def prepare_dataframe(df, columns):
    """
    Prepare dates and numeric business metrics.
    """

    result = df.copy()

    date_column = columns.get("date")

    if not date_column:
        return pd.DataFrame()

    result[date_column] = pd.to_datetime(
        result[date_column],
        errors="coerce",
    )

    result = result.dropna(
        subset=[date_column]
    )

    for key in [
        "revenue",
        "profit",
        "units",
    ]:

        column = columns.get(key)

        if column:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            ).fillna(0)

    return result


def calculate_period_metrics(
    df,
    columns,
):
    """
    Calculate total business performance
    for a selected period.
    """

    metrics = {
        "revenue": 0.0,
        "profit": 0.0,
        "units": 0.0,
        "transactions": 0,
    }

    if df is None or df.empty:
        return metrics

    revenue_column = columns.get("revenue")
    profit_column = columns.get("profit")
    units_column = columns.get("units")

    if revenue_column:
        metrics["revenue"] = safe_float(
            df[revenue_column].sum()
        )

    if profit_column:
        metrics["profit"] = safe_float(
            df[profit_column].sum()
        )

    if units_column:
        metrics["units"] = safe_float(
            df[units_column].sum()
        )

    metrics["transactions"] = len(df)

    return metrics


def calculate_period_change(
    before,
    after,
):
    """
    Calculate percentage changes between
    the before and after periods.
    """

    def change(before_value, after_value):
        before_value = safe_float(before_value)
        after_value = safe_float(after_value)

        if before_value == 0:

            if after_value == 0:
                return 0.0

            return 100.0

        return (
            (after_value - before_value)
            / abs(before_value)
        ) * 100

    return {
        "revenue": change(
            before.get("revenue", 0),
            after.get("revenue", 0),
        ),

        "profit": change(
            before.get("profit", 0),
            after.get("profit", 0),
        ),

        "units": change(
            before.get("units", 0),
            after.get("units", 0),
        ),
    }


def measure_action_impact(
    df,
    completed_at,
    expected_revenue_change=0,
    expected_profit_change=0,
    expected_units_change=0,
    expected_impact_score=0,
    period_days=30,
):
    """
    Measure actual business performance around
    the action completion date.

    Before:
        30 days before completion

    After:
        30 days after completion
    """

    if df is None or df.empty:
        return {
            "success": False,
            "message": "Dataset is empty.",
        }

    columns = detect_business_columns(df)

    if not columns["date"]:
        return {
            "success": False,
            "message": "No date column could be detected.",
        }

    if not columns["revenue"]:
        return {
            "success": False,
            "message": "No revenue or sales column could be detected.",
        }

    prepared = prepare_dataframe(
        df,
        columns,
    )

    if prepared.empty:
        return {
            "success": False,
            "message": "No valid dated records were found.",
        }

    completion_date = pd.to_datetime(
        completed_at,
        errors="coerce",
    )

    if pd.isna(completion_date):
        return {
            "success": False,
            "message": "Action completion date is invalid.",
        }

    completion_date = completion_date.normalize()

    before_start = (
        completion_date
        - pd.Timedelta(days=period_days)
    )

    before_end = (
        completion_date
        - pd.Timedelta(days=1)
    )

    after_start = completion_date

    after_end = (
        completion_date
        + pd.Timedelta(days=period_days - 1)
    )

    date_series = prepared[
        columns["date"]
    ].dt.normalize()

    before_df = prepared[
        (date_series >= before_start)
        & (date_series <= before_end)
    ].copy()

    after_df = prepared[
        (date_series >= after_start)
        & (date_series <= after_end)
    ].copy()

    before_metrics = calculate_period_metrics(
        before_df,
        columns,
    )

    after_metrics = calculate_period_metrics(
        after_df,
        columns,
    )

    actual_changes = calculate_period_change(
        before_metrics,
        after_metrics,
    )

    analysis = build_complete_impact_analysis(
        expected_revenue_change=expected_revenue_change,
        expected_profit_change=expected_profit_change,
        expected_units_change=expected_units_change,
        actual_revenue_change=actual_changes["revenue"],
        actual_profit_change=actual_changes["profit"],
        actual_units_change=actual_changes["units"],
        expected_impact_score=expected_impact_score,
    )

    return {
        "success": True,

        "columns": columns,

        "period": {
            "before_start": before_start.date(),
            "before_end": before_end.date(),
            "after_start": after_start.date(),
            "after_end": after_end.date(),
            "days": period_days,
        },

        "before": before_metrics,

        "after": after_metrics,

        "actual_changes": actual_changes,

        "analysis": analysis,

        "before_rows": len(before_df),
        "after_rows": len(after_df),
    }


def generate_measurement_summary(result):
    """
    Generate a business-friendly summary.
    """

    if not result.get("success"):
        return result.get(
            "message",
            "Impact measurement failed.",
        )

    analysis = result.get(
        "analysis",
        {},
    )

    actual = analysis.get(
        "actual",
        {},
    )

    status = analysis.get(
        "impact_status",
        "Neutral",
    )

    revenue = safe_float(
        actual.get(
            "revenue_change",
            0,
        )
    )

    profit = safe_float(
        actual.get(
            "profit_change",
            0,
        )
    )

    units = safe_float(
        actual.get(
            "units_change",
            0,
        )
    )

    if status == "Positive":

        return (
            f"The completed decision produced a positive "
            f"business impact. Revenue changed by "
            f"{revenue:.1f}%, profit changed by "
            f"{profit:.1f}%, and units changed by "
            f"{units:.1f}%."
        )

    if status == "Negative":

        return (
            f"The completed decision produced a negative "
            f"business impact. Revenue changed by "
            f"{revenue:.1f}%, profit changed by "
            f"{profit:.1f}%, and units changed by "
            f"{units:.1f}%."
        )

    return (
        f"The completed decision produced a neutral "
        f"business impact. Revenue changed by "
        f"{revenue:.1f}%, profit changed by "
        f"{profit:.1f}%, and units changed by "
        f"{units:.1f}%."
    )