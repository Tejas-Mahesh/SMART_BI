import pandas as pd
import numpy as np


# =========================================================
# REQUIRED COLUMNS
# =========================================================

CORE_REQUIRED_COLUMNS = [
    "Product_ID",
]


# =========================================================
# OPTIONAL COLUMNS
# =========================================================

OPTIONAL_COLUMNS = [
    "Product_Name",
    "Category",
    "Date",
    "Quantity",
    "Sales_Amount",
    "Unit_Price",
    "Cost",
    "Profit",
    "Region",
]


# =========================================================
# COLUMN ALIASES
# =========================================================

COLUMN_ALIASES = {

    "Product_ID": [
        "Product_ID",
        "Product Id",
        "ProductID",
        "Product ID",
        "Product_Code",
        "Product Code",
        "SKU",
        "SKU_ID",
    ],

    "Product_Name": [
        "Product_Name",
        "Product Name",
        "ProductName",
        "Product",
        "Item_Name",
        "Item Name",
    ],

    "Category": [
        "Category",
        "Product_Category",
        "Product Category",
        "ProductCategory",
        "Category_Name",
        "Category Name",
    ],

    "Date": [
        "Date",
        "Product_Date",
        "Product Date",
        "Order_Date",
        "Order Date",
        "Sales_Date",
        "Sales Date",
    ],

    "Quantity": [
        "Quantity",
        "Qty",
        "Units",
        "Units_Sold",
        "Units Sold",
        "Quantity_Sold",
        "Quantity Sold",
    ],

    "Sales_Amount": [
        "Sales_Amount",
        "Sales Amount",
        "Sales",
        "Revenue",
        "Revenue_Amount",
        "Revenue Amount",
        "Total_Sales",
        "Total Sales",
    ],

    "Unit_Price": [
        "Unit_Price",
        "Unit Price",
        "Price",
        "Selling_Price",
        "Selling Price",
    ],

    "Cost": [
        "Cost",
        "Product_Cost",
        "Product Cost",
        "Cost_Price",
        "Cost Price",
    ],

    "Profit": [
        "Profit",
        "Profit_Amount",
        "Profit Amount",
        "Gross_Profit",
        "Gross Profit",
    ],

    "Region": [
        "Region",
        "Region_Name",
        "Region Name",
        "Location",
    ],
}


# =========================================================
# COLUMN NORMALIZATION
# =========================================================

