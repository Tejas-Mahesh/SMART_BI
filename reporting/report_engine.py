import math
import re

import pandas as pd


# ============================================================
# DATASET TYPE CONFIGURATION
# ============================================================

SUPPORTED_REPORT_TYPES = [
    "Executive",
    "Sales",
    "Customer",
    "Product",
    "Regional",
    "Marketing",
    "Financial",
    "Returns",
    "Operational",
]


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {
    "date": [
        "date",
        "order_date",
        "transaction_date",
        "invoice_date",
        "sale_date",
        "purchase_date",
        "created_date",
        "created_at",
        "timestamp",
    ],
    "sales": [
        "sales",
        "sale",
        "revenue",
        "total_sales",
        "sales_amount",
        "revenue_amount",
        "amount",
        "net_sales",
        "net_revenue",
    ],
    "profit": [
        "profit",
        "net_profit",
        "gross_profit",
        "profit_amount",
    ],
    "cost": [
        "cost",
        "total_cost",
        "cost_amount",
        "purchase_cost",
        "cogs",
    ],
    "quantity": [
        "quantity",
        "qty",
        "units",
        "units_sold",
        "order_quantity",
    ],
    "customer": [
        "customer",
        "customer_id",
        "customer_name",
        "client",
        "client_id",
    ],
    "product": [
        "product",
        "product_id",
        "product_name",
        "item",
        "item_name",
    ],
    "category": [
        "category",
        "product_category",
        "segment",
        "product_segment",
    ],
    "region": [
        "region",
        "area",
        "territory",
        "location",
        "state",
        "city",
        "zone",
    ],
    "campaign": [
        "campaign",
        "campaign_name",
        "campaign_id",
    ],
    "channel": [
        "channel",
        "sales_channel",
        "marketing_channel",
        "source",
        "medium",
    ],
    "spend": [
        "spend",
        "marketing_spend",
        "ad_spend",
        "advertising_spend",
        "campaign_spend",
    ],
    "conversion": [
        "conversion",
        "conversions",
        "conversion_count",
    ],
    "return_amount": [
        "return_amount",
        "returns",
        "return_value",
        "refund",
        "refund_amount",
    ],
    "return_reason": [
        "return_reason",
        "reason",
        "return_type",
    ],
    "order": [
        "order",
        "order_id",
        "order_number",
        "invoice",
        "invoice_id",
    ],
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_column_name(value):
    value = str(value).strip().lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    value = re.sub(
        r"_+",
        "_",
        value,
    )

    return value.strip("_")


def find_column(dataframe, aliases):
    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    normalized_aliases = [
        normalize_column_name(alias)
        for alias in aliases
    ]

    for alias in normalized_aliases:
        if alias in normalized_columns:
            return normalized_columns[alias]

    return None


def find_logical_column(dataframe, logical_name):
    aliases = COLUMN_ALIASES.get(
        logical_name,
        [],
    )

    if not aliases:
        return None

    return find_column(
        dataframe,
        aliases,
    )


def safe_float(value):
    try:
        if pd.isna(value):
            return 0.0

        value = float(value)

        if not math.isfinite(value):
            return 0.0

        return value

    except (TypeError, ValueError):
        return 0.0


def clean_dataframe(dataframe):
    if dataframe is None:
        raise ValueError(
            "No dataframe was provided."
        )

    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError(
            "Invalid dataframe provided."
        )

    dataframe = dataframe.copy()

    dataframe = dataframe.dropna(
        how="all"
    )

    return dataframe


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            json_safe(item)
            for item in value
        ]

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    return value


def round_value(value, digits=2):
    return round(
        safe_float(value),
        digits,
    )


# ============================================================
# BASIC DATA SUMMARY
# ============================================================

def calculate_data_summary(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    numeric_columns = dataframe.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_columns = dataframe.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    datetime_columns = dataframe.select_dtypes(
        include=[
            "datetime64[ns]",
            "datetime64[ns, UTC]",
        ]
    ).columns.tolist()

    missing_values = int(
        dataframe.isna()
        .sum()
        .sum()
    )

    duplicate_rows = int(
        dataframe.duplicated().sum()
    )

    return {
        "rows": int(len(dataframe)),
        "columns": int(len(dataframe.columns)),
        "numeric_columns": int(
            len(numeric_columns)
        ),
        "categorical_columns": int(
            len(categorical_columns)
        ),
        "datetime_columns": int(
            len(datetime_columns)
        ),
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
    }


# ============================================================
# KPI HELPERS
# ============================================================

def make_kpi(
    name,
    value,
    unit="",
    description="",
):
    return {
        "name": name,
        "value": json_safe(
            round_value(value)
            if isinstance(
                value,
                (int, float),
            )
            else value
        ),
        "unit": unit,
        "description": description,
    }


def numeric_sum(
    dataframe,
    logical_name,
):
    column = find_logical_column(
        dataframe,
        logical_name,
    )

    if not column:
        return None

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )

    return safe_float(
        values.sum()
    )


