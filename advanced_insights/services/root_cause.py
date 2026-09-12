import numpy as np
import pandas as pd


def detect_column(df, candidates):
    """
    Detect a column using exact and partial matching.
    """

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:

        candidate = candidate.lower()

        if candidate in normalized:
            return normalized[candidate]

    for column in df.columns:

        column_name = str(column).strip().lower()

        for candidate in candidates:

            if candidate.lower() in column_name:
                return column

    return None


def prepare_data(df, date_column, metric_column):
    """
    Prepare transaction data for root cause analysis.
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
        subset=[
            date_column,
            metric_column
        ]
    )

    return data


def calculate_periods(
    data,
    date_column,
    period_days=30
):
    """
    Compare the latest period with the immediately
    preceding period of equal length.
    """

    if data.empty:
        return (
            data.iloc[0:0].copy(),
            data.iloc[0:0].copy(),
            None,
            None,
            None,
            None,
        )

    max_date = data[date_column].max().normalize()

    current_start = (
        max_date
        - pd.Timedelta(days=period_days - 1)
    )

    previous_end = (
        current_start
        - pd.Timedelta(days=1)
    )

    previous_start = (
        previous_end
        - pd.Timedelta(days=period_days - 1)
    )

    current = data[
        (data[date_column] >= current_start)
        &
        (data[date_column] <= max_date)
    ].copy()

    previous = data[
        (data[date_column] >= previous_start)
        &
        (data[date_column] <= previous_end)
    ].copy()

    return (
        current,
        previous,
        current_start,
        max_date,
        previous_start,
        previous_end,
    )


def calculate_percentage_change(
    current,
    previous
):
    """
    Calculate percentage change safely.
    """

    try:
        current = float(current)
        previous = float(previous)
    except (ValueError, TypeError):

        return 0

    if previous == 0:

        if current == 0:
            return 0

        return 100

    return (
        (current - previous)
        / previous
    ) * 100


def analyze_dimension(
    current,
    previous,
    dimension_column,
    metric_column
):
    """
    Compare current vs previous performance
    for one business dimension.
    """

    current_group = (
        current
        .groupby(dimension_column)[metric_column]
        .sum()
        .rename("current_value")
    )

    previous_group = (
        previous
        .groupby(dimension_column)[metric_column]
        .sum()
        .rename("previous_value")
    )

    comparison = pd.concat(
        [
            current_group,
            previous_group
        ],
        axis=1
    ).fillna(0)

    comparison["change"] = (
        comparison["current_value"]
        - comparison["previous_value"]
    )

    comparison["change_percent"] = comparison.apply(
        lambda row: calculate_percentage_change(
            row["current_value"],
            row["previous_value"]
        ),
        axis=1
    )

    comparison["abs_change"] = (
        comparison["change"].abs()
    )

    comparison = comparison.sort_values(
        "abs_change",
        ascending=False
    )

    return comparison


def find_root_causes(
    current,
    previous,
    metric_column,
    dimensions
):
    """
    Analyze available business dimensions and identify
    the strongest contributors to change.
    """

    results = []

    overall_current = current[metric_column].sum()
    overall_previous = previous[metric_column].sum()

    overall_change = (
        overall_current
        - overall_previous
    )

    for dimension in dimensions:

        if not dimension:
            continue

        if dimension not in current.columns:
            continue

        # Avoid analyzing continuous numeric columns
        # as business dimensions.
        if pd.api.types.is_numeric_dtype(
            current[dimension]
        ):
            continue

        current_copy = current.copy()
        previous_copy = previous.copy()

        current_copy[dimension] = (
            current_copy[dimension]
            .astype(str)
            .replace(
                "nan",
                "Unknown"
            )
        )

        previous_copy[dimension] = (
            previous_copy[dimension]
            .astype(str)
            .replace(
                "nan",
                "Unknown"
            )
        )

        comparison = analyze_dimension(
            current_copy,
            previous_copy,
            dimension,
            metric_column
        )

        if comparison.empty:
            continue

        for category, row in comparison.head(10).iterrows():

            contribution = 0

            if overall_change != 0:

                contribution = (
                    row["change"]
                    / overall_change
                ) * 100

            results.append({

                "dimension": str(dimension),

                "category": str(category),

                "current_value": round(
                    float(row["current_value"]),
                    2
                ),

                "previous_value": round(
                    float(row["previous_value"]),
                    2
                ),

                "change": round(
                    float(row["change"]),
                    2
                ),

                "change_percent": round(
                    float(row["change_percent"]),
                    2
                ),

                "contribution": round(
                    float(contribution),
                    2
                ),

            })

    # Strongest contributors first
    results.sort(
        key=lambda item: abs(
            item["change"]
        ),
        reverse=True
    )

    return results


def generate_root_cause_insights(
    results,
    overall_change,
    metric_column
):
    """
    Convert statistical findings into business language.
    """

    insights = []

    if not results:

        insights.append(
            "No suitable categorical business dimensions "
            "were available for root cause analysis."
        )

        return insights

    if overall_change < 0:

        insights.append(
            f"{metric_column} declined during the latest "
            "analysis period compared with the previous period."
        )

        negative_results = [
            item
            for item in results
            if item["change"] < 0
        ]

        for item in negative_results[:3]:

            insights.append(
                f"{item['dimension']} = "
                f"{item['category']} recorded a "
                f"{abs(item['change_percent']):.2f}% decline."
            )

    elif overall_change > 0:

        insights.append(
            f"{metric_column} increased during the latest "
            "analysis period compared with the previous period."
        )

        positive_results = [
            item
            for item in results
            if item["change"] > 0
        ]

        for item in positive_results[:3]:

            insights.append(
                f"{item['dimension']} = "
                f"{item['category']} recorded a "
                f"{item['change_percent']:.2f}% increase "
                "and may be contributing to overall growth."
            )

    else:

        insights.append(
            f"{metric_column} remained broadly stable "
            "between the two comparison periods."
        )

    return insights