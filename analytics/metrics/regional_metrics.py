# analytics/metrics/regional_metrics.py

import pandas as pd


# ============================================================
# REQUIRED COLUMNS
# ============================================================

CORE_REQUIRED_COLUMNS = [
    "Region",
]


# ============================================================
# OPTIONAL COLUMNS
# ============================================================

OPTIONAL_COLUMNS = [
    "Date",
    "Order_Date",
    "Order_ID",
    "Customer_ID",
    "Product_ID",
    "Product_Name",
    "Category",
    "Quantity",
    "Units",
    "Sales_Amount",
    "Sales",
    "Revenue",
    "Unit_Price",
    "Discount",
    "Profit",
    "Profit_Amount",
    "Cost",
    "Order_Status",
    "Sales_Channel",
    "City",
    "State",
    "Country",
]


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {
    "Region": [
        "Region",
        "Region_Name",
        "Regional_Name",
        "Area",
        "Territory",
        "Zone",
    ],

    "Date": [
        "Date",
        "Order_Date",
        "OrderDate",
        "Transaction_Date",
        "TransactionDate",
        "Sales_Date",
    ],

    "Order_ID": [
        "Order_ID",
        "OrderID",
        "Order_Number",
        "OrderNumber",
        "Transaction_ID",
        "TransactionID",
    ],

    "Customer_ID": [
        "Customer_ID",
        "CustomerID",
        "Customer_Number",
        "CustomerNumber",
    ],

    "Product_ID": [
        "Product_ID",
        "ProductID",
        "Product_Number",
        "ProductNumber",
    ],

    "Product_Name": [
        "Product_Name",
        "ProductName",
        "Product",
        "Item_Name",
        "ItemName",
    ],

    "Category": [
        "Category",
        "Product_Category",
        "ProductCategory",
        "Category_Name",
    ],

    "Quantity": [
        "Quantity",
        "Qty",
        "Units",
        "Units_Sold",
        "Unit_Sold",
        "Quantity_Sold",
    ],

    "Sales_Amount": [
        "Sales_Amount",
        "SalesAmount",
        "Sales",
        "Revenue",
        "Total_Sales",
        "TotalSales",
        "Order_Value",
        "OrderValue",
        "Amount",
    ],

    "Unit_Price": [
        "Unit_Price",
        "UnitPrice",
        "Price",
        "Selling_Price",
        "SellingPrice",
    ],

    "Discount": [
        "Discount",
        "Discount_Amount",
        "DiscountAmount",
        "Discount_Percentage",
        "DiscountPercentage",
    ],

    "Profit": [
        "Profit",
        "Profit_Amount",
        "ProfitAmount",
        "Net_Profit",
        "NetProfit",
    ],

    "Cost": [
        "Cost",
        "Total_Cost",
        "TotalCost",
        "Cost_Amount",
        "CostAmount",
    ],

    "Order_Status": [
        "Order_Status",
        "OrderStatus",
        "Status",
    ],

    "Sales_Channel": [
        "Sales_Channel",
        "SalesChannel",
        "Channel",
    ],

    "City": [
        "City",
        "City_Name",
        "CityName",
    ],

    "State": [
        "State",
        "State_Name",
        "StateName",
    ],

    "Country": [
        "Country",
        "Country_Name",
        "CountryName",
    ],
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_column_name(column):
    """
    Normalize a column name for comparison.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def resolve_columns(dataframe):
    """
    Resolve canonical Regional Intelligence column names
    against the actual dataframe columns.

    Returns:
        dict
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

            normalized_alias = normalize_column_name(
                alias
            )

            actual_column = normalized_columns.get(
                normalized_alias
            )

            if actual_column is not None:
                resolved[canonical_name] = actual_column
                break

    return resolved


def prepare_regional_dataframe(dataframe):
    """
    Prepare a Regional dataframe and validate required columns.

    Returns:
        dataframe,
        resolved_columns,
        missing_required_columns
    """

    if dataframe is None:
        return (
            pd.DataFrame(),
            {},
            CORE_REQUIRED_COLUMNS.copy(),
        )

    prepared_dataframe = dataframe.copy()

    resolved_columns = resolve_columns(
        prepared_dataframe
    )

    missing_required_columns = [
        column
        for column in CORE_REQUIRED_COLUMNS
        if column not in resolved_columns
    ]

    return (
        prepared_dataframe,
        resolved_columns,
        missing_required_columns,
    )


def get_numeric_series(dataframe, column):
    """
    Return a numeric pandas Series.

    Invalid values are converted to NaN.
    """

    if (
        dataframe is None
        or column is None
        or column not in dataframe.columns
    ):
        return None

    return pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )


def get_sales_column(resolved_columns):
    """
    Return the canonical sales column if available.
    """

    return resolved_columns.get(
        "Sales_Amount"
    )


def get_profit_column(resolved_columns):
    """
    Return the canonical profit column if available.
    """

    return resolved_columns.get(
        "Profit"
    )


def get_quantity_column(resolved_columns):
    """
    Return the canonical quantity column if available.
    """

    return resolved_columns.get(
        "Quantity"
    )


def clean_region_values(dataframe, region_column):
    """
    Return a cleaned region Series.

    Blank or missing regions become 'Unknown'.
    """

    if (
        dataframe is None
        or region_column is None
        or region_column not in dataframe.columns
    ):
        return None

    regions = (
        dataframe[region_column]
        .astype("string")
        .str.strip()
    )

    regions = regions.fillna("Unknown")

    regions = regions.replace(
        {
            "": "Unknown",
            "nan": "Unknown",
            "None": "Unknown",
            "<NA>": "Unknown",
        }
    )

    return regions


# ============================================================
# CORE REGIONAL METRICS
# ============================================================

def calculate_regional_metrics(dataframe):
    """
    Calculate the main Regional Intelligence KPIs.

    Supported metrics are calculated only when the required
    source columns are available.

    Returns:
        dict
    """

    if dataframe is None or dataframe.empty:
        return {
            "total_regions": 0,
            "total_sales": None,
            "total_orders": None,
            "units_sold": None,
            "average_order_value": None,
            "average_sales_per_region": None,
            "total_profit": None,
            "profit_margin": None,
            "top_region": None,
            "top_region_sales": None,
            "regional_growth": None,
        }

    resolved_columns = resolve_columns(
        dataframe
    )

    region_column = resolved_columns.get(
        "Region"
    )

    if not region_column:
        return {
            "total_regions": 0,
            "total_sales": None,
            "total_orders": None,
            "units_sold": None,
            "average_order_value": None,
            "average_sales_per_region": None,
            "total_profit": None,
            "profit_margin": None,
            "top_region": None,
            "top_region_sales": None,
            "regional_growth": None,
        }

    regions = clean_region_values(
        dataframe,
        region_column,
    )

    total_regions = (
        regions.nunique()
        if regions is not None
        else 0
    )

    sales_column = get_sales_column(
        resolved_columns
    )

    quantity_column = get_quantity_column(
        resolved_columns
    )

    profit_column = get_profit_column(
        resolved_columns
    )

    order_column = resolved_columns.get(
        "Order_ID"
    )

    total_sales = None
    units_sold = None
    total_profit = None
    total_orders = None
    average_order_value = None
    average_sales_per_region = None
    profit_margin = None
    top_region = None
    top_region_sales = None

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    if sales_column:

        sales = get_numeric_series(
            dataframe,
            sales_column,
        )

        if sales is not None:

            valid_sales = sales.dropna()

            if not valid_sales.empty:

                total_sales = float(
                    valid_sales.sum()
                )

                average_sales_per_region = (
                    float(
                        total_sales / total_regions
                    )
                    if total_regions > 0
                    else None
                )

                region_sales = (
                    pd.DataFrame(
                        {
                            "Region": regions,
                            "Sales": sales,
                        }
                    )
                    .dropna(subset=["Sales"])
                    .groupby(
                        "Region",
                        dropna=False,
                    )["Sales"]
                    .sum()
                    .sort_values(
                        ascending=False
                    )
                )

                if not region_sales.empty:

                    top_region = str(
                        region_sales.index[0]
                    )

                    top_region_sales = float(
                        region_sales.iloc[0]
                    )

    # --------------------------------------------------------
    # ORDERS
    # --------------------------------------------------------

    if order_column:

        order_values = dataframe[
            order_column
        ].dropna()

        if not order_values.empty:

            total_orders = int(
                order_values.nunique()
            )

            if (
                total_orders > 0
                and total_sales is not None
            ):
                average_order_value = float(
                    total_sales / total_orders
                )

    elif total_sales is not None:

        # If no Order_ID exists, each valid sales
        # record can be treated as a transaction row.
        valid_sales_count = (
            get_numeric_series(
                dataframe,
                sales_column,
            )
            .notna()
            .sum()
        )

        if valid_sales_count > 0:

            total_orders = int(
                valid_sales_count
            )

            average_order_value = float(
                total_sales / total_orders
            )

    # --------------------------------------------------------
    # UNITS
    # --------------------------------------------------------

    if quantity_column:

        quantity = get_numeric_series(
            dataframe,
            quantity_column,
        )

        if quantity is not None:

            valid_quantity = (
                quantity.dropna()
            )

            if not valid_quantity.empty:

                units_sold = float(
                    valid_quantity.sum()
                )

    # --------------------------------------------------------
    # PROFIT
    # --------------------------------------------------------

    if profit_column:

        profit = get_numeric_series(
            dataframe,
            profit_column,
        )

        if profit is not None:

            valid_profit = profit.dropna()

            if not valid_profit.empty:

                total_profit = float(
                    valid_profit.sum()
                )

                if (
                    total_sales is not None
                    and total_sales != 0
                ):
                    profit_margin = float(
                        (
                            total_profit
                            / total_sales
                        )
                        * 100
                    )

    return {
        "total_regions": int(
            total_regions
        ),

        "total_sales": total_sales,

        "total_orders": total_orders,

        "units_sold": units_sold,

        "average_order_value": (
            average_order_value
        ),

        "average_sales_per_region": (
            average_sales_per_region
        ),

        "total_profit": total_profit,

        "profit_margin": profit_margin,

        "top_region": top_region,

        "top_region_sales": top_region_sales,

        "regional_growth": None,
    }