def numeric_mean(
    dataframe,
    logical_name,
):
    column = find_logical_column(
        dataframe,
        logical_name,
    )

    if not column:
        return None

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )

    if values.dropna().empty:
        return None

    return safe_float(
        values.mean()
    )


def unique_count(
    dataframe,
    logical_name,
):
    column = find_logical_column(
        dataframe,
        logical_name,
    )

    if not column:
        return None

    return int(
        dataframe[column]
        .dropna()
        .nunique()
    )


# ============================================================
# SECTION / CHART / INSIGHT HELPERS
# ============================================================

def make_section(
    title,
    section_type,
    data=None,
    description="",
):
    return {
        "title": title,
        "type": section_type,
        "description": description,
        "data": data or [],
    }


def make_chart(
    title,
    chart_type,
    labels,
    values,
    series_name="Value",
    description="",
):
    return {
        "title": title,
        "type": chart_type,
        "description": description,
        "labels": [
            str(label)
            for label in labels
        ],
        "values": [
            round_value(value)
            for value in values
        ],
        "series": series_name,
    }


def make_insight(
    title,
    message,
    severity="info",
    category="General",
):
    return {
        "title": title,
        "message": message,
        "severity": severity,
        "category": category,
    }


# ============================================================
# GROUPED ANALYSIS HELPER
# ============================================================

def grouped_top_values(
    dataframe,
    group_column,
    value_column,
    limit=10,
):
    if not group_column or not value_column:
        return pd.Series(
            dtype="float64"
        )

    working = dataframe.copy()

    working[value_column] = pd.to_numeric(
        working[value_column],
        errors="coerce",
    ).fillna(0)

    grouped = (
        working
        .groupby(group_column)[value_column]
        .sum()
        .sort_values(
            ascending=False
        )
        .head(limit)
    )

    return grouped


# ============================================================
# SALES REPORT
# ============================================================

def generate_sales_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    sales = numeric_sum(
        dataframe,
        "sales",
    )

    quantity = numeric_sum(
        dataframe,
        "quantity",
    )

    profit = numeric_sum(
        dataframe,
        "profit",
    )

    orders = unique_count(
        dataframe,
        "order",
    )

    customers = unique_count(
        dataframe,
        "customer",
    )

    if orders is None:
        orders = len(dataframe)

    average_order_value = (
        sales / orders
        if sales is not None
        and orders > 0
        else 0
    )

    kpis = [
        make_kpi(
            "Total Sales",
            sales or 0,
            "currency",
            "Total sales or revenue identified.",
        ),
        make_kpi(
            "Orders",
            orders,
            "count",
            "Number of unique orders identified.",
        ),
        make_kpi(
            "Units Sold",
            quantity or 0,
            "units",
            "Total quantity or units recorded.",
        ),
        make_kpi(
            "Average Order Value",
            average_order_value,
            "currency",
            "Average sales value per order.",
        ),
    ]

    if customers is not None:
        kpis.append(
            make_kpi(
                "Customers",
                customers,
                "count",
                "Unique customers identified.",
            )
        )

    if profit is not None:
        kpis.append(
            make_kpi(
                "Profit",
                profit,
                "currency",
                "Total profit identified.",
            )
        )

    sections = []
    charts = []
    insights = []

    product_column = find_logical_column(
        dataframe,
        "product",
    )

    sales_column = find_logical_column(
        dataframe,
        "sales",
    )

    if product_column and sales_column:

        top_products = grouped_top_values(
            dataframe,
            product_column,
            sales_column,
            10,
        )

        sections.append(
            make_section(
                "Top Products by Sales",
                "table",
                [
                    {
                        "name": str(index),
                        "value": round_value(value),
                    }
                    for index, value
                    in top_products.items()
                ],
                "Products ranked by total sales.",
            )
        )

        charts.append(
            make_chart(
                "Top Products by Sales",
                "bar",
                top_products.index.tolist(),
                top_products.values.tolist(),
                "Sales",
                "Top products based on total sales.",
            )
        )

        if not top_products.empty:

            top_product = str(
                top_products.index[0]
            )

            top_product_value = safe_float(
                top_products.iloc[0]
            )

            insights.append(
                make_insight(
                    "Leading Product",
                    (
                        f"{top_product} generated "
                        f"{round_value(top_product_value)} "
                        "in sales and is the highest-sales "
                        "product in the selected data."
                    ),
                    "positive",
                    "Sales",
                )
            )

    if sales is not None and profit is not None:

        if sales != 0:

            margin = (
                profit / sales
            ) * 100

            insights.append(
                make_insight(
                    "Profit Margin",
                    (
                        f"The calculated profit margin "
                        f"is {round_value(margin)}%."
                    ),
                    "info",
                    "Financial",
                )
            )

    return {
        "report_type": "Sales",
        "kpis": kpis,
        "sections": sections,
        "charts": charts,
        "insights": insights,
    }


