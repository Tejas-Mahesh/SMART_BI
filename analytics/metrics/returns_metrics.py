
"""
Returns Intelligence Metrics
=============================

Reusable metrics and analytics for the Returns Intelligence module.

Architecture rules:
- Analytics consume the dataframe from the current DatasetVersion.
- No storage/version-management logic belongs in this module.
- Missing columns return unavailable metrics/charts instead of fabricated
  zero values.
- Common return-data column aliases are supported.
- Functions are designed to work with analytics/views/returns.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


# ============================================================================
# COLUMN DEFINITIONS
# ============================================================================

CORE_REQUIRED_COLUMNS = [
    "Return_Date",
]


OPTIONAL_COLUMNS = [
    "Return_ID",
    "Order_ID",
    "Customer_ID",
    "Product_ID",

    "Product_Name",
    "Category",

    "Return_Date",
    "Order_Date",

    "Quantity",
    "Returned_Quantity",
    "Return_Quantity",
    "Units_Returned",

    "Sales_Amount",
    "Sales",
    "Revenue",
    "Order_Value",

    "Return_Amount",
    "Refund_Amount",
    "Refund_Value",
    "Returned_Value",

    "Unit_Price",
    "Price",

    "Cost",
    "Cost_Amount",

    "Profit",
    "Profit_Amount",

    "Return_Reason",
    "Reason",

    "Return_Status",
    "Status",

    "Return_Type",
    "Return_Method",

    "Region",
    "City",
    "State",
    "Country",

    "Customer_Segment",
    "Customer_Status",

    "Payment_Method",
    "Sales_Channel",
]


# ============================================================================
# COLUMN ALIASES
# ============================================================================

COLUMN_ALIASES = {

    "Return_ID": [
        "Return_ID",
        "Return_Id",
        "Return_Number",
        "Return_No",
        "Return",
    ],

    "Order_ID": [
        "Order_ID",
        "Order_Id",
        "Order_Number",
        "Order_No",
        "Order",
    ],

    "Customer_ID": [
        "Customer_ID",
        "Customer_Id",
        "Customer_Number",
        "Customer_No",
        "Customer",
    ],

    "Product_ID": [
        "Product_ID",
        "Product_Id",
        "Product_Number",
        "Product_No",
    ],

    "Product_Name": [
        "Product_Name",
        "Product",
        "Product_Title",
        "Item_Name",
        "Item",
    ],

    "Category": [
        "Category",
        "Product_Category",
        "Item_Category",
        "Product_Type",
    ],

    "Return_Date": [
        "Return_Date",
        "Returned_Date",
        "Date_Returned",
        "Refund_Date",
        "Date",
    ],

    "Order_Date": [
        "Order_Date",
        "Purchase_Date",
        "Sale_Date",
        "OrderDate",
    ],

    "Quantity": [
        "Quantity",
        "Units",
        "Units_Sold",
        "Order_Quantity",
        "Sold_Quantity",
    ],

    "Returned_Quantity": [
        "Returned_Quantity",
        "Return_Quantity",
        "Units_Returned",
        "Quantity_Returned",
        "Returned_Units",
    ],

    "Sales_Amount": [
        "Sales_Amount",
        "Sales",
        "Revenue",
        "Order_Value",
        "Order_Amount",
        "Sale_Amount",
        "Total_Sales",
    ],

    "Return_Amount": [
        "Return_Amount",
        "Refund_Amount",
        "Refund_Value",
        "Returned_Value",
        "Return_Value",
        "Refund",
    ],

    "Unit_Price": [
        "Unit_Price",
        "Price",
        "Selling_Price",
        "Sale_Price",
    ],

    "Cost": [
        "Cost",
        "Cost_Amount",
        "Product_Cost",
        "Unit_Cost",
        "Total_Cost",
    ],

    "Profit": [
        "Profit",
        "Profit_Amount",
        "Net_Profit",
        "Gross_Profit",
    ],

    "Return_Reason": [
        "Return_Reason",
        "Reason",
        "Return_Cause",
        "Reason_for_Return",
    ],

    "Return_Status": [
        "Return_Status",
        "Status",
        "Return_State",
        "Refund_Status",
    ],

    "Return_Type": [
        "Return_Type",
        "Type_of_Return",
        "Refund_Type",
    ],

    "Return_Method": [
        "Return_Method",
        "Method",
        "Refund_Method",
    ],

    "Region": [
        "Region",
        "Area",
        "Territory",
        "Sales_Region",
    ],

    "City": [
        "City",
        "Town",
    ],

    "State": [
        "State",
        "Province",
    ],

    "Country": [
        "Country",
        "Nation",
    ],

    "Customer_Segment": [
        "Customer_Segment",
        "Segment",
        "Customer_Group",
    ],

    "Customer_Status": [
        "Customer_Status",
        "Customer_State",
    ],

    "Payment_Method": [
        "Payment_Method",
        "Payment_Type",
        "Payment",
    ],

    "Sales_Channel": [
        "Sales_Channel",
        "Channel",
        "Order_Channel",
    ],
}


# ============================================================================
# GENERAL HELPERS
# ============================================================================

def normalize_column_name(
    column: Any,
) -> str:
    """
    Normalize a dataframe column name for alias matching.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def resolve_columns(
    dataframe: pd.DataFrame,
    aliases: Optional[
        Dict[str, List[str]]
    ] = None,
) -> Dict[str, Optional[str]]:
    """
    Resolve canonical names to actual dataframe columns.
    """

    if dataframe is None:
        return {}

    aliases = aliases or COLUMN_ALIASES

    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    resolved = {}

    for canonical_name, possible_names in aliases.items():

        actual_column = None

        for possible_name in possible_names:

            normalized_name = normalize_column_name(
                possible_name
            )

            if normalized_name in normalized_columns:

                actual_column = normalized_columns[
                    normalized_name
                ]

                break

        resolved[canonical_name] = actual_column

    return resolved


