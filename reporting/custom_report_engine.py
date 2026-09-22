
import math

import pandas as pd


# ============================================================
# COLUMN HELPERS
# ============================================================

def normalize_column_name(value):
    """
    Normalize a dataframe column name for safe comparisons.
    """
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """
    try:
        if pd.isna(value):
            return default

        number = float(value)

        if not math.isfinite(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def json_safe(value):
    """
    Convert pandas/numpy/date values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

        return round(value, 6)

    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            pass

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, (pd.Series,)):
        return [
            json_safe(item)
            for item in value.tolist()
        ]

    if isinstance(value, (list, tuple)):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    return value


# ============================================================
# DATA CLEANING
# ============================================================

def prepare_dataframe(dataframe):
    """
    Prepare a dataframe for custom report processing.
    """

    if dataframe is None:
        raise ValueError(
            "No dataset was provided."
        )

    dataframe = dataframe.copy()

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    if dataframe.empty:
        return dataframe

    # Remove completely empty rows.
    dataframe = dataframe.dropna(
        how="all"
    ).copy()

    return dataframe


# ============================================================
# COLUMN VALIDATION
# ============================================================

def validate_columns(
    dataframe,
    selected_columns=None,
    selected_metrics=None,
    selected_dimensions=None,
):
    """
    Keep only columns that actually exist in the dataframe.
    """

    available_columns = {
        str(column)
        for column in dataframe.columns
    }

    selected_columns = [
        column
        for column in (selected_columns or [])
        if column in available_columns
    ]

    selected_metrics = [
        column
        for column in (selected_metrics or [])
        if column in available_columns
    ]

    selected_dimensions = [
        column
        for column in (selected_dimensions or [])
        if column in available_columns
    ]

    return (
        selected_columns,
        selected_metrics,
        selected_dimensions,
    )


# ============================================================
# FILTERING
# ============================================================

def apply_filters(
    dataframe,
    filters=None,
):
    """
    Apply saved custom report filters.

    Supported filter structure:

    [
        {
            "column": "Region",
            "operator": "equals",
            "value": "North"
        }
    ]

    Supported operators:

    equals
    not_equals
    contains
    starts_with
    ends_with
    greater_than
    greater_or_equal
    less_than
    less_or_equal
    """

    if dataframe.empty:
        return dataframe

    if not filters:
        return dataframe

    result = dataframe.copy()

    for filter_item in filters:

        if not isinstance(filter_item, dict):
            continue

        column = filter_item.get(
            "column"
        )

        operator = filter_item.get(
            "operator",
            "equals",
        )

        value = filter_item.get(
            "value"
        )

        if column not in result.columns:
            continue

        series = result[column]

        try:

            if operator == "equals":

                mask = (
                    series.astype(str).str.strip()
                    == str(value).strip()
                )

            elif operator == "not_equals":

                mask = (
                    series.astype(str).str.strip()
                    != str(value).strip()
                )

            elif operator == "contains":

                mask = (
                    series.astype(str)
                    .str.contains(
                        str(value),
                        case=False,
                        na=False,
                    )
                )

            elif operator == "starts_with":

                mask = (
                    series.astype(str)
                    .str.startswith(
                        str(value),
                        na=False,
                    )
                )

            elif operator == "ends_with":

                mask = (
                    series.astype(str)
                    .str.endswith(
                        str(value),
                        na=False,
                    )
                )

            elif operator == "greater_than":

                numeric_series = pd.to_numeric(
                    series,
                    errors="coerce",
                )

                mask = (
                    numeric_series
                    > safe_float(value)
                )

            elif operator == "greater_or_equal":

                numeric_series = pd.to_numeric(
                    series,
                    errors="coerce",
                )

                mask = (
                    numeric_series
                    >= safe_float(value)
                )

            elif operator == "less_than":

                numeric_series = pd.to_numeric(
                    series,
                    errors="coerce",
                )

                mask = (
                    numeric_series
                    < safe_float(value)
                )

            elif operator == "less_or_equal":

                numeric_series = pd.to_numeric(
                    series,
                    errors="coerce",
                )

                mask = (
                    numeric_series
                    <= safe_float(value)
                )

            else:
                continue

            result = result.loc[mask].copy()

        except Exception:
            continue

    return result


