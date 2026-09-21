import os

import pandas as pd


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
    ],
    "sales": [
        "sales",
        "sale",
        "revenue",
        "total_sales",
        "total_revenue",
        "amount",
        "sales_amount",
        "revenue_amount",
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
        "unit_cost",
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
        "product_type",
        "segment",
    ],
    "region": [
        "region",
        "area",
        "territory",
        "location",
        "state",
        "city",
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
    ],
    "spend": [
        "spend",
        "marketing_spend",
        "ad_spend",
        "advertising_spend",
        "cost_of_marketing",
    ],
    "conversions": [
        "conversions",
        "conversion",
        "converted",
    ],
    "return_amount": [
        "return_amount",
        "returned_amount",
        "refund",
        "refund_amount",
        "returns",
    ],
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_column_name(column):
    """
    Converts a dataframe column name into a normalized format
    for reliable matching.
    """
    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_column(dataframe, logical_name):
    """
    Finds a dataframe column using the aliases defined above.
    """

    if dataframe is None or dataframe.empty:
        return None

    normalized_columns = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    aliases = COLUMN_ALIASES.get(logical_name, [])

    for alias in aliases:
        normalized_alias = normalize_column_name(alias)

        if normalized_alias in normalized_columns:
            return normalized_columns[normalized_alias]

    return None


def safe_float(value, default=0.0):
    """
    Safely converts a value into float.
    """

    try:
        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def percentage(value):
    """
    Converts a numeric value into a bounded percentage.
    """

    return round(
        max(0.0, min(100.0, safe_float(value))),
        2,
    )


def calculate_percentage_change(current, previous):
    """
    Calculates percentage change between two values.
    """

    current = safe_float(current)
    previous = safe_float(previous)

    if previous == 0:
        if current > 0:
            return 100.0

        return 0.0

    return round(
        ((current - previous) / abs(previous)) * 100,
        2,
    )


def clean_numeric_series(series):
    """
    Converts a pandas series to numeric values safely.
    """

    return pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0)


# ============================================================
# DATASET ANALYSIS
# ============================================================