def prepare_returns_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare the returns dataframe without modifying the original object.

    The resolved-column mapping is stored in dataframe.attrs for reuse.
    """

    if dataframe is None:
        return pd.DataFrame()

    prepared = dataframe.copy()

    prepared.attrs[
        "_resolved_columns"
    ] = resolve_columns(
        prepared
    )

    return prepared


def get_resolved_columns(
    dataframe: pd.DataFrame,
) -> Dict[str, Optional[str]]:
    """
    Return the cached column mapping or resolve it.
    """

    if dataframe is None:
        return {}

    resolved = dataframe.attrs.get(
        "_resolved_columns"
    )

    if resolved:
        return resolved

    return resolve_columns(
        dataframe
    )


def get_column(
    dataframe: pd.DataFrame,
    canonical_name: str,
) -> Optional[str]:
    """
    Return the actual dataframe column associated with a canonical name.
    """

    return get_resolved_columns(
        dataframe
    ).get(
        canonical_name
    )


def get_numeric_series(
    dataframe: pd.DataFrame,
    column: Optional[str],
) -> Optional[pd.Series]:
    """
    Safely convert a column to numeric values.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not column
        or column not in dataframe.columns
    ):
        return None

    return pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )


def safe_sum(
    dataframe: pd.DataFrame,
    column: Optional[str],
) -> Optional[float]:
    """
    Return a numeric sum or None when usable data is unavailable.
    """

    series = get_numeric_series(
        dataframe,
        column,
    )

    if series is None:
        return None

    if series.notna().sum() == 0:
        return None

    return float(
        series.sum(
            skipna=True
        )
    )


def safe_mean(
    dataframe: pd.DataFrame,
    column: Optional[str],
) -> Optional[float]:
    """
    Return a numeric mean or None.
    """

    series = get_numeric_series(
        dataframe,
        column,
    )

    if series is None:
        return None

    if series.notna().sum() == 0:
        return None

    return float(
        series.mean(
            skipna=True
        )
    )