# ============================================================
# REGIONAL SALES TREND
# ============================================================

def regional_sales_trend(dataframe):
    """
    Return sales aggregated by date.

    Output format:

    [
        {
            "date": "2026-08-01",
            "sales": 10000
        }
    ]
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    date_column = resolved_columns.get(
        "Date"
    )

    sales_column = get_sales_column(
        resolved_columns
    )

    if not date_column or not sales_column:
        return []

    working_dataframe = dataframe[
        [date_column, sales_column]
    ].copy()

    working_dataframe["Date"] = pd.to_datetime(
        working_dataframe[date_column],
        errors="coerce",
        dayfirst=True,
    )

    working_dataframe["Sales"] = pd.to_numeric(
        working_dataframe[sales_column],
        errors="coerce",
    )

    working_dataframe = (
        working_dataframe
        .dropna(subset=["Date", "Sales"])
    )

    if working_dataframe.empty:
        return []

    trend = (
        working_dataframe
        .groupby(
            working_dataframe["Date"].dt.date
        )["Sales"]
        .sum()
        .reset_index()
    )

    trend.columns = [
        "date",
        "sales",
    ]

    trend = trend.sort_values(
        "date"
    )

    return [
        {
            "date": str(row["date"]),
            "sales": float(row["sales"]),
        }
        for _, row in trend.iterrows()
    ]


# ============================================================
# SALES BY REGION
# ============================================================

def sales_by_region(
    dataframe,
    limit=None,
):
    """
    Return total sales by region.

    Output format:

    [
        {
            "region": "North",
            "sales": 50000
        }
    ]
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    region_column = resolved_columns.get(
        "Region"
    )

    sales_column = get_sales_column(
        resolved_columns
    )

    if not region_column or not sales_column:
        return []

    regions = clean_region_values(
        dataframe,
        region_column,
    )

    sales = get_numeric_series(
        dataframe,
        sales_column,
    )

    if regions is None or sales is None:
        return []

    working_dataframe = pd.DataFrame(
        {
            "Region": regions,
            "Sales": sales,
        }
    )

    working_dataframe = (
        working_dataframe
        .dropna(subset=["Sales"])
    )

    if working_dataframe.empty:
        return []

    grouped = (
        working_dataframe
        .groupby(
            "Region",
            dropna=False,
        )["Sales"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    if limit:
        grouped = grouped.head(
            limit
        )

    return [
        {
            "region": str(region),
            "sales": float(sales_value),
        }
        for region, sales_value
        in grouped.items()
    ]


# ============================================================
# UNITS BY REGION
# ============================================================

def units_by_region(
    dataframe,
    limit=None,
):
    """
    Return total units sold by region.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    region_column = resolved_columns.get(
        "Region"
    )

    quantity_column = get_quantity_column(
        resolved_columns
    )

    if not region_column or not quantity_column:
        return []

    regions = clean_region_values(
        dataframe,
        region_column,
    )

    quantity = get_numeric_series(
        dataframe,
        quantity_column,
    )

    if regions is None or quantity is None:
        return []

    working_dataframe = pd.DataFrame(
        {
            "Region": regions,
            "Units": quantity,
        }
    )

    working_dataframe = (
        working_dataframe
        .dropna(subset=["Units"])
    )

    if working_dataframe.empty:
        return []

    grouped = (
        working_dataframe
        .groupby(
            "Region",
            dropna=False,
        )["Units"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    if limit:
        grouped = grouped.head(
            limit
        )

    return [
        {
            "region": str(region),
            "units": float(units),
        }
        for region, units
        in grouped.items()
    ]


# ============================================================
# PROFIT BY REGION
# ============================================================

def profit_by_region(
    dataframe,
    limit=None,
):
    """
    Return total profit by region.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    region_column = resolved_columns.get(
        "Region"
    )

    profit_column = get_profit_column(
        resolved_columns
    )

    if not region_column or not profit_column:
        return []

    regions = clean_region_values(
        dataframe,
        region_column,
    )

    profit = get_numeric_series(
        dataframe,
        profit_column,
    )

    if regions is None or profit is None:
        return []

    working_dataframe = pd.DataFrame(
        {
            "Region": regions,
            "Profit": profit,
        }
    )

    working_dataframe = (
        working_dataframe
        .dropna(subset=["Profit"])
    )

    if working_dataframe.empty:
        return []

    grouped = (
        working_dataframe
        .groupby(
            "Region",
            dropna=False,
        )["Profit"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    if limit:
        grouped = grouped.head(
            limit
        )

    return [
        {
            "region": str(region),
            "profit": float(profit_value),
        }
        for region, profit_value
        in grouped.items()
    ]


# ============================================================
# REGIONAL SALES CONTRIBUTION
# ============================================================

def regional_sales_contribution(dataframe):
    """
    Calculate each region's percentage contribution
    to total sales.

    Output:

    [
        {
            "region": "North",
            "sales": 50000,
            "percentage": 35.5
        }
    ]
    """

    sales_data = sales_by_region(
        dataframe
    )

    if not sales_data:
        return []

    total_sales = sum(
        item["sales"]
        for item in sales_data
    )

    if total_sales == 0:
        return [
            {
                "region": item["region"],
                "sales": item["sales"],
                "percentage": 0.0,
            }
            for item in sales_data
        ]

    return [
        {
            "region": item["region"],
            "sales": item["sales"],
            "percentage": float(
                (
                    item["sales"]
                    / total_sales
                )
                * 100
            ),
        }
        for item in sales_data
    ]


# ============================================================
# REGIONAL PERFORMANCE COMPARISON
# ============================================================

def regional_performance_comparison(
    dataframe,
    limit=None,
):
    """
    Combine sales, units and profit by region.

    Missing optional metrics remain None rather than
    being replaced with artificial zeroes.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    region_column = resolved_columns.get(
        "Region"
    )

    if not region_column:
        return []

    regions = clean_region_values(
        dataframe,
        region_column,
    )

    working_dataframe = pd.DataFrame(
        {
            "Region": regions,
        }
    )

    sales_column = get_sales_column(
        resolved_columns
    )

    quantity_column = get_quantity_column(
        resolved_columns
    )

    profit_column = get_profit_column(
        resolved_columns
    )

    if sales_column:

        working_dataframe["Sales"] = (
            get_numeric_series(
                dataframe,
                sales_column,
            )
        )

    if quantity_column:

        working_dataframe["Units"] = (
            get_numeric_series(
                dataframe,
                quantity_column,
            )
        )

    if profit_column:

        working_dataframe["Profit"] = (
            get_numeric_series(
                dataframe,
                profit_column,
            )
        )

    aggregations = {}

    if "Sales" in working_dataframe.columns:
        aggregations["Sales"] = "sum"

    if "Units" in working_dataframe.columns:
        aggregations["Units"] = "sum"

    if "Profit" in working_dataframe.columns:
        aggregations["Profit"] = "sum"

    if not aggregations:
        return []

    grouped = (
        working_dataframe
        .groupby(
            "Region",
            dropna=False,
        )
        .agg(aggregations)
        .reset_index()
    )

    if "Sales" in grouped.columns:
        grouped = grouped.sort_values(
            "Sales",
            ascending=False,
        )

    if limit:
        grouped = grouped.head(
            limit
        )

    result = []

    for _, row in grouped.iterrows():

        item = {
            "region": str(
                row["Region"]
            )
        }

        if "Sales" in grouped.columns:
            value = row["Sales"]

            item["sales"] = (
                None
                if pd.isna(value)
                else float(value)
            )
        else:
            item["sales"] = None

        if "Units" in grouped.columns:
            value = row["Units"]

            item["units"] = (
                None
                if pd.isna(value)
                else float(value)
            )
        else:
            item["units"] = None

        if "Profit" in grouped.columns:
            value = row["Profit"]

            item["profit"] = (
                None
                if pd.isna(value)
                else float(value)
            )
        else:
            item["profit"] = None

        result.append(item)

    return result


# ============================================================
# REGIONAL GROWTH
# ============================================================

def calculate_regional_growth(
    dataframe,
    current_from_date=None,
    current_to_date=None,
):
    """
    Compare the selected period with the immediately
    preceding period of the same length.

    Returns a percentage.

    Returns None when:
    - dates are unavailable,
    - sales are unavailable,
    - there is no previous-period data,
    - previous sales are zero.
    """

    if (
        dataframe is None
        or dataframe.empty
        or current_from_date is None
        or current_to_date is None
    ):
        return None

    resolved_columns = resolve_columns(
        dataframe
    )

    date_column = resolved_columns.get(
        "Date"
    )

    sales_column = get_sales_column(
        resolved_columns
    )

    if not date_column or not sales_column:
        return None

    dates = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
        dayfirst=True,
    )

    sales = pd.to_numeric(
        dataframe[sales_column],
        errors="coerce",
    )

    working_dataframe = pd.DataFrame(
        {
            "Date": dates,
            "Sales": sales,
        }
    ).dropna(
        subset=[
            "Date",
            "Sales",
        ]
    )

    if working_dataframe.empty:
        return None

    current_from = pd.to_datetime(
        current_from_date,
        errors="coerce",
    )

    current_to = pd.to_datetime(
        current_to_date,
        errors="coerce",
    )

    if (
        pd.isna(current_from)
        or pd.isna(current_to)
    ):
        return None

    if current_from > current_to:
        current_from, current_to = (
            current_to,
            current_from,
        )

    period_length = (
        current_to - current_from
    ).days + 1

    if period_length <= 0:
        return None

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

    current_data = working_dataframe[
        (
            working_dataframe["Date"]
            >= current_from
        )
        & (
            working_dataframe["Date"]
            <= current_to
        )
    ]

    previous_data = working_dataframe[
        (
            working_dataframe["Date"]
            >= previous_from
        )
        & (
            working_dataframe["Date"]
            <= previous_to
        )
    ]

    if current_data.empty:
        return None

    if previous_data.empty:
        return None

    current_sales = float(
        current_data["Sales"].sum()
    )

    previous_sales = float(
        previous_data["Sales"].sum()
    )

    if previous_sales == 0:
        return None

    return float(
        (
            (
                current_sales
                - previous_sales
            )
            / previous_sales
        )
        * 100
    )


# ============================================================
# REGIONAL TREND BY REGION
# ============================================================

def regional_sales_by_date(
    dataframe,
    limit=None,
):
    """
    Return sales by date and region.

    Useful for a multi-region trend chart.

    Output:

    [
        {
            "date": "2026-08-01",
            "region": "North",
            "sales": 5000
        }
    ]
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    date_column = resolved_columns.get(
        "Date"
    )

    region_column = resolved_columns.get(
        "Region"
    )

    sales_column = get_sales_column(
        resolved_columns
    )

    if (
        not date_column
        or not region_column
        or not sales_column
    ):
        return []

    working_dataframe = pd.DataFrame(
        {
            "Date": pd.to_datetime(
                dataframe[date_column],
                errors="coerce",
                dayfirst=True,
            ),
            "Region": clean_region_values(
                dataframe,
                region_column,
            ),
            "Sales": get_numeric_series(
                dataframe,
                sales_column,
            ),
        }
    )

    working_dataframe = (
        working_dataframe
        .dropna(
            subset=[
                "Date",
                "Sales",
            ]
        )
    )

    if working_dataframe.empty:
        return []

    region_totals = (
        working_dataframe
        .groupby("Region")["Sales"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    if limit:
        selected_regions = set(
            region_totals.head(
                limit
            ).index
        )

        working_dataframe = (
            working_dataframe[
                working_dataframe["Region"].isin(
                    selected_regions
                )
            ]
        )

    grouped = (
        working_dataframe
        .groupby(
            [
                working_dataframe[
                    "Date"
                ].dt.date,
                "Region",
            ],
            dropna=False,
        )["Sales"]
        .sum()
        .reset_index()
    )

    grouped.columns = [
        "date",
        "region",
        "sales",
    ]

    grouped = grouped.sort_values(
        [
            "date",
            "sales",
        ]
    )

    return [
        {
            "date": str(row["date"]),
            "region": str(row["region"]),
            "sales": float(row["sales"]),
        }
        for _, row in grouped.iterrows()
    ]


# ============================================================
# SMART REGIONAL INSIGHTS
# ============================================================

def generate_regional_insights(
    metrics,
    sales_regions=None,
    profit_regions=None,
    growth=None,
):
    """
    Generate rule-based Regional Intelligence insights.

    Returns a list of dictionaries.

    Example:

    {
        "type": "positive",
        "title": "Top Performing Region",
        "message": "North generated the highest sales..."
    }
    """

    insights = []

    if not metrics:
        return insights

    # --------------------------------------------------------
    # TOP REGION
    # --------------------------------------------------------

    top_region = metrics.get(
        "top_region"
    )

    top_region_sales = metrics.get(
        "top_region_sales"
    )

    total_sales = metrics.get(
        "total_sales"
    )

    if (
        top_region
        and top_region_sales is not None
    ):

        if (
            total_sales is not None
            and total_sales > 0
        ):

            contribution = (
                top_region_sales
                / total_sales
            ) * 100

            insights.append(
                {
                    "type": "positive",
                    "title": "Top Performing Region",
                    "message": (
                        f"{top_region} generated the "
                        f"highest sales of "
                        f"{top_region_sales:,.2f}, "
                        f"representing "
                        f"{contribution:.1f}% "
                        f"of total sales."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "positive",
                    "title": "Top Performing Region",
                    "message": (
                        f"{top_region} generated the "
                        f"highest regional sales "
                        f"of {top_region_sales:,.2f}."
                    ),
                }
            )

    # --------------------------------------------------------
    # GROWTH
    # --------------------------------------------------------

    if growth is not None:

        if growth > 0:

            insights.append(
                {
                    "type": "positive",
                    "title": "Regional Sales Growth",
                    "message": (
                        f"Regional sales increased "
                        f"by {growth:.2f}% compared "
                        f"with the previous "
                        f"comparable period."
                    ),
                }
            )

        elif growth < 0:

            insights.append(
                {
                    "type": "warning",
                    "title": "Regional Sales Decline",
                    "message": (
                        f"Regional sales decreased "
                        f"by {abs(growth):.2f}% compared "
                        f"with the previous "
                        f"comparable period."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "neutral",
                    "title": "Regional Sales Stable",
                    "message": (
                        "Regional sales remained "
                        "unchanged compared with "
                        "the previous comparable "
                        "period."
                    ),
                }
            )

    # --------------------------------------------------------
    # SALES CONCENTRATION
    # --------------------------------------------------------

    if (
        sales_regions
        and total_sales
        and total_sales > 0
    ):

        first_region = sales_regions[0]

        first_region_sales = first_region.get(
            "sales"
        )

        if first_region_sales is not None:

            contribution = (
                first_region_sales
                / total_sales
            ) * 100

            if contribution >= 50:

                insights.append(
                    {
                        "type": "warning",
                        "title": "High Regional Concentration",
                        "message": (
                            f"{first_region.get('region')} "
                            f"accounts for approximately "
                            f"{contribution:.1f}% of total "
                            f"sales. Sales are therefore "
                            "highly concentrated in this "
                            "region."
                        ),
                    }
                )

            elif contribution >= 30:

                insights.append(
                    {
                        "type": "neutral",
                        "title": "Regional Concentration",
                        "message": (
                            f"{first_region.get('region')} "
                            f"contributes approximately "
                            f"{contribution:.1f}% of total "
                            "sales."
                        ),
                    }
                )

    # --------------------------------------------------------
    # PROFITABILITY
    # --------------------------------------------------------

    if profit_regions:

        valid_profit_regions = [
            item
            for item in profit_regions
            if item.get("profit") is not None
        ]

        if valid_profit_regions:

            highest_profit = max(
                valid_profit_regions,
                key=lambda item: item["profit"],
            )

            lowest_profit = min(
                valid_profit_regions,
                key=lambda item: item["profit"],
            )

            if (
                highest_profit.get("region")
                != lowest_profit.get("region")
            ):

                insights.append(
                    {
                        "type": "positive",
                        "title": "Regional Profit Leader",
                        "message": (
                            f"{highest_profit.get('region')} "
                            f"generated the highest "
                            f"regional profit of "
                            f"{highest_profit.get('profit'):,.2f}."
                        ),
                    }
                )

                if (
                    lowest_profit.get("profit", 0)
                    < 0
                ):

                    insights.append(
                        {
                            "type": "warning",
                            "title": "Regional Loss Detected",
                            "message": (
                                f"{lowest_profit.get('region')} "
                                f"recorded a negative profit "
                                f"of "
                                f"{abs(lowest_profit.get('profit')):,.2f}."
                            ),
                        }
                    )

    # --------------------------------------------------------
    # MULTI-REGION COVERAGE
    # --------------------------------------------------------

    total_regions = metrics.get(
        "total_regions"
    )

    if total_regions == 1:

        insights.append(
            {
                "type": "neutral",
                "title": "Single Region Dataset",
                "message": (
                    "The available dataset contains "
                    "only one region, so regional "
                    "comparisons are limited."
                ),
            }
        )

    return insights


# ============================================================
# BACKWARD-COMPATIBILITY ALIASES
# ============================================================

def regional_sales(dataframe, limit=None):
    """
    Backward-compatible alias for sales_by_region().
    """

    return sales_by_region(
        dataframe,
        limit=limit,
    )


def regional_units(dataframe, limit=None):
    """
    Backward-compatible alias for units_by_region().
    """

    return units_by_region(
        dataframe,
        limit=limit,
    )


def regional_profit(dataframe, limit=None):
    """
    Backward-compatible alias for profit_by_region().
    """

    return profit_by_region(
        dataframe,
        limit=limit,
    )