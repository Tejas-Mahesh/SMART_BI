# ============================================================
# ROOT CAUSE ANALYSIS SERVICE
# ============================================================

import math

import pandas as pd


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value):
    """
    Convert a value to a JSON-safe Python float.
    """
    try:
        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except (TypeError, ValueError):
        return None


def _percentage_change(current, previous):
    """
    Calculate percentage change safely.
    """
    if previous is None or previous == 0:
        if current == 0:
            return 0.0

        return None

    return ((current - previous) / abs(previous)) * 100


def _format_number(value):
    """
    Format numbers for human-readable summaries.
    """
    if value is None:
        return "N/A"

    value = float(value)

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"

    if abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"

    return f"{value:.2f}"


def _clean_dimension_value(value):
    """
    Convert dimension values into readable strings.
    """
    if pd.isna(value):
        return "Unknown"

    value = str(value).strip()

    if not value:
        return "Unknown"

    return value


# ============================================================
# MAIN ROOT CAUSE ANALYSIS
# ============================================================

def analyze_root_causes(
    dataframe,
    metric_column,
    dimension_column,
    date_column=None,
    target_period=None,
    comparison_period=None,
):
    """
    Perform contribution-based Root Cause Analysis.

    The analysis compares a target period against a comparison
    period and determines which dimension values contributed
    most to the overall change.
    """

    # ========================================================
    # VALIDATION
    # ========================================================

    if dataframe is None:
        raise ValueError("No dataset was provided.")

    if dataframe.empty:
        raise ValueError("The dataset contains no records.")

    if not metric_column:
        raise ValueError("Metric column was not provided.")

    if metric_column not in dataframe.columns:
        raise ValueError(
            f"Metric column '{metric_column}' was not found."
        )

    if not dimension_column:
        raise ValueError("Dimension column was not provided.")

    if dimension_column not in dataframe.columns:
        raise ValueError(
            f"Dimension column '{dimension_column}' was not found."
        )

    # ========================================================
    # COPY DATA
    # ========================================================

    df = dataframe.copy()

    # ========================================================
    # NUMERIC METRIC
    # ========================================================

    df[metric_column] = pd.to_numeric(
        df[metric_column],
        errors="coerce",
    )

    df = df.dropna(
        subset=[metric_column]
    ).copy()

    if df.empty:
        raise ValueError(
            f"No valid numeric values were found in '{metric_column}'."
        )

    # ========================================================
    # CLEAN DIMENSION
    # ========================================================

    df[dimension_column] = (
        df[dimension_column]
        .apply(_clean_dimension_value)
    )

    # ========================================================
    # DATE PROCESSING
    # ========================================================

    if date_column:

        if date_column not in df.columns:
            raise ValueError(
                f"Date column '{date_column}' was not found."
            )

        df["_rca_date"] = pd.to_datetime(
            df[date_column],
            errors="coerce",
        )

        df = df.dropna(
            subset=["_rca_date"]
        ).copy()

        if df.empty:
            raise ValueError(
                "No valid dates were found for Root Cause Analysis."
            )

        df["_rca_period"] = (
            df["_rca_date"]
            .dt.to_period("M")
        )

    # ========================================================
    # PERIOD FILTERING
    # ========================================================

    target_df = df.copy()
    comparison_df = df.copy()

    if date_column and target_period:

        try:
            target_period_obj = pd.Period(
                str(target_period),
                freq="M",
            )

            target_df = df[
                df["_rca_period"] == target_period_obj
            ].copy()

        except Exception:
            raise ValueError(
                "Invalid target period."
            )

    if date_column and comparison_period:

        try:
            comparison_period_obj = pd.Period(
                str(comparison_period),
                freq="M",
            )

            comparison_df = df[
                df["_rca_period"] == comparison_period_obj
            ].copy()

        except Exception:
            raise ValueError(
                "Invalid comparison period."
            )

    # ========================================================
    # CHECK PERIOD DATA
    # ========================================================

    if target_df.empty:
        raise ValueError(
            "No records were found for the selected target period."
        )

    if comparison_df.empty:
        raise ValueError(
            "No records were found for the selected comparison period."
        )

    # ========================================================
    # TOTAL VALUES
    # ========================================================

    target_total = float(
        target_df[metric_column].sum()
    )

    comparison_total = float(
        comparison_df[metric_column].sum()
    )

    change_value = (
        target_total - comparison_total
    )

    change_percentage = _percentage_change(
        target_total,
        comparison_total,
    )

    # ========================================================
    # GROUP BY DIMENSION
    # ========================================================

    target_grouped = (
        target_df
        .groupby(dimension_column)[metric_column]
        .sum()
    )

    comparison_grouped = (
        comparison_df
        .groupby(dimension_column)[metric_column]
        .sum()
    )

    all_dimensions = sorted(
        set(target_grouped.index)
        | set(comparison_grouped.index),
        key=lambda value: str(value).lower(),
    )

    cause_data = []

    # ========================================================
    # CONTRIBUTION CALCULATION
    # ========================================================

    for dimension_value in all_dimensions:

        target_value = float(
            target_grouped.get(
                dimension_value,
                0,
            )
        )

        comparison_value = float(
            comparison_grouped.get(
                dimension_value,
                0,
            )
        )

        dimension_change = (
            target_value - comparison_value
        )

        # Contribution relative to overall change.
        if change_value != 0:

            contribution_percentage = (
                dimension_change
                / abs(change_value)
            ) * 100

        else:
            contribution_percentage = 0.0

        dimension_change_percentage = _percentage_change(
            target_value,
            comparison_value,
        )

        if dimension_change > 0:
            direction = "Increase"

        elif dimension_change < 0:
            direction = "Decrease"

        else:
            direction = "No Change"

        cause_data.append(
            {
                "dimension": str(dimension_value),
                "target_value": _safe_float(target_value),
                "comparison_value": _safe_float(
                    comparison_value
                ),
                "change_value": _safe_float(
                    dimension_change
                ),
                "change_percentage": _safe_float(
                    dimension_change_percentage
                ),
                "contribution_percentage": _safe_float(
                    contribution_percentage
                ),
                "direction": direction,
            }
        )

    # ========================================================
    # SORT BY ABSOLUTE CONTRIBUTION
    # ========================================================

    cause_data.sort(
        key=lambda item: abs(
            item["contribution_percentage"] or 0
        ),
        reverse=True,
    )

    # ========================================================
    # PRIMARY CAUSE
    # ========================================================

    if cause_data:

        primary = cause_data[0]

        primary_cause = primary["dimension"]

        primary_cause_contribution = (
            primary["contribution_percentage"]
        )

    else:

        primary_cause = ""

        primary_cause_contribution = None

    # ========================================================
    # CHART DATA
    # ========================================================

    chart_data = []

    for item in cause_data:

        chart_data.append(
            {
                "label": item["dimension"],
                "change": item["change_value"],
                "contribution": item[
                    "contribution_percentage"
                ],
                "direction": item["direction"],
            }
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    target_text = _format_number(
        target_total
    )

    comparison_text = _format_number(
        comparison_total
    )

    change_text = _format_number(
        abs(change_value)
    )

    if change_percentage is None:

        percentage_text = "N/A"

    else:

        percentage_text = (
            f"{abs(change_percentage):.2f}%"
        )

    if change_value > 0:

        overall_direction = "increased"

    elif change_value < 0:

        overall_direction = "decreased"

    else:

        overall_direction = "remained unchanged"

    if primary_cause:

        primary_text = (
            f"The primary contributing factor was "
            f"{primary_cause}, contributing approximately "
            f"{abs(primary_cause_contribution or 0):.2f}% "
            f"of the overall change."
        )

    else:

        primary_text = (
            "No clear primary contributing factor "
            "was identified."
        )

    summary = (
        f"{metric_column} {overall_direction} by "
        f"{change_text} ({percentage_text}). "
        f"The target period value was {target_text}, "
        f"compared with {comparison_text} in the "
        f"comparison period. "
        f"{primary_text}"
    )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {
        "metric_column": metric_column,
        "date_column": date_column or "",
        "dimension_column": dimension_column,
        "analysis_type": "Contribution Analysis",
        "target_period": str(
            target_period or ""
        ),
        "comparison_period": str(
            comparison_period or ""
        ),
        "total_value": _safe_float(
            target_total
        ),
        "comparison_value": _safe_float(
            comparison_total
        ),
        "change_value": _safe_float(
            change_value
        ),
        "change_percentage": _safe_float(
            change_percentage
        ),
        "primary_cause": primary_cause,
        "primary_cause_contribution": _safe_float(
            primary_cause_contribution
        ),
        "cause_count": len(cause_data),
        "summary": summary,
        "cause_data": cause_data,
        "chart_data": chart_data,
    }