def round_value(
    value: Any,
    digits: int = 2,
) -> Optional[float]:
    """
    Safely round numeric values.
    """

    if value is None:
        return None

    try:

        if pd.isna(value):
            return None

    except (
        TypeError,
        ValueError,
    ):
        pass

    try:

        return round(
            float(value),
            digits,
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


def clean_text_series(
    series: pd.Series,
) -> pd.Series:
    """
    Clean categorical values used in grouping.
    """

    cleaned = (
        series
        .astype(str)
        .str.strip()
    )

    cleaned = cleaned.replace(
        {
            "": "Unknown",
            "nan": "Unknown",
            "NaN": "Unknown",
            "None": "Unknown",
        }
    )

    return cleaned


# ============================================================================
# COLUMN ACCESSORS
# ============================================================================

def get_return_date_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Return_Date",
    )


def get_order_date_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Order_Date",
    )


def get_return_id_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Return_ID",
    )


def get_order_id_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Order_ID",
    )


def get_product_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return (
        get_column(
            dataframe,
            "Product_Name",
        )
        or get_column(
            dataframe,
            "Product_ID",
        )
    )


def get_category_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Category",
    )


def get_return_quantity_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Returned_Quantity",
    )


def get_quantity_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Quantity",
    )


def get_sales_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Sales_Amount",
    )


def get_return_amount_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Return_Amount",
    )


def get_profit_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Profit",
    )


def get_reason_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Return_Reason",
    )


def get_status_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Return_Status",
    )


def get_region_column(
    dataframe: pd.DataFrame,
) -> Optional[str]:
    return get_column(
        dataframe,
        "Region",
    )


# ============================================================================
# CORE RETURN METRICS
# ============================================================================