def normalize_column_name(column):
    """
    Normalize a dataframe column name.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


# =========================================================
# COLUMN RESOLUTION
# =========================================================

def resolve_columns(dataframe):
    """
    Resolve available dataframe columns into canonical
    Product Intelligence column names.
    """

    if dataframe is None:
        return {}

    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    resolved = {}

    for canonical_name, aliases in COLUMN_ALIASES.items():

        for alias in aliases:

            normalized_alias = (
                normalize_column_name(alias)
            )

            actual_column = (
                normalized_columns.get(
                    normalized_alias
                )
            )

            if actual_column:

                resolved[
                    canonical_name
                ] = actual_column

                break

    return resolved


# =========================================================
# PREPARE PRODUCT DATAFRAME
# =========================================================

def prepare_product_dataframe(dataframe):
    """
    Prepare Product dataframe using canonical
    column mappings.

    Returns:

        dataframe
        resolved_columns
        missing_required_columns
    """

    if dataframe is None:

        return (
            None,
            {},
            CORE_REQUIRED_COLUMNS.copy(),
        )

    dataframe = dataframe.copy()

    resolved_columns = resolve_columns(
        dataframe
    )

    missing_required_columns = [
        column
        for column in CORE_REQUIRED_COLUMNS
        if column not in resolved_columns
    ]

    rename_map = {
        actual_column: canonical_name
        for canonical_name, actual_column
        in resolved_columns.items()
    }

    dataframe = dataframe.rename(
        columns=rename_map
    )

    return (
        dataframe,
        resolved_columns,
        missing_required_columns,
    )


# =========================================================
# DATE PARSING
# =========================================================

def _parse_dates(series):
    """
    Parse Product dates consistently.

    Product datasets use DD-MM-YYYY style dates in
    the current project.

    dayfirst=True ensures values such as:

        05-01-2026
        30-08-2026
        05-09-2026

    are interpreted correctly.
    """

    return pd.to_datetime(
        series,
        errors="coerce",
        dayfirst=True,
    )


# =========================================================
# NUMERIC HELPERS
# =========================================================

def _numeric_series(dataframe, column):

    if dataframe is None:
        return pd.Series(dtype=float)

    if column not in dataframe.columns:
        return pd.Series(dtype=float)

    return pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )


def _safe_sum(dataframe, column):

    if column not in dataframe.columns:
        return None

    values = _numeric_series(
        dataframe,
        column,
    ).dropna()

    if values.empty:
        return None

    return float(values.sum())


def _safe_mean(dataframe, column):

    if column not in dataframe.columns:
        return None

    values = _numeric_series(
        dataframe,
        column,
    ).dropna()

    if values.empty:
        return None

    return float(values.mean())


def _safe_round(value, digits=2):

    if value is None:
        return None

    if isinstance(
        value,
        (float, np.floating),
    ):

        if not np.isfinite(value):
            return None

    return round(
        float(value),
        digits,
    )


# =========================================================
# PRODUCT KPI METRICS
# =========================================================

def calculate_product_metrics(dataframe):
    """
    Calculate Product Intelligence KPIs.
    """

    if dataframe is None or dataframe.empty:

        return {
            "total_products": 0,
            "active_products": 0,
            "total_sales": None,
            "units_sold": None,
            "average_product_sales": None,
            "average_unit_price": None,
            "total_profit": None,
            "profit_margin": None,
            "top_product": None,
            "top_product_sales": None,
        }

    metrics = {
        "total_products": 0,
        "active_products": 0,
        "total_sales": None,
        "units_sold": None,
        "average_product_sales": None,
        "average_unit_price": None,
        "total_profit": None,
        "profit_margin": None,
        "top_product": None,
        "top_product_sales": None,
    }

    # -----------------------------------------------------
    # TOTAL PRODUCTS
    # -----------------------------------------------------

    if "Product_ID" in dataframe.columns:

        product_ids = (
            dataframe["Product_ID"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        product_ids = product_ids[
            product_ids != ""
        ]

        metrics["total_products"] = int(
            product_ids.nunique()
        )

    # -----------------------------------------------------
    # ACTIVE PRODUCTS
    # -----------------------------------------------------

    if "Product_ID" in dataframe.columns:

        active = dataframe[
            dataframe["Product_ID"].notna()
        ]

        metrics["active_products"] = int(
            active["Product_ID"]
            .astype(str)
            .str.strip()
            .replace("", np.nan)
            .dropna()
            .nunique()
        )

    # -----------------------------------------------------
    # TOTAL SALES
    # -----------------------------------------------------

    total_sales = _safe_sum(
        dataframe,
        "Sales_Amount",
    )

    metrics["total_sales"] = _safe_round(
        total_sales
    )

    # -----------------------------------------------------
    # UNITS SOLD
    # -----------------------------------------------------

    units_sold = _safe_sum(
        dataframe,
        "Quantity",
    )

    metrics["units_sold"] = _safe_round(
        units_sold
    )

    # -----------------------------------------------------
    # AVERAGE UNIT PRICE
    # -----------------------------------------------------

    unit_price = _safe_mean(
        dataframe,
        "Unit_Price",
    )

    metrics["average_unit_price"] = _safe_round(
        unit_price
    )

    # -----------------------------------------------------
    # TOP PRODUCT
    # -----------------------------------------------------

    if (
        "Sales_Amount" in dataframe.columns
        and "Product_ID" in dataframe.columns
    ):

        sales_data = dataframe.copy()

        sales_data["Sales_Amount"] = pd.to_numeric(
            sales_data["Sales_Amount"],
            errors="coerce",
        )

        sales_data = sales_data.dropna(
            subset=[
                "Product_ID",
                "Sales_Amount",
            ]
        )

        if not sales_data.empty:

            product_sales = (
                sales_data
                .groupby("Product_ID")[
                    "Sales_Amount"
                ]
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            if not product_sales.empty:

                top_product_id = (
                    product_sales.index[0]
                )

                metrics["top_product_sales"] = (
                    _safe_round(
                        product_sales.iloc[0]
                    )
                )

                if (
                    "Product_Name"
                    in sales_data.columns
                ):

                    matching_products = (
                        sales_data[
                            sales_data[
                                "Product_ID"
                            ]
                            == top_product_id
                        ]["Product_Name"]
                        .dropna()
                        .astype(str)
                    )

                    if not matching_products.empty:

                        metrics[
                            "top_product"
                        ] = matching_products.iloc[0]

                if metrics["top_product"] is None:

                    metrics["top_product"] = str(
                        top_product_id
                    )

    # -----------------------------------------------------
    # AVERAGE PRODUCT SALES
    # -----------------------------------------------------

    if (
        total_sales is not None
        and metrics["total_products"] > 0
    ):

        metrics[
            "average_product_sales"
        ] = _safe_round(
            total_sales
            / metrics["total_products"]
        )

    # -----------------------------------------------------
    # TOTAL PROFIT
    # -----------------------------------------------------

    total_profit = _safe_sum(
        dataframe,
        "Profit",
    )

    metrics["total_profit"] = _safe_round(
        total_profit
    )

    # -----------------------------------------------------
    # PROFIT MARGIN
    # -----------------------------------------------------

    if (
        total_profit is not None
        and total_sales is not None
        and total_sales != 0
    ):

        metrics["profit_margin"] = _safe_round(
            (
                total_profit
                / total_sales
            ) * 100
        )

    return metrics


# =========================================================
# PRODUCT SALES TREND
# =========================================================

def product_sales_trend(dataframe):
    """
    Return daily Product sales trend.

    Dates are parsed using dayfirst=True.
    """

    if dataframe is None or dataframe.empty:
        return []

    required = [
        "Date",
        "Sales_Amount",
    ]

    if not all(
        column in dataframe.columns
        for column in required
    ):
        return []

    trend = dataframe.copy()

    # -----------------------------------------------------
    # IMPORTANT:
    # Parse DD-MM-YYYY correctly.
    # -----------------------------------------------------

    trend["Date"] = _parse_dates(
        trend["Date"]
    )

    trend["Sales_Amount"] = pd.to_numeric(
        trend["Sales_Amount"],
        errors="coerce",
    )

    trend = trend.dropna(
        subset=[
            "Date",
            "Sales_Amount",
        ]
    )

    if trend.empty:
        return []

    trend["Date"] = (
        trend["Date"]
        .dt.strftime("%Y-%m-%d")
    )

    result = (
        trend
        .groupby(
            "Date",
            as_index=False,
        )["Sales_Amount"]
        .sum()
        .sort_values("Date")
    )

    return [
        {
            "date": row["Date"],
            "sales": _safe_round(
                row["Sales_Amount"]
            ),
        }
        for _, row in result.iterrows()
    ]


# =========================================================
# SALES BY PRODUCT
# =========================================================

def sales_by_product(
    dataframe,
    limit=10,
):
    """
    Return products ranked by sales.
    """

    if dataframe is None or dataframe.empty:
        return []

    if (
        "Product_ID" not in dataframe.columns
        or "Sales_Amount"
        not in dataframe.columns
    ):
        return []

    data = dataframe.copy()

    data["Sales_Amount"] = pd.to_numeric(
        data["Sales_Amount"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "Product_ID",
            "Sales_Amount",
        ]
    )

    if data.empty:
        return []

    grouped = (
        data
        .groupby(
            "Product_ID",
            as_index=False,
        )["Sales_Amount"]
        .sum()
        .sort_values(
            "Sales_Amount",
            ascending=False,
        )
        .head(limit)
    )

    result = []

    for _, row in grouped.iterrows():

        product_id = row[
            "Product_ID"
        ]

        product_name = str(
            product_id
        )

        if "Product_Name" in data.columns:

            names = (
                data[
                    data["Product_ID"]
                    == product_id
                ]["Product_Name"]
                .dropna()
                .astype(str)
            )

            if not names.empty:
                product_name = names.iloc[0]

        result.append({
            "product_id": str(
                product_id
            ),
            "product_name": product_name,
            "sales": _safe_round(
                row["Sales_Amount"]
            ),
        })

    return result


# =========================================================
# UNITS BY PRODUCT
# =========================================================

def units_by_product(
    dataframe,
    limit=10,
):
    """
    Return products ranked by units sold.
    """

    if dataframe is None or dataframe.empty:
        return []

    if (
        "Product_ID" not in dataframe.columns
        or "Quantity"
        not in dataframe.columns
    ):
        return []

    data = dataframe.copy()

    data["Quantity"] = pd.to_numeric(
        data["Quantity"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "Product_ID",
            "Quantity",
        ]
    )

    if data.empty:
        return []

    grouped = (
        data
        .groupby(
            "Product_ID",
            as_index=False,
        )["Quantity"]
        .sum()
        .sort_values(
            "Quantity",
            ascending=False,
        )
        .head(limit)
    )

    result = []

    for _, row in grouped.iterrows():

        product_id = row[
            "Product_ID"
        ]

        product_name = str(
            product_id
        )

        if "Product_Name" in data.columns:

            names = (
                data[
                    data["Product_ID"]
                    == product_id
                ]["Product_Name"]
                .dropna()
                .astype(str)
            )

            if not names.empty:
                product_name = names.iloc[0]

        result.append({
            "product_id": str(
                product_id
            ),
            "product_name": product_name,
            "units": _safe_round(
                row["Quantity"]
            ),
        })

    return result


# =========================================================
# SALES BY CATEGORY
# =========================================================

def sales_by_category(dataframe):
    """
    Return total sales by product category.
    """

    if dataframe is None or dataframe.empty:
        return []

    if (
        "Category" not in dataframe.columns
        or "Sales_Amount"
        not in dataframe.columns
    ):
        return []

    data = dataframe.copy()

    data["Sales_Amount"] = pd.to_numeric(
        data["Sales_Amount"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "Category",
            "Sales_Amount",
        ]
    )

    if data.empty:
        return []

    data["Category"] = (
        data["Category"]
        .astype(str)
        .str.strip()
    )

    data = data[
        data["Category"] != ""
    ]

    grouped = (
        data
        .groupby(
            "Category",
            as_index=False,
        )["Sales_Amount"]
        .sum()
        .sort_values(
            "Sales_Amount",
            ascending=False,
        )
    )

    return [
        {
            "category": row[
                "Category"
            ],
            "sales": _safe_round(
                row["Sales_Amount"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


# =========================================================
# PROFIT BY PRODUCT
# =========================================================

def profit_by_product(
    dataframe,
    limit=10,
):
    """
    Return products ranked by profit.
    """

    if dataframe is None or dataframe.empty:
        return []

    if (
        "Product_ID" not in dataframe.columns
        or "Profit"
        not in dataframe.columns
    ):
        return []

    data = dataframe.copy()

    data["Profit"] = pd.to_numeric(
        data["Profit"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "Product_ID",
            "Profit",
        ]
    )

    if data.empty:
        return []

    grouped = (
        data
        .groupby(
            "Product_ID",
            as_index=False,
        )["Profit"]
        .sum()
        .sort_values(
            "Profit",
            ascending=False,
        )
        .head(limit)
    )

    result = []

    for _, row in grouped.iterrows():

        product_id = row[
            "Product_ID"
        ]

        product_name = str(
            product_id
        )

        if "Product_Name" in data.columns:

            names = (
                data[
                    data["Product_ID"]
                    == product_id
                ]["Product_Name"]
                .dropna()
                .astype(str)
            )

            if not names.empty:
                product_name = names.iloc[0]

        result.append({
            "product_id": str(
                product_id
            ),
            "product_name": product_name,
            "profit": _safe_round(
                row["Profit"]
            ),
        })

    return result


# =========================================================
# PRODUCT QUANTITY DISTRIBUTION
# =========================================================

def product_quantity_distribution(dataframe):
    """
    Group products into quantity-performance bands.
    """

    if dataframe is None or dataframe.empty:
        return []

    if (
        "Product_ID" not in dataframe.columns
        or "Quantity"
        not in dataframe.columns
    ):
        return []

    data = dataframe.copy()

    data["Quantity"] = pd.to_numeric(
        data["Quantity"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "Product_ID",
            "Quantity",
        ]
    )

    if data.empty:
        return []

    product_quantity = (
        data
        .groupby("Product_ID")[
            "Quantity"
        ]
        .sum()
    )

    bands = [
        ("0", 0, 0),
        ("1–10", 1, 10),
        ("11–50", 11, 50),
        ("51–100", 51, 100),
        ("101–500", 101, 500),
        ("500+", 501, float("inf")),
    ]

    result = []

    for label, minimum, maximum in bands:

        if label == "0":

            count = int(
                (
                    product_quantity == 0
                ).sum()
            )

        else:

            count = int(
                (
                    (
                        product_quantity
                        >= minimum
                    )
                    & (
                        product_quantity
                        <= maximum
                    )
                ).sum()
            )

        result.append({
            "band": label,
            "products": count,
        })

    return result


# =========================================================
# PRODUCT SALES GROWTH
# =========================================================

def calculate_product_growth(
    dataframe,
    current_from_date=None,
    current_to_date=None,
):
    """
    Compare Product sales in the selected period
    with the immediately preceding period of the
    same length.

    Example:

        Current:
            08-08-2026 → 05-09-2026

        Previous:
            10-07-2026 → 07-08-2026

    Returns None when a reliable comparison
    cannot be calculated.
    """

    # -----------------------------------------------------
    # BASIC VALIDATION
    # -----------------------------------------------------

    if (
        dataframe is None
        or dataframe.empty
        or "Date" not in dataframe.columns
        or "Sales_Amount"
        not in dataframe.columns
    ):
        return None

    if (
        current_from_date is None
        or current_to_date is None
    ):
        return None

    # -----------------------------------------------------
    # PARSE DATASET DATES
    # -----------------------------------------------------

    dates = _parse_dates(
        dataframe["Date"]
    )

    sales = pd.to_numeric(
        dataframe["Sales_Amount"],
        errors="coerce",
    )

    data = pd.DataFrame({
        "Date": dates,
        "Sales_Amount": sales,
    })

    data = data.dropna(
        subset=[
            "Date",
            "Sales_Amount",
        ]
    )

    if data.empty:
        return None

    # -----------------------------------------------------
    # PARSE CURRENT PERIOD
    # -----------------------------------------------------

    current_from = pd.to_datetime(
        current_from_date,
        errors="coerce",
        dayfirst=True,
    )

    current_to = pd.to_datetime(
        current_to_date,
        errors="coerce",
        dayfirst=True,
    )

    if (
        pd.isna(current_from)
        or pd.isna(current_to)
    ):
        return None

    # Normalize boundaries.
    current_from = (
        current_from.normalize()
    )

    current_to = (
        current_to.normalize()
        + pd.Timedelta(days=1)
        - pd.Timedelta(microseconds=1)
    )

    if current_to < current_from:
        return None

    # -----------------------------------------------------
    # CALCULATE PERIOD LENGTH
    # -----------------------------------------------------

    period_length = (
        current_to.normalize()
        - current_from
    ).days + 1

    if period_length <= 0:
        return None

    # -----------------------------------------------------
    # PREVIOUS PERIOD
    # -----------------------------------------------------

    previous_to = (
        current_from
        - pd.Timedelta(days=1)
    )

    previous_from = (
        previous_to
        - pd.Timedelta(
            days=period_length - 1
        )
    )

    # -----------------------------------------------------
    # CURRENT PERIOD DATA
    # -----------------------------------------------------

    current_data = data[
        (
            data["Date"]
            >= current_from
        )
        & (
            data["Date"]
            <= current_to
        )
    ]

    # -----------------------------------------------------
    # PREVIOUS PERIOD DATA
    # -----------------------------------------------------

    previous_data = data[
        (
            data["Date"]
            >= previous_from
        )
        & (
            data["Date"]
            <= previous_to
        )
    ]

    # -----------------------------------------------------
    # BOTH PERIODS MUST HAVE DATA
    # -----------------------------------------------------

    if current_data.empty:
        return None

    if previous_data.empty:
        return None

    # -----------------------------------------------------
    # SALES TOTALS
    # -----------------------------------------------------

    current_sales = float(
        current_data[
            "Sales_Amount"
        ].sum()
    )

    previous_sales = float(
        previous_data[
            "Sales_Amount"
        ].sum()
    )

    # -----------------------------------------------------
    # PREVIOUS SALES MUST NOT BE ZERO
    # -----------------------------------------------------

    if previous_sales == 0:
        return None

    # -----------------------------------------------------
    # GROWTH %
    # -----------------------------------------------------

    growth = (
        (
            current_sales
            - previous_sales
        )
        / previous_sales
    ) * 100

    if not np.isfinite(growth):
        return None

    return _safe_round(
        growth
    )


# =========================================================
# SMART PRODUCT INSIGHTS
# =========================================================

def generate_product_insights(
    metrics,
    sales_products=None,
    category_sales=None,
    profit_products=None,
    growth=None,
):
    """
    Generate rule-based Smart Product Insights.

    Only available metrics are used.
    """

    insights = []

    if not metrics:
        return insights

    # -----------------------------------------------------
    # TOP PRODUCT
    # -----------------------------------------------------

    if (
        metrics.get("top_product")
        and metrics.get(
            "top_product_sales"
        ) is not None
    ):

        insights.append({
            "type": "top_product",
            "title": "Top Performing Product",
            "message": (
                f"{metrics['top_product']} "
                "generated "
                f"{metrics['top_product_sales']:,.2f} "
                "in sales during the selected period."
            ),
        })

    # -----------------------------------------------------
    # PRODUCT SALES GROWTH
    # -----------------------------------------------------

    if growth is not None:

        if growth > 0:

            insights.append({
                "type": "growth",
                "title": "Product Sales Growth",
                "message": (
                    "Product sales increased by "
                    f"{growth:.2f}% compared with "
                    "the previous comparable period."
                ),
            })

        elif growth < 0:

            insights.append({
                "type": "decline",
                "title": "Product Sales Decline",
                "message": (
                    "Product sales decreased by "
                    f"{abs(growth):.2f}% compared with "
                    "the previous comparable period."
                ),
            })

        else:

            insights.append({
                "type": "growth",
                "title": "Product Sales Stable",
                "message": (
                    "Product sales remained unchanged "
                    "compared with the previous "
                    "comparable period."
                ),
            })

    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if (
        category_sales
        and len(category_sales) >= 2
    ):

        top_category = (
            category_sales[0]
        )

        insights.append({
            "type": "category",
            "title": "Leading Category",
            "message": (
                f"{top_category['category']} "
                "is the highest-sales category "
                "with "
                f"{top_category['sales']:,.2f} "
                "in sales."
            ),
        })

    # -----------------------------------------------------
    # PROFIT LEADER
    # -----------------------------------------------------

    if (
        profit_products
        and len(profit_products) > 0
    ):

        top_profit_product = (
            profit_products[0]
        )

        insights.append({
            "type": "profit",
            "title": "Profit Leader",
            "message": (
                f"{top_profit_product['product_name']} "
                "has the highest recorded product "
                "profit at "
                f"{top_profit_product['profit']:,.2f}."
            ),
        })

    # -----------------------------------------------------
    # PROFIT MARGIN
    # -----------------------------------------------------

    if (
        metrics.get("profit_margin")
        is not None
    ):

        insights.append({
            "type": "margin",
            "title": "Product Profit Margin",
            "message": (
                "The overall product profit margin "
                "is "
                f"{metrics['profit_margin']:.2f}% "
                "for the selected data."
            ),
        })

    return insights