# ============================================================
# CUSTOMER REPORT
# ============================================================

def generate_customer_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    customers = unique_count(
        dataframe,
        "customer",
    )

    regions = unique_count(
        dataframe,
        "region",
    )

    segments = unique_count(
        dataframe,
        "category",
    )

    orders = unique_count(
        dataframe,
        "order",
    )

    if customers is None:
        customers = len(dataframe)

    kpis = [
        make_kpi(
            "Total Customers",
            customers,
            "count",
            "Unique customers identified.",
        ),
        make_kpi(
            "Customer Records",
            len(dataframe),
            "records",
            "Total customer-related records.",
        ),
    ]

    if regions is not None:
        kpis.append(
            make_kpi(
                "Regions",
                regions,
                "count",
                "Distinct regions represented.",
            )
        )

    if segments is not None:
        kpis.append(
            make_kpi(
                "Segments",
                segments,
                "count",
                "Distinct customer or category segments.",
            )
        )

    if orders is not None:
        kpis.append(
            make_kpi(
                "Orders",
                orders,
                "count",
                "Unique orders associated with customers.",
            )
        )

    sections = []
    charts = []
    insights = []

    region_column = find_logical_column(
        dataframe,
        "region",
    )

    if region_column:

        regional_counts = (
            dataframe[region_column]
            .dropna()
            .astype(str)
            .value_counts()
            .head(10)
        )

        sections.append(
            make_section(
                "Customer Distribution by Region",
                "table",
                [
                    {
                        "name": str(index),
                        "value": int(value),
                    }
                    for index, value
                    in regional_counts.items()
                ],
                "Customer records grouped by region.",
            )
        )

        charts.append(
            make_chart(
                "Customer Distribution by Region",
                "bar",
                regional_counts.index.tolist(),
                regional_counts.values.tolist(),
                "Customers",
            )
        )

    return {
        "report_type": "Customer",
        "kpis": kpis,
        "sections": sections,
        "charts": charts,
        "insights": insights,
    }


# ============================================================
# PRODUCT REPORT
# ============================================================

def generate_product_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    products = unique_count(
        dataframe,
        "product",
    )

    categories = unique_count(
        dataframe,
        "category",
    )

    quantity = numeric_sum(
        dataframe,
        "quantity",
    )

    sales = numeric_sum(
        dataframe,
        "sales",
    )

    kpis = [
        make_kpi(
            "Products",
            products
            if products is not None
            else len(dataframe),
            "count",
            "Distinct products identified.",
        ),
    ]

    if categories is not None:
        kpis.append(
            make_kpi(
                "Categories",
                categories,
                "count",
                "Distinct product categories.",
            )
        )

    if quantity is not None:
        kpis.append(
            make_kpi(
                "Units",
                quantity,
                "units",
                "Total units represented.",
            )
        )

    if sales is not None:
        kpis.append(
            make_kpi(
                "Sales",
                sales,
                "currency",
                "Total sales associated with products.",
            )
        )

    sections = []
    charts = []
    insights = []

    product_column = find_logical_column(
        dataframe,
        "product",
    )

    sales_column = find_logical_column(
        dataframe,
        "sales",
    )

    if product_column and sales_column:

        top_products = grouped_top_values(
            dataframe,
            product_column,
            sales_column,
            10,
        )

        sections.append(
            make_section(
                "Top Products",
                "table",
                [
                    {
                        "name": str(index),
                        "value": round_value(value),
                    }
                    for index, value
                    in top_products.items()
                ],
                "Products ranked by sales.",
            )
        )

        charts.append(
            make_chart(
                "Top Products",
                "bar",
                top_products.index.tolist(),
                top_products.values.tolist(),
                "Sales",
            )
        )

    return {
        "report_type": "Product",
        "kpis": kpis,
        "sections": sections,
        "charts": charts,
        "insights": insights,
    }