# ============================================================
# METRIC CALCULATION
# ============================================================

def calculate_metric(
    dataframe,
    column,
    aggregation="sum",
):
    """
    Calculate a metric from a dataframe column.
    """

    if column not in dataframe.columns:
        return 0

    series = dataframe[column]

    if aggregation == "count":

        return int(
            series.notna().sum()
        )

    numeric_series = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if numeric_series.empty:
        return 0

    if aggregation == "sum":
        return safe_float(
            numeric_series.sum()
        )

    if aggregation == "average":
        return safe_float(
            numeric_series.mean()
        )

    if aggregation == "min":
        return safe_float(
            numeric_series.min()
        )

    if aggregation == "max":
        return safe_float(
            numeric_series.max()
        )

    return safe_float(
        numeric_series.sum()
    )


def calculate_metrics(
    dataframe,
    metrics,
):
    """
    Calculate all selected metrics.

    Metric configuration may be either:

    ["Sales", "Profit"]

    or:

    [
        {
            "column": "Sales",
            "aggregation": "sum"
        },
        {
            "column": "Profit",
            "aggregation": "average"
        }
    ]
    """

    results = []

    for metric in metrics or []:

        if isinstance(metric, str):

            column = metric
            aggregation = "sum"

        elif isinstance(metric, dict):

            column = metric.get(
                "column"
            )

            aggregation = metric.get(
                "aggregation",
                "sum",
            )

        else:
            continue

        if not column:
            continue

        value = calculate_metric(
            dataframe=dataframe,
            column=column,
            aggregation=aggregation,
        )

        results.append(
            {
                "column": column,
                "aggregation": aggregation,
                "label": (
                    f"{aggregation.title()} "
                    f"{column}"
                ),
                "value": json_safe(value),
            }
        )

    return results


# ============================================================
# GROUPED REPORT
# ============================================================

def build_grouped_report(
    dataframe,
    dimensions,
    metrics,
    sort_configuration=None,
):
    """
    Build grouped data using selected dimensions
    and numeric metrics.
    """

    if dataframe.empty:
        return []

    valid_dimensions = [
        dimension
        for dimension in (dimensions or [])
        if dimension in dataframe.columns
    ]

    valid_metrics = []

    for metric in metrics or []:

        if isinstance(metric, str):
            column = metric
            aggregation = "sum"

        elif isinstance(metric, dict):
            column = metric.get("column")
            aggregation = metric.get(
                "aggregation",
                "sum",
            )

        else:
            continue

        if (
            column
            and column in dataframe.columns
        ):
            valid_metrics.append(
                (
                    column,
                    aggregation,
                )
            )

    if not valid_dimensions:
        return []

    if not valid_metrics:
        grouped = (
            dataframe
            .groupby(
                valid_dimensions,
                dropna=False,
            )
            .size()
            .reset_index(
                name="count"
            )
        )

    else:

        aggregation_map = {}

        for column, aggregation in valid_metrics:

            if aggregation == "average":
                aggregation_map[column] = "mean"

            elif aggregation == "count":
                aggregation_map[column] = "count"

            elif aggregation == "min":
                aggregation_map[column] = "min"

            elif aggregation == "max":
                aggregation_map[column] = "max"

            else:
                aggregation_map[column] = "sum"

        numeric_columns = [
            column
            for column, _ in valid_metrics
        ]

        working_dataframe = dataframe.copy()

        for column in numeric_columns:
            working_dataframe[column] = pd.to_numeric(
                working_dataframe[column],
                errors="coerce",
            )

        grouped = (
            working_dataframe
            .groupby(
                valid_dimensions,
                dropna=False,
            )
            .agg(aggregation_map)
            .reset_index()
        )

    # ========================================================
    # SORTING
    # ========================================================

    if sort_configuration:
        sort_column = sort_configuration.get(
            "column"
        )

        sort_direction = sort_configuration.get(
            "direction",
            "desc",
        )

        if (
            sort_column
            and sort_column in grouped.columns
        ):
            grouped = grouped.sort_values(
                by=sort_column,
                ascending=(
                    sort_direction == "asc"
                ),
            )

    # ========================================================
    # JSON OUTPUT
    # ========================================================

    rows = []

    for _, row in grouped.iterrows():

        item = {}

        for column in grouped.columns:

            value = row[column]

            if pd.isna(value):
                value = None

            item[str(column)] = json_safe(
                value
            )

        rows.append(item)

    return rows


