# ============================================================
# CUSTOMER SEGMENTATION
# Advanced Insights
# ============================================================

import numpy as np
import pandas as pd


# ============================================================
# HELPERS
# ============================================================

def _safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """
    try:
        if pd.isna(value):
            return default

        value = float(value)

        if not np.isfinite(value):
            return default

        return value

    except (TypeError, ValueError):
        return default


def _clean_column_name(column):
    """
    Normalize a column name for matching.
    """
    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _find_column(dataframe, aliases):
    """
    Find the first matching dataframe column from a list of aliases.
    """

    normalized_columns = {
        _clean_column_name(column): column
        for column in dataframe.columns
    }

    # Exact normalized match
    for alias in aliases:
        normalized_alias = _clean_column_name(alias)

        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    # Partial match
    for column in dataframe.columns:
        normalized_column = _clean_column_name(column)

        for alias in aliases:
            normalized_alias = _clean_column_name(alias)

            if (
                normalized_alias in normalized_column
                or normalized_column in normalized_alias
            ):
                return column

    return None


def _numeric_columns(dataframe):
    """
    Return columns containing usable numeric data.
    """

    columns = []

    for column in dataframe.columns:

        numeric_values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        if numeric_values.notna().sum() > 0:
            columns.append(column)

    return columns


# ============================================================
# CUSTOMER COLUMN DETECTION
# ============================================================

def detect_customer_column(dataframe):
    """
    Detect the most likely customer identifier column.
    """

    aliases = [
        "Customer_ID",
        "Customer ID",
        "CustomerID",
        "customer_id",
        "customer",
        "customer_name",
        "customer_number",
        "customer_code",
        "client_id",
        "client",
        "buyer_id",
    ]

    return _find_column(
        dataframe,
        aliases,
    )


# ============================================================
# CUSTOMER METRIC DETECTION
# ============================================================

def detect_customer_metrics(dataframe):
    """
    Detect useful numerical columns for customer segmentation.
    """

    numeric_columns = _numeric_columns(dataframe)

    metric_aliases = {
        "monetary": [
            "Sales_Amount",
            "Sales Amount",
            "Revenue",
            "Sales",
            "Amount",
            "Total_Sales",
            "Total Revenue",
            "Purchase_Amount",
            "Order_Value",
        ],
        "quantity": [
            "Quantity",
            "Units",
            "Units_Sold",
            "Purchase_Quantity",
        ],
        "profit": [
            "Profit",
            "Profit_Amount",
            "Gross_Profit",
            "Net_Profit",
        ],
        "discount": [
            "Discount",
            "Discount_Amount",
        ],
    }

    detected = {}

    for metric_type, aliases in metric_aliases.items():

        column = _find_column(
            dataframe,
            aliases,
        )

        if column and column in numeric_columns:
            detected[metric_type] = column

    # If no known aliases were found, use numeric columns
    # as fallback candidates.
    if not detected:
        detected["numeric"] = numeric_columns

    return detected


# ============================================================
# SEGMENT LABELS
# ============================================================

def _segment_label(rank, total_segments):
    """
    Create readable segment names.
    """

    labels = {
        2: {
            1: "Lower Value Customers",
            2: "Higher Value Customers",
        },
        3: {
            1: "Low Value Customers",
            2: "Medium Value Customers",
            3: "High Value Customers",
        },
        4: {
            1: "Low Value Customers",
            2: "Developing Customers",
            3: "Valuable Customers",
            4: "High Value Customers",
        },
        5: {
            1: "Low Value Customers",
            2: "Emerging Customers",
            3: "Regular Customers",
            4: "Valuable Customers",
            5: "High Value Customers",
        },
    }

    if total_segments in labels:
        return labels[total_segments].get(
            rank,
            f"Customer Segment {rank}",
        )

    return f"Customer Segment {rank}"


# ============================================================
# MAIN SEGMENTATION FUNCTION
# ============================================================

def analyze_customer_segments(
    dataframe,
    customer_column=None,
    metric_columns=None,
    number_of_segments=4,
):
    """
    Perform customer segmentation using customer-level
    aggregated numerical behavior.

    The algorithm:
        1. Validates the dataframe.
        2. Identifies the customer column.
        3. Identifies usable numerical metrics.
        4. Aggregates metrics by customer.
        5. Builds a normalized customer score.
        6. Assigns customers into value-based segments.
        7. Generates chart and table data.
    """

    if dataframe is None or dataframe.empty:
        raise ValueError(
            "The selected dataset does not contain any records."
        )

    dataframe = dataframe.copy()

    # --------------------------------------------------------
    # Validate customer column
    # --------------------------------------------------------

    if customer_column:
        if customer_column not in dataframe.columns:
            raise ValueError(
                f"Customer column '{customer_column}' "
                "was not found in the selected dataset."
            )
    else:
        customer_column = detect_customer_column(dataframe)

    if not customer_column:
        raise ValueError(
            "No customer identifier column could be detected. "
            "Please select a customer column."
        )

    # --------------------------------------------------------
    # Validate number of segments
    # --------------------------------------------------------

    try:
        number_of_segments = int(number_of_segments)
    except (TypeError, ValueError):
        number_of_segments = 4

    number_of_segments = max(
        2,
        min(number_of_segments, 5),
    )

    # --------------------------------------------------------
    # Detect metrics
    # --------------------------------------------------------

    detected_metrics = detect_customer_metrics(
        dataframe
    )

    if metric_columns:
        valid_metrics = [
            column
            for column in metric_columns
            if column in dataframe.columns
        ]
    else:
        valid_metrics = list(
            detected_metrics.values()
        )

        # Flatten fallback numeric list
        if (
            len(valid_metrics) == 1
            and isinstance(valid_metrics[0], list)
        ):
            valid_metrics = valid_metrics[0]

    # Remove duplicates
    valid_metrics = list(
        dict.fromkeys(valid_metrics)
    )

    if not valid_metrics:
        raise ValueError(
            "No usable numerical columns were found "
            "for customer segmentation."
        )

    # --------------------------------------------------------
    # Prepare customer data
    # --------------------------------------------------------

    working = dataframe[
        [customer_column] + valid_metrics
    ].copy()

    working[customer_column] = (
        working[customer_column]
        .astype(str)
        .str.strip()
    )

    working = working[
        working[customer_column].notna()
        & (
            working[customer_column] != ""
        )
        & (
            working[customer_column].str.lower()
            != "nan"
        )
    ]

    if working.empty:
        raise ValueError(
            "No valid customer records were found."
        )

    # --------------------------------------------------------
    # Convert numerical metrics
    # --------------------------------------------------------

    for column in valid_metrics:
        working[column] = pd.to_numeric(
            working[column],
            errors="coerce",
        ).fillna(0)

    # --------------------------------------------------------
    # Aggregate customer behavior
    # --------------------------------------------------------

    customer_data = (
        working
        .groupby(customer_column, as_index=False)[valid_metrics]
        .sum()
    )

    if customer_data.empty:
        raise ValueError(
            "Unable to create customer-level data."
        )

    total_customers = len(customer_data)

    if total_customers < number_of_segments:
        number_of_segments = max(
            2,
            min(number_of_segments, total_customers),
        )

    if total_customers < 2:
        raise ValueError(
            "At least two unique customers are required "
            "for segmentation."
        )

    # --------------------------------------------------------
    # Create normalized score
    # --------------------------------------------------------

    normalized_values = []

    for column in valid_metrics:

        values = pd.to_numeric(
            customer_data[column],
            errors="coerce",
        ).fillna(0)

        minimum = values.min()
        maximum = values.max()

        if maximum == minimum:
            normalized = pd.Series(
                1.0,
                index=customer_data.index,
            )
        else:
            normalized = (
                (values - minimum)
                / (maximum - minimum)
            )

        normalized_values.append(
            normalized
        )

    score = pd.concat(
        normalized_values,
        axis=1,
    ).mean(axis=1)

    customer_data["_segmentation_score"] = score

    # --------------------------------------------------------
    # Assign segments using ranked score
    # --------------------------------------------------------

    customer_data["_rank"] = (
        customer_data["_segmentation_score"]
        .rank(
            method="first",
            ascending=True,
        )
    )

    customer_data["_segment_number"] = (
        pd.qcut(
            customer_data["_rank"],
            q=number_of_segments,
            labels=False,
            duplicates="drop",
        )
        + 1
    )

    customer_data["_segment_number"] = (
        customer_data["_segment_number"]
        .astype(int)
    )

    customer_data["segment"] = (
        customer_data["_segment_number"]
        .apply(
            lambda value: _segment_label(
                int(value),
                number_of_segments,
            )
        )
    )

    # --------------------------------------------------------
    # Segment statistics
    # --------------------------------------------------------

    segment_data = []

    for segment_number in sorted(
        customer_data["_segment_number"].unique()
    ):

        segment_rows = customer_data[
            customer_data["_segment_number"]
            == segment_number
        ]

        segment_name = _segment_label(
            int(segment_number),
            number_of_segments,
        )

        count = len(segment_rows)

        percentage = (
            count
            / total_customers
            * 100
        )

        average_score = (
            segment_rows["_segmentation_score"]
            .mean()
        )

        item = {
            "segment": segment_name,
            "segment_number": int(segment_number),
            "customer_count": int(count),
            "percentage": round(
                _safe_float(percentage),
                2,
            ),
            "average_score": round(
                _safe_float(average_score),
                4,
            ),
        }

        for column in valid_metrics:
            item[column] = round(
                _safe_float(
                    segment_rows[column].sum()
                ),
                2,
            )

        segment_data.append(item)

    # --------------------------------------------------------
    # Largest segment
    # --------------------------------------------------------

    largest_segment_data = max(
        segment_data,
        key=lambda item: item["customer_count"],
    )

    largest_segment = (
        largest_segment_data["segment"]
    )

    largest_segment_count = int(
        largest_segment_data["customer_count"]
    )

    # --------------------------------------------------------
    # Customer-level result data
    # --------------------------------------------------------

    customer_result_columns = [
        customer_column,
        *valid_metrics,
        "_segmentation_score",
        "segment",
    ]

    customer_result = (
        customer_data[
            customer_result_columns
        ]
        .copy()
    )

    customer_result = customer_result.rename(
        columns={
            "_segmentation_score": "score",
        }
    )

    customer_result["score"] = (
        customer_result["score"]
        .round(4)
    )

    customer_result = (
        customer_result
        .sort_values(
            "score",
            ascending=False,
        )
    )

# ============================================================
# CUSTOMER LEVEL RESULT DATA
# ============================================================

    customer_records = []

    for _, row in customer_result.iterrows():
        metric_values = []

        for column in valid_metrics:
            metric_values.append(
            {
                "name": str(column),
                "value": round(
                    _safe_float(row[column]),
                    2,
                ),
            }
        )

        record = {
        "customer": str(
            row[customer_column]
        ),

        "metrics": metric_values,

        "score": round(
            _safe_float(row["score"]),
            4,
        ),

        "segment": str(
            row["segment"]
        ),
    }

        customer_records.append(record)

    # --------------------------------------------------------
    # Chart data
    # --------------------------------------------------------

    chart_data = []

    for item in segment_data:
        chart_data.append(
            {
                "label": item["segment"],
                "value": item["customer_count"],
                "percentage": item["percentage"],
            }
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    metric_text = ", ".join(
        str(column)
        for column in valid_metrics
    )

    summary = (
        f"{total_customers:,} unique customers were "
        f"segmented into {len(segment_data)} customer "
        f"segments using {metric_text}. "
        f"The largest segment is "
        f"'{largest_segment}' with "
        f"{largest_segment_count:,} customers."
    )

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "customer_column": customer_column,
        "metric_columns": valid_metrics,
        "segmentation_method": "Value-Based Segmentation",
        "number_of_segments": len(segment_data),
        "total_records": int(len(dataframe)),
        "total_customers": int(total_customers),
        "segmented_customers": int(total_customers),
        "segment_count": int(len(segment_data)),
        "largest_segment": largest_segment,
        "largest_segment_count": largest_segment_count,
        "summary": summary,
        "segment_data": segment_data,
        "customer_data": customer_records,
        "chart_data": chart_data,
    }