# ============================================================
# REGIONAL REPORT
# ============================================================

def generate_regional_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    regions = unique_count(
        dataframe,
        "region",
    )

    sales = numeric_sum(
        dataframe,
        "sales",
    )

    quantity = numeric_sum(
        dataframe,
        "quantity",
    )

    kpis = [
        make_kpi(
            "Regions",
            regions
            if regions is not None
            else 0,
            "count",
            "Distinct regions identified.",
        ),
    ]

    if sales is not None:
        kpis.append(
            make_kpi(
                "Total Sales",
                sales,
                "currency",
                "Total sales across regions.",
            )
        )

    if quantity is not None:
        kpis.append(
            make_kpi(
                "Units",
                quantity,
                "units",
                "Total units across regions.",
            )
        )

    sections = []
    charts = []
    insights = []

    region_column = find_logical_column(
        dataframe,
        "region",
    )

    sales_column = find_logical_column(
        dataframe,
        "sales",
    )

    if region_column and sales_column:

        regional_sales = grouped_top_values(
            dataframe,
            region_column,
            sales_column,
            10,
        )

        sections.append(
            make_section(
                "Regional Sales",
                "table",
                [
                    {
                        "name": str(index),
                        "value": round_value(value),
                    }
                    for index, value
                    in regional_sales.items()
                ],
                "Sales grouped by region.",
            )
        )

        charts.append(
            make_chart(
                "Regional Sales",
                "bar",
                regional_sales.index.tolist(),
                regional_sales.values.tolist(),
                "Sales",
            )
        )

        if not regional_sales.empty:

            top_region = str(
                regional_sales.index[0]
            )

            insights.append(
                make_insight(
                    "Leading Region",
                    (
                        f"{top_region} has the highest "
                        "sales value among the regions "
                        "identified in the dataset."
                    ),
                    "positive",
                    "Regional",
                )
            )

    return {
        "report_type": "Regional",
        "kpis": kpis,
        "sections": sections,
        "charts": charts,
        "insights": insights,
    }


# ============================================================
# MARKETING REPORT
# ============================================================

def generate_marketing_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    spend = numeric_sum(
        dataframe,
        "spend",
    )

    conversions = numeric_sum(
        dataframe,
        "conversion",
    )

    campaigns = unique_count(
        dataframe,
        "campaign",
    )

    channels = unique_count(
        dataframe,
        "channel",
    )

    kpis = [
        make_kpi(
            "Campaigns",
            campaigns
            if campaigns is not None
            else 0,
            "count",
            "Distinct campaigns identified.",
        ),
    ]

    if spend is not None:
        kpis.append(
            make_kpi(
                "Marketing Spend",
                spend,
                "currency",
                "Total marketing spend.",
            )
        )

    if conversions is not None:
        kpis.append(
            make_kpi(
                "Conversions",
                conversions,
                "count",
                "Total conversions.",
            )
        )

    if channels is not None:
        kpis.append(
            make_kpi(
                "Channels",
                channels,
                "count",
                "Distinct marketing channels.",
            )
        )

    sections = []
    charts = []
    insights = []

    channel_column = find_logical_column(
        dataframe,
        "channel",
    )

    conversion_column = find_logical_column(
        dataframe,
        "conversion",
    )

    if channel_column and conversion_column:

        channel_data = dataframe.copy()

        channel_data[conversion_column] = (
            pd.to_numeric(
                channel_data[conversion_column],
                errors="coerce",
            )
            .fillna(0)
        )

        channel_conversions = (
            channel_data
            .groupby(channel_column)[
                conversion_column
            ]
            .sum()
            .sort_values(
                ascending=False
            )
            .head(10)
        )

        sections.append(
            make_section(
                "Conversions by Channel",
                "table",
                [
                    {
                        "name": str(index),
                        "value": round_value(value),
                    }
                    for index, value
                    in channel_conversions.items()
                ],
                "Conversions grouped by marketing channel.",
            )
        )

        charts.append(
            make_chart(
                "Conversions by Channel",
                "bar",
                channel_conversions.index.tolist(),
                channel_conversions.values.tolist(),
                "Conversions",
            )
        )

    if spend is not None and conversions:

        cost_per_conversion = (
            spend / conversions
        )

        kpis.append(
            make_kpi(
                "Cost per Conversion",
                cost_per_conversion,
                "currency",
                "Marketing spend divided by conversions.",
            )
        )

        insights.append(
            make_insight(
                "Conversion Efficiency",
                (
                    f"Average marketing cost per "
                    f"conversion is "
                    f"{round_value(cost_per_conversion)}."
                ),
                "info",
                "Marketing",
            )
        )

    return {
        "report_type": "Marketing",
        "kpis": kpis,
        "sections": sections,
        "charts": charts,
        "insights": insights,
    }


