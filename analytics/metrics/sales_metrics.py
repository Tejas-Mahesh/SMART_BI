import pandas as pd


# ============================================================
# CORE AND OPTIONAL COLUMNS
# ============================================================

CORE_REQUIRED_COLUMNS = [
    "Order_ID",
    "Order_Date",
    "Quantity",
    "Sales_Amount",
]


OPTIONAL_COLUMNS = [
    "Customer_ID",
    "Product_ID",
    "Product_Name",
    "Category",
    "Unit_Price",
    "Discount",
    "Sales_Channel",
    "Salesperson",
    "Region",
    "Payment_Method",
    "Order_Status",
]


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {

    "Order_ID": [
        "Order_ID",
        "Order ID",
        "order_id",
    ],

    "Order_Date": [
        "Order_Date",
        "Order Date",
        "order_date",
        "Date",
    ],

    "Customer_ID": [
        "Customer_ID",
        "Customer ID",
        "customer_id",
    ],

    "Product_ID": [
        "Product_ID",
        "Product ID",
        "product_id",
    ],

    "Product_Name": [
        "Product_Name",
        "Product Name",
        "product_name",
    ],

    "Category": [
        "Category",
        "category",
    ],

    "Quantity": [
        "Quantity",
        "quantity",
        "Qty",
        "qty",
    ],

    "Unit_Price": [
        "Unit_Price",
        "Unit Price",
        "unit_price",
    ],

    "Discount": [
        "Discount",
        "discount",
    ],

    "Sales_Amount": [
        "Sales_Amount",
        "Sales Amount",
        "sales_amount",
        "Sales",
        "Revenue",
    ],

    "Sales_Channel": [
        "Sales_Channel",
        "Sales Channel",
        "sales_channel",
        "Channel",
    ],

    "Salesperson": [
        "Salesperson",
        "salesperson",
        "Sales Person",
    ],

    "Region": [
        "Region",
        "region",
    ],

    "Payment_Method": [
        "Payment_Method",
        "Payment Method",
        "payment_method",
    ],

    "Order_Status": [
        "Order_Status",
        "Order Status",
        "order_status",
        "Status",
    ],
}


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