def calculate_returns_metrics(
    dataframe: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Calculate the primary Returns Intelligence KPIs.

    Unsupported metrics are represented by None.
    """

    metrics = {

        "total_returns": None,

        "returned_units": None,

        "return_value": None,

        "total_sales": None,

        "return_rate": None,

        "average_return_value": None,

        "average_return_units": None,

        "returning_customers": None,

        "return_customer_rate": None,

        "top_return_reason": None,

        "top_return_reason_count": None,

        "top_return_product": None,

        "top_return_product_count": None,

        "top_return_region": None,

        "top_return_region_count": None,

        "return_growth": None,
    }

    if (
        dataframe is None
        or dataframe.empty
    ):
        return metrics

    # ------------------------------------------------------------------
    # Return count
    # ------------------------------------------------------------------

    return_id_column = (
        get_return_id_column(
            dataframe
        )
    )

    if return_id_column:

        values = (
            dataframe[
                return_id_column
            ]
            .dropna()
        )

        if not values.empty:

            metrics[
                "total_returns"
            ] = int(
                values.nunique()
            )

    else:

        # A row can represent one return when no Return_ID exists.
        metrics[
            "total_returns"
        ] = int(
            len(dataframe.index)
        )

    # ------------------------------------------------------------------
    # Returned quantity
    # ------------------------------------------------------------------

    return_quantity_column = (
        get_return_quantity_column(
            dataframe
        )
    )

    returned_units = safe_sum(
        dataframe,
        return_quantity_column,
    )

    metrics[
        "returned_units"
    ] = round_value(
        returned_units
    )

    # ------------------------------------------------------------------
    # Return value
    # ------------------------------------------------------------------

    return_amount_column = (
        get_return_amount_column(
            dataframe
        )
    )

    return_value = safe_sum(
        dataframe,
        return_amount_column,
    )

    metrics[
        "return_value"
    ] = round_value(
        return_value
    )

    # ------------------------------------------------------------------
    # Sales value
    # ------------------------------------------------------------------

    sales_column = get_sales_column(
        dataframe
    )

    total_sales = safe_sum(
        dataframe,
        sales_column,
    )

    metrics[
        "total_sales"
    ] = round_value(
        total_sales
    )

    # ------------------------------------------------------------------
    # Return rate
    #
    # If quantity sold is available, use:
    # returned units / sold units * 100
    #
    # Otherwise use return records / sales records * 100.
    # ------------------------------------------------------------------

    quantity_column = get_quantity_column(
        dataframe
    )

    total_quantity = safe_sum(
        dataframe,
        quantity_column,
    )

    if (
        returned_units is not None
        and total_quantity is not None
        and total_quantity > 0
    ):

        metrics[
            "return_rate"
        ] = round_value(
            (
                returned_units
                / total_quantity
            ) * 100
        )

    elif (
        metrics["total_returns"] is not None
        and total_sales is not None
        and total_sales > 0
        and return_value is not None
    ):

        metrics[
            "return_rate"
        ] = round_value(
            (
                return_value
                / total_sales
            ) * 100
        )

    # ------------------------------------------------------------------
    # Average return value
    # ------------------------------------------------------------------

    if (
        return_value is not None
        and metrics["total_returns"]
        and metrics["total_returns"] > 0
    ):

        metrics[
            "average_return_value"
        ] = round_value(
            return_value
            / metrics[
                "total_returns"
            ]
        )

    # ------------------------------------------------------------------
    # Average returned units
    # ------------------------------------------------------------------

    if (
        returned_units is not None
        and metrics["total_returns"]
        and metrics["total_returns"] > 0
    ):

        metrics[
            "average_return_units"
        ] = round_value(
            returned_units
            / metrics[
                "total_returns"
            ]
        )

    # ------------------------------------------------------------------
    # Returning customers
    # ------------------------------------------------------------------

    customer_column = get_column(
        dataframe,
        "Customer_ID",
    )

    if customer_column:

        customer_values = (
            dataframe[
                customer_column
            ]
            .dropna()
        )

        if not customer_values.empty:

            customer_counts = (
                customer_values
                .value_counts()
            )

            metrics[
                "returning_customers"
            ] = int(
                (
                    customer_counts > 1
                ).sum()
            )

            unique_customers = (
                customer_values
                .nunique()
            )

            if unique_customers > 0:

                metrics[
                    "return_customer_rate"
                ] = round_value(
                    (
                        metrics[
                            "returning_customers"
                        ]
                        / unique_customers
                    ) * 100
                )

    # ------------------------------------------------------------------
    # Top return reason
    # ------------------------------------------------------------------

    reasons = returns_by_reason(
        dataframe
    )

    if reasons:

        metrics[
            "top_return_reason"
        ] = reasons[0].get(
            "reason"
        )

        metrics[
            "top_return_reason_count"
        ] = reasons[0].get(
            "returns"
        )

    # ------------------------------------------------------------------
    # Top return product
    # ------------------------------------------------------------------

    products = returns_by_product(
        dataframe
    )

    if products:

        metrics[
            "top_return_product"
        ] = products[0].get(
            "product"
        )

        metrics[
            "top_return_product_count"
        ] = products[0].get(
            "returns"
        )

    # ------------------------------------------------------------------
    # Top return region
    # ------------------------------------------------------------------

    regions = returns_by_region(
        dataframe
    )

    if regions:

        metrics[
            "top_return_region"
        ] = regions[0].get(
            "region"
        )

        metrics[
            "top_return_region_count"
        ] = regions[0].get(
            "returns"
        )

    return metrics


# ============================================================================
# RETURN TREND
# ============================================================================

def returns_trend(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Return daily return count and return value.
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    date_column = get_return_date_column(
        dataframe
    )

    if not date_column:
        return []

    return_amount_column = (
        get_return_amount_column(
            dataframe
        )
    )

    return_id_column = (
        get_return_id_column(
            dataframe
        )
    )

    return_quantity_column = (
        get_return_quantity_column(
            dataframe
        )
    )

    if not (
        return_amount_column
        or return_id_column
        or return_quantity_column
    ):
        return []

    working = dataframe.copy()

    working[
        "_return_date"
    ] = pd.to_datetime(
        working[date_column],
        errors="coerce",
    )

    working = working.dropna(
        subset=[
            "_return_date"
        ]
    )

    if working.empty:
        return []

    grouped = working.groupby(
        working[
            "_return_date"
        ].dt.date
    )

    result = []

    for date_value, group in grouped:

        item = {
            "date": str(date_value),
            "returns": None,
            "returned_units": None,
            "return_value": None,
        }

        # Return count
        if return_id_column:

            ids = (
                group[
                    return_id_column
                ]
                .dropna()
            )

            if not ids.empty:

                item[
                    "returns"
                ] = int(
                    ids.nunique()
                )

        else:

            item[
                "returns"
            ] = int(
                len(group.index)
            )

        # Returned units
        if return_quantity_column:

            value = safe_sum(
                group,
                return_quantity_column,
            )

            item[
                "returned_units"
            ] = round_value(
                value
            )

        # Return value
        if return_amount_column:

            value = safe_sum(
                group,
                return_amount_column,
            )

            item[
                "return_value"
            ] = round_value(
                value
            )

        result.append(item)

    return result


# ============================================================================
# RETURNS BY REASON
# ============================================================================

def returns_by_reason(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Group returns by reason.
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    reason_column = get_reason_column(
        dataframe
    )

    if not reason_column:
        return []

    working = dataframe.copy()

    working[
        "_reason"
    ] = clean_text_series(
        working[
            reason_column
        ]
    )

    grouped = (
        working
        .groupby(
            "_reason"
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    total = int(
        grouped.sum()
    )

    result = []

    for reason, count in grouped.items():

        percentage = None

        if total > 0:

            percentage = (
                float(count)
                / total
            ) * 100

        result.append(
            {
                "reason": str(reason),
                "returns": int(count),
                "percentage": round_value(
                    percentage
                ),
            }
        )

    return result


# ============================================================================
# RETURNS BY PRODUCT
# ============================================================================

def returns_by_product(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Group returns by product.
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    product_column = get_product_column(
        dataframe
    )

    if not product_column:
        return []

    return_amount_column = (
        get_return_amount_column(
            dataframe
        )
    )

    return_quantity_column = (
        get_return_quantity_column(
            dataframe
        )
    )

    working = dataframe.copy()

    working[
        "_product"
    ] = clean_text_series(
        working[
            product_column
        ]
    )

    grouped = (
        working
        .groupby(
            "_product"
        )
    )

    result = []

    for product, group in grouped:

        returns = int(
            len(group.index)
        )

        return_value = safe_sum(
            group,
            return_amount_column,
        )

        returned_units = safe_sum(
            group,
            return_quantity_column,
        )

        result.append(
            {
                "product": str(product),
                "returns": returns,
                "returned_units": round_value(
                    returned_units
                ),
                "return_value": round_value(
                    return_value
                ),
            }
        )

    result.sort(
        key=lambda item: (
            item["returns"]
            if item["returns"] is not None
            else 0
        ),
        reverse=True,
    )

    return result


# ============================================================================
# RETURNS BY CATEGORY
# ============================================================================

def returns_by_category(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Group returns by product/category.
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    category_column = get_category_column(
        dataframe
    )

    if not category_column:
        return []

    return_amount_column = (
        get_return_amount_column(
            dataframe
        )
    )

    return_quantity_column = (
        get_return_quantity_column(
            dataframe
        )
    )

    working = dataframe.copy()

    working[
        "_category"
    ] = clean_text_series(
        working[
            category_column
        ]
    )

    grouped = (
        working
        .groupby(
            "_category"
        )
    )

    result = []

    for category, group in grouped:

        returns = int(
            len(group.index)
        )

        return_value = safe_sum(
            group,
            return_amount_column,
        )

        returned_units = safe_sum(
            group,
            return_quantity_column,
        )

        result.append(
            {
                "category": str(category),
                "returns": returns,
                "returned_units": round_value(
                    returned_units
                ),
                "return_value": round_value(
                    return_value
                ),
            }
        )

    result.sort(
        key=lambda item: (
            item["returns"]
            if item["returns"] is not None
            else 0
        ),
        reverse=True,
    )

    return result


# ============================================================================
# RETURNS BY REGION
# ============================================================================

def returns_by_region(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Group returns by region.
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    region_column = get_region_column(
        dataframe
    )

    if not region_column:
        return []

    return_amount_column = (
        get_return_amount_column(
            dataframe
        )
    )

    return_quantity_column = (
        get_return_quantity_column(
            dataframe
        )
    )

    working = dataframe.copy()

    working[
        "_region"
    ] = clean_text_series(
        working[
            region_column
        ]
    )

    grouped = (
        working
        .groupby(
            "_region"
        )
    )

    result = []

    for region, group in grouped:

        returns = int(
            len(group.index)
        )

        return_value = safe_sum(
            group,
            return_amount_column,
        )

        returned_units = safe_sum(
            group,
            return_quantity_column,
        )

        result.append(
            {
                "region": str(region),
                "returns": returns,
                "returned_units": round_value(
                    returned_units
                ),
                "return_value": round_value(
                    return_value
                ),
            }
        )

    result.sort(
        key=lambda item: (
            item["returns"]
            if item["returns"] is not None
            else 0
        ),
        reverse=True,
    )

    return result


# ============================================================================
# RETURN VALUE DISTRIBUTION
# ============================================================================

def return_value_distribution(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Group individual return values into useful bands.

    Bands:
        0–1K
        1K–5K
        5K–10K
        10K–50K
        50K+
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    return_amount_column = (
        get_return_amount_column(
            dataframe
        )
    )

    if not return_amount_column:
        return []

    values = get_numeric_series(
        dataframe,
        return_amount_column,
    )

    if values is None:
        return []

    values = values.dropna()

    if values.empty:
        return []

    bands = [
        (
            "0–1K",
            0,
            1_000,
        ),
        (
            "1K–5K",
            1_000,
            5_000,
        ),
        (
            "5K–10K",
            5_000,
            10_000,
        ),
        (
            "10K–50K",
            10_000,
            50_000,
        ),
        (
            "50K+",
            50_000,
            None,
        ),
    ]

    result = []

    for label, lower, upper in bands:

        if upper is None:

            mask = (
                values >= lower
            )

        else:

            mask = (
                (values >= lower)
                & (values < upper)
            )

        count = int(
            mask.sum()
        )

        if count > 0:

            total_value = float(
                values[
                    mask
                ].sum()
            )

            result.append(
                {
                    "band": label,
                    "returns": count,
                    "value": round_value(
                        total_value
                    ),
                }
            )

    return result


# ============================================================================
# RETURN STATUS ANALYSIS
# ============================================================================

def returns_by_status(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Group returns by status.
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    status_column = get_status_column(
        dataframe
    )

    if not status_column:
        return []

    working = dataframe.copy()

    working[
        "_status"
    ] = clean_text_series(
        working[
            status_column
        ]
    )

    grouped = (
        working
        .groupby(
            "_status"
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    total = int(
        grouped.sum()
    )

    result = []

    for status, count in grouped.items():

        percentage = None

        if total > 0:

            percentage = (
                float(count)
                / total
            ) * 100

        result.append(
            {
                "status": str(status),
                "returns": int(count),
                "percentage": round_value(
                    percentage
                ),
            }
        )

    return result


# ============================================================================
# RETURN RATE BY CATEGORY
# ============================================================================

def return_rate_by_category(
    dataframe: pd.DataFrame,
) -> List[Dict[str, Any]]:
    """
    Calculate category-level return rates when both sold and returned
    quantities are available.

    Falls back to return-count distribution when sold quantity is absent.
    """

    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    category_column = get_category_column(
        dataframe
    )

    if not category_column:
        return []

    return_quantity_column = (
        get_return_quantity_column(
            dataframe
        )
    )

    quantity_column = (
        get_quantity_column(
            dataframe
        )
    )

    working = dataframe.copy()

    working[
        "_category"
    ] = clean_text_series(
        working[
            category_column
        ]
    )

    grouped = (
        working
        .groupby(
            "_category"
        )
    )

    result = []

    for category, group in grouped:

        returned_units = safe_sum(
            group,
            return_quantity_column,
        )

        sold_units = safe_sum(
            group,
            quantity_column,
        )

        rate = None

        if (
            returned_units is not None
            and sold_units is not None
            and sold_units > 0
        ):

            rate = (
                returned_units
                / sold_units
            ) * 100

        returns = int(
            len(group.index)
        )

        result.append(
            {
                "category": str(category),
                "returns": returns,
                "returned_units": round_value(
                    returned_units
                ),
                "sold_units": round_value(
                    sold_units
                ),
                "return_rate": round_value(
                    rate
                ),
            }
        )

    result.sort(
        key=lambda item: (
            item["return_rate"]
            if item["return_rate"] is not None
            else item["returns"]
        ),
        reverse=True,
    )

    return result


# ============================================================================
# RETURN GROWTH
# ============================================================================

def calculate_returns_growth(
    dataframe: pd.DataFrame,
    current_from_date=None,
    current_to_date=None,
) -> Optional[float]:
    """
    Compare return count in the selected period with the immediately
    preceding period of equal duration.

    Returns None when a meaningful comparison cannot be calculated.
    """

    if (
        dataframe is None
        or dataframe.empty
        or current_from_date is None
        or current_to_date is None
    ):
        return None

    date_column = get_return_date_column(
        dataframe
    )

    if not date_column:
        return None

    dates = pd.to_datetime(
        dataframe[
            date_column
        ],
        errors="coerce",
    )

    working = pd.DataFrame(
        {
            "_date": dates,
        }
    ).dropna(
        subset=[
            "_date"
        ]
    )

    if working.empty:
        return None

    current_start = pd.to_datetime(
        current_from_date,
        errors="coerce",
    )

    current_end = pd.to_datetime(
        current_to_date,
        errors="coerce",
    )

    if (
        pd.isna(current_start)
        or pd.isna(current_end)
        or current_end < current_start
    ):
        return None

    period_length = (
        current_end
        - current_start
    ) + pd.Timedelta(
        days=1
    )

    previous_end = (
        current_start
        - pd.Timedelta(
            days=1
        )
    )

    previous_start = (
        previous_end
        - period_length
        + pd.Timedelta(
            days=1
        )
    )

    current_data = working[
        (
            working[
                "_date"
            ]
            >= current_start
        )
        & (
            working[
                "_date"
            ]
            <= current_end
        )
    ]

    previous_data = working[
        (
            working[
                "_date"
            ]
            >= previous_start
        )
        & (
            working[
                "_date"
            ]
            <= previous_end
        )
    ]

    if current_data.empty:
        return None

    if previous_data.empty:
        return None

    current_returns = int(
        len(current_data.index)
    )

    previous_returns = int(
        len(previous_data.index)
    )

    if previous_returns == 0:
        return None

    growth = (
        (
            current_returns
            - previous_returns
        )
        / previous_returns
    ) * 100

    return round_value(
        growth
    )


# ============================================================================
# SMART RETURN INSIGHTS
# ============================================================================

def generate_returns_insights(
    metrics: Dict[str, Any],
    reasons: Optional[
        List[Dict[str, Any]]
    ] = None,
    products: Optional[
        List[Dict[str, Any]]
    ] = None,
    categories: Optional[
        List[Dict[str, Any]]
    ] = None,
    regions: Optional[
        List[Dict[str, Any]]
    ] = None,
    statuses: Optional[
        List[Dict[str, Any]]
    ] = None,
    return_growth: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Generate rule-based Smart Return Insights.

    Insights are based only on available calculated metrics.
    """

    insights = []

    metrics = metrics or {}

    reasons = reasons or []
    products = products or []
    categories = categories or []
    regions = regions or []
    statuses = statuses or []

    # ------------------------------------------------------------------
    # Return growth
    # ------------------------------------------------------------------

    if return_growth is not None:

        if return_growth > 0:

            insights.append(
                {
                    "type": "warning",
                    "title": "Returns Increased",
                    "message": (
                        f"Return volume increased by "
                        f"{return_growth:.2f}% compared "
                        "with the previous comparable period."
                    ),
                }
            )

        elif return_growth < 0:

            insights.append(
                {
                    "type": "positive",
                    "title": "Returns Decreased",
                    "message": (
                        f"Return volume decreased by "
                        f"{abs(return_growth):.2f}% compared "
                        "with the previous comparable period."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "info",
                    "title": "Returns Stable",
                    "message": (
                        "Return volume remained unchanged "
                        "compared with the previous "
                        "comparable period."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Return rate
    # ------------------------------------------------------------------

    return_rate = metrics.get(
        "return_rate"
    )

    if return_rate is not None:

        if return_rate >= 20:

            insights.append(
                {
                    "type": "warning",
                    "title": "High Return Rate",
                    "message": (
                        f"The calculated return rate is "
                        f"{return_rate:.2f}%."
                    ),
                }
            )

        elif return_rate >= 10:

            insights.append(
                {
                    "type": "warning",
                    "title": "Elevated Return Rate",
                    "message": (
                        f"The calculated return rate is "
                        f"{return_rate:.2f}%."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "positive",
                    "title": "Return Rate",
                    "message": (
                        f"The calculated return rate is "
                        f"{return_rate:.2f}%."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Top return reason
    # ------------------------------------------------------------------

    if reasons:

        top_reason = reasons[0]

        reason = top_reason.get(
            "reason"
        )

        percentage = top_reason.get(
            "percentage"
        )

        if reason:

            if percentage is not None:

                message = (
                    f"{reason} is the most frequently "
                    f"recorded return reason, representing "
                    f"{percentage:.2f}% of returns."
                )

            else:

                message = (
                    f"{reason} is the most frequently "
                    "recorded return reason."
                )

            insights.append(
                {
                    "type": "info",
                    "title": "Leading Return Reason",
                    "message": message,
                }
            )

    # ------------------------------------------------------------------
    # Top product
    # ------------------------------------------------------------------

    if products:

        top_product = products[0]

        product = top_product.get(
            "product"
        )

        returns = top_product.get(
            "returns"
        )

        if (
            product
            and returns is not None
        ):

            insights.append(
                {
                    "type": "warning",
                    "title": "Highest Return Product",
                    "message": (
                        f"{product} has the highest recorded "
                        f"return count at {returns}."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Top category
    # ------------------------------------------------------------------

    if categories:

        top_category = categories[0]

        category = top_category.get(
            "category"
        )

        returns = top_category.get(
            "returns"
        )

        if (
            category
            and returns is not None
        ):

            insights.append(
                {
                    "type": "info",
                    "title": "Highest Return Category",
                    "message": (
                        f"{category} has the highest recorded "
                        f"return count at {returns}."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Top region
    # ------------------------------------------------------------------

    if regions:

        top_region = regions[0]

        region = top_region.get(
            "region"
        )

        returns = top_region.get(
            "returns"
        )

        if (
            region
            and returns is not None
        ):

            insights.append(
                {
                    "type": "info",
                    "title": "Highest Return Region",
                    "message": (
                        f"{region} has the highest recorded "
                        f"return count at {returns}."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Return value
    # ------------------------------------------------------------------

    return_value = metrics.get(
        "return_value"
    )

    if return_value is not None:

        insights.append(
            {
                "type": "info",
                "title": "Returned Value",
                "message": (
                    f"The recorded return value for the "
                    f"selected data is {return_value:,.2f}."
                ),
            }
        )

    # ------------------------------------------------------------------
    # Customer concentration
    # ------------------------------------------------------------------

    returning_customers = metrics.get(
        "returning_customers"
    )

    return_customer_rate = metrics.get(
        "return_customer_rate"
    )

    if (
        returning_customers is not None
        and return_customer_rate is not None
    ):

        if return_customer_rate >= 50:

            insights.append(
                {
                    "type": "warning",
                    "title": "Repeat Return Activity",
                    "message": (
                        f"{returning_customers} customers "
                        f"account for repeat return records, "
                        f"representing {return_customer_rate:.2f}% "
                        "of customers represented in return data."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Status concentration
    # ------------------------------------------------------------------

    if statuses:

        top_status = statuses[0]

        status = top_status.get(
            "status"
        )

        percentage = top_status.get(
            "percentage"
        )

        if (
            status
            and percentage is not None
            and percentage >= 70
        ):

            insights.append(
                {
                    "type": "info",
                    "title": "Return Status Concentration",
                    "message": (
                        f"{status} represents approximately "
                        f"{percentage:.2f}% of recorded returns."
                    ),
                }
            )

    # ------------------------------------------------------------------
    # Data availability
    # ------------------------------------------------------------------

    if metrics.get(
        "total_returns"
    ) is None:

        insights.append(
            {
                "type": "info",
                "title": "Return Data Unavailable",
                "message": (
                    "Return records could not be calculated "
                    "from the selected dataset."
                ),
            }
        )

    return insights


# ============================================================================
# BACKWARD-COMPATIBILITY ALIASES
# ============================================================================

return_trend = returns_trend
return_by_reason = returns_by_reason
return_by_product = returns_by_product
return_by_category = returns_by_category
return_by_region = returns_by_region
return_status_analysis = returns_by_status
return_value_bands = return_value_distribution
