import re

import numpy as np
import pandas as pd


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_column_name(value):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).strip().lower(),
    ).strip("_")


def _find_column(dataframe, aliases):
    """
    Find a dataframe column using normalized aliases.
    """
    normalized_columns = {
        _clean_column_name(column): column
        for column in dataframe.columns
    }

    for alias in aliases:
        normalized_alias = _clean_column_name(alias)

        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    return None


def _numeric_columns(dataframe):
    """
    Return columns that contain usable numeric values.
    """
    columns = []

    for column in dataframe.columns:
        converted = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        if converted.notna().sum() > 0:
            columns.append(column)

    return columns


# ============================================================
# COLUMN DETECTION
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
        "buyer",
        "account_id",
        "account",
    ]

    column = _find_column(
        dataframe,
        aliases,
    )

    if column:
        return column

    # Fallback keyword detection.
    for column in dataframe.columns:

        normalized = _clean_column_name(column)

        if (
            "customer" in normalized
            or "client" in normalized
            or "buyer" in normalized
        ):
            return column

    return None


def detect_date_column(dataframe):
    """
    Detect the most likely transaction/activity date column.
    """

    aliases = [
        "Order_Date",
        "Order Date",
        "Transaction_Date",
        "Transaction Date",
        "Purchase_Date",
        "Purchase Date",
        "Invoice_Date",
        "Invoice Date",
        "Date",
        "Activity_Date",
        "Activity Date",
        "Last_Purchase_Date",
        "Last Purchase Date",
    ]

    column = _find_column(
        dataframe,
        aliases,
    )

    if column:
        return column

    # Fallback:
    # Only accept a column when most non-empty values
    # can actually be interpreted as dates.
    for column in dataframe.columns:

        series = dataframe[column]

        if pd.api.types.is_numeric_dtype(series):
            continue

        parsed = pd.to_datetime(
            series,
            errors="coerce",
        )

        non_empty = series.notna().sum()

        if non_empty == 0:
            continue

        success_rate = parsed.notna().sum() / non_empty

        if success_rate >= 0.70:
            return column

    return None


def detect_activity_metrics(dataframe):
    """
    Detect useful customer activity/value columns.
    """

    aliases = [
        "Sales_Amount",
        "Sales Amount",
        "Revenue",
        "Sales",
        "Amount",
        "Total_Sales",
        "Total Revenue",
        "Purchase_Amount",
        "Order_Value",
        "Quantity",
        "Units",
        "Units_Sold",
        "Purchase_Quantity",
        "Profit",
        "Profit_Amount",
        "Gross_Profit",
        "Net_Profit",
        "Order_ID",
        "Order ID",
        "Transaction_ID",
        "Transaction ID",
    ]

    metrics = []

    for alias in aliases:

        column = _find_column(
            dataframe,
            [alias],
        )

        if column and column not in metrics:
            metrics.append(column)

    # Add numeric fallback columns.
    for column in _numeric_columns(dataframe):

        if column not in metrics:
            metrics.append(column)

    return metrics


# ============================================================
# RISK LABELS
# ============================================================

def _risk_label(score):
    """
    Convert a 0-100 risk score into a risk category.
    """

    score = _safe_float(score)

    if score >= 67:
        return "High Risk"

    if score >= 34:
        return "Medium Risk"

    return "Low Risk"


def _risk_reason(
    recency_score,
    frequency_score,
    value_score,
):
    """
    Generate an understandable reason for the risk classification.
    """

    reasons = []

    if recency_score >= 67:
        reasons.append("Long time since last activity")
    elif recency_score >= 34:
        reasons.append("Moderate activity gap")

    if frequency_score >= 67:
        reasons.append("Low activity frequency")
    elif frequency_score >= 34:
        reasons.append("Moderate activity frequency")

    if value_score >= 67:
        reasons.append("Low customer value")
    elif value_score >= 34:
        reasons.append("Moderate customer value")

    if not reasons:
        reasons.append("Recent and consistent activity")

    return ", ".join(reasons)


# ============================================================
# MAIN CHURN / RISK ANALYSIS
# ============================================================