def normalize_column_name(column):
    """
    Normalize a dataframe column name so that different
    naming styles can be compared safely.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


# ============================================================
# RESOLVE ACTUAL DATAFRAME COLUMNS
# ============================================================

def resolve_columns(dataframe):
    """
    Map canonical Sales column names to the actual
    column names present in the dataframe.
    """

    normalized = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    resolved = {}

    for canonical, aliases in COLUMN_ALIASES.items():

        for alias in aliases:

            actual = normalized.get(
                normalize_column_name(alias)
            )

            if actual:
                resolved[canonical] = actual
                break

    return resolved


# ============================================================
# PREPARE SALES DATAFRAME
# ============================================================

def prepare_sales_dataframe(dataframe):
    """
    Prepare the Sales dataframe for analytics.

    Returns:

        dataframe
        resolved_columns
        missing_core_columns
        missing_optional_columns
    """

    dataframe = dataframe.copy()

    resolved = resolve_columns(
        dataframe
    )

    missing_core_columns = [
        column
        for column in CORE_REQUIRED_COLUMNS
        if column not in resolved
    ]

    missing_optional_columns = [
        column
        for column in OPTIONAL_COLUMNS
        if column not in resolved
    ]

    # --------------------------------------------------------
    # Numeric conversions
    # --------------------------------------------------------

    numeric_columns = [
        "Quantity",
        "Unit_Price",
        "Discount",
        "Sales_Amount",
    ]

    for canonical in numeric_columns:

        actual = resolved.get(
            canonical
        )

        if actual:

            dataframe[actual] = pd.to_numeric(
                dataframe[actual],
                errors="coerce",
            )

    # --------------------------------------------------------
    # Date conversion
    # --------------------------------------------------------

    date_column = resolved.get(
        "Order_Date"
    )

    if date_column:

        dataframe[date_column] = pd.to_datetime(
    dataframe[date_column],
    errors="coerce",
    dayfirst=True,
)

    return (
        dataframe,
        resolved,
        missing_core_columns,
        missing_optional_columns,
    )


# ============================================================
# SALES KPI METRICS
# ============================================================

def calculate_sales_metrics(
    dataframe,
    columns,
):
    """
    Calculate Sales Intelligence KPIs.
    """

    sales_column = columns.get(
        "Sales_Amount"
    )

    order_column = columns.get(
        "Order_ID"
    )

    quantity_column = columns.get(
        "Quantity"
    )

    status_column = columns.get(
        "Order_Status"
    )

    # --------------------------------------------------------
    # Total Sales
    # --------------------------------------------------------

    if sales_column:

        total_sales = dataframe[
            sales_column
        ].sum()

    else:

        total_sales = 0

    # --------------------------------------------------------
    # Total Orders
    # --------------------------------------------------------

    if order_column:

        total_orders = dataframe[
            order_column
        ].nunique()

    else:

        total_orders = len(
            dataframe
        )

    # --------------------------------------------------------
    # Units Sold
    # --------------------------------------------------------

    if quantity_column:

        units_sold = dataframe[
            quantity_column
        ].sum()

    else:

        units_sold = 0

    # --------------------------------------------------------
    # Average Order Value
    # --------------------------------------------------------

    if total_orders:

        average_order_value = (
            total_sales
            / total_orders
        )

    else:

        average_order_value = 0

    # --------------------------------------------------------
    # Completed Orders
    # --------------------------------------------------------

    completed_orders = 0

    if status_column:

        status = (
            dataframe[status_column]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        completed_orders = (
            status.isin(
                [
                    "completed",
                    "complete",
                    "delivered",
                    "closed",
                ]
            )
            .sum()
        )

    # --------------------------------------------------------
    # Completed Order Percentage
    # --------------------------------------------------------

    completed_order_percentage = (
        (
            completed_orders
            / total_orders
        )
        * 100
        if total_orders
        else 0
    )

    return {

        "total_sales": float(
            total_sales or 0
        ),

        "total_orders": int(
            total_orders or 0
        ),

        "units_sold": float(
            units_sold or 0
        ),

        "average_order_value": float(
            average_order_value or 0
        ),

        "completed_order_percentage": float(
            completed_order_percentage or 0
        ),
    }


# ============================================================
# SALES TREND
# ============================================================

def sales_trend(
    dataframe,
    columns,
):
    """
    Calculate daily sales trend.
    """

    date_column = columns.get(
        "Order_Date"
    )

    sales_column = columns.get(
        "Sales_Amount"
    )

    if (
        not date_column
        or not sales_column
    ):

        return []

    working = dataframe.dropna(
        subset=[
            date_column
        ]
    ).copy()

    if working.empty:

        return []

    working["__date"] = (
        working[date_column]
        .dt.to_period("D")
        .dt.to_timestamp()
    )

    result = (
        working
        .groupby(
            "__date"
        )[sales_column]
        .sum()
        .reset_index()
        .sort_values(
            "__date"
        )
    )

    return [

        {
            "date": row[
                "__date"
            ].strftime(
                "%Y-%m-%d"
            ),

            "sales": float(
                row[sales_column] or 0
            ),
        }

        for _, row in result.iterrows()
    ]


# ============================================================
# SALES BY CATEGORY
# ============================================================

def sales_by_category(
    dataframe,
    columns,
):
    """
    Calculate sales grouped by category.
    """

    category_column = columns.get(
        "Category"
    )

    sales_column = columns.get(
        "Sales_Amount"
    )

    if (
        not category_column
        or not sales_column
    ):

        return []

    working = dataframe[
        [
            category_column,
            sales_column,
        ]
    ].dropna(
        subset=[
            category_column
        ]
    )

    if working.empty:

        return []

    result = (
        working
        .groupby(
            category_column
        )[sales_column]
        .sum()
        .sort_values(
            ascending=False
        )
        .reset_index()
    )

    return [

        {
            "category": str(
                row[category_column]
            ),

            "sales": float(
                row[sales_column] or 0
            ),
        }

        for _, row in result.iterrows()
    ]


# ============================================================
# TOP PRODUCTS
# ============================================================

def top_products(
    dataframe,
    columns,
    limit=10,
):
    """
    Calculate top products by sales.
    """

    product_column = columns.get(
        "Product_Name"
    )

    sales_column = columns.get(
        "Sales_Amount"
    )

    if (
        not product_column
        or not sales_column
    ):

        return []

    working = dataframe[
        [
            product_column,
            sales_column,
        ]
    ].dropna(
        subset=[
            product_column
        ]
    )

    if working.empty:

        return []

    result = (
        working
        .groupby(
            product_column
        )[sales_column]
        .sum()
        .sort_values(
            ascending=False
        )
        .head(limit)
        .reset_index()
    )

    return [

        {
            "product": str(
                row[product_column]
            ),

            "sales": float(
                row[sales_column] or 0
            ),
        }

        for _, row in result.iterrows()
    ]


# ============================================================
# SALES BY CHANNEL
# ============================================================

def sales_by_channel(
    dataframe,
    columns,
):
    """
    Calculate sales grouped by sales channel.
    """

    channel_column = columns.get(
        "Sales_Channel"
    )

    sales_column = columns.get(
        "Sales_Amount"
    )

    if (
        not channel_column
        or not sales_column
    ):

        return []

    working = dataframe[
        [
            channel_column,
            sales_column,
        ]
    ].dropna(
        subset=[
            channel_column
        ]
    )

    if working.empty:

        return []

    result = (
        working
        .groupby(
            channel_column
        )[sales_column]
        .sum()
        .sort_values(
            ascending=False
        )
        .reset_index()
    )

    return [

        {
            "channel": str(
                row[channel_column]
            ),

            "sales": float(
                row[sales_column] or 0
            ),
        }

        for _, row in result.iterrows()
    ]


# ============================================================
# SALESPERSON PERFORMANCE
# ============================================================

def salesperson_performance(
    dataframe,
    columns,
):
    """
    Calculate sales grouped by salesperson.
    """

    salesperson_column = columns.get(
        "Salesperson"
    )

    sales_column = columns.get(
        "Sales_Amount"
    )

    if (
        not salesperson_column
        or not sales_column
    ):

        return []

    working = dataframe[
        [
            salesperson_column,
            sales_column,
        ]
    ].dropna(
        subset=[
            salesperson_column
        ]
    )

    if working.empty:

        return []

    result = (
        working
        .groupby(
            salesperson_column
        )[sales_column]
        .sum()
        .sort_values(
            ascending=False
        )
        .reset_index()
    )

    return [

        {
            "salesperson": str(
                row[salesperson_column]
            ),

            "sales": float(
                row[sales_column] or 0
            ),
        }

        for _, row in result.iterrows()
    ]


# ============================================================
# SALES BY QUANTITY BAND
# ============================================================

def sales_by_quantity_band(
    dataframe,
    columns,
):
    """
    Group sales into practical quantity bands.

    Bands:

        1–5
        6–10
        11–25
        26–50
        51+

    This produces a business-friendly chart instead of
    plotting every individual transaction as a scatter point.
    """

    quantity_column = columns.get(
        "Quantity"
    )

    sales_column = columns.get(
        "Sales_Amount"
    )

    if (
        not quantity_column
        or not sales_column
    ):

        return []

    working = dataframe[
        [
            quantity_column,
            sales_column,
        ]
    ].copy()

    working[quantity_column] = pd.to_numeric(
        working[quantity_column],
        errors="coerce",
    )

    working[sales_column] = pd.to_numeric(
        working[sales_column],
        errors="coerce",
    )

    working = working.dropna(
        subset=[
            quantity_column,
            sales_column,
        ]
    )

    if working.empty:

        return []

    # --------------------------------------------------------
    # Remove zero / negative quantities
    # --------------------------------------------------------

    working = working[
        working[quantity_column] > 0
    ]

    if working.empty:

        return []

    # --------------------------------------------------------
    # Create quantity bands
    # --------------------------------------------------------

    def get_quantity_band(quantity):

        if quantity <= 5:
            return "1–5"

        if quantity <= 10:
            return "6–10"

        if quantity <= 25:
            return "11–25"

        if quantity <= 50:
            return "26–50"

        return "51+"

    working["__quantity_band"] = (
        working[quantity_column]
        .apply(get_quantity_band)
    )

    band_order = [
        "1–5",
        "6–10",
        "11–25",
        "26–50",
        "51+",
    ]

    result = (
        working
        .groupby(
            "__quantity_band"
        )
        .agg(
            sales=(
                sales_column,
                "sum",
            ),
            orders=(
                quantity_column,
                "size",
            ),
            units=(
                quantity_column,
                "sum",
            ),
        )
        .reindex(
            band_order,
            fill_value=0,
        )
        .reset_index()
    )

    return [

        {
            "band": str(
                row["__quantity_band"]
            ),

            "sales": float(
                row["sales"] or 0
            ),

            "orders": int(
                row["orders"] or 0
            ),

            "units": float(
                row["units"] or 0
            ),
        }

        for _, row in result.iterrows()

        if row["orders"] > 0
    ]


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def quantity_vs_sales(
    dataframe,
    columns,
):
    """
    Backward-compatible wrapper.

    Existing code using quantity_vs_sales() will now receive
    quantity-band analysis rather than thousands of scatter
    points.

    New code should use sales_by_quantity_band().
    """

    return sales_by_quantity_band(
        dataframe,
        columns,
    )


def calculate_sales_growth(
    current_dataframe,
    full_dataframe,
    columns,
    from_date=None,
    to_date=None,
):
    """
    Compare the selected period with the immediately
    preceding period of the same duration.
    """

    date_column = columns.get(
        "Order_Date"
    )

    sales_column = columns.get(
        "Sales_Amount"
    )

    if not date_column or not sales_column:
        return None

    if from_date in (None, ""):
        return None

    if to_date in (None, ""):
        return None

    current_start = pd.to_datetime(
        from_date,
        errors="coerce",
    )

    current_end = pd.to_datetime(
        to_date,
        errors="coerce",
    )

    if pd.isna(current_start):
        return None

    if pd.isna(current_end):
        return None

    current_start = current_start.normalize()
    current_end = current_end.normalize()

    if current_end < current_start:
        return None

    if full_dataframe is None:
        return None

    if full_dataframe.empty:
        return None

    if date_column not in full_dataframe.columns:
        return None

    if sales_column not in full_dataframe.columns:
        return None

    # --------------------------------------------------------
    # Prepare historical data
    # --------------------------------------------------------

    working = full_dataframe[
        [
            date_column,
            sales_column,
        ]
    ].copy()

    working["__growth_date"] = pd.to_datetime(
        working[date_column],
        errors="coerce",
    )

    working["__growth_sales"] = pd.to_numeric(
        working[sales_column],
        errors="coerce",
    )

    working = working.dropna(
        subset=[
            "__growth_date",
            "__growth_sales",
        ]
    )

    if working.empty:
        return None

    working["__growth_date"] = (
        working["__growth_date"]
        .dt.normalize()
    )

    # --------------------------------------------------------
    # Current period
    # --------------------------------------------------------

    current_mask = (
        (working["__growth_date"] >= current_start)
        &
        (working["__growth_date"] <= current_end)
    )

    current_period = working.loc[
        current_mask
    ]

    current_sales = float(
        current_period[
            "__growth_sales"
        ].sum()
    )

    # --------------------------------------------------------
    # Number of days in current period
    # --------------------------------------------------------

    period_days = (
        current_end - current_start
    ).days + 1

    if period_days <= 0:
        return None

    # --------------------------------------------------------
    # Previous comparable period
    # --------------------------------------------------------

    previous_end = (
        current_start
        - pd.Timedelta(days=1)
    )

    previous_start = (
        previous_end
        - pd.Timedelta(
            days=period_days - 1
        )
    )

    previous_mask = (
        (working["__growth_date"] >= previous_start)
        &
        (working["__growth_date"] <= previous_end)
    )

    previous_period = working.loc[
        previous_mask
    ]

    # --------------------------------------------------------
    # No previous rows
    # --------------------------------------------------------

    if previous_period.empty:
        return None

    previous_sales = float(
        previous_period[
            "__growth_sales"
        ].sum()
    )

    # --------------------------------------------------------
    # Previous sales = zero
    # --------------------------------------------------------

    if previous_sales == 0:
        return None

    # --------------------------------------------------------
    # Growth %
    # --------------------------------------------------------

    growth = (
        (
            current_sales
            - previous_sales
        )
        / previous_sales
    ) * 100

    return round(
        float(growth),
        2,
    )
# ============================================================
# SMART SALES INSIGHTS
# ============================================================

def generate_sales_insights(
    metrics,
    category_data,
    product_data,
    channel_data,
    salesperson_data,
):
    """
    Generate simple rule-based Sales Intelligence
    insights from calculated metrics.
    """

    insights = []

    total_sales = metrics.get(
        "total_sales",
        0,
    )

    total_orders = metrics.get(
        "total_orders",
        0,
    )

    units_sold = metrics.get(
        "units_sold",
        0,
    )

    aov = metrics.get(
        "average_order_value",
        0,
    )

    completed_percentage = metrics.get(
        "completed_order_percentage",
        0,
    )

    sales_growth = metrics.get(
        "sales_growth"
    )

    # --------------------------------------------------------
    # Total Sales
    # --------------------------------------------------------

    if total_sales > 0:

        insights.append(
            f"Total sales reached "
            f"{total_sales:,.2f} across "
            f"{total_orders:,} orders."
        )

    # --------------------------------------------------------
    # Average Order Value
    # --------------------------------------------------------

    if aov > 0:

        insights.append(
            f"Average order value is "
            f"{aov:,.2f}."
        )

    # --------------------------------------------------------
    # Units Sold
    # --------------------------------------------------------

    if units_sold > 0:

        insights.append(
            f"{units_sold:,.0f} units were sold "
            f"during the selected period."
        )

    # --------------------------------------------------------
    # Sales Growth
    # --------------------------------------------------------

    if sales_growth is not None:

        if sales_growth > 0:

            insights.append(
                f"Sales increased by "
                f"{sales_growth:.1f}% "
                f"compared with the previous period."
            )

        elif sales_growth < 0:

            insights.append(
                f"Sales decreased by "
                f"{abs(sales_growth):.1f}% "
                f"compared with the previous period."
            )

        else:

            insights.append(
                "Sales remained unchanged "
                "compared with the previous period."
            )

    # --------------------------------------------------------
    # Top Category
    # --------------------------------------------------------

    if category_data:

        top_category = category_data[0]

        insights.append(
            f"{top_category['category']} is the "
            f"highest-sales category."
        )

    # --------------------------------------------------------
    # Top Product
    # --------------------------------------------------------

    if product_data:

        top_product = product_data[0]

        insights.append(
            f"{top_product['product']} is the "
            f"top product by sales."
        )

    # --------------------------------------------------------
    # Top Channel
    # --------------------------------------------------------

    if channel_data:

        top_channel = channel_data[0]

        insights.append(
            f"{top_channel['channel']} is the "
            f"leading sales channel."
        )

    # --------------------------------------------------------
    # Top Salesperson
    # --------------------------------------------------------

    if salesperson_data:

        top_salesperson = salesperson_data[0]

        insights.append(
            f"{top_salesperson['salesperson']} "
            f"has the highest sales among "
            f"salespeople."
        )

    # --------------------------------------------------------
    # Completed Orders
    # --------------------------------------------------------

    if completed_percentage:

        insights.append(
            f"Completed-order rate is "
            f"{completed_percentage:.1f}%."
        )

    return insights[:6]