# ============================================================
# FINANCIAL REPORT
# ============================================================

def generate_financial_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    sales = numeric_sum(
        dataframe,
        "sales",
    )

    profit = numeric_sum(
        dataframe,
        "profit",
    )

    cost = numeric_sum(
        dataframe,
        "cost",
    )

    profit_margin = (
        (profit / sales) * 100
        if profit is not None
        and sales
        and sales != 0
        else 0
    )

    kpis = []

    if sales is not None:
        kpis.append(
            make_kpi(
                "Revenue",
                sales,
                "currency",
                "Total revenue identified.",
            )
        )

    if cost is not None:
        kpis.append(
            make_kpi(
                "Cost",
                cost,
                "currency",
                "Total cost identified.",
            )
        )

    if profit is not None:
        kpis.append(
            make_kpi(
                "Profit",
                profit,
                "currency",
                "Total profit identified.",
            )
        )

    if sales is not None and profit is not None:
        kpis.append(
            make_kpi(
                "Profit Margin",
                profit_margin,
                "percent",
                "Profit as a percentage of revenue.",
            )
        )

    sections = []
    charts = []
    insights = []

    financial_values = []

    if sales is not None:
        financial_values.append(
            ("Revenue", sales)
        )

    if cost is not None:
        financial_values.append(
            ("Cost", cost)
        )

    if profit is not None:
        financial_values.append(
            ("Profit", profit)
        )

    if financial_values:

        sections.append(
            make_section(
                "Financial Overview",
                "table",
                [
                    {
                        "name": name,
                        "value": round_value(value),
                    }
                    for name, value
                    in financial_values
                ],
                "Core financial totals.",
            )
        )

        charts.append(
            make_chart(
                "Financial Overview",
                "bar",
                [
                    item[0]
                    for item in financial_values
                ],
                [
                    item[1]
                    for item in financial_values
                ],
                "Amount",
            )
        )

    if sales is not None and profit is not None:

        insights.append(
            make_insight(
                "Profitability",
                (
                    f"The calculated profit margin "
                    f"is {round_value(profit_margin)}%."
                ),
                "info",
                "Financial",
            )
        )

    return {
        "report_type": "Financial",
        "kpis": kpis,
        "sections": sections,
        "charts": charts,
        "insights": insights,
    }


# ============================================================
# RETURNS REPORT
# ============================================================

def generate_returns_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    return_amount = numeric_sum(
        dataframe,
        "return_amount",
    )

    return_reasons = unique_count(
        dataframe,
        "return_reason",
    )

    orders = unique_count(
        dataframe,
        "order",
    )

    kpis = [
        make_kpi(
            "Return Records",
            len(dataframe),
            "records",
            "Total return-related records.",
        ),
    ]

    if return_amount is not None:
        kpis.append(
            make_kpi(
                "Return Amount",
                return_amount,
                "currency",
                "Total return or refund amount.",
            )
        )

    if return_reasons is not None:
        kpis.append(
            make_kpi(
                "Return Reasons",
                return_reasons,
                "count",
                "Distinct return reasons.",
            )
        )

    if orders is not None:
        kpis.append(
            make_kpi(
                "Orders",
                orders,
                "count",
                "Unique orders associated with returns.",
            )
        )

    sections = []
    charts = []
    insights = []

    reason_column = find_logical_column(
        dataframe,
        "return_reason",
    )

    if reason_column:

        reasons = (
            dataframe[reason_column]
            .dropna()
            .astype(str)
            .value_counts()
            .head(10)
        )

        sections.append(
            make_section(
                "Return Reasons",
                "table",
                [
                    {
                        "name": str(index),
                        "value": int(value),
                    }
                    for index, value
                    in reasons.items()
                ],
                "Return records grouped by reason.",
            )
        )

        charts.append(
            make_chart(
                "Return Reasons",
                "bar",
                reasons.index.tolist(),
                reasons.values.tolist(),
                "Returns",
            )
        )

        if not reasons.empty:

            top_reason = str(
                reasons.index[0]
            )

            insights.append(
                make_insight(
                    "Most Common Return Reason",
                    (
                        f"{top_reason} is the most "
                        "frequently recorded return reason."
                    ),
                    "warning",
                    "Returns",
                )
            )

    return {
        "report_type": "Returns",
        "kpis": kpis,
        "sections": sections,
        "charts": charts,
        "insights": insights,
    }