def analyze_churn_risk(
    dataframe,
    customer_column=None,
    date_column=None,
    metric_columns=None,
):
    """
    Perform activity-based customer churn/risk analysis.

    Risk is estimated from:
        1. Recency
        2. Activity frequency
        3. Customer value

    The function does not require a historical churn label.
    """

    if dataframe is None:
        raise ValueError("No dataset was provided.")

    if dataframe.empty:
        raise ValueError("The selected dataset contains no records.")

    dataframe = dataframe.copy()

    # --------------------------------------------------------
    # CUSTOMER COLUMN
    # --------------------------------------------------------

    if not customer_column:
        customer_column = detect_customer_column(dataframe)

    if not customer_column:
        raise ValueError(
            "No customer column could be detected. "
            "Please select a dataset containing a customer identifier."
        )

    if customer_column not in dataframe.columns:
        raise ValueError(
            f"Customer column '{customer_column}' was not found."
        )

    # Remove empty customer records.
    dataframe = dataframe[
        dataframe[customer_column].notna()
    ].copy()

    if dataframe.empty:
        raise ValueError(
            "No valid customer records were found."
        )

    dataframe[customer_column] = (
        dataframe[customer_column]
        .astype(str)
        .str.strip()
    )

    dataframe = dataframe[
        dataframe[customer_column] != ""
    ].copy()

    if dataframe.empty:
        raise ValueError(
            "No valid customer identifiers were found."
        )

    # --------------------------------------------------------
    # DATE COLUMN
    # --------------------------------------------------------

    if not date_column:
        date_column = detect_date_column(dataframe)

    parsed_dates = None

    if date_column:

        if date_column not in dataframe.columns:
            raise ValueError(
                f"Date column '{date_column}' was not found."
            )

        parsed_dates = pd.to_datetime(
            dataframe[date_column],
            errors="coerce",
        )

        valid_date_count = parsed_dates.notna().sum()

        if valid_date_count == 0:
            date_column = None
            parsed_dates = None

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    if metric_columns is None:
        metric_columns = detect_activity_metrics(
            dataframe
        )

    metric_columns = [
        column
        for column in metric_columns
        if column in dataframe.columns
    ]

    # Keep only numeric metrics.
    valid_metrics = []

    for column in metric_columns:

        numeric_values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        if numeric_values.notna().sum() > 0:

            dataframe[column] = numeric_values

            valid_metrics.append(column)

    # --------------------------------------------------------
    # CUSTOMER AGGREGATION
    # --------------------------------------------------------

    grouped = dataframe.groupby(
        customer_column,
        dropna=False,
    )

    customer_result = grouped.size().reset_index(
        name="_activity_frequency"
    )

    # --------------------------------------------------------
    # RECENCY
    # --------------------------------------------------------

    if parsed_dates is not None:

        dataframe["_parsed_activity_date"] = parsed_dates

        latest_dataset_date = (
            dataframe["_parsed_activity_date"]
            .max()
        )

        latest_dates = (
            dataframe
            .groupby(customer_column)["_parsed_activity_date"]
            .max()
            .reset_index()
        )

        latest_dates["_recency_days"] = (
            latest_dataset_date
            - latest_dates["_parsed_activity_date"]
        ).dt.days

        latest_dates["_recency_days"] = (
            latest_dates["_recency_days"]
            .fillna(0)
            .clip(lower=0)
        )

        customer_result = customer_result.merge(
            latest_dates[
                [
                    customer_column,
                    "_parsed_activity_date",
                    "_recency_days",
                ]
            ],
            on=customer_column,
            how="left",
        )

    else:

        customer_result["_recency_days"] = 0

    # --------------------------------------------------------
    # METRIC AGGREGATION
    # --------------------------------------------------------

    for column in valid_metrics:

        metric_values = (
            dataframe
            .groupby(customer_column)[column]
            .sum(min_count=1)
            .reset_index()
        )

        metric_values[column] = (
            metric_values[column]
            .fillna(0)
        )

        customer_result = customer_result.merge(
            metric_values,
            on=customer_column,
            how="left",
        )

    # --------------------------------------------------------
    # CUSTOMER VALUE
    # --------------------------------------------------------

    preferred_value_column = _find_column(
        customer_result,
        [
            "Sales_Amount",
            "Sales Amount",
            "Revenue",
            "Sales",
            "Amount",
            "Total_Sales",
            "Total Revenue",
            "Purchase_Amount",
            "Order_Value",
            "Profit",
        ],
    )

    if preferred_value_column:

        customer_result["_customer_value"] = (
            pd.to_numeric(
                customer_result[
                    preferred_value_column
                ],
                errors="coerce",
            )
            .fillna(0)
        )

    elif valid_metrics:

        customer_result["_customer_value"] = (
            customer_result[valid_metrics]
            .apply(
                pd.to_numeric,
                errors="coerce",
            )
            .fillna(0)
            .sum(axis=1)
        )

    else:

        customer_result["_customer_value"] = (
            customer_result["_activity_frequency"]
            .astype(float)
        )

    # --------------------------------------------------------
    # RECENCY RISK
    # --------------------------------------------------------

    if parsed_dates is not None:

        max_recency = customer_result[
            "_recency_days"
        ].max()

        if max_recency > 0:

            customer_result[
                "_recency_score"
            ] = (
                customer_result[
                    "_recency_days"
                ]
                / max_recency
                * 100
            )

        else:

            customer_result[
                "_recency_score"
            ] = 0

    else:

        customer_result[
            "_recency_score"
        ] = 0

    # --------------------------------------------------------
    # FREQUENCY RISK
    # --------------------------------------------------------

    frequency = customer_result[
        "_activity_frequency"
    ].astype(float)

    max_frequency = frequency.max()

    if max_frequency > 0:

        customer_result[
            "_frequency_score"
        ] = (
            1
            - (
                frequency
                / max_frequency
            )
        ) * 100

    else:

        customer_result[
            "_frequency_score"
        ] = 0

    # --------------------------------------------------------
    # VALUE RISK
    # --------------------------------------------------------

    customer_value = (
        customer_result[
            "_customer_value"
        ]
        .astype(float)
        .clip(lower=0)
    )

    max_value = customer_value.max()

    if max_value > 0:

        customer_result[
            "_value_score"
        ] = (
            1
            - (
                customer_value
                / max_value
            )
        ) * 100

    else:

        customer_result[
            "_value_score"
        ] = 0

    # --------------------------------------------------------
    # FINAL RISK SCORE
    # --------------------------------------------------------

    customer_result[
        "_risk_score"
    ] = (
        customer_result[
            "_recency_score"
        ] * 0.50
        +
        customer_result[
            "_frequency_score"
        ] * 0.30
        +
        customer_result[
            "_value_score"
        ] * 0.20
    )

    customer_result[
        "_risk_score"
    ] = (
        customer_result[
            "_risk_score"
        ]
        .clip(0, 100)
        .round(2)
    )

    # --------------------------------------------------------
    # RISK CATEGORY
    # --------------------------------------------------------

    customer_result["risk_level"] = (
        customer_result[
            "_risk_score"
        ]
        .apply(_risk_label)
    )

    # --------------------------------------------------------
    # RISK REASON
    # --------------------------------------------------------

    customer_result["risk_reason"] = customer_result.apply(
        lambda row: _risk_reason(
            row["_recency_score"],
            row["_frequency_score"],
            row["_value_score"],
        ),
        axis=1,
    )

    # --------------------------------------------------------
    # SORT HIGHEST RISK FIRST
    # --------------------------------------------------------

    customer_result = customer_result.sort_values(
        "_risk_score",
        ascending=False,
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # RISK COUNTS
    # --------------------------------------------------------

    high_risk_count = int(
        (
            customer_result["risk_level"]
            == "High Risk"
        ).sum()
    )

    medium_risk_count = int(
        (
            customer_result["risk_level"]
            == "Medium Risk"
        ).sum()
    )

    low_risk_count = int(
        (
            customer_result["risk_level"]
            == "Low Risk"
        ).sum()
    )

    total_customers = len(
        customer_result
    )

    assessed_customers = total_customers

    high_risk_percentage = (
        high_risk_count
        / total_customers
        * 100
        if total_customers
        else 0
    )

    average_risk_score = (
        customer_result[
            "_risk_score"
        ].mean()
        if total_customers
        else 0
    )

    # --------------------------------------------------------
    # HIGHEST RISK CUSTOMER
    # --------------------------------------------------------

    if total_customers:

        highest_risk_row = (
            customer_result.iloc[0]
        )

        highest_risk_customer = str(
            highest_risk_row[
                customer_column
            ]
        )

        highest_risk_score = _safe_float(
            highest_risk_row[
                "_risk_score"
            ]
        )

    else:

        highest_risk_customer = ""
        highest_risk_score = 0

    # --------------------------------------------------------
    # SEGMENT / RISK DATA
    # --------------------------------------------------------

    risk_data = [
        {
            "risk_level": "High Risk",
            "count": high_risk_count,
            "percentage": round(
                high_risk_count
                / total_customers
                * 100,
                2,
            )
            if total_customers
            else 0,
        },
        {
            "risk_level": "Medium Risk",
            "count": medium_risk_count,
            "percentage": round(
                medium_risk_count
                / total_customers
                * 100,
                2,
            )
            if total_customers
            else 0,
        },
        {
            "risk_level": "Low Risk",
            "count": low_risk_count,
            "percentage": round(
                low_risk_count
                / total_customers
                * 100,
                2,
            )
            if total_customers
            else 0,
        },
    ]

    # --------------------------------------------------------
    # CUSTOMER DATA
    # --------------------------------------------------------

    customer_data = []

    for _, row in customer_result.iterrows():

        record = {
            "customer": str(
                row[customer_column]
            ),

            "risk_score": round(
                _safe_float(
                    row["_risk_score"]
                ),
                2,
            ),

            "risk_level": str(
                row["risk_level"]
            ),

            "risk_reason": str(
                row["risk_reason"]
            ),

            "recency_days": int(
                max(
                    0,
                    _safe_float(
                        row["_recency_days"]
                    ),
                )
            ),

            "activity_frequency": int(
                max(
                    0,
                    _safe_float(
                        row[
                            "_activity_frequency"
                        ]
                    ),
                )
            ),

            "customer_value": round(
                _safe_float(
                    row[
                        "_customer_value"
                    ]
                ),
                2,
            ),
        }

        if parsed_dates is not None:

            latest_activity = (
                row.get(
                    "_parsed_activity_date"
                )
            )

            if pd.notna(
                latest_activity
            ):
                record[
                    "last_activity"
                ] = latest_activity.strftime(
                    "%Y-%m-%d"
                )
            else:
                record[
                    "last_activity"
                ] = ""

        else:

            record[
                "last_activity"
            ] = ""

        metric_values = []

        for column in valid_metrics:

            metric_values.append(
                {
                    "name": str(column),
                    "value": round(
                        _safe_float(
                            row[column]
                        ),
                        2,
                    ),
                }
            )

        record[
            "metrics"
        ] = metric_values

        customer_data.append(
            record
        )

    # --------------------------------------------------------
    # CHART DATA
    # --------------------------------------------------------

    chart_data = [
        {
            "label": item["risk_level"],
            "value": item["count"],
        }
        for item in risk_data
    ]

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if total_customers == 0:

        summary = (
            "No customers were available "
            "for churn risk assessment."
        )

    else:

        if parsed_dates is not None:

            summary = (
                f"{total_customers} customers were assessed "
                f"using activity recency, frequency, and "
                f"customer value. "
                f"{high_risk_count} customers "
                f"({high_risk_percentage:.2f}%) "
                f"are currently classified as high risk."
            )

        else:

            summary = (
                f"{total_customers} customers were assessed "
                f"using available activity frequency and "
                f"customer value information. "
                f"{high_risk_count} customers "
                f"({high_risk_percentage:.2f}%) "
                f"are currently classified as high risk. "
                f"No reliable activity date was available, "
                f"so recency was not included."
            )

    # --------------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------------

    return {
        "customer_column": customer_column,

        "date_column": date_column or "",

        "metric_columns": valid_metrics,

        "risk_method": (
            "Activity-Based Risk Analysis"
        ),

        "total_records": int(
            len(dataframe)
        ),

        "total_customers": int(
            total_customers
        ),

        "assessed_customers": int(
            assessed_customers
        ),

        "high_risk_customers": int(
            high_risk_count
        ),

        "medium_risk_customers": int(
            medium_risk_count
        ),

        "low_risk_customers": int(
            low_risk_count
        ),

        "high_risk_percentage": round(
            high_risk_percentage,
            2,
        ),

        "average_risk_score": round(
            _safe_float(
                average_risk_score
            ),
            2,
        ),

        "highest_risk_customer": (
            highest_risk_customer
        ),

        "highest_risk_score": round(
            highest_risk_score,
            2,
        ),

        "summary": summary,

        "risk_data": risk_data,

        "customer_data": customer_data,

        "chart_data": chart_data,
    }