def analyze_dataset(dataframe):
    """
    Performs the core analysis used by the recommendation engine.

    The engine is intentionally dataset-driven. It only generates
    recommendations when the required columns are available.
    """

    if dataframe is None:
        raise ValueError("No dataframe was provided.")

    if dataframe.empty:
        return {
            "recommendations": [],
            "summary": {
                "total_records": 0,
                "recommendations_count": 0,
            },
        }

    dataframe = dataframe.copy()

    sales_column = find_column(dataframe, "sales")
    profit_column = find_column(dataframe, "profit")
    quantity_column = find_column(dataframe, "quantity")
    customer_column = find_column(dataframe, "customer")
    product_column = find_column(dataframe, "product")
    category_column = find_column(dataframe, "category")
    region_column = find_column(dataframe, "region")
    spend_column = find_column(dataframe, "spend")
    return_column = find_column(dataframe, "return_amount")

    recommendations = []

    # --------------------------------------------------------
    # SALES ANALYSIS
    # --------------------------------------------------------

    if sales_column:
        sales = clean_numeric_series(
            dataframe[sales_column]
        )

        total_sales = sales.sum()

        if total_sales > 0:
            average_sales = sales.mean()

            low_sales_records = int(
                (sales < average_sales * 0.5).sum()
            )

            if low_sales_records > 0:
                recommendations.append(
                    {
                        "title": "Review Low-Value Sales Records",
                        "category": "Sales",
                        "description": (
                            f"{low_sales_records:,} records are "
                            "significantly below the average sales value."
                        ),
                        "supporting_insight": (
                            f"Average sales value is "
                            f"{average_sales:,.2f}."
                        ),
                        "recommended_action": (
                            "Review the low-value transactions to "
                            "identify pricing, product mix, or "
                            "customer-level opportunities."
                        ),
                        "expected_outcome": (
                            "Improved transaction value and better "
                            "identification of revenue opportunities."
                        ),
                        "priority": "Medium",
                        "impact_level": "Medium",
                        "confidence": 75,
                    }
                )

    # --------------------------------------------------------
    # PROFIT ANALYSIS
    # --------------------------------------------------------

    if profit_column:
        profit = clean_numeric_series(
            dataframe[profit_column]
        )

        total_profit = profit.sum()

        negative_profit_records = int(
            (profit < 0).sum()
        )

        if negative_profit_records > 0:
            negative_profit_percentage = (
                negative_profit_records
                / max(len(dataframe), 1)
            ) * 100

            priority = (
                "High"
                if negative_profit_percentage >= 10
                else "Medium"
            )

            recommendations.append(
                {
                    "title": "Investigate Negative-Profit Records",
                    "category": "Financial",
                    "description": (
                        f"{negative_profit_records:,} records "
                        "have negative profit values."
                    ),
                    "supporting_insight": (
                        f"Negative-profit records represent "
                        f"{negative_profit_percentage:.2f}% "
                        "of the dataset."
                    ),
                    "recommended_action": (
                        "Review pricing, costs, discounts, returns, "
                        "and product-level profitability for these records."
                    ),
                    "expected_outcome": (
                        "Reduction of loss-making transactions "
                        "and improved profitability."
                    ),
                    "priority": priority,
                    "impact_level": "High",
                    "confidence": 90,
                }
            )

    # --------------------------------------------------------
    # PRODUCT ANALYSIS
    # --------------------------------------------------------

    if product_column and sales_column:

        product_sales = (
            dataframe.groupby(product_column)[sales_column]
            .apply(
                lambda series: clean_numeric_series(series).sum()
            )
            .sort_values(ascending=False)
        )

        if len(product_sales) >= 2:

            top_product = product_sales.index[0]
            top_value = safe_float(product_sales.iloc[0])

            bottom_product = product_sales.index[-1]
            bottom_value = safe_float(product_sales.iloc[-1])

            if top_value > 0:

                recommendations.append(
                    {
                        "title": "Review Product Sales Concentration",
                        "category": "Product",
                        "description": (
                            f"Product '{top_product}' generates "
                            f"{top_value:,.2f} in recorded sales."
                        ),
                        "supporting_insight": (
                            f"The lowest-sales product in the "
                            f"available product grouping is "
                            f"'{bottom_product}' with "
                            f"{bottom_value:,.2f}."
                        ),
                        "recommended_action": (
                            "Compare high- and low-performing products "
                            "and review pricing, availability, promotion, "
                            "and product mix."
                        ),
                        "expected_outcome": (
                            "Better allocation of commercial attention "
                            "toward products with identifiable growth potential."
                        ),
                        "priority": "Medium",
                        "impact_level": "Medium",
                        "confidence": 80,
                    }
                )

    # --------------------------------------------------------
    # REGIONAL ANALYSIS
    # --------------------------------------------------------

    if region_column and sales_column:

        regional_sales = (
            dataframe.groupby(region_column)[sales_column]
            .apply(
                lambda series: clean_numeric_series(series).sum()
            )
            .sort_values(ascending=False)
        )

        if len(regional_sales) >= 2:

            top_region = regional_sales.index[0]
            top_region_value = safe_float(
                regional_sales.iloc[0]
            )

            bottom_region = regional_sales.index[-1]
            bottom_region_value = safe_float(
                regional_sales.iloc[-1]
            )

            if top_region_value > 0:

                recommendations.append(
                    {
                        "title": "Review Regional Performance",
                        "category": "Regional",
                        "description": (
                            f"'{top_region}' records the highest "
                            f"sales contribution at "
                            f"{top_region_value:,.2f}."
                        ),
                        "supporting_insight": (
                            f"'{bottom_region}' records "
                            f"{bottom_region_value:,.2f}."
                        ),
                        "recommended_action": (
                            "Compare regional demand, customer mix, "
                            "distribution, pricing, and marketing activity "
                            "to identify expansion opportunities."
                        ),
                        "expected_outcome": (
                            "Improved regional resource allocation "
                            "and identification of underdeveloped markets."
                        ),
                        "priority": "Medium",
                        "impact_level": "Medium",
                        "confidence": 78,
                    }
                )

    # --------------------------------------------------------
    # MARKETING ANALYSIS
    # --------------------------------------------------------

    if spend_column:
        conversions_column = find_column(
            dataframe,
            "conversions",
        )

        if conversions_column:
            spend = clean_numeric_series(
                dataframe[spend_column]
            )

            conversions = clean_numeric_series(
                dataframe[conversions_column]
            )

            total_spend = spend.sum()
            total_conversions = conversions.sum()

            if total_spend > 0:

                conversion_efficiency = (
                    total_conversions / total_spend
                )

                recommendations.append(
                    {
                        "title": "Review Marketing Conversion Efficiency",
                        "category": "Marketing",
                        "description": (
                            f"Recorded marketing spend is "
                            f"{total_spend:,.2f} with "
                            f"{total_conversions:,.0f} conversions."
                        ),
                        "supporting_insight": (
                            f"Overall conversions per unit of spend: "
                            f"{conversion_efficiency:.4f}."
                        ),
                        "recommended_action": (
                            "Compare campaigns and channels using "
                            "spend-to-conversion efficiency before "
                            "reallocating marketing resources."
                        ),
                        "expected_outcome": (
                            "More informed marketing budget allocation "
                            "and improved conversion efficiency."
                        ),
                        "priority": "Medium",
                        "impact_level": "Medium",
                        "confidence": 72,
                    }
                )

    # --------------------------------------------------------
    # RETURNS ANALYSIS
    # --------------------------------------------------------

    if return_column and sales_column:

        returns = clean_numeric_series(
            dataframe[return_column]
        )

        sales = clean_numeric_series(
            dataframe[sales_column]
        )

        total_returns = returns.sum()
        total_sales = sales.sum()

        if total_sales > 0 and total_returns > 0:

            return_ratio = (
                total_returns / total_sales
            ) * 100

            if return_ratio >= 5:

                recommendations.append(
                    {
                        "title": "Investigate Elevated Return Value",
                        "category": "Returns",
                        "description": (
                            f"Return value represents "
                            f"{return_ratio:.2f}% of recorded sales."
                        ),
                        "supporting_insight": (
                            f"Total recorded returns: "
                            f"{total_returns:,.2f}."
                        ),
                        "recommended_action": (
                            "Review return reasons, products, regions, "
                            "and customer segments to identify the "
                            "largest return drivers."
                        ),
                        "expected_outcome": (
                            "Lower return-related losses and improved "
                            "customer and product performance."
                        ),
                        "priority": "High",
                        "impact_level": "High",
                        "confidence": 88,
                    }
                )

    # --------------------------------------------------------
    # CUSTOMER ANALYSIS
    # --------------------------------------------------------

    if customer_column and sales_column:

        customer_count = (
            dataframe[customer_column]
            .dropna()
            .nunique()
        )

        total_sales = clean_numeric_series(
            dataframe[sales_column]
        ).sum()

        if customer_count > 0 and total_sales > 0:

            average_customer_value = (
                total_sales / customer_count
            )

            recommendations.append(
                {
                    "title": "Review Customer Value Distribution",
                    "category": "Customer",
                    "description": (
                        f"The dataset contains approximately "
                        f"{customer_count:,} unique customers."
                    ),
                    "supporting_insight": (
                        f"Average recorded sales per unique customer "
                        f"are approximately "
                        f"{average_customer_value:,.2f}."
                    ),
                    "recommended_action": (
                        "Segment customers by contribution and identify "
                        "high-value, low-value, and growth-potential groups "
                        "for targeted actions."
                    ),
                    "expected_outcome": (
                        "Improved customer value management and "
                        "more targeted commercial decisions."
                    ),
                    "priority": "Medium",
                    "impact_level": "High",
                    "confidence": 82,
                }
            )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = {
        "total_records": int(len(dataframe)),
        "recommendations_count": len(recommendations),
        "categories_detected": sorted(
            list(
                {
                    recommendation["category"]
                    for recommendation in recommendations
                }
            )
        ),
    }

    return {
        "recommendations": recommendations,
        "summary": summary,
    }


# ============================================================
# PUBLIC ENGINE FUNCTION
# ============================================================

def generate_recommendations(dataframe):
    """
    Public entry point for the Recommendation Engine.
    """

    result = analyze_dataset(dataframe)

    return result