# ============================================================
# EXECUTIVE REPORT
# ============================================================

def generate_executive_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    summary = calculate_data_summary(
        dataframe
    )

    sales = numeric_sum(
        dataframe,
        "sales",
    )

    profit = numeric_sum(
        dataframe,
        "profit",
    )

    quantity = numeric_sum(
        dataframe,
        "quantity",
    )

    customers = unique_count(
        dataframe,
        "customer",
    )

    orders = unique_count(
        dataframe,
        "order",
    )

    if orders is None:
        orders = len(dataframe)

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    kpis = [
        make_kpi(
            "Records",
            summary["rows"],
            "records",
            "Total records in the selected dataset version.",
        ),
        make_kpi(
            "Columns",
            summary["columns"],
            "columns",
            "Total columns in the selected dataset version.",
        ),
        make_kpi(
            "Orders",
            orders,
            "count",
            "Orders identified in the selected dataset.",
        ),
    ]

    if sales is not None:
        kpis.append(
            make_kpi(
                "Sales",
                sales,
                "currency",
                "Total sales identified.",
            )
        )

    if profit is not None:
        kpis.append(
            make_kpi(
                "Profit",
                profit,
                "currency",
                "Total profit identified.",
            )
        )

    if quantity is not None:
        kpis.append(
            make_kpi(
                "Units",
                quantity,
                "units",
                "Total quantity or units identified.",
            )
        )

    if customers is not None:
        kpis.append(
            make_kpi(
                "Customers",
                customers,
                "count",
                "Unique customers identified.",
            )
        )

    # --------------------------------------------------------
    # EXECUTIVE SUMMARY
    # --------------------------------------------------------

    executive_summary = {
        "title": "Executive Summary",
        "text": (
            f"The selected dataset contains "
            f"{summary['rows']} records across "
            f"{summary['columns']} columns."
        ),
        "data_quality": {
            "missing_values": summary[
                "missing_values"
            ],
            "duplicate_rows": summary[
                "duplicate_rows"
            ],
        },
    }

    # Add useful business wording when metrics exist.

    summary_parts = []

    if sales is not None:
        summary_parts.append(
            f"total sales are {round_value(sales)}"
        )

    if profit is not None:
        summary_parts.append(
            f"total profit is {round_value(profit)}"
        )

    if customers is not None:
        summary_parts.append(
            f"{customers} unique customers are represented"
        )

    if summary_parts:
        executive_summary["text"] += (
            " The dataset indicates "
            + ", ".join(summary_parts)
            + "."
        )

    # --------------------------------------------------------
    # DETAILED ANALYSIS
    # --------------------------------------------------------

    sections = []

    sections.append(
        make_section(
            "Dataset Overview",
            "summary",
            [
                {
                    "metric": "Rows",
                    "value": summary["rows"],
                },
                {
                    "metric": "Columns",
                    "value": summary["columns"],
                },
                {
                    "metric": "Numeric Columns",
                    "value": summary[
                        "numeric_columns"
                    ],
                },
                {
                    "metric": "Categorical Columns",
                    "value": summary[
                        "categorical_columns"
                    ],
                },
                {
                    "metric": "Datetime Columns",
                    "value": summary[
                        "datetime_columns"
                    ],
                },
                {
                    "metric": "Missing Values",
                    "value": summary[
                        "missing_values"
                    ],
                },
                {
                    "metric": "Duplicate Rows",
                    "value": summary[
                        "duplicate_rows"
                    ],
                },
            ],
            "Structural overview of the selected dataset.",
        )
    )

    # --------------------------------------------------------
    # PRODUCT ANALYSIS
    # --------------------------------------------------------

    product_column = find_logical_column(
        dataframe,
        "product",
    )

    sales_column = find_logical_column(
        dataframe,
        "sales",
    )

    charts = []
    insights = []

    if product_column and sales_column:

        top_products = grouped_top_values(
            dataframe,
            product_column,
            sales_column,
            10,
        )

        sections.append(
            make_section(
                "Top Products by Sales",
                "table",
                [
                    {
                        "name": str(index),
                        "value": round_value(value),
                    }
                    for index, value
                    in top_products.items()
                ],
                "Top products ranked by sales.",
            )
        )

        charts.append(
            make_chart(
                "Top Products by Sales",
                "bar",
                top_products.index.tolist(),
                top_products.values.tolist(),
                "Sales",
            )
        )

        if not top_products.empty:

            top_product = str(
                top_products.index[0]
            )

            insights.append(
                make_insight(
                    "Top Performing Product",
                    (
                        f"{top_product} has the highest "
                        "sales value among the products "
                        "identified."
                    ),
                    "positive",
                    "Product",
                )
            )

    # --------------------------------------------------------
    # REGIONAL ANALYSIS
    # --------------------------------------------------------

    region_column = find_logical_column(
        dataframe,
        "region",
    )

    if region_column and sales_column:

        regional_sales = grouped_top_values(
            dataframe,
            region_column,
            sales_column,
            10,
        )

        sections.append(
            make_section(
                "Regional Performance",
                "table",
                [
                    {
                        "name": str(index),
                        "value": round_value(value),
                    }
                    for index, value
                    in regional_sales.items()
                ],
                "Sales grouped by region.",
            )
        )

        charts.append(
            make_chart(
                "Regional Performance",
                "bar",
                regional_sales.index.tolist(),
                regional_sales.values.tolist(),
                "Sales",
            )
        )

        if not regional_sales.empty:

            top_region = str(
                regional_sales.index[0]
            )

            insights.append(
                make_insight(
                    "Leading Region",
                    (
                        f"{top_region} has the highest "
                        "sales value among the regions "
                        "identified."
                    ),
                    "positive",
                    "Regional",
                )
            )

    # --------------------------------------------------------
    # FINANCIAL ANALYSIS
    # --------------------------------------------------------

    if sales is not None and profit is not None:

        profit_margin = (
            (profit / sales) * 100
            if sales != 0
            else 0
        )

        sections.append(
            make_section(
                "Financial Performance",
                "table",
                [
                    {
                        "metric": "Sales",
                        "value": round_value(
                            sales
                        ),
                    },
                    {
                        "metric": "Profit",
                        "value": round_value(
                            profit
                        ),
                    },
                    {
                        "metric": "Profit Margin",
                        "value": round_value(
                            profit_margin
                        ),
                    },
                ],
                "Financial indicators available in the dataset.",
            )
        )

        charts.append(
            make_chart(
                "Sales vs Profit",
                "bar",
                [
                    "Sales",
                    "Profit",
                ],
                [
                    sales,
                    profit,
                ],
                "Amount",
            )
        )

        insights.append(
            make_insight(
                "Profitability",
                (
                    f"The calculated profit margin "
                    f"is {round_value(profit_margin)}%."
                ),
                "info",
                "Financial",
            )
        )

    # --------------------------------------------------------
    # DATA QUALITY INSIGHT
    # --------------------------------------------------------

    if summary["missing_values"] > 0:

        insights.append(
            make_insight(
                "Missing Values Detected",
                (
                    f"The selected dataset contains "
                    f"{summary['missing_values']} "
                    "missing values."
                ),
                "warning",
                "Data Quality",
            )
        )
    else:

        insights.append(
            make_insight(
                "Data Completeness",
                "No missing values were identified in the selected dataset.",
                "positive",
                "Data Quality",
            )
        )

    if summary["duplicate_rows"] > 0:

        insights.append(
            make_insight(
                "Duplicate Records",
                (
                    f"{summary['duplicate_rows']} "
                    "duplicate rows were identified."
                ),
                "warning",
                "Data Quality",
            )
        )

    # --------------------------------------------------------
    # EXECUTIVE REPORT
    # --------------------------------------------------------

    return {
        "report_type": "Executive",

        "summary": executive_summary,

        "kpis": kpis,

        "sections": sections,

        "charts": charts,

        "insights": insights,
    }


