# analytics/metrics/marketing_metrics.py

import pandas as pd


# ============================================================
# REQUIRED COLUMNS
# ============================================================

CORE_REQUIRED_COLUMNS = [
    "Campaign_ID",
]


# ============================================================
# OPTIONAL COLUMNS
# ============================================================

OPTIONAL_COLUMNS = [
    "Date",
    "Campaign_ID",
    "Campaign_Name",
    "Campaign",
    "Channel",
    "Marketing_Channel",
    "Campaign_Type",
    "Region",
    "Impressions",
    "Clicks",
    "CTR",
    "Conversions",
    "Conversion_Rate",
    "Leads",
    "Orders",
    "Sales_Amount",
    "Sales",
    "Revenue",
    "Cost",
    "Marketing_Cost",
    "Ad_Spend",
    "Spend",
    "Profit",
    "Profit_Amount",
    "ROI",
    "ROAS",
    "Customers_Acquired",
    "New_Customers",
    "Reach",
    "Engagements",
    "Engagement_Rate",
]


# ============================================================
# COLUMN ALIASES
# ============================================================

COLUMN_ALIASES = {

    "Date": [
        "Date",
        "Campaign_Date",
        "CampaignDate",
        "Marketing_Date",
        "MarketingDate",
        "Start_Date",
        "StartDate",
    ],

    "Campaign_ID": [
        "Campaign_ID",
        "CampaignID",
        "Campaign_Id",
        "Campaign_Number",
        "CampaignNumber",
        "Campaign_Code",
        "CampaignCode",
    ],

    "Campaign_Name": [
        "Campaign_Name",
        "CampaignName",
        "Campaign",
        "Campaign_Title",
        "CampaignTitle",
    ],

    "Channel": [
        "Channel",
        "Marketing_Channel",
        "MarketingChannel",
        "Sales_Channel",
        "SalesChannel",
        "Platform",
        "Source",
    ],

    "Campaign_Type": [
        "Campaign_Type",
        "CampaignType",
        "Marketing_Type",
        "MarketingType",
        "Type",
    ],

    "Region": [
        "Region",
        "Region_Name",
        "Regional_Name",
        "Area",
        "Territory",
        "Zone",
    ],

    "Impressions": [
        "Impressions",
        "Impression",
        "Views",
        "Ad_Impressions",
        "AdImpressions",
    ],

    "Clicks": [
        "Clicks",
        "Click",
        "Total_Clicks",
        "TotalClicks",
        "Ad_Clicks",
        "AdClicks",
    ],

    "CTR": [
        "CTR",
        "Click_Through_Rate",
        "ClickThroughRate",
        "Click_Rate",
        "ClickRate",
    ],

    "Conversions": [
        "Conversions",
        "Conversion",
        "Total_Conversions",
        "TotalConversions",
        "Converted",
    ],

    "Conversion_Rate": [
        "Conversion_Rate",
        "ConversionRate",
        "CVR",
        "Conversion_Percentage",
        "ConversionPercentage",
    ],

    "Leads": [
        "Leads",
        "Lead",
        "Total_Leads",
        "TotalLeads",
        "Generated_Leads",
        "GeneratedLeads",
    ],

    "Orders": [
        "Orders",
        "Order_Count",
        "OrderCount",
        "Total_Orders",
        "TotalOrders",
    ],

    "Sales_Amount": [
        "Sales_Amount",
        "SalesAmount",
        "Sales",
        "Revenue",
        "Total_Sales",
        "TotalSales",
        "Revenue_Amount",
        "RevenueAmount",
        "Order_Value",
        "OrderValue",
    ],

    "Cost": [
        "Cost",
        "Marketing_Cost",
        "MarketingCost",
        "Ad_Spend",
        "AdSpend",
        "Spend",
        "Campaign_Cost",
        "CampaignCost",
        "Advertising_Cost",
        "AdvertisingCost",
    ],

    "Profit": [
        "Profit",
        "Profit_Amount",
        "ProfitAmount",
        "Net_Profit",
        "NetProfit",
        "Campaign_Profit",
        "CampaignProfit",
    ],

    "ROI": [
        "ROI",
        "Return_On_Investment",
        "ReturnOnInvestment",
        "Marketing_ROI",
        "MarketingROI",
    ],

    "ROAS": [
        "ROAS",
        "Return_On_Ad_Spend",
        "ReturnOnAdSpend",
        "Marketing_ROAS",
        "MarketingROAS",
    ],

    "Customers_Acquired": [
        "Customers_Acquired",
        "CustomersAcquired",
        "Acquired_Customers",
        "AcquiredCustomers",
        "New_Customers",
        "NewCustomers",
    ],

    "Reach": [
        "Reach",
        "Audience_Reach",
        "AudienceReach",
        "Unique_Reach",
        "UniqueReach",
    ],

    "Engagements": [
        "Engagements",
        "Engagement",
        "Total_Engagements",
        "TotalEngagements",
        "Interactions",
        "Interactions_Count",
    ],

    "Engagement_Rate": [
        "Engagement_Rate",
        "EngagementRate",
        "Engagement_Percentage",
        "EngagementPercentage",
    ],
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def normalize_column_name(column):
    """
    Normalize a column name so that common variations can
    be matched reliably.
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
    Resolve canonical Marketing Intelligence fields against
    the actual dataframe column names.

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

            normalized_alias = (
                normalize_column_name(alias)
            )

            actual_column = (
                normalized_columns.get(
                    normalized_alias
                )
            )

            if actual_column is not None:

                resolved[canonical_name] = (
                    actual_column
                )

                break

    return resolved


def prepare_marketing_dataframe(dataframe):
    """
    Prepare the Marketing dataframe and validate required
    columns.

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


def get_numeric_series(
    dataframe,
    column,
):
    """
    Convert a dataframe column to numeric values.

    Invalid values become NaN.
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


def clean_text_values(
    dataframe,
    column,
    unknown_label="Unknown",
):
    """
    Clean a text/category column.

    Missing or blank values become the supplied unknown label.
    """

    if (
        dataframe is None
        or column is None
        or column not in dataframe.columns
    ):

        return None

    values = (
        dataframe[column]
        .astype("string")
        .str.strip()
    )

    values = values.fillna(
        unknown_label
    )

    values = values.replace(
        {
            "": unknown_label,
            "nan": unknown_label,
            "None": unknown_label,
            "<NA>": unknown_label,
        }
    )

    return values


def get_sales_column(
    resolved_columns,
):
    return resolved_columns.get(
        "Sales_Amount"
    )


def get_cost_column(
    resolved_columns,
):
    return resolved_columns.get(
        "Cost"
    )


def get_profit_column(
    resolved_columns,
):
    return resolved_columns.get(
        "Profit"
    )


# ============================================================
# CORE MARKETING METRICS
# ============================================================

def calculate_marketing_metrics(
    dataframe,
):
    """
    Calculate the main Marketing Intelligence KPIs.

    Unsupported metrics return None instead of fabricated
    zero values.
    """

    if dataframe is None or dataframe.empty:

        return {
            "total_campaigns": 0,
            "total_impressions": None,
            "total_clicks": None,
            "total_conversions": None,
            "total_leads": None,
            "total_sales": None,
            "total_marketing_cost": None,
            "total_profit": None,
            "average_ctr": None,
            "conversion_rate": None,
            "cost_per_click": None,
            "cost_per_conversion": None,
            "cost_per_lead": None,
            "roi": None,
            "roas": None,
            "customers_acquired": None,
            "average_campaign_sales": None,
            "top_campaign": None,
            "top_campaign_sales": None,
            "marketing_growth": None,
        }

    resolved_columns = resolve_columns(
        dataframe
    )

    campaign_column = resolved_columns.get(
        "Campaign_ID"
    )

    if campaign_column:

        campaign_values = dataframe[
            campaign_column
        ].dropna()

        total_campaigns = int(
            campaign_values.nunique()
        )

    else:

        total_campaigns = 0


    impressions_column = resolved_columns.get(
        "Impressions"
    )

    clicks_column = resolved_columns.get(
        "Clicks"
    )

    conversions_column = resolved_columns.get(
        "Conversions"
    )

    leads_column = resolved_columns.get(
        "Leads"
    )

    sales_column = get_sales_column(
        resolved_columns
    )

    cost_column = get_cost_column(
        resolved_columns
    )

    profit_column = get_profit_column(
        resolved_columns
    )

    customers_column = resolved_columns.get(
        "Customers_Acquired"
    )


    total_impressions = None
    total_clicks = None
    total_conversions = None
    total_leads = None
    total_sales = None
    total_cost = None
    total_profit = None
    customers_acquired = None

    average_ctr = None
    conversion_rate = None
    cost_per_click = None
    cost_per_conversion = None
    cost_per_lead = None
    roi = None
    roas = None
    average_campaign_sales = None

    top_campaign = None
    top_campaign_sales = None


    # ========================================================
    # IMPRESSIONS
    # ========================================================

    if impressions_column:

        impressions = get_numeric_series(
            dataframe,
            impressions_column,
        )

        if impressions is not None:

            valid = impressions.dropna()

            if not valid.empty:

                total_impressions = float(
                    valid.sum()
                )


    # ========================================================
    # CLICKS
    # ========================================================

    if clicks_column:

        clicks = get_numeric_series(
            dataframe,
            clicks_column,
        )

        if clicks is not None:

            valid = clicks.dropna()

            if not valid.empty:

                total_clicks = float(
                    valid.sum()
                )


    # ========================================================
    # CONVERSIONS
    # ========================================================

    if conversions_column:

        conversions = get_numeric_series(
            dataframe,
            conversions_column,
        )

        if conversions is not None:

            valid = conversions.dropna()

            if not valid.empty:

                total_conversions = float(
                    valid.sum()
                )


    # ========================================================
    # LEADS
    # ========================================================

    if leads_column:

        leads = get_numeric_series(
            dataframe,
            leads_column,
        )

        if leads is not None:

            valid = leads.dropna()

            if not valid.empty:

                total_leads = float(
                    valid.sum()
                )


    # ========================================================
    # SALES
    # ========================================================

    if sales_column:

        sales = get_numeric_series(
            dataframe,
            sales_column,
        )

        if sales is not None:

            valid = sales.dropna()

            if not valid.empty:

                total_sales = float(
                    valid.sum()
                )

                if total_campaigns > 0:

                    average_campaign_sales = (
                        float(
                            total_sales
                            / total_campaigns
                        )
                    )


                if campaign_column:

                    campaign_series = (
                        clean_text_values(
                            dataframe,
                            campaign_column,
                        )
                    )

                    campaign_sales = (
                        pd.DataFrame(
                            {
                                "Campaign":
                                    campaign_series,

                                "Sales":
                                    sales,
                            }
                        )
                        .dropna(
                            subset=["Sales"]
                        )
                        .groupby(
                            "Campaign",
                            dropna=False,
                        )["Sales"]
                        .sum()
                        .sort_values(
                            ascending=False
                        )
                    )

                    if not campaign_sales.empty:

                        top_campaign = str(
                            campaign_sales.index[0]
                        )

                        top_campaign_sales = float(
                            campaign_sales.iloc[0]
                        )


    # ========================================================
    # COST
    # ========================================================

    if cost_column:

        cost = get_numeric_series(
            dataframe,
            cost_column,
        )

        if cost is not None:

            valid = cost.dropna()

            if not valid.empty:

                total_cost = float(
                    valid.sum()
                )


    # ========================================================
    # PROFIT
    # ========================================================

    if profit_column:

        profit = get_numeric_series(
            dataframe,
            profit_column,
        )

        if profit is not None:

            valid = profit.dropna()

            if not valid.empty:

                total_profit = float(
                    valid.sum()
                )


    # ========================================================
    # CUSTOMERS ACQUIRED
    # ========================================================

    if customers_column:

        customers = get_numeric_series(
            dataframe,
            customers_column,
        )

        if customers is not None:

            valid = customers.dropna()

            if not valid.empty:

                customers_acquired = float(
                    valid.sum()
                )


    # ========================================================
    # CTR
    # ========================================================

    if (
        total_clicks is not None
        and total_impressions is not None
        and total_impressions != 0
    ):

        average_ctr = float(
            (
                total_clicks
                / total_impressions
            )
            * 100
        )

    else:

        ctr_column = resolved_columns.get(
            "CTR"
        )

        if ctr_column:

            ctr = get_numeric_series(
                dataframe,
                ctr_column,
            )

            if ctr is not None:

                valid = ctr.dropna()

                if not valid.empty:

                    average_ctr = float(
                        valid.mean()
                    )


    # ========================================================
    # CONVERSION RATE
    # ========================================================

    if (
        total_conversions is not None
        and total_clicks is not None
        and total_clicks != 0
    ):

        conversion_rate = float(
            (
                total_conversions
                / total_clicks
            )
            * 100
        )

    else:

        conversion_rate_column = (
            resolved_columns.get(
                "Conversion_Rate"
            )
        )

        if conversion_rate_column:

            conversion_rates = (
                get_numeric_series(
                    dataframe,
                    conversion_rate_column,
                )
            )

            if conversion_rates is not None:

                valid = (
                    conversion_rates.dropna()
                )

                if not valid.empty:

                    conversion_rate = float(
                        valid.mean()
                    )


    # ========================================================
    # COST PER CLICK
    # ========================================================

    if (
        total_cost is not None
        and total_clicks is not None
        and total_clicks != 0
    ):

        cost_per_click = float(
            total_cost
            / total_clicks
        )


    # ========================================================
    # COST PER CONVERSION
    # ========================================================

    if (
        total_cost is not None
        and total_conversions is not None
        and total_conversions != 0
    ):

        cost_per_conversion = float(
            total_cost
            / total_conversions
        )


    # ========================================================
    # COST PER LEAD
    # ========================================================

    if (
        total_cost is not None
        and total_leads is not None
        and total_leads != 0
    ):

        cost_per_lead = float(
            total_cost
            / total_leads
        )


    # ========================================================
    # ROI
    # ========================================================

    if (
        total_profit is not None
        and total_cost is not None
        and total_cost != 0
    ):

        roi = float(
            (
                total_profit
                / total_cost
            )
            * 100
        )

    else:

        roi_column = resolved_columns.get(
            "ROI"
        )

        if roi_column:

            roi_values = get_numeric_series(
                dataframe,
                roi_column,
            )

            if roi_values is not None:

                valid = roi_values.dropna()

                if not valid.empty:

                    roi = float(
                        valid.mean()
                    )


    # ========================================================
    # ROAS
    # ========================================================

    if (
        total_sales is not None
        and total_cost is not None
        and total_cost != 0
    ):

        roas = float(
            total_sales
            / total_cost
        )

    else:

        roas_column = resolved_columns.get(
            "ROAS"
        )

        if roas_column:

            roas_values = get_numeric_series(
                dataframe,
                roas_column,
            )

            if roas_values is not None:

                valid = roas_values.dropna()

                if not valid.empty:

                    roas = float(
                        valid.mean()
                    )


    return {

        "total_campaigns":
            total_campaigns,

        "total_impressions":
            total_impressions,

        "total_clicks":
            total_clicks,

        "total_conversions":
            total_conversions,

        "total_leads":
            total_leads,

        "total_sales":
            total_sales,

        "total_marketing_cost":
            total_cost,

        "total_profit":
            total_profit,

        "average_ctr":
            average_ctr,

        "conversion_rate":
            conversion_rate,

        "cost_per_click":
            cost_per_click,

        "cost_per_conversion":
            cost_per_conversion,

        "cost_per_lead":
            cost_per_lead,

        "roi":
            roi,

        "roas":
            roas,

        "customers_acquired":
            customers_acquired,

        "average_campaign_sales":
            average_campaign_sales,

        "top_campaign":
            top_campaign,

        "top_campaign_sales":
            top_campaign_sales,

        "marketing_growth":
            None,
    }


# ============================================================
# MARKETING SALES TREND
# ============================================================

def marketing_sales_trend(dataframe):
    """
    Return marketing sales aggregated by date.

    Output:

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

    if (
        not date_column
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
# SALES BY CAMPAIGN
# ============================================================

def sales_by_campaign(
    dataframe,
    limit=None,
):
    """
    Return sales grouped by campaign.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    campaign_column = resolved_columns.get(
        "Campaign_Name"
    )

    if not campaign_column:
        campaign_column = resolved_columns.get(
            "Campaign_ID"
        )

    sales_column = get_sales_column(
        resolved_columns
    )

    if (
        not campaign_column
        or not sales_column
    ):

        return []

    campaigns = clean_text_values(
        dataframe,
        campaign_column,
    )

    sales = get_numeric_series(
        dataframe,
        sales_column,
    )

    if campaigns is None or sales is None:
        return []

    working_dataframe = pd.DataFrame(
        {
            "Campaign": campaigns,
            "Sales": sales,
        }
    ).dropna(
        subset=["Sales"]
    )

    if working_dataframe.empty:
        return []

    grouped = (
        working_dataframe
        .groupby(
            "Campaign",
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
            "campaign": str(campaign),
            "sales": float(sales),
        }
        for campaign, sales
        in grouped.items()
    ]


# ============================================================
# COST BY CAMPAIGN
# ============================================================

def cost_by_campaign(
    dataframe,
    limit=None,
):
    """
    Return marketing cost grouped by campaign.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    campaign_column = resolved_columns.get(
        "Campaign_Name"
    )

    if not campaign_column:
        campaign_column = resolved_columns.get(
            "Campaign_ID"
        )

    cost_column = get_cost_column(
        resolved_columns
    )

    if (
        not campaign_column
        or not cost_column
    ):

        return []

    campaigns = clean_text_values(
        dataframe,
        campaign_column,
    )

    cost = get_numeric_series(
        dataframe,
        cost_column,
    )

    if campaigns is None or cost is None:
        return []

    working_dataframe = pd.DataFrame(
        {
            "Campaign": campaigns,
            "Cost": cost,
        }
    ).dropna(
        subset=["Cost"]
    )

    if working_dataframe.empty:
        return []

    grouped = (
        working_dataframe
        .groupby(
            "Campaign",
            dropna=False,
        )["Cost"]
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
            "campaign": str(campaign),
            "cost": float(cost),
        }
        for campaign, cost
        in grouped.items()
    ]


# ============================================================
# CONVERSIONS BY CAMPAIGN
# ============================================================

def conversions_by_campaign(
    dataframe,
    limit=None,
):
    """
    Return conversions grouped by campaign.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    campaign_column = resolved_columns.get(
        "Campaign_Name"
    )

    if not campaign_column:
        campaign_column = resolved_columns.get(
            "Campaign_ID"
        )

    conversion_column = resolved_columns.get(
        "Conversions"
    )

    if (
        not campaign_column
        or not conversion_column
    ):

        return []

    campaigns = clean_text_values(
        dataframe,
        campaign_column,
    )

    conversions = get_numeric_series(
        dataframe,
        conversion_column,
    )

    if (
        campaigns is None
        or conversions is None
    ):

        return []

    working_dataframe = pd.DataFrame(
        {
            "Campaign": campaigns,
            "Conversions": conversions,
        }
    ).dropna(
        subset=["Conversions"]
    )

    if working_dataframe.empty:
        return []

    grouped = (
        working_dataframe
        .groupby(
            "Campaign",
            dropna=False,
        )["Conversions"]
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
            "campaign": str(campaign),
            "conversions": float(
                conversions
            ),
        }
        for campaign, conversions
        in grouped.items()
    ]


# ============================================================
# CHANNEL PERFORMANCE
# ============================================================

def channel_performance(
    dataframe,
    limit=None,
):
    """
    Combine major marketing metrics by channel.

    Missing optional metrics remain None.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    channel_column = resolved_columns.get(
        "Channel"
    )

    if not channel_column:
        return []

    channels = clean_text_values(
        dataframe,
        channel_column,
    )

    working_dataframe = pd.DataFrame(
        {
            "Channel": channels,
        }
    )

    sales_column = get_sales_column(
        resolved_columns
    )

    cost_column = get_cost_column(
        resolved_columns
    )

    clicks_column = resolved_columns.get(
        "Clicks"
    )

    conversions_column = (
        resolved_columns.get(
            "Conversions"
        )
    )

    impressions_column = (
        resolved_columns.get(
            "Impressions"
        )
    )

    leads_column = resolved_columns.get(
        "Leads"
    )


    if sales_column:

        working_dataframe["Sales"] = (
            get_numeric_series(
                dataframe,
                sales_column,
            )
        )


    if cost_column:

        working_dataframe["Cost"] = (
            get_numeric_series(
                dataframe,
                cost_column,
            )
        )


    if clicks_column:

        working_dataframe["Clicks"] = (
            get_numeric_series(
                dataframe,
                clicks_column,
            )
        )


    if conversions_column:

        working_dataframe[
            "Conversions"
        ] = get_numeric_series(
            dataframe,
            conversions_column,
        )


    if impressions_column:

        working_dataframe[
            "Impressions"
        ] = get_numeric_series(
            dataframe,
            impressions_column,
        )


    if leads_column:

        working_dataframe["Leads"] = (
            get_numeric_series(
                dataframe,
                leads_column,
            )
        )


    numeric_columns = [
        column
        for column in [
            "Sales",
            "Cost",
            "Clicks",
            "Conversions",
            "Impressions",
            "Leads",
        ]
        if column in working_dataframe.columns
    ]


    if not numeric_columns:
        return []


    aggregation_map = {
        column: "sum"
        for column in numeric_columns
    }


    grouped = (
        working_dataframe
        .groupby(
            "Channel",
            dropna=False,
        )
        .agg(aggregation_map)
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
            "channel": str(
                row["Channel"]
            ),

            "sales": None,

            "cost": None,

            "clicks": None,

            "conversions": None,

            "impressions": None,

            "leads": None,

            "ctr": None,

            "conversion_rate": None,

            "roas": None,
        }


        if "Sales" in grouped.columns:

            value = row["Sales"]

            if not pd.isna(value):

                item["sales"] = float(
                    value
                )


        if "Cost" in grouped.columns:

            value = row["Cost"]

            if not pd.isna(value):

                item["cost"] = float(
                    value
                )


        if "Clicks" in grouped.columns:

            value = row["Clicks"]

            if not pd.isna(value):

                item["clicks"] = float(
                    value
                )


        if "Conversions" in grouped.columns:

            value = row["Conversions"]

            if not pd.isna(value):

                item["conversions"] = float(
                    value
                )


        if "Impressions" in grouped.columns:

            value = row["Impressions"]

            if not pd.isna(value):

                item["impressions"] = float(
                    value
                )


        if "Leads" in grouped.columns:

            value = row["Leads"]

            if not pd.isna(value):

                item["leads"] = float(
                    value
                )


        # CTR

        if (
            item["clicks"] is not None
            and item["impressions"] is not None
            and item["impressions"] != 0
        ):

            item["ctr"] = float(
                (
                    item["clicks"]
                    / item["impressions"]
                )
                * 100
            )


        # Conversion Rate

        if (
            item["conversions"] is not None
            and item["clicks"] is not None
            and item["clicks"] != 0
        ):

            item["conversion_rate"] = float(
                (
                    item["conversions"]
                    / item["clicks"]
                )
                * 100
            )


        # ROAS

        if (
            item["sales"] is not None
            and item["cost"] is not None
            and item["cost"] != 0
        ):

            item["roas"] = float(
                item["sales"]
                / item["cost"]
            )


        result.append(item)


    return result


# ============================================================
# MARKETING ROI BY CAMPAIGN
# ============================================================

def roi_by_campaign(
    dataframe,
    limit=None,
):
    """
    Calculate ROI and ROAS for each campaign when the required
    sales/cost/profit information is available.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    campaign_column = resolved_columns.get(
        "Campaign_Name"
    )

    if not campaign_column:
        campaign_column = resolved_columns.get(
            "Campaign_ID"
        )

    sales_column = get_sales_column(
        resolved_columns
    )

    cost_column = get_cost_column(
        resolved_columns
    )

    profit_column = get_profit_column(
        resolved_columns
    )

    if (
        not campaign_column
        or not sales_column
        or not cost_column
    ):

        return []

    campaigns = clean_text_values(
        dataframe,
        campaign_column,
    )

    sales = get_numeric_series(
        dataframe,
        sales_column,
    )

    cost = get_numeric_series(
        dataframe,
        cost_column,
    )

    working_dataframe = pd.DataFrame(
        {
            "Campaign": campaigns,
            "Sales": sales,
            "Cost": cost,
        }
    )

    if profit_column:

        working_dataframe["Profit"] = (
            get_numeric_series(
                dataframe,
                profit_column,
            )
        )

    working_dataframe = (
        working_dataframe
        .dropna(
            subset=[
                "Sales",
                "Cost",
            ]
        )
    )

    if working_dataframe.empty:
        return []

    aggregations = {
        "Sales": "sum",
        "Cost": "sum",
    }

    if "Profit" in working_dataframe.columns:
        aggregations["Profit"] = "sum"

    grouped = (
        working_dataframe
        .groupby(
            "Campaign",
            dropna=False,
        )
        .agg(aggregations)
        .reset_index()
    )

    grouped["ROAS"] = grouped.apply(
        lambda row:
            (
                row["Sales"]
                / row["Cost"]
                if row["Cost"] != 0
                else None
            ),
        axis=1,
    )

    if "Profit" in grouped.columns:

        grouped["ROI"] = grouped.apply(
            lambda row:
                (
                    (
                        row["Profit"]
                        / row["Cost"]
                    )
                    * 100
                    if row["Cost"] != 0
                    else None
                ),
            axis=1,
        )

    else:

        grouped["ROI"] = None


    grouped = grouped.sort_values(
        "ROAS",
        ascending=False,
        na_position="last",
    )


    if limit:
        grouped = grouped.head(
            limit
        )


    result = []


    for _, row in grouped.iterrows():

        item = {
            "campaign": str(
                row["Campaign"]
            ),

            "sales": float(
                row["Sales"]
            ),

            "cost": float(
                row["Cost"]
            ),

            "roas": None,

            "roi": None,
        }


        if not pd.isna(
            row["ROAS"]
        ):

            item["roas"] = float(
                row["ROAS"]
            )


        if not pd.isna(
            row["ROI"]
        ):

            item["roi"] = float(
                row["ROI"]
            )


        result.append(item)


    return result


# ============================================================
# LEAD / CONVERSION FUNNEL
# ============================================================

def marketing_funnel(
    dataframe,
):
    """
    Build a marketing funnel using available metrics.

    Possible stages:
        impressions
        clicks
        leads
        conversions

    Missing stages are omitted.
    """

    if dataframe is None or dataframe.empty:
        return []

    resolved_columns = resolve_columns(
        dataframe
    )

    funnel = []


    # --------------------------------------------------------
    # IMPRESSIONS
    # --------------------------------------------------------

    impressions_column = resolved_columns.get(
        "Impressions"
    )

    if impressions_column:

        impressions = get_numeric_series(
            dataframe,
            impressions_column,
        )

        if impressions is not None:

            value = impressions.dropna()

            if not value.empty:

                funnel.append(
                    {
                        "stage": "Impressions",
                        "value": float(
                            value.sum()
                        ),
                    }
                )


    # --------------------------------------------------------
    # CLICKS
    # --------------------------------------------------------

    clicks_column = resolved_columns.get(
        "Clicks"
    )

    if clicks_column:

        clicks = get_numeric_series(
            dataframe,
            clicks_column,
        )

        if clicks is not None:

            value = clicks.dropna()

            if not value.empty:

                funnel.append(
                    {
                        "stage": "Clicks",
                        "value": float(
                            value.sum()
                        ),
                    }
                )


    # --------------------------------------------------------
    # LEADS
    # --------------------------------------------------------

    leads_column = resolved_columns.get(
        "Leads"
    )

    if leads_column:

        leads = get_numeric_series(
            dataframe,
            leads_column,
        )

        if leads is not None:

            value = leads.dropna()

            if not value.empty:

                funnel.append(
                    {
                        "stage": "Leads",
                        "value": float(
                            value.sum()
                        ),
                    }
                )


    # --------------------------------------------------------
    # CONVERSIONS
    # --------------------------------------------------------

    conversions_column = (
        resolved_columns.get(
            "Conversions"
        )
    )

    if conversions_column:

        conversions = get_numeric_series(
            dataframe,
            conversions_column,
        )

        if conversions is not None:

            value = conversions.dropna()

            if not value.empty:

                funnel.append(
                    {
                        "stage": "Conversions",
                        "value": float(
                            value.sum()
                        ),
                    }
                )


    return funnel


# ============================================================
# MARKETING PERFORMANCE BY REGION
# ============================================================

def marketing_by_region(
    dataframe,
    limit=None,
):
    """
    Return marketing sales/cost/performance by region.
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

    regions = clean_text_values(
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

    cost_column = get_cost_column(
        resolved_columns
    )

    conversions_column = (
        resolved_columns.get(
            "Conversions"
        )
    )

    if sales_column:

        working_dataframe["Sales"] = (
            get_numeric_series(
                dataframe,
                sales_column,
            )
        )

    if cost_column:

        working_dataframe["Cost"] = (
            get_numeric_series(
                dataframe,
                cost_column,
            )
        )

    if conversions_column:

        working_dataframe[
            "Conversions"
        ] = get_numeric_series(
            dataframe,
            conversions_column,
        )


    numeric_columns = [
        column
        for column in [
            "Sales",
            "Cost",
            "Conversions",
        ]
        if column in working_dataframe.columns
    ]


    if not numeric_columns:
        return []


    grouped = (
        working_dataframe
        .groupby(
            "Region",
            dropna=False,
        )[numeric_columns]
        .sum()
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
            ),

            "sales": None,

            "cost": None,

            "conversions": None,

            "roas": None,
        }


        if "Sales" in grouped.columns:

            value = row["Sales"]

            if not pd.isna(value):

                item["sales"] = float(
                    value
                )


        if "Cost" in grouped.columns:

            value = row["Cost"]

            if not pd.isna(value):

                item["cost"] = float(
                    value
                )


        if "Conversions" in grouped.columns:

            value = row["Conversions"]

            if not pd.isna(value):

                item["conversions"] = float(
                    value
                )


        if (
            item["sales"] is not None
            and item["cost"] is not None
            and item["cost"] != 0
        ):

            item["roas"] = float(
                item["sales"]
                / item["cost"]
            )


        result.append(item)


    return result


# ============================================================
# MARKETING GROWTH
# ============================================================

def calculate_marketing_growth(
    dataframe,
    current_from_date=None,
    current_to_date=None,
):
    """
    Compare marketing sales for the selected period with the
    immediately preceding period of equal length.

    Returns:
        percentage
        or None
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

    if (
        not date_column
        or not sales_column
    ):

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


    current_data = (
        working_dataframe[
            (
                working_dataframe["Date"]
                >= current_from
            )
            & (
                working_dataframe["Date"]
                <= current_to
            )
        ]
    )


    previous_data = (
        working_dataframe[
            (
                working_dataframe["Date"]
                >= previous_from
            )
            & (
                working_dataframe["Date"]
                <= previous_to
            )
        ]
    )


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
# SMART MARKETING INSIGHTS
# ============================================================

def generate_marketing_insights(
    metrics,
    campaigns=None,
    channels=None,
    roi_campaigns=None,
    growth=None,
):
    """
    Generate rule-based Marketing Intelligence insights.

    No artificial conclusions are generated when the required
    metrics are unavailable.
    """

    insights = []


    if not metrics:
        return insights


    # ========================================================
    # TOP CAMPAIGN
    # ========================================================

    top_campaign = metrics.get(
        "top_campaign"
    )

    top_campaign_sales = metrics.get(
        "top_campaign_sales"
    )

    total_sales = metrics.get(
        "total_sales"
    )


    if (
        top_campaign
        and top_campaign_sales is not None
    ):

        if (
            total_sales is not None
            and total_sales > 0
        ):

            contribution = (
                top_campaign_sales
                / total_sales
            ) * 100

            insights.append(
                {
                    "type": "positive",

                    "title": "Top Performing Campaign",

                    "message": (
                        f"{top_campaign} generated "
                        f"the highest campaign sales "
                        f"of {top_campaign_sales:,.2f}, "
                        f"representing "
                        f"{contribution:.1f}% "
                        f"of total marketing sales."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "positive",

                    "title": "Top Performing Campaign",

                    "message": (
                        f"{top_campaign} generated "
                        f"the highest campaign sales "
                        f"of {top_campaign_sales:,.2f}."
                    ),
                }
            )


    # ========================================================
    # MARKETING GROWTH
    # ========================================================

    if growth is not None:

        if growth > 0:

            insights.append(
                {
                    "type": "positive",

                    "title": "Marketing Sales Growth",

                    "message": (
                        f"Marketing-driven sales "
                        f"increased by "
                        f"{growth:.2f}% compared with "
                        "the previous comparable "
                        "period."
                    ),
                }
            )

        elif growth < 0:

            insights.append(
                {
                    "type": "warning",

                    "title": "Marketing Sales Decline",

                    "message": (
                        f"Marketing-driven sales "
                        f"decreased by "
                        f"{abs(growth):.2f}% compared "
                        "with the previous comparable "
                        "period."
                    ),
                }
            )

        else:

            insights.append(
                {
                    "type": "neutral",

                    "title": "Marketing Sales Stable",

                    "message": (
                        "Marketing-driven sales "
                        "remained unchanged compared "
                        "with the previous comparable "
                        "period."
                    ),
                }
            )


    # ========================================================
    # CTR
    # ========================================================

    ctr = metrics.get(
        "average_ctr"
    )

    if ctr is not None:

        if ctr >= 5:

            insights.append(
                {
                    "type": "positive",

                    "title": "Strong Click-Through Rate",

                    "message": (
                        f"The average click-through "
                        f"rate is {ctr:.2f}%, indicating "
                        "strong engagement with the "
                        "available marketing traffic."
                    ),
                }
            )

        elif ctr < 1:

            insights.append(
                {
                    "type": "warning",

                    "title": "Low Click-Through Rate",

                    "message": (
                        f"The average click-through "
                        f"rate is {ctr:.2f}%. "
                        "Campaign engagement may "
                        "require closer review."
                    ),
                }
            )


    # ========================================================
    # CONVERSION RATE
    # ========================================================

    conversion_rate = metrics.get(
        "conversion_rate"
    )

    if conversion_rate is not None:

        if conversion_rate >= 10:

            insights.append(
                {
                    "type": "positive",

                    "title": "Strong Conversion Rate",

                    "message": (
                        f"The available campaigns "
                        f"show an average conversion "
                        f"rate of {conversion_rate:.2f}%."
                    ),
                }
            )

        elif conversion_rate < 2:

            insights.append(
                {
                    "type": "warning",

                    "title": "Low Conversion Rate",

                    "message": (
                        f"The average conversion "
                        f"rate is {conversion_rate:.2f}%. "
                        "The conversion funnel may "
                        "need further analysis."
                    ),
                }
            )


    # ========================================================
    # ROAS
    # ========================================================

    roas = metrics.get(
        "roas"
    )

    if roas is not None:

        if roas > 1:

            insights.append(
                {
                    "type": "positive",

                    "title": "Positive Marketing Return",

                    "message": (
                        f"Marketing generated "
                        f"{roas:.2f} in sales for "
                        "each unit of marketing spend "
                        "based on the available data."
                    ),
                }
            )

        elif roas < 1:

            insights.append(
                {
                    "type": "warning",

                    "title": "Low Marketing Return",

                    "message": (
                        f"Marketing generated "
                        f"{roas:.2f} in sales for "
                        "each unit of marketing spend "
                        "based on the available data."
                    ),
                }
            )


    # ========================================================
    # CHANNEL PERFORMANCE
    # ========================================================

    if channels:

        valid_channels = [
            item
            for item in channels
            if item.get("sales") is not None
        ]

        if valid_channels:

            top_channel = max(
                valid_channels,
                key=lambda item: item["sales"],
            )

            insights.append(
                {
                    "type": "positive",

                    "title": "Leading Marketing Channel",

                    "message": (
                        f"{top_channel.get('channel')} "
                        f"generated the highest "
                        f"available channel sales of "
                        f"{top_channel.get('sales'):,.2f}."
                    ),
                }
            )


    # ========================================================
    # CAMPAIGN ROI
    # ========================================================

    if roi_campaigns:

        valid_roi = [
            item
            for item in roi_campaigns
            if item.get("roas") is not None
        ]

        if valid_roi:

            top_roi = max(
                valid_roi,
                key=lambda item: item["roas"],
            )

            insights.append(
                {
                    "type": "positive",

                    "title": "Highest Campaign ROAS",

                    "message": (
                        f"{top_roi.get('campaign')} "
                        f"has the highest available "
                        f"ROAS at "
                        f"{top_roi.get('roas'):.2f}."
                    ),
                }
            )


    # ========================================================
    # CAMPAIGN COUNT
    # ========================================================

    total_campaigns = metrics.get(
        "total_campaigns"
    )

    if total_campaigns == 1:

        insights.append(
            {
                "type": "neutral",

                "title": "Single Campaign Dataset",

                "message": (
                    "Only one campaign is available "
                    "in the selected dataset, so campaign "
                    "comparisons are limited."
                ),
            }
        )


    return insights


# ============================================================
# BACKWARD-COMPATIBILITY ALIASES
# ============================================================

def marketing_sales(
    dataframe,
    limit=None,
):
    """
    Backward-compatible alias.
    """

    return sales_by_campaign(
        dataframe,
        limit=limit,
    )


def campaign_performance(
    dataframe,
    limit=None,
):
    """
    Backward-compatible alias.
    """

    return roi_by_campaign(
        dataframe,
        limit=limit,
    )


def channel_sales(
    dataframe,
    limit=None,
):
    """
    Backward-compatible helper returning channel
    performance data.
    """

    return channel_performance(
        dataframe,
        limit=limit,
    )