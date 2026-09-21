# analytics/metrics/customer_metrics.py

import pandas as pd


# ============================================================
# REQUIRED / OPTIONAL COLUMNS
# ============================================================

CORE_REQUIRED_COLUMNS = [
    "Customer_ID",
]

OPTIONAL_COLUMNS = [
    "Registration_Date",
    "Last_Order_Date",
    "Order_Count",
    "Total_Orders",
    "Total_Spend",
    "Sales_Amount",
    "Order_Value",
    "Region",
    "City",
    "State",
    "Country",
    "Gender",
    "Age",
    "Customer_Segment",
    "Customer_Status",
]


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {
    "Customer_ID": [
        "Customer_ID",
        "Customer Id",
        "CustomerID",
        "Customer ID",
        "Customer_Code",
        "Customer Code",
    ],

    "Registration_Date": [
        "Registration_Date",
        "Registration Date",
        "Register_Date",
        "Register Date",
        "Signup_Date",
        "Signup Date",
        "Sign_Up_Date",
        "Sign Up Date",
        "Join_Date",
        "Join Date",
    ],

    "Last_Order_Date": [
        "Last_Order_Date",
        "Last Order Date",
        "LastOrderDate",
        "Latest_Order_Date",
        "Latest Order Date",
    ],

    "Order_Count": [
        "Order_Count",
        "Order Count",
        "OrderCount",
        "Orders",
        "Number_of_Orders",
        "Number of Orders",
    ],

    "Total_Orders": [
        "Total_Orders",
        "Total Orders",
        "TotalOrder",
        "Total Order Count",
    ],

    "Total_Spend": [
        "Total_Spend",
        "Total Spend",
        "TotalSpend",
        "Customer_Spend",
        "Customer Spend",
        "Lifetime_Value",
        "Lifetime Value",
        "CLV",
    ],

    "Sales_Amount": [
        "Sales_Amount",
        "Sales Amount",
        "SalesAmount",
        "Revenue",
        "Revenue_Amount",
        "Revenue Amount",
        "Amount",
    ],

    "Order_Value": [
        "Order_Value",
        "Order Value",
        "OrderValue",
        "Average_Order_Value",
        "Average Order Value",
    ],

    "Region": [
        "Region",
        "Customer_Region",
        "Customer Region",
    ],

    "City": [
        "City",
        "Customer_City",
        "Customer City",
    ],

    "State": [
        "State",
        "Customer_State",
        "Customer State",
    ],

    "Country": [
        "Country",
        "Customer_Country",
        "Customer Country",
    ],

    "Gender": [
        "Gender",
        "Sex",
    ],

    "Age": [
        "Age",
        "Customer_Age",
        "Customer Age",
    ],

    "Customer_Segment": [
        "Customer_Segment",
        "Customer Segment",
        "Segment",
    ],

    "Customer_Status": [
        "Customer_Status",
        "Customer Status",
        "Status",
    ],
}


# ============================================================
# COLUMN HELPERS
# ============================================================