# ============================================================
# OPERATIONAL REPORT
# ============================================================

def generate_operational_report(dataframe):
    dataframe = clean_dataframe(
        dataframe
    )

    summary = calculate_data_summary(
        dataframe
    )

    kpis = [
        make_kpi(
            "Records",
            summary["rows"],
            "records",
            "Total records available.",
        ),
        make_kpi(
            "Columns",
            summary["columns"],
            "columns",
            "Total columns available.",
        ),
        make_kpi(
            "Missing Values",
            summary["missing_values"],
            "values",
            "Missing values identified.",
        ),
        make_kpi(
            "Duplicate Rows",
            summary["duplicate_rows"],
            "rows",
            "Duplicate rows identified.",
        ),
    ]

    sections = [
        make_section(
            "Data Quality Overview",
            "table",
            [
                {
                    "metric": "Rows",
                    "value": summary["rows"],
                },
                {
                    "metric": "Columns",
                    "value": summary["columns"],
                },
                {
                    "metric": "Missing Values",
                    "value": summary["missing_values"],
                },
                {
                    "metric": "Duplicate Rows",
                    "value": summary["duplicate_rows"],
                },
            ],
            "Operational data-quality indicators.",
        )
    ]

    insights = []

    if summary["missing_values"] > 0:
        insights.append(
            make_insight(
                "Missing Data",
                (
                    f"{summary['missing_values']} "
                    "missing values were identified."
                ),
                "warning",
                "Data Quality",
            )
        )

    if summary["duplicate_rows"] > 0:
        insights.append(
            make_insight(
                "Duplicate Data",
                (
                    f"{summary['duplicate_rows']} "
                    "duplicate rows were identified."
                ),
                "warning",
                "Data Quality",
            )
        )

    return {
        "report_type": "Operational",
        "kpis": kpis,
        "sections": sections,
        "charts": [],
        "insights": insights,
    }