# ============================================================
# CHART DATA
# ============================================================

def build_chart(
    grouped_rows,
    dimensions,
    metrics,
):
    """
    Build chart-ready configuration.

    The first selected dimension becomes
    the category axis.

    The first selected metric becomes
    the primary value.
    """

    if not grouped_rows:
        return None

    if not dimensions:
        return None

    category_column = dimensions[0]

    if metrics:

        first_metric = metrics[0]

        if isinstance(first_metric, str):
            metric_column = first_metric
        else:
            metric_column = first_metric.get(
                "column"
            )

    else:
        metric_column = "count"

    if not metric_column:
        return None

    chart_data = []

    for row in grouped_rows:

        chart_data.append(
            {
                "label": json_safe(
                    row.get(category_column)
                ),
                "value": safe_float(
                    row.get(metric_column, 0)
                ),
            }
        )

    return {
        "type": "bar",
        "title": (
            f"{metric_column} by "
            f"{category_column}"
        ),
        "category": category_column,
        "value": metric_column,
        "data": chart_data[:25],
    }


# ============================================================
# INSIGHTS
# ============================================================

def generate_insights(
    grouped_rows,
    dimensions,
    metrics,
):
    """
    Generate simple descriptive insights from
    grouped report results.
    """

    insights = []

    if not grouped_rows:
        return insights

    if not dimensions:
        return insights

    dimension = dimensions[0]

    metric_column = None

    if metrics:

        first_metric = metrics[0]

        if isinstance(first_metric, str):
            metric_column = first_metric

        elif isinstance(first_metric, dict):
            metric_column = first_metric.get(
                "column"
            )

    if not metric_column:
        metric_column = "count"

    valid_rows = []

    for row in grouped_rows:

        value = safe_float(
            row.get(metric_column, 0)
        )

        valid_rows.append(
            (
                row.get(dimension),
                value,
            )
        )

    if not valid_rows:
        return insights

    highest = max(
        valid_rows,
        key=lambda item: item[1],
    )

    lowest = min(
        valid_rows,
        key=lambda item: item[1],
    )

    insights.append(
        {
            "type": "highest",
            "title": "Highest value",
            "message": (
                f"{highest[0]} has the highest "
                f"{metric_column} with "
                f"{round(highest[1], 2):,}."
            ),
        }
    )

    if len(valid_rows) > 1:

        insights.append(
            {
                "type": "lowest",
                "title": "Lowest value",
                "message": (
                    f"{lowest[0]} has the lowest "
                    f"{metric_column} with "
                    f"{round(lowest[1], 2):,}."
                ),
            }
        )

    return insights


# ============================================================
# SUMMARY
# ============================================================

def build_summary(
    original_dataframe,
    filtered_dataframe,
    selected_columns,
    selected_metrics,
    selected_dimensions,
):
    """
    Build metadata and summary for the custom report.
    """

    return {
        "original_rows": int(
            len(original_dataframe)
        ),
        "filtered_rows": int(
            len(filtered_dataframe)
        ),
        "original_columns": int(
            len(original_dataframe.columns)
        ),
        "selected_columns": int(
            len(selected_columns)
        ),
        "selected_metrics": int(
            len(selected_metrics)
        ),
        "selected_dimensions": int(
            len(selected_dimensions)
        ),
        "rows_removed_by_filters": int(
            len(original_dataframe)
            - len(filtered_dataframe)
        ),
    }


# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_custom_report(
    dataframe,
    selected_columns=None,
    selected_metrics=None,
    selected_dimensions=None,
    filters=None,
    sort_configuration=None,
    chart_configuration=None,
):
    """
    Generate a complete custom report.

    Returns:

    {
        "summary": {},
        "kpis": [],
        "sections": [],
        "charts": [],
        "insights": [],
        "metadata": {}
    }
    """

    dataframe = prepare_dataframe(
        dataframe
    )

    original_dataframe = dataframe.copy()

    if dataframe.empty:
        return {
            "summary": {
                "original_rows": 0,
                "filtered_rows": 0,
                "original_columns": 0,
                "selected_columns": 0,
                "selected_metrics": 0,
                "selected_dimensions": 0,
                "rows_removed_by_filters": 0,
            },
            "kpis": [],
            "sections": [],
            "charts": [],
            "insights": [
                {
                    "type": "warning",
                    "title": "No data",
                    "message": (
                        "The selected dataset version "
                        "does not contain usable rows."
                    ),
                }
            ],
            "metadata": {},
        }

    (
        selected_columns,
        selected_metrics,
        selected_dimensions,
    ) = validate_columns(
        dataframe=dataframe,
        selected_columns=selected_columns,
        selected_metrics=selected_metrics,
        selected_dimensions=selected_dimensions,
    )

    # ========================================================
    # FILTER
    # ========================================================

    filtered_dataframe = apply_filters(
        dataframe=dataframe,
        filters=filters,
    )

    # ========================================================
    # KPI METRICS
    # ========================================================

    kpis = calculate_metrics(
        dataframe=filtered_dataframe,
        metrics=selected_metrics,
    )

    # Always provide record count.
    kpis.insert(
        0,
        {
            "column": "__records__",
            "aggregation": "count",
            "label": "Records",
            "value": int(
                len(filtered_dataframe)
            ),
        },
    )

    # ========================================================
    # GROUPED DATA
    # ========================================================

    grouped_rows = build_grouped_report(
        dataframe=filtered_dataframe,
        dimensions=selected_dimensions,
        metrics=selected_metrics,
        sort_configuration=sort_configuration,
    )

    # ========================================================
    # SECTION
    # ========================================================

    sections = []

    if grouped_rows:

        sections.append(
            {
                "title": "Grouped Analysis",
                "description": (
                    "Analysis grouped by the "
                    "selected dimensions."
                ),
                "columns": list(
                    grouped_rows[0].keys()
                ),
                "rows": grouped_rows,
            }
        )

    elif selected_columns:

        display_columns = [
            column
            for column in selected_columns
            if column in filtered_dataframe.columns
        ]

        if display_columns:

            table_dataframe = (
                filtered_dataframe[
                    display_columns
                ]
                .head(100)
            )

            table_rows = []

            for _, row in table_dataframe.iterrows():

                table_rows.append(
                    {
                        column: json_safe(
                            row[column]
                        )
                        for column in display_columns
                    }
                )

            sections.append(
                {
                    "title": "Selected Data",
                    "description": (
                        "Rows from the selected "
                        "dataset fields."
                    ),
                    "columns": display_columns,
                    "rows": table_rows,
                }
            )

    # ========================================================
    # CHART
    # ========================================================

    charts = []

    chart = build_chart(
        grouped_rows=grouped_rows,
        dimensions=selected_dimensions,
        metrics=selected_metrics,
    )

    if chart:
        charts.append(chart)

    # Respect explicitly saved chart configuration.
    if chart_configuration:
        for configuration in chart_configuration:
            if isinstance(configuration, dict):
                chart_copy = dict(configuration)
                chart_copy.setdefault(
                    "data",
                    [],
                )
                charts.append(chart_copy)

    # ========================================================
    # INSIGHTS
    # ========================================================

    insights = generate_insights(
        grouped_rows=grouped_rows,
        dimensions=selected_dimensions,
        metrics=selected_metrics,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = build_summary(
        original_dataframe=original_dataframe,
        filtered_dataframe=filtered_dataframe,
        selected_columns=selected_columns,
        selected_metrics=selected_metrics,
        selected_dimensions=selected_dimensions,
    )

    # ========================================================
    # METADATA
    # ========================================================

    metadata = {
        "engine": "custom_report_engine",
        "version": "1.0",
        "filters_applied": len(
            filters or []
        ),
        "grouped_rows": len(
            grouped_rows
        ),
        "available_columns": [
            str(column)
            for column in dataframe.columns
        ],
    }

    return json_safe(
        {
            "summary": summary,
            "kpis": kpis,
            "sections": sections,
            "charts": charts,
            "insights": insights,
            "metadata": metadata,
        }
    )