def normalize_column_name(column):
    """
    Normalize dataframe column names for reliable alias matching.
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
    Resolve available dataframe columns to canonical
    Customer Intelligence column names.
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

            if actual_column:
                resolved[canonical_name] = (
                    actual_column
                )
                break

    return resolved


def prepare_customer_dataframe(dataframe):
    """
    Prepare Customer dataframe for analytics.
    """

    if dataframe is None:

        return (
            pd.DataFrame(),
            {},
            CORE_REQUIRED_COLUMNS.copy(),
        )

    prepared = dataframe.copy()

    columns = resolve_columns(
        prepared
    )

    missing_required = [
        column
        for column in CORE_REQUIRED_COLUMNS
        if column not in columns
    ]

    return (
        prepared,
        columns,
        missing_required,
    )


# ============================================================
# CUSTOMER ID HELPER
# ============================================================

def get_valid_customer_series(
    dataframe,
    customer_column,
):
    """
    Return cleaned Customer_ID values.
    """

    if (
        dataframe is None
        or dataframe.empty
        or not customer_column
        or customer_column not in dataframe.columns
    ):
        return pd.Series(
            dtype="object"
        )

    customer_series = (
        dataframe[customer_column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    customer_series = customer_series[
        customer_series != ""
    ]

    return customer_series


# ============================================================
# BASIC CUSTOMER METRICS
# ============================================================

def calculate_customer_metrics(
    dataframe,
    columns,
):
    """
    Calculate the primary Customer Intelligence KPIs.

    Metrics are calculated from the dataframe supplied by
    the Customer Intelligence view.

    Unsupported metrics return None rather than fake zeroes.
    """

    metrics = {
        "total_customers": None,
        "new_customers": None,
        "active_customers": None,
        "repeat_customers": None,
        "average_customer_value": None,
        "average_orders_per_customer": None,
        "customer_growth": None,
    }

    if dataframe is None or dataframe.empty:
        return metrics

    customer_column = columns.get(
        "Customer_ID"
    )

    if not customer_column:
        return metrics

    customer_series = get_valid_customer_series(
        dataframe,
        customer_column,
    )

    if customer_series.empty:
        return metrics

    # --------------------------------------------------------
    # TOTAL CUSTOMERS
    # --------------------------------------------------------

    metrics["total_customers"] = int(
        customer_series.nunique()
    )

    # --------------------------------------------------------
    # NEW CUSTOMERS
    # --------------------------------------------------------
    #
    # When Registration_Date exists, customers appearing
    # in the selected dataframe are treated as customers
    # registered in the selected analysis period.
    #
    # This works naturally with the date-filtered dataframe
    # supplied by customer_intelligence().
    # --------------------------------------------------------

    registration_column = columns.get(
        "Registration_Date"
    )

    if (
        registration_column
        and registration_column in dataframe.columns
    ):

        registration_dates = pd.to_datetime(
            dataframe[registration_column],
            errors="coerce",
            dayfirst=True,
        )

        registration_customers = (
            dataframe.loc[
                registration_dates.notna(),
                customer_column,
            ]
            .dropna()
            .astype(str)
            .str.strip()
        )

        registration_customers = (
            registration_customers[
                registration_customers != ""
            ]
        )

        if not registration_customers.empty:

            metrics["new_customers"] = int(
                registration_customers.nunique()
            )

    # --------------------------------------------------------
    # ACTIVE CUSTOMERS
    # --------------------------------------------------------
    #
    # Priority:
    #
    # 1. Customer_Status
    # 2. Last_Order_Date
    # 3. Order_Count / Total_Orders
    #
    # This prevents active_customers from remaining None
    # simply because one particular column is unavailable.
    # --------------------------------------------------------

    status_column = columns.get(
        "Customer_Status"
    )

    last_order_column = columns.get(
        "Last_Order_Date"
    )

    order_count_column = (
        columns.get("Order_Count")
        or columns.get("Total_Orders")
    )

    active_customer_ids = set()

    # --------------------------------------------------------
    # METHOD 1: CUSTOMER STATUS
    # --------------------------------------------------------

    if (
        status_column
        and status_column in dataframe.columns
    ):

        status_working = dataframe.copy()

        status_working["_customer_id"] = (
            status_working[
                customer_column
            ]
            .astype(str)
            .str.strip()
        )

        status_working["_customer_status"] = (
            status_working[
                status_column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

        active_statuses = {
            "active",
            "current",
            "engaged",
            "retained",
            "1",
            "yes",
            "true",
        }

        active_rows = status_working[
            status_working[
                "_customer_status"
            ].isin(active_statuses)
        ]

        if not active_rows.empty:

            active_customer_ids.update(
                active_rows[
                    "_customer_id"
                ]
                .loc[
                    active_rows[
                        "_customer_id"
                    ] != ""
                ]
                .unique()
                .tolist()
            )

    # --------------------------------------------------------
    # METHOD 2: LAST ORDER DATE
    # --------------------------------------------------------

    if (
        last_order_column
        and last_order_column in dataframe.columns
        and not active_customer_ids
    ):

        last_order_dates = pd.to_datetime(
            dataframe[
                last_order_column
            ],
            errors="coerce",
            dayfirst=True,
        )

        active_rows = dataframe[
            last_order_dates.notna()
        ]

        if not active_rows.empty:

            ids = (
                active_rows[
                    customer_column
                ]
                .dropna()
                .astype(str)
                .str.strip()
            )

            ids = ids[
                ids != ""
            ]

            active_customer_ids.update(
                ids.unique().tolist()
            )

    # --------------------------------------------------------
    # METHOD 3: ORDER COUNT
    # --------------------------------------------------------

    if (
        order_count_column
        and order_count_column in dataframe.columns
        and not active_customer_ids
    ):

        order_counts = pd.to_numeric(
            dataframe[
                order_count_column
            ],
            errors="coerce",
        )

        active_rows = dataframe[
            order_counts > 0
        ]

        if not active_rows.empty:

            ids = (
                active_rows[
                    customer_column
                ]
                .dropna()
                .astype(str)
                .str.strip()
            )

            ids = ids[
                ids != ""
            ]

            active_customer_ids.update(
                ids.unique().tolist()
            )

    if active_customer_ids:

        metrics["active_customers"] = int(
            len(active_customer_ids)
        )

    # --------------------------------------------------------
    # TOTAL SPEND / CUSTOMER VALUE
    # --------------------------------------------------------

    spend_column = (
        columns.get("Total_Spend")
        or columns.get("Sales_Amount")
    )

    if (
        spend_column
        and spend_column in dataframe.columns
    ):

        working = pd.DataFrame(
            {
                "customer": (
                    dataframe[
                        customer_column
                    ]
                    .astype(str)
                    .str.strip()
                ),
                "spend": pd.to_numeric(
                    dataframe[
                        spend_column
                    ],
                    errors="coerce",
                ),
            }
        )

        working = working[
            working["customer"] != ""
        ]

        customer_spend = (
            working
            .groupby("customer")["spend"]
            .sum()
        )

        if not customer_spend.empty:

            metrics[
                "average_customer_value"
            ] = round(
                float(
                    customer_spend.mean()
                ),
                2,
            )

    # --------------------------------------------------------
    # ORDER COUNT
    # --------------------------------------------------------

    if (
        order_count_column
        and order_count_column in dataframe.columns
    ):

        working = pd.DataFrame(
            {
                "customer": (
                    dataframe[
                        customer_column
                    ]
                    .astype(str)
                    .str.strip()
                ),
                "orders": pd.to_numeric(
                    dataframe[
                        order_count_column
                    ],
                    errors="coerce",
                ),
            }
        )

        working = working[
            working["customer"] != ""
        ]

        customer_orders = (
            working
            .groupby("customer")["orders"]
            .sum()
        )

        if not customer_orders.empty:

            metrics[
                "average_orders_per_customer"
            ] = round(
                float(
                    customer_orders.mean()
                ),
                2,
            )

            metrics[
                "repeat_customers"
            ] = int(
                (
                    customer_orders > 1
                ).sum()
            )

    return metrics


# ============================================================
# CUSTOMER REGISTRATION TREND
# ============================================================

def customer_registration_trend(
    dataframe,
    columns,
    aggregation="auto",
):
    """
    Generate customer registration trend.
    """

    date_column = columns.get(
        "Registration_Date"
    )

    customer_column = columns.get(
        "Customer_ID"
    )

    if not date_column or not customer_column:
        return []

    working = dataframe.copy()

    working[date_column] = pd.to_datetime(
        working[date_column],
        errors="coerce",
        dayfirst=True,
    )

    working = working.dropna(
        subset=[date_column]
    )

    if working.empty:
        return []

    working["_customer_id"] = (
        working[customer_column]
        .astype(str)
        .str.strip()
    )

    working = working[
        working["_customer_id"] != ""
    ]

    if working.empty:
        return []

    if aggregation == "auto":
        aggregation = "daily"

    if aggregation == "weekly":

        working["_period"] = (
            working[date_column]
            .dt.to_period("W")
            .dt.start_time
        )

    elif aggregation == "monthly":

        working["_period"] = (
            working[date_column]
            .dt.to_period("M")
            .dt.start_time
        )

    else:

        working["_period"] = (
            working[date_column]
            .dt.normalize()
        )

    grouped = (
        working
        .groupby("_period")["_customer_id"]
        .nunique()
        .reset_index()
    )

    grouped.columns = [
        "date",
        "customers",
    ]

    grouped = grouped.sort_values(
        "date"
    )

    return [
        {
            "date": row["date"].strftime(
                "%Y-%m-%d"
            ),
            "customers": int(
                row["customers"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


# ============================================================
# CUSTOMER BY REGION
# ============================================================

def customers_by_region(
    dataframe,
    columns,
):
    """
    Customer count by region.
    """

    customer_column = columns.get(
        "Customer_ID"
    )

    region_column = columns.get(
        "Region"
    )

    if not customer_column or not region_column:
        return []

    working = dataframe.copy()

    working["_customer_id"] = (
        working[customer_column]
        .astype(str)
        .str.strip()
    )

    working["_region"] = (
        working[region_column]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    working.loc[
        working["_region"] == "",
        "_region",
    ] = "Unknown"

    working = working[
        working["_customer_id"] != ""
    ]

    result = (
        working
        .groupby("_region")["_customer_id"]
        .nunique()
        .reset_index()
    )

    result.columns = [
        "region",
        "customers",
    ]

    result = result.sort_values(
        "customers",
        ascending=False,
    )

    return [
        {
            "region": row["region"],
            "customers": int(
                row["customers"]
            ),
        }
        for _, row in result.iterrows()
    ]


# ============================================================
# CUSTOMER SEGMENTS
# ============================================================

def customers_by_segment(
    dataframe,
    columns,
):
    """
    Customer count by customer segment.
    """

    customer_column = columns.get(
        "Customer_ID"
    )

    segment_column = columns.get(
        "Customer_Segment"
    )

    if not customer_column or not segment_column:
        return []

    working = dataframe.copy()

    working["_customer_id"] = (
        working[customer_column]
        .astype(str)
        .str.strip()
    )

    working["_segment"] = (
        working[segment_column]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    working.loc[
        working["_segment"] == "",
        "_segment",
    ] = "Unknown"

    working = working[
        working["_customer_id"] != ""
    ]

    result = (
        working
        .groupby("_segment")["_customer_id"]
        .nunique()
        .reset_index()
    )

    result.columns = [
        "segment",
        "customers",
    ]

    result = result.sort_values(
        "customers",
        ascending=False,
    )

    return [
        {
            "segment": row["segment"],
            "customers": int(
                row["customers"]
            ),
        }
        for _, row in result.iterrows()
    ]


# ============================================================
# CUSTOMER STATUS
# ============================================================

def customers_by_status(
    dataframe,
    columns,
):
    """
    Customer count by status.
    """

    customer_column = columns.get(
        "Customer_ID"
    )

    status_column = columns.get(
        "Customer_Status"
    )

    if not customer_column or not status_column:
        return []

    working = dataframe.copy()

    working["_customer_id"] = (
        working[customer_column]
        .astype(str)
        .str.strip()
    )

    working["_status"] = (
        working[status_column]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    working.loc[
        working["_status"] == "",
        "_status",
    ] = "Unknown"

    working = working[
        working["_customer_id"] != ""
    ]

    result = (
        working
        .groupby("_status")["_customer_id"]
        .nunique()
        .reset_index()
    )

    result.columns = [
        "status",
        "customers",
    ]

    result = result.sort_values(
        "customers",
        ascending=False,
    )

    return [
        {
            "status": row["status"],
            "customers": int(
                row["customers"]
            ),
        }
        for _, row in result.iterrows()
    ]


# ============================================================
# CUSTOMER VALUE DISTRIBUTION
# ============================================================

def customer_value_distribution(
    dataframe,
    columns,
):
    """
    Group customers into value bands.
    """

    customer_column = columns.get(
        "Customer_ID"
    )

    spend_column = (
        columns.get("Total_Spend")
        or columns.get("Sales_Amount")
    )

    if not customer_column or not spend_column:
        return []

    working = dataframe.copy()

    working["_customer_id"] = (
        working[customer_column]
        .astype(str)
        .str.strip()
    )

    working["_spend"] = pd.to_numeric(
        working[spend_column],
        errors="coerce",
    ).fillna(0)

    working = working[
        working["_customer_id"] != ""
    ]

    customer_values = (
        working
        .groupby("_customer_id")["_spend"]
        .sum()
    )

    if customer_values.empty:
        return []

    def get_band(value):

        if value < 10000:
            return "0–10K"

        if value < 50000:
            return "10K–50K"

        if value < 100000:
            return "50K–1L"

        if value < 500000:
            return "1L–5L"

        return "5L+"

    bands = customer_values.apply(
        get_band
    )

    result = (
        bands
        .value_counts()
        .rename_axis("band")
        .reset_index(name="customers")
    )

    band_order = [
        "0–10K",
        "10K–50K",
        "50K–1L",
        "1L–5L",
        "5L+",
    ]

    result["band"] = pd.Categorical(
        result["band"],
        categories=band_order,
        ordered=True,
    )

    result = result.sort_values(
        "band"
    )

    return [
        {
            "band": row["band"],
            "customers": int(
                row["customers"]
            ),
        }
        for _, row in result.iterrows()
    ]


# ============================================================
# REPEAT CUSTOMER ANALYSIS
# ============================================================

def repeat_customer_analysis(
    dataframe,
    columns,
):
    """
    Calculate new/repeat customer counts when
    sufficient order information exists.
    """

    customer_column = columns.get(
        "Customer_ID"
    )

    order_count_column = (
        columns.get("Order_Count")
        or columns.get("Total_Orders")
    )

    if (
        not customer_column
        or not order_count_column
    ):

        return {
            "new_customers": None,
            "repeat_customers": None,
        }

    working = dataframe.copy()

    working["_customer_id"] = (
        working[customer_column]
        .astype(str)
        .str.strip()
    )

    working["_orders"] = pd.to_numeric(
        working[order_count_column],
        errors="coerce",
    )

    working = working[
        working["_customer_id"] != ""
    ]

    customer_orders = (
        working
        .groupby("_customer_id")["_orders"]
        .sum()
    )

    if customer_orders.empty:

        return {
            "new_customers": None,
            "repeat_customers": None,
        }

    return {
        "new_customers": int(
            (
                customer_orders <= 1
            ).sum()
        ),
        "repeat_customers": int(
            (
                customer_orders > 1
            ).sum()
        ),
    }


# ============================================================
# SMART CUSTOMER INSIGHTS
# ============================================================

def generate_customer_insights(
    metrics,
    customer_segments=None,
    regions=None,
):
    """
    Generate rule-based Customer Intelligence insights.
    """

    insights = []

    total_customers = metrics.get(
        "total_customers"
    )

    repeat_customers = metrics.get(
        "repeat_customers"
    )

    average_customer_value = metrics.get(
        "average_customer_value"
    )

    active_customers = metrics.get(
        "active_customers"
    )

    customer_growth = metrics.get(
        "customer_growth"
    )

    # --------------------------------------------------------
    # CUSTOMER GROWTH
    # --------------------------------------------------------

    if customer_growth is not None:

        growth_text = (
            f"{customer_growth:+.2f}%"
        )

        insights.append(
            {
                "type": "customer_growth",
                "title": "Customer Growth",
                "description": (
                    "Customer count changed by "
                    f"{growth_text} compared with "
                    "the previous comparable period."
                ),
            }
        )

    # --------------------------------------------------------
    # ACTIVE CUSTOMER RATE
    # --------------------------------------------------------

    if (
        total_customers is not None
        and active_customers is not None
        and total_customers > 0
    ):

        active_rate = (
            active_customers
            / total_customers
        ) * 100

        insights.append(
            {
                "type": "active_customers",
                "title": "Active Customer Rate",
                "description": (
                    f"{active_rate:.1f}% of identified "
                    "customers are currently classified "
                    "as active."
                ),
            }
        )

    # --------------------------------------------------------
    # REPEAT CUSTOMER RATE
    # --------------------------------------------------------

    if (
        total_customers is not None
        and repeat_customers is not None
        and total_customers > 0
    ):

        repeat_rate = (
            repeat_customers
            / total_customers
        ) * 100

        insights.append(
            {
                "type": "customer_retention",
                "title": "Repeat Customer Rate",
                "description": (
                    f"{repeat_rate:.1f}% of identified "
                    "customers are repeat customers."
                ),
            }
        )

    # --------------------------------------------------------
    # CUSTOMER VALUE
    # --------------------------------------------------------

    if average_customer_value is not None:

        insights.append(
            {
                "type": "customer_value",
                "title": "Average Customer Value",
                "description": (
                    "Average customer value is "
                    f"₹{average_customer_value:,.2f}."
                ),
            }
        )

    # --------------------------------------------------------
    # TOP REGION
    # --------------------------------------------------------

    if regions:

        top_region = regions[0]

        insights.append(
            {
                "type": "regional_customer",
                "title": "Largest Customer Region",
                "description": (
                    f"{top_region['region']} has "
                    f"{top_region['customers']:,} "
                    "identified customers."
                ),
            }
        )

    # --------------------------------------------------------
    # TOP SEGMENT
    # --------------------------------------------------------

    if customer_segments:

        top_segment = customer_segments[0]

        insights.append(
            {
                "type": "customer_segment",
                "title": "Largest Customer Segment",
                "description": (
                    f"{top_segment['segment']} contains "
                    f"{top_segment['customers']:,} "
                    "identified customers."
                ),
            }
        )

    return insights