# ============================================================
# GENERIC REPORT DISPATCHER
# ============================================================

REPORT_GENERATORS = {
    "Executive": generate_executive_report,
    "Sales": generate_sales_report,
    "Customer": generate_customer_report,
    "Product": generate_product_report,
    "Regional": generate_regional_report,
    "Marketing": generate_marketing_report,
    "Financial": generate_financial_report,
    "Returns": generate_returns_report,
    "Operational": generate_operational_report,
}


# ============================================================
# AUTOMATED REPORT ENGINE
# ============================================================

def generate_automated_report(
    dataframe,
    report_type="Executive",
):
    """
    Generate a complete structured automated report
    from a cleaned DatasetVersion dataframe.
    """

    if report_type not in REPORT_GENERATORS:
        raise ValueError(
            f"Unsupported report type: {report_type}"
        )

    dataframe = clean_dataframe(
        dataframe
    )

    generator = REPORT_GENERATORS[
        report_type
    ]

    result = generator(
        dataframe
    )

    # --------------------------------------------------------
    # COMMON SUMMARY
    # --------------------------------------------------------

    data_summary = calculate_data_summary(
        dataframe
    )

    # Some report generators already provide
    # a human-readable executive summary.
    # Preserve it rather than replacing it.

    if "summary" not in result:
        result["summary"] = data_summary

    # --------------------------------------------------------
    # GUARANTEE STRUCTURE
    # --------------------------------------------------------

    result.setdefault(
        "kpis",
        [],
    )

    result.setdefault(
        "sections",
        [],
    )

    result.setdefault(
        "charts",
        [],
    )

    result.setdefault(
        "insights",
        [],
    )

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    result["metadata"] = {
        "report_type": report_type,
        "row_count": int(
            len(dataframe)
        ),
        "column_count": int(
            len(dataframe.columns)
        ),
        "columns": [
            str(column)
            for column in dataframe.columns
        ],
        "numeric_columns": int(
            data_summary[
                "numeric_columns"
            ]
        ),
        "categorical_columns": int(
            data_summary[
                "categorical_columns"
            ]
        ),
        "datetime_columns": int(
            data_summary[
                "datetime_columns"
            ]
        ),
        "missing_values": int(
            data_summary[
                "missing_values"
            ]
        ),
        "duplicate_rows": int(
            data_summary[
                "duplicate_rows"
            ]
        ),
    }

    # --------------------------------------------------------
    # FINAL JSON-SAFE RESULT
    # --------------------------------------------------------

    return json_safe(
        result
    )


# ============================================================
# PUBLIC WRAPPER
# ============================================================

def generate_report(
    dataframe,
    report_type="Executive",
):
    """
    Public reporting engine entry point.
    """

    return generate_automated_report(
        dataframe=dataframe,
        report_type=report_type,
    )