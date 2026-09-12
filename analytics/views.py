import json

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from data_management.models import Dataset

import json
import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required
from .date_filters import (
    DATE_RANGE_OPTIONS,
    apply_date_filter,
    get_previous_period,
    calculate_percentage_change,
)

from data_management.models import Dataset, DatasetVersion
# ==========================================================
# AUTHORIZATION
# ==========================================================

def user_is_approved(request):
    return (
        request.user.is_authenticated
        and getattr(
            request.user,
            "approval_status",
            None
        ) == "Approved"
    )


# ==========================================================
# CLEANED DATASET
# ==========================================================

def get_cleaned_version(dataset):
    """
    Return the current/latest cleaned dataset version.
    """

    cleaned_versions = (
        dataset.versions
        .filter(version_type="Cleaned")
        .order_by("-version_number")
    )

    current_version = (
        cleaned_versions
        .filter(is_current=True)
        .first()
    )

    return current_version or cleaned_versions.first()


# ==========================================================
# READ DATASET
# ==========================================================

def read_dataset(version):
    """
    Read the stored dataset into a pandas DataFrame.
    """

    if not version or not version.file:
        return None

    try:
        filename = (
            version.file_name
            or version.file.name
            or ""
        ).lower()

        with version.file.open("rb") as file:

            if filename.endswith(".csv"):

                dataframe = pd.read_csv(file)

            elif filename.endswith(".xlsx"):

                dataframe = pd.read_excel(
                    file,
                    engine="openpyxl"
                )

            elif filename.endswith(".xls"):

                dataframe = pd.read_excel(file)

            else:

                return None

        return dataframe

    except Exception:
        return None


# ==========================================================
# COLUMN DETECTION
# ==========================================================

def find_column(dataframe, possible_names):
    """
    Find a column using case-insensitive matching.
    """

    if dataframe is None:
        return None

    normalized = {
        str(column).strip().lower(): column
        for column in dataframe.columns
    }

    for name in possible_names:

        if name.lower() in normalized:
            return normalized[name.lower()]

    return None


# ==========================================================
# PERCENTAGE CHANGE
# ==========================================================

def percentage_change(current, previous):
    """
    Calculate percentage change safely.
    """

    if previous is None:
        return 0

    if previous == 0:

        if current > 0:
            return 100

        return 0

    return (
        (current - previous)
        / abs(previous)
    ) * 100


# ==========================================================
# KPI STATUS
# ==========================================================

def performance_status(
    value,
    positive_is_good=True
):
    """
    Convert a KPI percentage into a business status.

    Returns:
        Good
        Warning
        Critical
    """

    if positive_is_good:

        if value >= 5:
            return "Good"

        if value >= 0:
            return "Warning"

        return "Critical"

    else:

        if value <= 0:
            return "Good"

        if value <= 5:
            return "Warning"

        return "Critical"


# ==========================================================
# STATUS CSS CLASS
# ==========================================================

def performance_class(status):
    """
    CSS-friendly KPI status class.
    """

    return {
        "Good": "good",
        "Warning": "warning",
        "Critical": "critical",
    }.get(
        status,
        "warning"
    )


# ==========================================================
# BUSINESS INTELLIGENCE
# ==========================================================

@login_required
def business_intelligence(request):

    # ======================================================
    # AUTHORIZATION
    # ======================================================

    if not user_is_approved(request):

        return redirect(
            "accounts:login"
        )


    # ======================================================
    # DATASETS
    # ======================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True
        )
        .order_by("-uploaded_at")
    )


    if not datasets.exists():

        return render(
            request,
            "analytics/business_intelligence.html",
            {
                "has_data": False,
                "datasets": [],
            }
        )


    # ======================================================
    # SELECT DATASET
    # ======================================================

    dataset_id = request.GET.get(
        "dataset"
    )

    selected_dataset = None


    if dataset_id:

        try:

            selected_dataset = (
                datasets
                .filter(
                    id=int(dataset_id)
                )
                .first()
            )

        except (
            TypeError,
            ValueError
        ):

            selected_dataset = None


    if selected_dataset is None:

        selected_dataset = datasets.first()


    # ======================================================
    # GET CLEANED VERSION
    # ======================================================

    cleaned_version = get_cleaned_version(
        selected_dataset
    )


    if cleaned_version is None:

        return render(
            request,
            "analytics/business_intelligence.html",
            {
                "has_data": False,
                "datasets": datasets,
                "selected_dataset": selected_dataset,
            }
        )


    # ======================================================
    # READ CLEANED DATA
    # ======================================================

    dataframe = read_dataset(
        cleaned_version
    )


    if (
        dataframe is None
        or dataframe.empty
    ):

        return render(
            request,
            "analytics/business_intelligence.html",
            {
                "has_data": False,
                "datasets": datasets,
                "selected_dataset": selected_dataset,
            }
        )


    # ======================================================
    # COPY DATAFRAME
    # ======================================================

    dataframe = dataframe.copy()


    # ======================================================
    # NORMALIZE COLUMN NAMES
    # ======================================================

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]


    # ======================================================
    # FIND BUSINESS COLUMNS
    # ======================================================

    date_column = find_column(
        dataframe,
        [
            "date",
            "order_date",
            "sales_date",
            "transaction_date",
            "created_at",
        ]
    )


    sales_column = find_column(
        dataframe,
        [
            "sales",
            "revenue",
            "amount",
            "total_sales",
            "total_revenue",
        ]
    )


    quantity_column = find_column(
        dataframe,
        [
            "quantity",
            "qty",
            "units",
            "units_sold",
        ]
    )


    discount_column = find_column(
        dataframe,
        [
            "discount",
            "discount_percent",
            "discount_percentage",
        ]
    )


    region_column = find_column(
        dataframe,
        [
            "region",
            "area",
            "city",
            "location",
        ]
    )


    product_column = find_column(
        dataframe,
        [
            "product",
            "product_name",
            "item",
            "item_name",
        ]
    )


    # ======================================================
    # DATE NORMALIZATION
    # ======================================================

    if date_column:

        dataframe[date_column] = pd.to_datetime(
            dataframe[date_column],
            errors="coerce"
        )

        dataframe = dataframe.dropna(
            subset=[date_column]
        )

        dataframe = (
            dataframe
            .sort_values(
                by=date_column
            )
            .reset_index(drop=True)
        )


    # ======================================================
    # NUMERIC NORMALIZATION
    # ======================================================

    if sales_column:

        dataframe[sales_column] = (
            pd.to_numeric(
                dataframe[sales_column],
                errors="coerce"
            )
            .fillna(0)
        )


    if quantity_column:

        dataframe[quantity_column] = (
            pd.to_numeric(
                dataframe[quantity_column],
                errors="coerce"
            )
            .fillna(0)
        )


    if discount_column:

        dataframe[discount_column] = (
            pd.to_numeric(
                dataframe[discount_column],
                errors="coerce"
            )
            .fillna(0)
        )


    # ======================================================
    # PERIOD SELECTION
    # ======================================================

    selected_period = request.GET.get(
        "period",
        "12m"
    )


    custom_start = request.GET.get(
        "start_date",
        ""
    )


    custom_end = request.GET.get(
        "end_date",
        ""
    )


    filtered_df = dataframe.copy()


    display_start = (
        "All available data"
    )

    display_end = ""


    # ======================================================
    # DATE RANGE FILTERING
    # ======================================================

    if (
        date_column
        and not dataframe.empty
    ):

        max_date = (
            dataframe[date_column].max()
        )

        min_date = (
            dataframe[date_column].min()
        )


        # --------------------------------------------------
        # 30 DAYS
        # --------------------------------------------------

        if selected_period == "30d":

            start_date = (
                max_date
                - pd.Timedelta(days=30)
            )

            filtered_df = dataframe[
                dataframe[date_column]
                >= start_date
            ]

            display_start = (
                start_date.strftime(
                    "%d %b %Y"
                )
            )

            display_end = (
                max_date.strftime(
                    "%d %b %Y"
                )
            )


        # --------------------------------------------------
        # 3 MONTHS
        # --------------------------------------------------

        elif selected_period == "3m":

            start_date = (
                max_date
                - pd.DateOffset(months=3)
            )

            filtered_df = dataframe[
                dataframe[date_column]
                >= start_date
            ]

            display_start = (
                start_date.strftime(
                    "%d %b %Y"
                )
            )

            display_end = (
                max_date.strftime(
                    "%d %b %Y"
                )
            )


        # --------------------------------------------------
        # 6 MONTHS
        # --------------------------------------------------

        elif selected_period == "6m":

            start_date = (
                max_date
                - pd.DateOffset(months=6)
            )

            filtered_df = dataframe[
                dataframe[date_column]
                >= start_date
            ]

            display_start = (
                start_date.strftime(
                    "%d %b %Y"
                )
            )

            display_end = (
                max_date.strftime(
                    "%d %b %Y"
                )
            )


        # --------------------------------------------------
        # 12 MONTHS
        # --------------------------------------------------

        elif selected_period == "12m":

            start_date = (
                max_date
                - pd.DateOffset(months=12)
            )

            filtered_df = dataframe[
                dataframe[date_column]
                >= start_date
            ]

            display_start = (
                start_date.strftime(
                    "%d %b %Y"
                )
            )

            display_end = (
                max_date.strftime(
                    "%d %b %Y"
                )
            )


        # --------------------------------------------------
        # CUSTOM RANGE
        # --------------------------------------------------

        elif selected_period == "custom":

            parsed_start = pd.to_datetime(
                custom_start,
                errors="coerce"
            )

            parsed_end = pd.to_datetime(
                custom_end,
                errors="coerce"
            )


            if (
                not pd.isna(parsed_start)
                and not pd.isna(parsed_end)
            ):

                filtered_df = dataframe[
                    (
                        dataframe[date_column]
                        >= parsed_start
                    )
                    &
                    (
                        dataframe[date_column]
                        <= parsed_end
                    )
                ]

                display_start = (
                    parsed_start.strftime(
                        "%d %b %Y"
                    )
                )

                display_end = (
                    parsed_end.strftime(
                        "%d %b %Y"
                    )
                )


        # --------------------------------------------------
        # ALL DATA
        # --------------------------------------------------

        elif selected_period == "all":

            filtered_df = (
                dataframe.copy()
            )

            display_start = (
                min_date.strftime(
                    "%d %b %Y"
                )
            )

            display_end = (
                max_date.strftime(
                    "%d %b %Y"
                )
            )


    # ======================================================
    # FALLBACK
    # ======================================================

    if filtered_df.empty:

        filtered_df = dataframe.copy()


    # ======================================================
    # CURRENT PERIOD KPIs
    # ======================================================

    total_orders = len(
        filtered_df
    )


    total_revenue = 0


    total_quantity = 0


    average_order_value = 0


    average_discount = 0


    if sales_column:

        total_revenue = float(
            filtered_df[
                sales_column
            ].sum()
        )


    if quantity_column:

        total_quantity = float(
            filtered_df[
                quantity_column
            ].sum()
        )


    if total_orders > 0:

        average_order_value = (
            total_revenue
            / total_orders
        )


    if discount_column:

        average_discount = float(
            filtered_df[
                discount_column
            ].mean()
        )


    # ======================================================
    # PREVIOUS PERIOD
    # ======================================================

    previous_revenue = 0


    previous_orders = 0


    previous_quantity = 0


    previous_aov = 0


    previous_discount = 0


    if (
        date_column
        and not filtered_df.empty
    ):

        current_min = (
            filtered_df[
                date_column
            ].min()
        )


        current_max = (
            filtered_df[
                date_column
            ].max()
        )


        period_length = (
            current_max
            - current_min
        )


        previous_end = (
            current_min
        )


        previous_start = (
            previous_end
            - period_length
        )


        previous_df = dataframe[
            (
                dataframe[date_column]
                >= previous_start
            )
            &
            (
                dataframe[date_column]
                < previous_end
            )
        ]


        previous_orders = len(
            previous_df
        )


        if sales_column:

            previous_revenue = float(
                previous_df[
                    sales_column
                ].sum()
            )


        if quantity_column:

            previous_quantity = float(
                previous_df[
                    quantity_column
                ].sum()
            )


        if previous_orders > 0:

            previous_aov = (
                previous_revenue
                / previous_orders
            )


        if (
            discount_column
            and not previous_df.empty
        ):

            previous_discount = float(
                previous_df[
                    discount_column
                ].mean()
            )


    # ======================================================
    # KPI GROWTH
    # ======================================================

    revenue_growth = percentage_change(
        total_revenue,
        previous_revenue
    )


    order_growth = percentage_change(
        total_orders,
        previous_orders
    )


    quantity_growth = percentage_change(
        total_quantity,
        previous_quantity
    )


    aov_growth = percentage_change(
        average_order_value,
        previous_aov
    )


    discount_change = percentage_change(
        average_discount,
        previous_discount
    )


    # ======================================================
    # KPI STATUS
    # ======================================================

    revenue_status = performance_status(
        revenue_growth,
        positive_is_good=True
    )


    order_status = performance_status(
        order_growth,
        positive_is_good=True
    )


    quantity_status = performance_status(
        quantity_growth,
        positive_is_good=True
    )


    aov_status = performance_status(
        aov_growth,
        positive_is_good=True
    )


    discount_status = performance_status(
        discount_change,
        positive_is_good=False
    )


    # ======================================================
    # STATUS CSS CLASSES
    # ======================================================

    revenue_status_class = performance_class(
        revenue_status
    )


    order_status_class = performance_class(
        order_status
    )


    quantity_status_class = performance_class(
        quantity_status
    )


    aov_status_class = performance_class(
        aov_status
    )


    discount_status_class = performance_class(
        discount_status
    )


    # ======================================================
    # MONTHLY REVENUE
    # ======================================================

    monthly_labels = []


    monthly_values = []


    if (
        date_column
        and sales_column
        and not filtered_df.empty
    ):

        monthly = (
            filtered_df
            .set_index(date_column)[
                sales_column
            ]
            .resample("ME")
            .sum()
        )


        for date, value in monthly.items():

            monthly_labels.append(
                date.strftime(
                    "%b %Y"
                )
            )


            monthly_values.append(
                round(
                    float(value),
                    2
                )
            )


    # ======================================================
    # REGION PERFORMANCE
    # ======================================================

    region_labels = []


    region_values = []


    if (
        region_column
        and sales_column
    ):

        region_data = (
            filtered_df
            .groupby(region_column)[
                sales_column
            ]
            .sum()
            .sort_values(
                ascending=False
            )
        )


        for region, value in (
            region_data.items()
        ):

            region_labels.append(
                str(region)
            )


            region_values.append(
                round(
                    float(value),
                    2
                )
            )


    # ======================================================
    # PRODUCT PERFORMANCE
    # ======================================================

    product_labels = []


    product_values = []


    if (
        product_column
        and sales_column
    ):

        product_data = (
            filtered_df
            .groupby(product_column)[
                sales_column
            ]
            .sum()
            .sort_values(
                ascending=False
            )
            .head(10)
        )


        for product, value in (
            product_data.items()
        ):

            product_labels.append(
                str(product)
            )


            product_values.append(
                round(
                    float(value),
                    2
                )
            )


    # ==========================================================
    # ADVANCED BUSINESS ANALYSIS
    # ==========================================================

    advanced_insights = []


    best_product = None


    best_product_revenue = 0


    worst_product = None


    worst_product_revenue = 0


    best_region = None


    best_region_revenue = 0


    worst_region = None


    worst_region_revenue = 0


    # ==========================================================
    # PRODUCT CONTRIBUTION
    # ==========================================================

    product_contribution = []


    if (
        product_column
        and sales_column
        and not filtered_df.empty
    ):

        product_analysis = (
            filtered_df
            .groupby(product_column)[
                sales_column
            ]
            .sum()
            .sort_values(
                ascending=False
            )
        )


        total_product_revenue = float(
            product_analysis.sum()
        )


        if not product_analysis.empty:

            best_product = str(
                product_analysis.index[0]
            )


            best_product_revenue = float(
                product_analysis.iloc[0]
            )


            worst_product = str(
                product_analysis.index[-1]
            )


            worst_product_revenue = float(
                product_analysis.iloc[-1]
            )


        for product, revenue in (
            product_analysis.items()
        ):

            revenue = float(
                revenue
            )


            contribution = 0


            if total_product_revenue > 0:

                contribution = (
                    revenue
                    / total_product_revenue
                ) * 100


            product_contribution.append({
                "name": str(product),
                "revenue": round(
                    revenue,
                    2
                ),
                "contribution": round(
                    contribution,
                    2
                ),
            })


    # ==========================================================
    # REGION CONTRIBUTION
    # ==========================================================

    region_contribution = []


    if (
        region_column
        and sales_column
        and not filtered_df.empty
    ):

        region_analysis = (
            filtered_df
            .groupby(region_column)[
                sales_column
            ]
            .sum()
            .sort_values(
                ascending=False
            )
        )


        total_region_revenue = float(
            region_analysis.sum()
        )


        if not region_analysis.empty:

            best_region = str(
                region_analysis.index[0]
            )


            best_region_revenue = float(
                region_analysis.iloc[0]
            )


            worst_region = str(
                region_analysis.index[-1]
            )


            worst_region_revenue = float(
                region_analysis.iloc[-1]
            )


        for region, revenue in (
            region_analysis.items()
        ):

            revenue = float(
                revenue
            )


            contribution = 0


            if total_region_revenue > 0:

                contribution = (
                    revenue
                    / total_region_revenue
                ) * 100


            region_contribution.append({
                "name": str(region),
                "revenue": round(
                    revenue,
                    2
                ),
                "contribution": round(
                    contribution,
                    2
                ),
            })


    # ==========================================================
    # REVENUE CHANGE DRIVER ANALYSIS
    # ==========================================================

    if revenue_growth > 5:

        advanced_insights.append({
            "type": "positive",
            "title": "Strong revenue momentum",
            "description": (
                f"Revenue increased by "
                f"{revenue_growth:.1f}% compared "
                "with the previous period."
            ),
        })


    elif revenue_growth < -5:

        advanced_insights.append({
            "type": "negative",
            "title": "Revenue decline detected",
            "description": (
                f"Revenue decreased by "
                f"{abs(revenue_growth):.1f}% compared "
                "with the previous period."
            ),
        })


    # ==========================================================
    # ORDER VS REVENUE ANALYSIS
    # ==========================================================

    if (
        revenue_growth > order_growth
        and revenue_growth > 0
    ):

        advanced_insights.append({
            "type": "positive",
            "title": "Higher value per order",
            "description": (
                "Revenue is growing faster than "
                "order volume, suggesting customers "
                "are generating more value per transaction."
            ),
        })


    elif (
        order_growth > revenue_growth
        and order_growth > 0
    ):

        advanced_insights.append({
            "type": "warning",
            "title": "Order volume is outpacing revenue",
            "description": (
                "Orders are increasing faster than "
                "revenue. Monitor average order value "
                "and product mix."
            ),
        })


    # ==========================================================
    # AOV ANALYSIS
    # ==========================================================

    if aov_growth > 5:

        advanced_insights.append({
            "type": "positive",
            "title": "Average order value improving",
            "description": (
                f"AOV increased by "
                f"{aov_growth:.1f}%, indicating "
                "stronger revenue generation per order."
            ),
        })


    elif aov_growth < -5:

        advanced_insights.append({
            "type": "negative",
            "title": "Average order value declining",
            "description": (
                f"AOV decreased by "
                f"{abs(aov_growth):.1f}%."
            ),
        })


    # ==========================================================
    # PRODUCT DRIVER
    # ==========================================================

    if best_product:

        advanced_insights.append({
            "type": "positive",
            "title": "Top product driver",
            "description": (
                f"{best_product} generated "
                f"₹{best_product_revenue:,.0f} "
                "in revenue and is the strongest "
                "product contributor."
            ),
        })


    if (
        worst_product
        and best_product
        and worst_product != best_product
    ):

        advanced_insights.append({
            "type": "warning",
            "title": "Product performance gap",
            "description": (
                f"{worst_product} is currently the "
                "lowest revenue product and may "
                "require further investigation."
            ),
        })


    # ==========================================================
    # REGION DRIVER
    # ==========================================================

    if best_region:

        advanced_insights.append({
            "type": "positive",
            "title": "Leading region",
            "description": (
                f"{best_region} generated "
                f"₹{best_region_revenue:,.0f} "
                "and is the strongest regional market."
            ),
        })


    if (
        worst_region
        and best_region
        and worst_region != best_region
    ):

        advanced_insights.append({
            "type": "warning",
            "title": "Regional performance gap",
            "description": (
                f"{worst_region} is currently the "
                "lowest revenue region."
            ),
        })


    # ==========================================================
    # DISCOUNT IMPACT
    # ==========================================================

    if discount_column:

        if discount_change > 10:

            advanced_insights.append({
                "type": "warning",
                "title": "Discount usage increasing",
                "description": (
                    f"Average discount changed by "
                    f"{discount_change:.1f}%. "
                    "Higher discounting should be "
                    "monitored for profitability impact."
                ),
            })


        elif discount_change < -5:

            advanced_insights.append({
                "type": "positive",
                "title": "Discount dependency reduced",
                "description": (
                    "Average discount usage decreased "
                    "while the business is maintaining "
                    "its sales activity."
                ),
            })


    # ==========================================================
    # REVENUE CONCENTRATION
    # ==========================================================

    top_product_concentration = 0


    if product_contribution:

        top_product_concentration = (
            product_contribution[0][
                "contribution"
            ]
        )


    if top_product_concentration >= 50:

        advanced_insights.append({
            "type": "warning",
            "title": "High product concentration",
            "description": (
                f"{best_product} contributes approximately "
                f"{top_product_concentration:.1f}% of revenue. "
                "The business may have product concentration risk."
            ),
        })


    # ==========================================================
    # MONTHLY MOMENTUM
    # ==========================================================

    monthly_growth = []


    if (
        date_column
        and sales_column
        and len(monthly_values) >= 2
    ):

        for index in range(
            1,
            len(monthly_values)
        ):

            previous_month = (
                monthly_values[index - 1]
            )


            current_month = (
                monthly_values[index]
            )


            change = percentage_change(
                current_month,
                previous_month
            )


            monthly_growth.append({
                "month": monthly_labels[index],
                "growth": round(
                    change,
                    2
                ),
            })


    # ==========================================================
    # TREND DIRECTION
    # ==========================================================

    trend_direction = "Stable"


    if len(monthly_values) >= 2:

        if (
            monthly_values[-1]
            > monthly_values[0]
        ):

            trend_direction = "Growing"


        elif (
            monthly_values[-1]
            < monthly_values[0]
        ):

            trend_direction = "Declining"


    # ==========================================================
    # BUSINESS HEALTH SIGNAL
    # ==========================================================

    positive_signals = 0


    warning_signals = 0


    critical_signals = 0


    for insight in advanced_insights:

        if insight["type"] == "positive":

            positive_signals += 1


        elif insight["type"] == "warning":

            warning_signals += 1


        elif insight["type"] == "negative":

            critical_signals += 1


    if critical_signals >= 2:

        business_signal = "Critical"


    elif warning_signals >= 2:

        business_signal = "Needs Attention"


    else:

        business_signal = "Healthy"


    # ======================================================
    # EXECUTIVE SUMMARY
    # ======================================================

    summary = []


    if revenue_growth > 5:

        summary.append(
            f"Revenue is growing strongly at "
            f"{revenue_growth:.1f}% compared with "
            "the previous period."
        )


    elif revenue_growth >= 0:

        summary.append(
            f"Revenue is showing moderate growth "
            f"of {revenue_growth:.1f}%."
        )


    else:

        summary.append(
            f"Revenue declined by "
            f"{abs(revenue_growth):.1f}% compared "
            "with the previous period."
        )


    if order_growth > 0:

        summary.append(
            f"Order volume increased by "
            f"{order_growth:.1f}%."
        )


    elif order_growth < 0:

        summary.append(
            f"Order volume decreased by "
            f"{abs(order_growth):.1f}%."
        )


    if aov_growth > 0:

        summary.append(
            f"Average order value increased by "
            f"{aov_growth:.1f}%, indicating stronger "
            "value per transaction."
        )


    elif aov_growth < 0:

        summary.append(
            f"Average order value decreased by "
            f"{abs(aov_growth):.1f}%."
        )


    if (
        discount_column
        and discount_change > 5
    ):

        summary.append(
            "Average discount usage has increased "
            "significantly and should be monitored "
            "for margin impact."
        )


    if product_labels:

        summary.append(
            f"{product_labels[0]} is currently the "
            "highest-revenue product."
        )


    if region_labels:

        summary.append(
            f"{region_labels[0]} is the leading "
            "revenue region."
        )


    # ======================================================
    # JSON FOR CHART.JS
    # ======================================================

    monthly_labels_json = json.dumps(
        monthly_labels
    )


    monthly_values_json = json.dumps(
        monthly_values
    )


    region_labels_json = json.dumps(
        region_labels
    )


    region_values_json = json.dumps(
        region_values
    )


    product_labels_json = json.dumps(
        product_labels
    )


    product_values_json = json.dumps(
        product_values
    )


    # ======================================================
    # CONTEXT
    # ======================================================

    context = {

        # --------------------------------------------------
        # GENERAL
        # --------------------------------------------------

        "has_data": True,

        "datasets": datasets,

        "selected_dataset":
            selected_dataset,

        "cleaned_version":
            cleaned_version,


        # --------------------------------------------------
        # BASIC KPIs
        # --------------------------------------------------

        "total_revenue":
            total_revenue,

        "total_orders":
            total_orders,

        "total_quantity":
            total_quantity,

        "average_order_value":
            average_order_value,

        "average_discount":
            average_discount,


        # --------------------------------------------------
        # GROWTH KPIs
        # --------------------------------------------------

        "growth_percentage":
            revenue_growth,

        "revenue_growth":
            revenue_growth,

        "order_growth":
            order_growth,

        "quantity_growth":
            quantity_growth,

        "aov_growth":
            aov_growth,

        "discount_change":
            discount_change,


        # --------------------------------------------------
        # PREVIOUS PERIOD
        # --------------------------------------------------

        "previous_revenue":
            previous_revenue,

        "previous_orders":
            previous_orders,

        "previous_quantity":
            previous_quantity,

        "previous_aov":
            previous_aov,

        "previous_discount":
            previous_discount,


        # --------------------------------------------------
        # KPI STATUS
        # --------------------------------------------------

        "revenue_status":
            revenue_status,

        "order_status":
            order_status,

        "quantity_status":
            quantity_status,

        "aov_status":
            aov_status,

        "discount_status":
            discount_status,


        # --------------------------------------------------
        # KPI CSS CLASSES
        # --------------------------------------------------

        "revenue_status_class":
            revenue_status_class,

        "order_status_class":
            order_status_class,

        "quantity_status_class":
            quantity_status_class,

        "aov_status_class":
            aov_status_class,

        "discount_status_class":
            discount_status_class,


        # --------------------------------------------------
        # CHART DATA
        # --------------------------------------------------

        "monthly_labels":
            monthly_labels_json,

        "monthly_values":
            monthly_values_json,

        "region_labels":
            region_labels_json,

        "region_values":
            region_values_json,

        "product_labels":
            product_labels_json,

        "product_values":
            product_values_json,


        # --------------------------------------------------
        # EXECUTIVE SUMMARY
        # --------------------------------------------------

        "summary":
            summary,


        # --------------------------------------------------
        # DATE RANGE
        # --------------------------------------------------

        "selected_period":
            selected_period,

        "custom_start":
            custom_start,

        "custom_end":
            custom_end,

        "display_start":
            display_start,

        "display_end":
            display_end,


        # --------------------------------------------------
        # DATASET INFORMATION
        # --------------------------------------------------

        "total_rows":
            len(filtered_df),

        "total_columns":
            len(filtered_df.columns),


        # ==================================================
        # ADVANCED BUSINESS INTELLIGENCE
        # ==================================================

        "advanced_insights":
            advanced_insights,

        "product_contribution":
            product_contribution,

        "region_contribution":
            region_contribution,


        # --------------------------------------------------
        # PRODUCT INTELLIGENCE
        # --------------------------------------------------

        "best_product":
            best_product,

        "best_product_revenue":
            best_product_revenue,

        "worst_product":
            worst_product,

        "worst_product_revenue":
            worst_product_revenue,


        # --------------------------------------------------
        # REGIONAL INTELLIGENCE
        # --------------------------------------------------

        "best_region":
            best_region,

        "best_region_revenue":
            best_region_revenue,

        "worst_region":
            worst_region,

        "worst_region_revenue":
            worst_region_revenue,


        # --------------------------------------------------
        # TREND INTELLIGENCE
        # --------------------------------------------------

        "monthly_growth":
            monthly_growth,

        "trend_direction":
            trend_direction,


        # --------------------------------------------------
        # BUSINESS HEALTH
        # --------------------------------------------------

        "business_signal":
            business_signal,

        "positive_signals":
            positive_signals,

        "warning_signals":
            warning_signals,

        "critical_signals":
            critical_signals,


        # --------------------------------------------------
        # CONCENTRATION
        # --------------------------------------------------

        "top_product_concentration":
            top_product_concentration,
    }


    # ======================================================
    # RENDER
    # ======================================================

    return render(
        request,
        "analytics/business_intelligence.html",
        context
    )

# ==========================================================
# CUSTOMER INTELLIGENCE
# ==========================================================

# ==========================================================
# CUSTOMER INTELLIGENCE
# ==========================================================

@login_required
def customer_intelligence(request):

    # ======================================================
    # AUTHORIZATION
    # ======================================================

    if not user_is_approved(request):
        return redirect("accounts:login")

    # ======================================================
    # DATASETS
    # ======================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    if not datasets.exists():

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "datasets": [],
            }
        )

    # ======================================================
    # SELECT DATASET
    # ======================================================

    dataset_id = request.GET.get("dataset")

    selected_dataset = None

    if dataset_id:

        try:
            selected_dataset = datasets.filter(
                id=int(dataset_id)
            ).first()

        except (TypeError, ValueError):

            selected_dataset = None

    if selected_dataset is None:
        selected_dataset = datasets.first()

    # ======================================================
    # CLEANED VERSION
    # ======================================================

    cleaned_version = get_cleaned_version(
        selected_dataset
    )

    if cleaned_version is None:

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "cleaned_version": None,
            }
        )

    # ======================================================
    # READ CLEANED DATA
    # ======================================================

    dataframe = read_dataset(
        cleaned_version
    )

    if dataframe is None or dataframe.empty:

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "cleaned_version": cleaned_version,
            }
        )

    dataframe = dataframe.copy()

    # ======================================================
    # NORMALIZE COLUMN NAMES
    # ======================================================

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    # ======================================================
    # FIND CUSTOMER COLUMN
    # ======================================================

    customer_column = find_column(
        dataframe,
        [
            "customer_id",
            "customerid",
            "customer",
            "customer_name",
            "client_id",
            "client",
            "user_id",
            "user",
        ]
    )

    # ======================================================
    # FIND DATE COLUMN
    # ======================================================

    date_column = find_column(
        dataframe,
        [
            "date",
            "order_date",
            "sales_date",
            "transaction_date",
            "purchase_date",
            "created_at",
        ]
    )

    # ======================================================
    # FIND SALES COLUMN
    # ======================================================

    sales_column = find_column(
        dataframe,
        [
            "sales",
            "revenue",
            "amount",
            "total_sales",
            "total_revenue",
            "order_value",
        ]
    )

    # ======================================================
    # OPTIONAL QUANTITY COLUMN
    # ======================================================

    quantity_column = find_column(
        dataframe,
        [
            "quantity",
            "qty",
            "units",
            "units_sold",
        ]
    )

    # ======================================================
    # OPTIONAL ORDER COLUMN
    # ======================================================

    order_column = find_column(
        dataframe,
        [
            "order_id",
            "order",
            "transaction_id",
            "invoice_id",
            "invoice",
            "transaction",
        ]
    )

    # ======================================================
    # VALIDATION
    # ======================================================

    if not all(
        [
            customer_column,
            date_column,
            sales_column,
        ]
    ):

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "cleaned_version": cleaned_version,

                "customer_column": customer_column,
                "date_column": date_column,
                "sales_column": sales_column,

                "missing_customer_columns": True,
            }
        )

    # ======================================================
    # DATA NORMALIZATION
    # ======================================================

    dataframe[customer_column] = (
        dataframe[customer_column]
        .astype(str)
        .str.strip()
    )

    dataframe[date_column] = pd.to_datetime(
        dataframe[date_column],
        errors="coerce"
    )

    dataframe[sales_column] = pd.to_numeric(
        dataframe[sales_column],
        errors="coerce"
    ).fillna(0)

    if quantity_column:

        dataframe[quantity_column] = pd.to_numeric(
            dataframe[quantity_column],
            errors="coerce"
        ).fillna(0)

    # ======================================================
    # REMOVE INVALID ROWS
    # ======================================================

    dataframe = dataframe.dropna(
        subset=[
            customer_column,
            date_column,
        ]
    )

    dataframe = dataframe[
        dataframe[customer_column] != ""
    ]

    if dataframe.empty:

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "cleaned_version": cleaned_version,
            }
        )

    # ======================================================
    # ANALYSIS DATE
    # ======================================================

    analysis_date = dataframe[
        date_column
    ].max()

    # ======================================================
    # RFM BASE TABLE
    # ======================================================

    aggregation = {
        "last_purchase": (
            date_column,
            "max"
        ),

        "frequency": (
            date_column,
            "count"
        ),

        "monetary": (
            sales_column,
            "sum"
        ),
    }

    # If an order ID exists, use unique orders
    # instead of raw transaction rows.

    if order_column:

        dataframe[order_column] = (
            dataframe[order_column]
            .astype(str)
            .str.strip()
        )

        aggregation["frequency"] = (
            order_column,
            "nunique"
        )

    rfm = (
        dataframe
        .groupby(customer_column)
        .agg(**aggregation)
        .reset_index()
    )

    # ======================================================
    # RECENCY
    # ======================================================

    rfm["recency"] = (
        analysis_date
        - rfm["last_purchase"]
    ).dt.days

    rfm["recency"] = (
        rfm["recency"]
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )

    # ======================================================
    # NUMERIC SAFETY
    # ======================================================

    rfm["frequency"] = pd.to_numeric(
        rfm["frequency"],
        errors="coerce"
    ).fillna(0)

    rfm["monetary"] = pd.to_numeric(
        rfm["monetary"],
        errors="coerce"
    ).fillna(0)

    # ======================================================
    # RFM SCORING
    # ======================================================

    customer_count = len(rfm)

    if customer_count >= 2:

        # --------------------------------------------------
        # RECENCY
        # Lower days = better
        # --------------------------------------------------

        rfm["recency_score"] = pd.qcut(
            rfm["recency"].rank(
                method="first"
            ),
            5,
            labels=False,
            duplicates="drop"
        )

        rfm["recency_score"] = (
            5
            - rfm["recency_score"]
        )

        # --------------------------------------------------
        # FREQUENCY
        # Higher = better
        # --------------------------------------------------

        rfm["frequency_score"] = pd.qcut(
            rfm["frequency"].rank(
                method="first"
            ),
            5,
            labels=False,
            duplicates="drop"
        ) + 1

        # --------------------------------------------------
        # MONETARY
        # Higher = better
        # --------------------------------------------------

        rfm["monetary_score"] = pd.qcut(
            rfm["monetary"].rank(
                method="first"
            ),
            5,
            labels=False,
            duplicates="drop"
        ) + 1

    else:

        rfm["recency_score"] = 5
        rfm["frequency_score"] = 5
        rfm["monetary_score"] = 5

    # ======================================================
    # SCORE CLEANUP
    # ======================================================

    for column in [
        "recency_score",
        "frequency_score",
        "monetary_score",
    ]:

        rfm[column] = (
            pd.to_numeric(
                rfm[column],
                errors="coerce"
            )
            .fillna(1)
            .clip(1, 5)
            .astype(int)
        )

    # ======================================================
    # TOTAL RFM SCORE
    # ======================================================

    rfm["rfm_score"] = (
        rfm["recency_score"]
        + rfm["frequency_score"]
        + rfm["monetary_score"]
    )

    # ======================================================
    # CUSTOMER SEGMENTATION
    # ======================================================

    def classify_customer(row):

        recency = row["recency"]
        frequency = row["frequency"]

        recency_score = row["recency_score"]
        frequency_score = row["frequency_score"]
        monetary_score = row["monetary_score"]

        # --------------------------------------------------
        # HIGH VALUE
        # --------------------------------------------------

        if (
            monetary_score >= 4
            and frequency_score >= 4
            and recency_score >= 4
        ):

            return "High Value"

        # --------------------------------------------------
        # LOYAL
        # --------------------------------------------------

        if (
            frequency_score >= 4
            and recency_score >= 3
        ):

            return "Loyal"

        # --------------------------------------------------
        # AT RISK
        # --------------------------------------------------

        if (
            recency_score <= 2
            and frequency_score >= 3
        ):

            return "At Risk"

        # --------------------------------------------------
        # NEW
        # --------------------------------------------------

        if (
            recency <= 30
            and frequency <= 2
        ):

            return "New"

        # --------------------------------------------------
        # LOW VALUE
        # --------------------------------------------------

        return "Low Value"

    rfm["segment"] = rfm.apply(
        classify_customer,
        axis=1
    )

    # ======================================================
    # SEGMENT ORDER
    # ======================================================

    segment_order = [
        "High Value",
        "Loyal",
        "New",
        "At Risk",
        "Low Value",
    ]

    # ======================================================
    # CUSTOMER KPIs
    # ======================================================

    total_customers = len(rfm)

    active_customers = int(
        (
            rfm["recency"] <= 90
        ).sum()
    )

    repeat_customers = int(
        (
            rfm["frequency"] > 1
        ).sum()
    )

    at_risk_customers = int(
        (
            rfm["segment"] == "At Risk"
        ).sum()
    )

    high_value_customers = int(
        (
            rfm["segment"] == "High Value"
        ).sum()
    )

    loyal_customers = int(
        (
            rfm["segment"] == "Loyal"
        ).sum()
    )

    new_customers = int(
        (
            rfm["segment"] == "New"
        ).sum()
    )

    low_value_customers = int(
        (
            rfm["segment"] == "Low Value"
        ).sum()
    )

    total_customer_revenue = float(
        rfm["monetary"].sum()
    )

    average_customer_value = (
        total_customer_revenue
        / total_customers
        if total_customers
        else 0
    )

    repeat_customer_rate = (
        repeat_customers
        / total_customers
        * 100
        if total_customers
        else 0
    )

    # ======================================================
    # SEGMENT ANALYSIS
    # ======================================================

    segment_distribution = []

    for segment in segment_order:

        segment_df = rfm[
            rfm["segment"] == segment
        ]

        customer_count_segment = len(
            segment_df
        )

        revenue = float(
            segment_df["monetary"].sum()
        )

        percentage = (
            customer_count_segment
            / total_customers
            * 100
            if total_customers
            else 0
        )

        revenue_percentage = (
            revenue
            / total_customer_revenue
            * 100
            if total_customer_revenue
            else 0
        )

        average_value = (
            revenue
            / customer_count_segment
            if customer_count_segment
            else 0
        )

        segment_distribution.append({

            "name": segment,

            "count": customer_count_segment,

            "percentage": round(
                percentage,
                2
            ),

            "revenue": round(
                revenue,
                2
            ),

            "revenue_percentage": round(
                revenue_percentage,
                2
            ),

            "average_value": round(
                average_value,
                2
            ),
        })

    # ======================================================
    # SEGMENT CHART DATA
    # ======================================================

    segment_labels = [
        item["name"]
        for item in segment_distribution
    ]

    segment_values = [
        item["count"]
        for item in segment_distribution
    ]

    segment_revenue_values = [
        item["revenue"]
        for item in segment_distribution
    ]

    segment_revenue_percentages = [
        item["revenue_percentage"]
        for item in segment_distribution
    ]

    # ======================================================
    # RFM SCORE DISTRIBUTION
    # ======================================================

    rfm_score_distribution = []

    for score in range(3, 16):

        count = int(
            (
                rfm["rfm_score"] == score
            ).sum()
        )

        rfm_score_distribution.append({

            "score": score,

            "count": count,

        })

    rfm_score_labels = [
        item["score"]
        for item in rfm_score_distribution
    ]

    rfm_score_values = [
        item["count"]
        for item in rfm_score_distribution
    ]

    # ======================================================
    # RFM AVERAGES
    # ======================================================

    average_recency = float(
        rfm["recency"].mean()
    )

    average_frequency = float(
        rfm["frequency"].mean()
    )

    average_monetary = float(
        rfm["monetary"].mean()
    )

    average_rfm_score = float(
        rfm["rfm_score"].mean()
    )

    # ======================================================
    # TOP CUSTOMERS
    # ======================================================

    top_customers = []

    top_customer_df = (
        rfm
        .sort_values(
            "monetary",
            ascending=False
        )
        .head(10)
    )

    for _, row in top_customer_df.iterrows():

        top_customers.append({

            "customer": str(
                row[customer_column]
            ),

            "recency": int(
                row["recency"]
            ),

            "frequency": int(
                row["frequency"]
            ),

            "monetary": round(
                float(row["monetary"]),
                2
            ),

            "segment": str(
                row["segment"]
            ),

            "rfm_score": int(
                row["rfm_score"]
            ),
        })

    # ======================================================
    # AT-RISK CUSTOMERS
    # ======================================================

    at_risk_customers_list = []

    at_risk_df = (
        rfm[
            rfm["segment"] == "At Risk"
        ]
        .sort_values(
            "monetary",
            ascending=False
        )
        .head(10)
    )

    for _, row in at_risk_df.iterrows():

        at_risk_customers_list.append({

            "customer": str(
                row[customer_column]
            ),

            "recency": int(
                row["recency"]
            ),

            "frequency": int(
                row["frequency"]
            ),

            "monetary": round(
                float(row["monetary"]),
                2
            ),

            "segment": "At Risk",

            "rfm_score": int(
                row["rfm_score"]
            ),
        })

    # ======================================================
    # CUSTOMER INSIGHTS
    # ======================================================

    customer_insights = []

    if high_value_customers > 0:

        customer_insights.append({

            "type": "positive",

            "title": "High-value customer base",

            "description": (
                f"{high_value_customers} customers "
                "are classified as High Value."
            ),
        })

    if loyal_customers > 0:

        customer_insights.append({

            "type": "positive",

            "title": "Strong customer loyalty",

            "description": (
                f"{loyal_customers} customers "
                "show strong repeat-purchase behavior."
            ),
        })

    if at_risk_customers > 0:

        customer_insights.append({

            "type": "warning",

            "title": "At-risk customers detected",

            "description": (
                f"{at_risk_customers} customers "
                "show signs of declining engagement."
            ),
        })

    if new_customers > 0:

        customer_insights.append({

            "type": "info",

            "title": "New customer opportunity",

            "description": (
                f"{new_customers} customers "
                "are currently classified as New."
            ),
        })

    if repeat_customer_rate >= 60:

        customer_insights.append({

            "type": "positive",

            "title": "Healthy repeat-customer rate",

            "description": (
                f"{repeat_customer_rate:.1f}% of customers "
                "have made more than one purchase."
            ),
        })

    # ======================================================
    # CUSTOMER HEALTH
    # ======================================================

    if total_customers == 0:

        customer_health = "No Data"

    elif (
        at_risk_customers
        / total_customers
        >= 0.40
    ):

        customer_health = "Critical"

    elif (
        at_risk_customers
        / total_customers
        >= 0.20
    ):

        customer_health = "Needs Attention"

    else:

        customer_health = "Healthy"

    # ======================================================
    # CONTEXT
    # ======================================================

    context = {

        # --------------------------------------------------
        # DATASET
        # --------------------------------------------------

        "has_data": True,

        "datasets": datasets,

        "selected_dataset":
            selected_dataset,

        "cleaned_version":
            cleaned_version,

        # --------------------------------------------------
        # COLUMNS
        # --------------------------------------------------

        "customer_column":
            customer_column,

        "date_column":
            date_column,

        "sales_column":
            sales_column,

        "quantity_column":
            quantity_column,

        "order_column":
            order_column,

        # --------------------------------------------------
        # CUSTOMER KPIs
        # --------------------------------------------------

        "total_customers":
            total_customers,

        "active_customers":
            active_customers,

        "repeat_customers":
            repeat_customers,

        "repeat_customer_rate":
            repeat_customer_rate,

        "average_customer_value":
            average_customer_value,

        "total_customer_revenue":
            total_customer_revenue,

        "high_value_customers":
            high_value_customers,

        "loyal_customers":
            loyal_customers,

        "new_customers":
            new_customers,

        "at_risk_customers":
            at_risk_customers,

        "low_value_customers":
            low_value_customers,

        # --------------------------------------------------
        # RFM
        # --------------------------------------------------

        "average_recency":
            average_recency,

        "average_frequency":
            average_frequency,

        "average_monetary":
            average_monetary,

        "average_rfm_score":
            average_rfm_score,

        # --------------------------------------------------
        # SEGMENTS
        # --------------------------------------------------

        "segment_distribution":
            segment_distribution,

        # --------------------------------------------------
        # CHART DATA
        # --------------------------------------------------

        "segment_labels":
            json.dumps(
                segment_labels
            ),

        "segment_values":
            json.dumps(
                segment_values
            ),

        "segment_revenue_values":
            json.dumps(
                segment_revenue_values
            ),

        "segment_revenue_percentages":
            json.dumps(
                segment_revenue_percentages
            ),

        "rfm_score_labels":
            json.dumps(
                rfm_score_labels
            ),

        "rfm_score_values":
            json.dumps(
                rfm_score_values
            ),

        # --------------------------------------------------
        # CUSTOMERS
        # --------------------------------------------------

        "top_customers":
            top_customers,

        "at_risk_customers_list":
            at_risk_customers_list,

        # --------------------------------------------------
        # INSIGHTS
        # --------------------------------------------------

        "customer_insights":
            customer_insights,

        "customer_health":
            customer_health,

        # --------------------------------------------------
        # ANALYSIS DATE
        # --------------------------------------------------

        "analysis_date":
            analysis_date.strftime(
                "%d %b %Y"
            ),
    }

    return render(
        request,
        "analytics/customer_intelligence.html",
        context
    )

    # -----------------------------------------------------
    # CUSTOMER SEGMENT
    # -----------------------------------------------------

    def classify_customer(row):

        if (
            row["monetary_score"] >= 4
            and row["frequency_score"] >= 4
            and row["recency_score"] >= 4
        ):
            return "High Value"

        if (
            row["frequency_score"] >= 4
            and row["recency_score"] >= 3
        ):
            return "Loyal"

        if (
            row["recency_score"] <= 2
            and row["frequency_score"] >= 3
        ):
            return "At Risk"

        if (
            row["recency"] <= 30
            and row["frequency"] <= 2
        ):
            return "New"

        return "Low Value"

    all_customer_rfm["segment"] = (
        all_customer_rfm.apply(
            classify_customer,
            axis=1
        )
    )

    # -----------------------------------------------------
    # SELECT CUSTOMER RFM RECORD
    # -----------------------------------------------------

    customer_rfm = all_customer_rfm[
        all_customer_rfm[customer_column].astype(str).str.strip()
        == customer_id
    ]

    if customer_rfm.empty:

        rfm_score = 0
        recency_score = 0
        frequency_score = 0
        monetary_score = 0
        segment = "Unknown"

    else:

        rfm_row = customer_rfm.iloc[0]

        rfm_score = int(
            rfm_row["rfm_score"]
        )

        recency_score = int(
            rfm_row["recency_score"]
        )

        frequency_score = int(
            rfm_row["frequency_score"]
        )

        monetary_score = int(
            rfm_row["monetary_score"]
        )

        segment = str(
            rfm_row["segment"]
        )

    # -----------------------------------------------------
    # CUSTOMER ACTION
    # -----------------------------------------------------

    recommended_action = ""

    action_type = "positive"

    if segment == "High Value":

        recommended_action = (
            "Treat this customer as a VIP. "
            "Prioritize retention, loyalty rewards, "
            "exclusive offers and personalized engagement."
        )

        action_type = "positive"

    elif segment == "Loyal":

        recommended_action = (
            "Strengthen the relationship with loyalty "
            "benefits, cross-sell opportunities and "
            "personalized product recommendations."
        )

        action_type = "positive"

    elif segment == "New":

        recommended_action = (
            "Focus on onboarding and encouraging the "
            "customer's second purchase through relevant "
            "offers and personalized communication."
        )

        action_type = "info"

    elif segment == "At Risk":

        recommended_action = (
            "Launch a targeted win-back campaign. "
            "Use personalized offers and re-engagement "
            "communication before the customer becomes inactive."
        )

        action_type = "warning"

    else:

        recommended_action = (
            "Use cost-efficient targeted promotions and "
            "monitor purchasing behavior before increasing "
            "retention investment."
        )

        action_type = "negative"

    # -----------------------------------------------------
    # PURCHASE HISTORY
    # -----------------------------------------------------

    purchase_history = []

    for _, row in customer_dataframe.head(30).iterrows():

        transaction = {

            "date": row[date_column].strftime(
                "%d %b %Y"
            ),

            "sales": float(
                row[sales_column]
            ),

        }

        if product_column:

            transaction["product"] = str(
                row[product_column]
            )

        else:

            transaction["product"] = "—"

        if quantity_column:

            transaction["quantity"] = float(
                row[quantity_column]
            )

        else:

            transaction["quantity"] = "—"

        if region_column:

            transaction["region"] = str(
                row[region_column]
            )

        else:

            transaction["region"] = "—"

        purchase_history.append(
            transaction
        )

    # -----------------------------------------------------
    # PRODUCT MIX
    # -----------------------------------------------------

    product_mix = []

    if product_column:

        product_group = (
            customer_dataframe
            .groupby(product_column)
            .agg(
                purchases=(sales_column, "count"),
                revenue=(sales_column, "sum")
            )
            .reset_index()
            .sort_values(
                "revenue",
                ascending=False
            )
            .head(8)
        )

        for _, row in product_group.iterrows():

            product_mix.append({

                "product": str(
                    row[product_column]
                ),

                "purchases": int(
                    row["purchases"]
                ),

                "revenue": float(
                    row["revenue"]
                )
            })

    # -----------------------------------------------------
    # MONTHLY CUSTOMER REVENUE
    # -----------------------------------------------------

    monthly_customer = (
        customer_dataframe
        .set_index(date_column)
        .resample("ME")[sales_column]
        .sum()
    )

    monthly_labels = [
        date.strftime("%b %Y")
        for date in monthly_customer.index
    ]

    monthly_values = [
        round(float(value), 2)
        for value in monthly_customer.values
    ]

    # -----------------------------------------------------
    # RECENCY STATUS
    # -----------------------------------------------------

    if recency <= 30:

        recency_status = "Recently Active"
        recency_class = "positive"

    elif recency <= 90:

        recency_status = "Moderately Active"
        recency_class = "info"

    elif recency <= 180:

        recency_status = "Needs Attention"
        recency_class = "warning"

    else:

        recency_status = "Inactive Risk"
        recency_class = "negative"

    # -----------------------------------------------------
    # CUSTOMER VALUE RANK
    # -----------------------------------------------------

    customer_rank = (
        all_customer_rfm["monetary"]
        .rank(
            method="min",
            ascending=False
        )
    )

    rank_row = all_customer_rfm[
        all_customer_rfm[customer_column].astype(str).str.strip()
        == customer_id
    ]

    if not rank_row.empty:

        customer_value_rank = int(
            customer_rank.loc[
                rank_row.index[0]
            ]
        )

    else:

        customer_value_rank = 0

    total_analyzed_customers = len(
        all_customer_rfm
    )

    # -----------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------

    context = {

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "has_data": True,

        "customer_found": True,

        # Customer identity
        "customer_id": customer_id,

        # Columns
        "customer_column": customer_column,
        "date_column": date_column,
        "sales_column": sales_column,
        "quantity_column": quantity_column,
        "product_column": product_column,
        "region_column": region_column,
        "discount_column": discount_column,

        # RFM
        "recency": recency,
        "frequency": frequency,
        "monetary": monetary,

        "recency_score": recency_score,
        "frequency_score": frequency_score,
        "monetary_score": monetary_score,

        "rfm_score": rfm_score,

        "segment": segment,

        # Financial
        "average_order_value": average_order_value,
        "total_quantity": total_quantity,
        "average_discount": average_discount,

        # Dates
        "first_purchase": first_purchase.strftime(
            "%d %b %Y"
        ),

        "last_purchase": last_purchase.strftime(
            "%d %b %Y"
        ),

        "analysis_date": analysis_date.strftime(
            "%d %b %Y"
        ),

        # Status
        "recency_status": recency_status,
        "recency_class": recency_class,

        # Ranking
        "customer_value_rank": customer_value_rank,

        "total_analyzed_customers":
            total_analyzed_customers,

        # Action
        "recommended_action":
            recommended_action,

        "action_type":
            action_type,

        # Tables
        "purchase_history":
            purchase_history,

        "product_mix":
            product_mix,

        # Chart
        "monthly_labels":
            json.dumps(monthly_labels),

        "monthly_values":
            json.dumps(monthly_values),
    }

    return render(
        request,
        "analytics/customer_detail.html",
        context
    )
@login_required
def customer_detail(request):
    if not user_is_approved(request):
        return redirect("accounts:login")

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True
    ).order_by("-uploaded_at")

    if not datasets.exists():
        return render(
            request,
            "analytics/customer_detail.html",
            {
                "datasets": datasets,
                "detail_available": False,
                "detail_message": "No datasets are available."
            }
        )

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        selected_dataset = datasets.filter(id=dataset_id).first()
    else:
        selected_dataset = datasets.first()

    if not selected_dataset:
        selected_dataset = datasets.first()

    customer_id = request.GET.get("customer", "").strip()

    if not customer_id:
        return render(
            request,
            "analytics/customer_detail.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "detail_available": False,
                "detail_message": "No customer was selected."
            }
        )

    cleaned_version = get_cleaned_version(selected_dataset)

    if not cleaned_version:
        return render(
            request,
            "analytics/customer_detail.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "detail_available": False,
                "detail_message": "This dataset does not have a cleaned version yet."
            }
        )

    dataframe = read_dataset(cleaned_version)

    if dataframe is None or dataframe.empty:
        return render(
            request,
            "analytics/customer_detail.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "detail_available": False,
                "detail_message": "The cleaned dataset could not be read."
            }
        )

    dataframe.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in dataframe.columns
    ]

    customer_column = find_column(
        dataframe,
        [
            "customer_id",
            "customerid",
            "customer",
            "customer_name",
            "client_id",
            "client",
            "user_id",
            "user",
        ]
    )

    date_column = find_column(
        dataframe,
        [
            "date",
            "order_date",
            "sales_date",
            "transaction_date",
            "purchase_date",
            "created_at",
        ]
    )

    sales_column = find_column(
        dataframe,
        [
            "sales",
            "revenue",
            "amount",
            "total_sales",
            "total_revenue",
            "order_value",
        ]
    )

    quantity_column = find_column(
        dataframe,
        [
            "quantity",
            "qty",
            "units",
            "units_sold",
        ]
    )

    product_column = find_column(
        dataframe,
        [
            "product",
            "product_name",
            "item",
            "item_name",
            "sku",
        ]
    )

    region_column = find_column(
        dataframe,
        [
            "region",
            "area",
            "city",
            "state",
            "location",
        ]
    )

    discount_column = find_column(
        dataframe,
        [
            "discount",
            "discount_percent",
            "discount_percentage",
        ]
    )

    order_column = find_column(
        dataframe,
        [
            "order_id",
            "order",
            "transaction_id",
            "invoice_id",
            "invoice",
            "transaction",
        ]
    )

    required_columns = [
        customer_column,
        date_column,
        sales_column,
    ]

    if not all(required_columns):
        return render(
            request,
            "analytics/customer_detail.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "detail_available": False,
                "detail_message": (
                    "This dataset does not contain the required "
                    "customer, date and sales columns."
                ),
            }
        )

    dataframe[customer_column] = (
        dataframe[customer_column]
        .astype(str)
        .str.strip()
    )

    dataframe[date_column] = pd.to_datetime(
        dataframe[date_column],
        errors="coerce"
    )

    dataframe[sales_column] = pd.to_numeric(
        dataframe[sales_column],
        errors="coerce"
    )

    dataframe = dataframe.dropna(
        subset=[
            customer_column,
            date_column,
            sales_column,
        ]
    )

    customer_dataframe = dataframe[
        dataframe[customer_column] == customer_id
    ].copy()

    if customer_dataframe.empty:
        return render(
            request,
            "analytics/customer_detail.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "customer_id": customer_id,
                "detail_available": False,
                "detail_message": (
                    f"Customer '{customer_id}' was not found "
                    "in the cleaned dataset."
                ),
            }
        )

    customer_dataframe = customer_dataframe.sort_values(
        date_column,
        ascending=False
    )

    # ---------------------------------------------------------
    # CUSTOMER METRICS
    # ---------------------------------------------------------

    total_spend = float(
        customer_dataframe[sales_column].sum()
    )

    if order_column:
        customer_dataframe[order_column] = (
            customer_dataframe[order_column]
            .astype(str)
            .str.strip()
        )

        transactions = int(
            customer_dataframe[order_column]
            .nunique()
        )
    else:
        transactions = int(len(customer_dataframe))

    average_order_value = (
        total_spend / transactions
        if transactions
        else 0
    )

    if quantity_column:
        customer_dataframe[quantity_column] = pd.to_numeric(
            customer_dataframe[quantity_column],
            errors="coerce"
        )

        total_quantity = float(
            customer_dataframe[quantity_column].fillna(0).sum()
        )
    else:
        total_quantity = 0

    first_purchase = customer_dataframe[
        date_column
    ].min()

    last_purchase = customer_dataframe[
        date_column
    ].max()

    analysis_date = dataframe[date_column].max()

    recency = int(
        max(
            0,
            (analysis_date - last_purchase).days
        )
    )

    # ---------------------------------------------------------
    # RFM SCORE
    # ---------------------------------------------------------

    all_customer_rfm = (
        dataframe
        .groupby(customer_column)
        .agg(
            last_purchase=(date_column, "max"),
            frequency=(date_column, "count"),
            monetary=(sales_column, "sum"),
        )
        .reset_index()
    )

    all_customer_rfm["recency"] = (
        analysis_date -
        all_customer_rfm["last_purchase"]
    ).dt.days

    if len(all_customer_rfm) >= 2:

        try:
            all_customer_rfm["recency_score"] = pd.qcut(
                all_customer_rfm["recency"].rank(
                    method="first"
                ),
                5,
                labels=[5, 4, 3, 2, 1]
            ).astype(int)

            all_customer_rfm["frequency_score"] = pd.qcut(
                all_customer_rfm["frequency"].rank(
                    method="first"
                ),
                5,
                labels=[1, 2, 3, 4, 5]
            ).astype(int)

            all_customer_rfm["monetary_score"] = pd.qcut(
                all_customer_rfm["monetary"].rank(
                    method="first"
                ),
                5,
                labels=[1, 2, 3, 4, 5]
            ).astype(int)

        except ValueError:
            all_customer_rfm["recency_score"] = 5
            all_customer_rfm["frequency_score"] = 5
            all_customer_rfm["monetary_score"] = 5

    else:
        all_customer_rfm["recency_score"] = 5
        all_customer_rfm["frequency_score"] = 5
        all_customer_rfm["monetary_score"] = 5

    all_customer_rfm["rfm_score"] = (
        all_customer_rfm["recency_score"]
        + all_customer_rfm["frequency_score"]
        + all_customer_rfm["monetary_score"]
    )

    def assign_segment(row):
        if (
            row["monetary_score"] >= 4
            and row["frequency_score"] >= 4
            and row["recency_score"] >= 4
        ):
            return "High Value"

        if (
            row["frequency_score"] >= 4
            and row["recency_score"] >= 3
        ):
            return "Loyal"

        if row["recency_score"] <= 2 and row["frequency_score"] >= 3:
            return "At Risk"

        if row["recency"] <= 30 and row["frequency"] <= 2:
            return "New"

        return "Low Value"

    all_customer_rfm["segment"] = (
        all_customer_rfm.apply(
            assign_segment,
            axis=1
        )
    )

    selected_rfm = all_customer_rfm[
        all_customer_rfm[customer_column] == customer_id
    ]

    if not selected_rfm.empty:
        rfm_row = selected_rfm.iloc[0]

        rfm_recency_score = int(
            rfm_row["recency_score"]
        )

        rfm_frequency_score = int(
            rfm_row["frequency_score"]
        )

        rfm_monetary_score = int(
            rfm_row["monetary_score"]
        )

        rfm_score = int(
            rfm_row["rfm_score"]
        )

        segment = str(
            rfm_row["segment"]
        )

    else:
        rfm_recency_score = 0
        rfm_frequency_score = 0
        rfm_monetary_score = 0
        rfm_score = 0
        segment = "Unknown"

    # ---------------------------------------------------------
    # RECOMMENDED ACTION
    # ---------------------------------------------------------

    recommendations = {
        "High Value": (
            "Protect this customer with VIP retention, "
            "loyalty benefits and personalized offers."
        ),

        "Loyal": (
            "Strengthen loyalty through cross-selling, "
            "bundles and loyalty-program benefits."
        ),

        "New": (
            "Focus on onboarding and encourage the customer's "
            "second purchase."
        ),

        "At Risk": (
            "Launch a win-back campaign using personalized "
            "offers and relevant products."
        ),

        "Low Value": (
            "Use targeted promotions while keeping customer "
            "retention costs efficient."
        ),
    }

    recommended_action = recommendations.get(
        segment,
        "Monitor customer activity and purchasing behavior."
    )

    # ---------------------------------------------------------
    # MONTHLY SPEND
    # ---------------------------------------------------------

    monthly_spend = (
        customer_dataframe
        .set_index(date_column)[sales_column]
        .resample("ME")
        .sum()
    )

    monthly_labels = [
        date.strftime("%b %Y")
        for date in monthly_spend.index
    ]

    monthly_values = [
        round(float(value), 2)
        for value in monthly_spend.values
    ]

    # ---------------------------------------------------------
    # PRODUCT MIX
    # ---------------------------------------------------------

    product_mix = []

    if product_column:

        product_group = (
            customer_dataframe
            .groupby(product_column)
            .agg(
                revenue=(sales_column, "sum"),
                transactions=(sales_column, "count"),
            )
            .reset_index()
            .sort_values(
                "revenue",
                ascending=False
            )
        )

        for _, row in product_group.iterrows():

            product_mix.append({
                "product": str(
                    row[product_column]
                ),

                "revenue": round(
                    float(row["revenue"]),
                    2
                ),

                "transactions": int(
                    row["transactions"]
                ),
            })

    # ---------------------------------------------------------
    # PURCHASE HISTORY
    # ---------------------------------------------------------

    purchase_history = []

    for _, row in customer_dataframe.head(50).iterrows():

        purchase_history.append({
            "date": row[date_column].strftime(
                "%d %b %Y"
            ),

            "product": (
                str(row[product_column])
                if product_column
                else "—"
            ),

            "region": (
                str(row[region_column])
                if region_column
                else "—"
            ),

            "sales": round(
                float(row[sales_column]),
                2
            ),

            "quantity": (
                round(
                    float(row[quantity_column]),
                    2
                )
                if quantity_column
                and pd.notna(row[quantity_column])
                else "—"
            ),

            "discount": (
                round(
                    float(row[discount_column]),
                    2
                )
                if discount_column
                and pd.notna(row[discount_column])
                else "—"
            ),
        })

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "customer_id": customer_id,

        "detail_available": True,

        "total_spend": round(
            total_spend,
            2
        ),

        "transactions": transactions,

        "average_order_value": round(
            average_order_value,
            2
        ),

        "total_quantity": round(
            total_quantity,
            2
        ),

        "first_purchase": (
            first_purchase.strftime("%d %b %Y")
            if pd.notna(first_purchase)
            else "—"
        ),

        "last_purchase": (
            last_purchase.strftime("%d %b %Y")
            if pd.notna(last_purchase)
            else "—"
        ),

        "recency": recency,

        "segment": segment,

        "rfm_score": rfm_score,
        "rfm_recency_score": rfm_recency_score,
        "rfm_frequency_score": rfm_frequency_score,
        "rfm_monetary_score": rfm_monetary_score,

        "recommended_action": recommended_action,

        "monthly_labels": json.dumps(
            monthly_labels
        ),

        "monthly_values": json.dumps(
            monthly_values
        ),

        "product_mix": product_mix,

        "purchase_history": purchase_history,

        "source_rows": len(customer_dataframe),

        "columns_used": {
            "customer": customer_column,
            "date": date_column,
            "sales": sales_column,
            "quantity": quantity_column,
            "product": product_column,
            "region": region_column,
            "discount": discount_column,
            "order": order_column,
        },
    }

    return render(
        request,
        "analytics/customer_detail.html",
        context
    )


@login_required
def product_intelligence(request):

    # =========================================================
    # DATASETS BELONGING TO CURRENT USER
    # =========================================================

    datasets = Dataset.objects.filter(
        owner=request.user
    ).order_by("-uploaded_at")

    selected_dataset = None

    has_data = False

    # =========================================================
    # DEFAULT VALUES
    # =========================================================

    total_products = 0
    total_revenue = 0
    total_units = 0
    average_product_revenue = 0

    best_selling_product = "-"
    highest_revenue_product = "-"
    low_performing_products = 0

    product_rows = []

    product_labels = []
    product_revenue_values = []
    product_quantity_values = []

    product_insights = []

    product_column = None
    sales_column = None
    quantity_column = None
    date_column = None
    return_column = None

    # =========================================================
    # SELECT DATASET
    # =========================================================

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        selected_dataset = datasets.filter(
            id=dataset_id
        ).first()

    if not selected_dataset:
        selected_dataset = datasets.first()

    # =========================================================
    # NO DATASET
    # =========================================================

    if not selected_dataset:

        return render(
            request,
            "analytics/product_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": None,
                "has_data": False,
            }
        )

    # =========================================================
    # GET CLEANED VERSION
    # =========================================================

    cleaned_version = (
        DatasetVersion.objects
        .filter(
            dataset=selected_dataset,
            version_type="Cleaned"
        )
        .order_by(
            "-version_number",
            "-created_at"
        )
        .first()
    )

    # =========================================================
    # FALLBACK
    #
    # If there is no Cleaned version yet, use the current
    # version if it exists.
    # =========================================================

    if not cleaned_version:

        cleaned_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                is_current=True
            )
            .order_by(
                "-version_number",
                "-created_at"
            )
            .first()
        )

    # =========================================================
    # STILL NO VERSION
    # =========================================================

    if not cleaned_version:

        return render(
            request,
            "analytics/product_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    "No cleaned dataset version is available."
                ),
            }
        )

    # =========================================================
    # GET FILE
    # =========================================================

    cleaned_file = cleaned_version.file

    if not cleaned_file:

        return render(
            request,
            "analytics/product_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    "The cleaned dataset file is unavailable."
                ),
            }
        )

    # =========================================================
    # READ FILE
    # =========================================================

    try:

        file_path = cleaned_file.path

        if file_path.lower().endswith(".csv"):

            df = pd.read_csv(
                file_path
            )

        elif file_path.lower().endswith(
            (".xlsx", ".xls")
        ):

            df = pd.read_excel(
                file_path
            )

        else:

            return render(
                request,
                "analytics/product_intelligence.html",
                {
                    "datasets": datasets,
                    "selected_dataset": selected_dataset,
                    "has_data": False,
                    "error_message": (
                        "Unsupported cleaned dataset format."
                    ),
                }
            )

    except Exception as e:

        return render(
            request,
            "analytics/product_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    f"Unable to read cleaned dataset: {e}"
                ),
            }
        )

    # =========================================================
    # CLEAN COLUMN NAMES
    # =========================================================

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # =========================================================
    # COLUMN DETECTION
    # =========================================================

    normalized_columns = {
        str(column).lower().strip(): column
        for column in df.columns
    }

    def find_column(candidates):

        # Exact match first
        for candidate in candidates:

            key = candidate.lower().strip()

            if key in normalized_columns:

                return normalized_columns[key]

        # Partial match second
        for column in df.columns:

            column_lower = (
                str(column)
                .lower()
                .strip()
            )

            for candidate in candidates:

                candidate_lower = (
                    candidate.lower()
                    .strip()
                )

                if candidate_lower in column_lower:

                    return column

        return None

    # =========================================================
    # PRODUCT
    # =========================================================

    product_column = find_column([
        "product",
        "product name",
        "product_name",
        "product id",
        "product_id",
        "item",
        "item name",
        "item_name",
        "sku",
    ])

    # =========================================================
    # SALES
    # =========================================================

    sales_column = find_column([
        "sales",
        "revenue",
        "amount",
        "total sales",
        "total_sales",
        "order value",
        "order_value",
        "net sales",
        "net_sales",
    ])

    # =========================================================
    # QUANTITY
    # =========================================================

    quantity_column = find_column([
        "quantity",
        "qty",
        "units",
        "units sold",
        "units_sold",
    ])

    # =========================================================
    # DATE
    # =========================================================

    date_column = find_column([
        "date",
        "order date",
        "order_date",
        "transaction date",
        "transaction_date",
    ])

    # =========================================================
    # RETURNS
    # =========================================================

    return_column = find_column([
        "return",
        "returns",
        "returned",
        "return quantity",
        "return_quantity",
    ])

    # =========================================================
    # PRODUCT + SALES ARE REQUIRED
    # =========================================================

    if not product_column or not sales_column:

        return render(
            request,
            "analytics/product_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    "Product and sales columns "
                    "could not be detected."
                ),
            }
        )

    # =========================================================
    # WORKING COPY
    # =========================================================

    work_df = df.copy()

    # Remove missing products BEFORE converting to string.
    work_df = work_df[
        work_df[product_column].notna()
    ]

    # Convert product to clean text.
    work_df[product_column] = (
        work_df[product_column]
        .astype(str)
        .str.strip()
    )

    # Remove empty / nan products.
    work_df = work_df[
        ~work_df[product_column]
        .str.lower()
        .isin(["", "nan", "none", "null"])
    ]

    # =========================================================
    # SALES
    # =========================================================

    work_df[sales_column] = pd.to_numeric(
        work_df[sales_column],
        errors="coerce"
    ).fillna(0)

    # =========================================================
    # QUANTITY
    # =========================================================

    if quantity_column:

        work_df[quantity_column] = pd.to_numeric(
            work_df[quantity_column],
            errors="coerce"
        ).fillna(0)

    else:

        work_df["_quantity_"] = 1

        quantity_column = "_quantity_"

    # =========================================================
    # NO VALID DATA
    # =========================================================

    if work_df.empty:

        return render(
            request,
            "analytics/product_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    "The cleaned dataset contains "
                    "no valid product records."
                ),
            }
        )

    # =========================================================
    # GROUP BY PRODUCT
    # =========================================================

    grouped = (
        work_df
        .groupby(
            product_column,
            dropna=False
        )
        .agg(
            revenue=(
                sales_column,
                "sum"
            ),
            units=(
                quantity_column,
                "sum"
            ),
            purchases=(
                product_column,
                "count"
            ),
        )
        .reset_index()
    )

    grouped.rename(
        columns={
            product_column: "product"
        },
        inplace=True
    )

    # =========================================================
    # NUMERIC CLEANING
    # =========================================================

    grouped["revenue"] = pd.to_numeric(
        grouped["revenue"],
        errors="coerce"
    ).fillna(0)

    grouped["units"] = pd.to_numeric(
        grouped["units"],
        errors="coerce"
    ).fillna(0)

    # =========================================================
    # BASIC KPIs
    # =========================================================

    total_products = int(
        grouped["product"].nunique()
    )

    total_revenue = float(
        grouped["revenue"].sum()
    )

    total_units = float(
        grouped["units"].sum()
    )

    average_product_revenue = (
        total_revenue / total_products
        if total_products
        else 0
    )

    # =========================================================
    # TOP PRODUCTS
    # =========================================================

    revenue_sorted = grouped.sort_values(
        "revenue",
        ascending=False
    )

    quantity_sorted = grouped.sort_values(
        "units",
        ascending=False
    )

    if not revenue_sorted.empty:

        highest_revenue_product = str(
            revenue_sorted.iloc[0]["product"]
        )

    if not quantity_sorted.empty:

        best_selling_product = str(
            quantity_sorted.iloc[0]["product"]
        )

    # =========================================================
    # GROWTH ANALYSIS
    # =========================================================

    grouped["growth"] = 0.0

    if date_column:

        try:

            work_df[date_column] = pd.to_datetime(
                work_df[date_column],
                errors="coerce"
            )

            valid_dates = work_df[
                work_df[date_column].notna()
            ]

            if not valid_dates.empty:

                latest_date = valid_dates[
                    date_column
                ].max()

                current_start = (
                    latest_date
                    - pd.Timedelta(days=30)
                )

                previous_start = (
                    latest_date
                    - pd.Timedelta(days=60)
                )

                current_df = valid_dates[
                    valid_dates[date_column]
                    >= current_start
                ]

                previous_df = valid_dates[
                    (
                        valid_dates[date_column]
                        >= previous_start
                    )
                    &
                    (
                        valid_dates[date_column]
                        < current_start
                    )
                ]

                current_product_revenue = (
                    current_df
                    .groupby(product_column)[
                        sales_column
                    ]
                    .sum()
                )

                previous_product_revenue = (
                    previous_df
                    .groupby(product_column)[
                        sales_column
                    ]
                    .sum()
                )

                def calculate_growth(product):

                    current = float(
                        current_product_revenue.get(
                            product,
                            0
                        )
                    )

                    previous = float(
                        previous_product_revenue.get(
                            product,
                            0
                        )
                    )

                    if previous > 0:

                        return (
                            (current - previous)
                            / previous
                        ) * 100

                    if current > 0:

                        return 100.0

                    return 0.0

                grouped["growth"] = (
                    grouped["product"]
                    .apply(calculate_growth)
                    .astype(float)
                )

        except Exception:

            grouped["growth"] = 0.0

    # =========================================================
    # RETURNS
    # =========================================================

    if return_column:

        work_df[return_column] = pd.to_numeric(
            work_df[return_column],
            errors="coerce"
        ).fillna(0)

        returns_by_product = (
            work_df
            .groupby(product_column)[
                return_column
            ]
            .sum()
        )

        grouped["returns"] = (
            grouped["product"]
            .map(returns_by_product)
            .fillna(0)
        )

    else:

        grouped["returns"] = 0.0

    # =========================================================
    # RETURN RATE
    # =========================================================

    grouped["return_rate"] = np.where(
        grouped["units"] > 0,
        (
            grouped["returns"]
            / grouped["units"]
        ) * 100,
        0
    )

    # =========================================================
    # PERFORMANCE BENCHMARKS
    # =========================================================

    revenue_median = (
        grouped["revenue"].median()
        if not grouped.empty
        else 0
    )

    units_median = (
        grouped["units"].median()
        if not grouped.empty
        else 0
    )

    # =========================================================
    # PRODUCT STATUS
    # =========================================================

    def determine_status(row):

        revenue = float(row["revenue"])

        units = float(row["units"])

        growth = float(row["growth"])

        return_rate = float(
            row["return_rate"]
        )

        if (
            growth >= 10
            and revenue >= revenue_median
        ):

            return "Growing"

        if (
            revenue >= revenue_median
            and units >= units_median
            and return_rate < 5
        ):

            return "Strong"

        if return_rate >= 8:

            return "Return Risk"

        if (
            growth < -10
            or revenue < revenue_median * 0.5
        ):

            return "Weak"

        return "Stable"

    grouped["status"] = grouped.apply(
        determine_status,
        axis=1
    )

    # =========================================================
    # LOW PERFORMERS
    # =========================================================

    low_performing_products = int(
        (
            grouped["status"]
            == "Weak"
        ).sum()
    )

    # =========================================================
    # PRODUCT TABLE
    # =========================================================

    table_df = (
        grouped
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(50)
    )

    for _, row in table_df.iterrows():

        product_rows.append({

            "product": str(
                row["product"]
            ),

            "revenue": round(
                float(row["revenue"]),
                2
            ),

            "units": round(
                float(row["units"]),
                2
            ),

            "growth": round(
                float(row["growth"]),
                2
            ),

            "returns": round(
                float(row["return_rate"]),
                2
            ),

            "status": str(
                row["status"]
            ),

        })

    # =========================================================
    # TOP 10 CHART
    # =========================================================

    chart_df = (
        grouped
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(10)
    )

    product_labels = [
        str(value)
        for value in chart_df["product"]
    ]

    product_revenue_values = [
        round(
            float(value),
            2
        )
        for value in chart_df["revenue"]
    ]

    product_quantity_values = [
        round(
            float(value),
            2
        )
        for value in chart_df["units"]
    ]

    # =========================================================
    # AUTOMATIC PRODUCT INSIGHTS
    # =========================================================

    if not grouped.empty:

        top_product = (
            grouped
            .sort_values(
                "revenue",
                ascending=False
            )
            .iloc[0]
        )

        top_quantity_product = (
            grouped
            .sort_values(
                "units",
                ascending=False
            )
            .iloc[0]
        )

        high_return_products = grouped[
            grouped["return_rate"] >= 8
        ]

        growing_products = grouped[
            grouped["growth"] >= 10
        ]

        declining_products = grouped[
            grouped["growth"] <= -10
        ]

        # Revenue leader

        product_insights.append({

            "type": "positive",

            "title": "Revenue Leader",

            "text": (
                f"{top_product['product']} "
                f"is the highest "
                f"revenue-generating product "
                f"with ₹"
                f"{top_product['revenue']:,.0f} "
                f"in recorded sales."
            ),

        })

        # Best seller

        product_insights.append({

            "type": "positive",

            "title": "Best Seller",

            "text": (
                f"{top_quantity_product['product']} "
                f"has the highest unit sales "
                f"with "
                f"{top_quantity_product['units']:,.0f} "
                f"units recorded."
            ),

        })

        # Growing

        if not growing_products.empty:

            product_insights.append({

                "type": "positive",

                "title": "Growing Demand",

                "text": (
                    f"{len(growing_products)} "
                    f"product(s) show strong "
                    f"recent growth of at least 10%."
                ),

            })

        # Declining

        if not declining_products.empty:

            product_insights.append({

                "type": "warning",

                "title": "Declining Products",

                "text": (
                    f"{len(declining_products)} "
                    f"product(s) show a recent "
                    f"decline of at least 10%."
                ),

            })

        # Return risk

        if not high_return_products.empty:

            product_insights.append({

                "type": "negative",

                "title": "Return Risk",

                "text": (
                    f"{len(high_return_products)} "
                    f"product(s) have return rates "
                    f"of 8% or higher and require "
                    f"investigation."
                ),

            })

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        "datasets": datasets,

        "selected_dataset":
            selected_dataset,

        "selected_version":
            cleaned_version,

        "has_data":
            True,

        "total_products":
            total_products,

        "total_revenue":
            total_revenue,

        "total_units":
            total_units,

        "average_product_revenue":
            average_product_revenue,

        "best_selling_product":
            best_selling_product,

        "highest_revenue_product":
            highest_revenue_product,

        "low_performing_products":
            low_performing_products,

        "product_rows":
            product_rows,

        "product_labels":
            json.dumps(
                product_labels
            ),

        "product_revenue_values":
            json.dumps(
                product_revenue_values
            ),

        "product_quantity_values":
            json.dumps(
                product_quantity_values
            ),

        "product_insights":
            product_insights,

        "product_column":
            product_column,

        "sales_column":
            sales_column,

        "quantity_column":
            quantity_column,

        "date_column":
            date_column,

        "return_column":
            return_column,

    }

    return render(
        request,
        "analytics/product_intelligence.html",
        context
    )

@login_required
def regional_intelligence(request):

    datasets = Dataset.objects.filter(
        owner=request.user
    ).order_by("-uploaded_at")

    selected_dataset = None
    has_data = False

    total_regions = 0
    total_revenue = 0
    total_units = 0
    average_region_revenue = 0

    top_region = "-"
    lowest_region = "-"

    regional_rows = []

    region_labels = []
    region_revenue_values = []
    region_quantity_values = []

    regional_insights = []

    region_column = None
    sales_column = None
    quantity_column = None
    date_column = None
    return_column = None

    # =========================================================
    # SELECT DATASET
    # =========================================================

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        selected_dataset = datasets.filter(
            id=dataset_id
        ).first()

    if not selected_dataset:
        selected_dataset = datasets.first()

    if not selected_dataset:
        return render(
            request,
            "analytics/regional_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": None,
                "has_data": False,
            }
        )

    # =========================================================
    # GET CLEANED VERSION
    # =========================================================

    cleaned_version = (
        DatasetVersion.objects
        .filter(
            dataset=selected_dataset,
            version_type="Cleaned"
        )
        .order_by(
            "-version_number",
            "-created_at"
        )
        .first()
    )

    # Fallback to current version
    if not cleaned_version:

        cleaned_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                is_current=True
            )
            .order_by(
                "-version_number",
                "-created_at"
            )
            .first()
        )

    if not cleaned_version:

        return render(
            request,
            "analytics/regional_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    "No cleaned dataset version is available."
                ),
            }
        )

    # =========================================================
    # READ CLEANED FILE
    # =========================================================

    cleaned_file = cleaned_version.file

    if not cleaned_file:

        return render(
            request,
            "analytics/regional_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    "The cleaned dataset file is unavailable."
                ),
            }
        )

    try:

        file_path = cleaned_file.path

        if file_path.lower().endswith(".csv"):

            df = pd.read_csv(file_path)

        elif file_path.lower().endswith(
            (".xlsx", ".xls")
        ):

            df = pd.read_excel(file_path)

        else:

            return render(
                request,
                "analytics/regional_intelligence.html",
                {
                    "datasets": datasets,
                    "selected_dataset": selected_dataset,
                    "has_data": False,
                    "error_message": (
                        "Unsupported dataset format."
                    ),
                }
            )

    except Exception as e:

        return render(
            request,
            "analytics/regional_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    f"Unable to read cleaned dataset: {e}"
                ),
            }
        )

    # =========================================================
    # NORMALIZE COLUMN NAMES
    # =========================================================

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    normalized_columns = {
        str(column).lower().strip(): column
        for column in df.columns
    }

    def find_column(candidates):

        for candidate in candidates:

            key = candidate.lower().strip()

            if key in normalized_columns:
                return normalized_columns[key]

        for column in df.columns:

            column_lower = (
                str(column)
                .lower()
                .strip()
            )

            for candidate in candidates:

                candidate_lower = (
                    candidate.lower().strip()
                )

                if candidate_lower in column_lower:
                    return column

        return None

    # =========================================================
    # DETECT COLUMNS
    # =========================================================

    region_column = find_column([
        "region",
        "region name",
        "region_name",
        "area",
        "area name",
        "area_name",
        "territory",
        "zone",
        "location",
    ])

    sales_column = find_column([
        "sales",
        "revenue",
        "amount",
        "total sales",
        "total_sales",
        "order value",
        "order_value",
        "net sales",
        "net_sales",
    ])

    quantity_column = find_column([
        "quantity",
        "qty",
        "units",
        "units sold",
        "units_sold",
    ])

    date_column = find_column([
        "date",
        "order date",
        "order_date",
        "transaction date",
        "transaction_date",
    ])

    return_column = find_column([
        "return",
        "returns",
        "returned",
        "return quantity",
        "return_quantity",
    ])

    # =========================================================
    # REQUIRED COLUMNS
    # =========================================================

    if not region_column or not sales_column:

        return render(
            request,
            "analytics/regional_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    "Region and sales columns "
                    "could not be detected."
                ),
            }
        )

    # =========================================================
    # WORKING DATAFRAME
    # =========================================================

    work_df = df.copy()

    # Remove missing regions first
    work_df = work_df[
        work_df[region_column].notna()
    ]

    work_df[region_column] = (
        work_df[region_column]
        .astype(str)
        .str.strip()
    )

    # Remove invalid region names
    work_df = work_df[
        ~work_df[region_column]
        .str.lower()
        .isin([
            "",
            "nan",
            "none",
            "null",
        ])
    ]

    # =========================================================
    # SALES
    # =========================================================

    work_df[sales_column] = pd.to_numeric(
        work_df[sales_column],
        errors="coerce"
    ).fillna(0)

    # =========================================================
    # QUANTITY
    # =========================================================

    if quantity_column:

        work_df[quantity_column] = pd.to_numeric(
            work_df[quantity_column],
            errors="coerce"
        ).fillna(0)

    else:

        work_df["_quantity_"] = 1
        quantity_column = "_quantity_"

    if work_df.empty:

        return render(
            request,
            "analytics/regional_intelligence.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "has_data": False,
                "error_message": (
                    "The cleaned dataset contains "
                    "no valid regional records."
                ),
            }
        )

    # =========================================================
    # GROUP BY REGION
    # =========================================================

    grouped = (
        work_df
        .groupby(
            region_column,
            dropna=False
        )
        .agg(
            revenue=(
                sales_column,
                "sum"
            ),
            units=(
                quantity_column,
                "sum"
            ),
            orders=(
                region_column,
                "count"
            ),
        )
        .reset_index()
    )

    grouped.rename(
        columns={
            region_column: "region"
        },
        inplace=True
    )

    grouped["revenue"] = pd.to_numeric(
        grouped["revenue"],
        errors="coerce"
    ).fillna(0)

    grouped["units"] = pd.to_numeric(
        grouped["units"],
        errors="coerce"
    ).fillna(0)

    # =========================================================
    # BASIC KPIs
    # =========================================================

    total_regions = int(
        grouped["region"].nunique()
    )

    total_revenue = float(
        grouped["revenue"].sum()
    )

    total_units = float(
        grouped["units"].sum()
    )

    average_region_revenue = (
        total_revenue / total_regions
        if total_regions
        else 0
    )

    # =========================================================
    # REGIONAL GROWTH
    # =========================================================

    grouped["growth"] = 0.0

    if date_column:

        try:

            work_df[date_column] = pd.to_datetime(
                work_df[date_column],
                errors="coerce"
            )

            valid_dates = work_df[
                work_df[date_column].notna()
            ]

            if not valid_dates.empty:

                latest_date = valid_dates[
                    date_column
                ].max()

                current_start = (
                    latest_date
                    - pd.Timedelta(days=30)
                )

                previous_start = (
                    latest_date
                    - pd.Timedelta(days=60)
                )

                current_df = valid_dates[
                    valid_dates[date_column]
                    >= current_start
                ]

                previous_df = valid_dates[
                    (
                        valid_dates[date_column]
                        >= previous_start
                    )
                    &
                    (
                        valid_dates[date_column]
                        < current_start
                    )
                ]

                current_revenue = (
                    current_df
                    .groupby(region_column)[
                        sales_column
                    ]
                    .sum()
                )

                previous_revenue = (
                    previous_df
                    .groupby(region_column)[
                        sales_column
                    ]
                    .sum()
                )

                def calculate_growth(region):

                    current = float(
                        current_revenue.get(
                            region,
                            0
                        )
                    )

                    previous = float(
                        previous_revenue.get(
                            region,
                            0
                        )
                    )

                    if previous > 0:

                        return (
                            (current - previous)
                            / previous
                        ) * 100

                    if current > 0:
                        return 100.0

                    return 0.0

                grouped["growth"] = (
                    grouped["region"]
                    .apply(calculate_growth)
                    .astype(float)
                )

        except Exception:

            grouped["growth"] = 0.0

    # =========================================================
    # RETURNS
    # =========================================================

    if return_column:

        work_df[return_column] = pd.to_numeric(
            work_df[return_column],
            errors="coerce"
        ).fillna(0)

        returns_by_region = (
            work_df
            .groupby(region_column)[
                return_column
            ]
            .sum()
        )

        grouped["returns"] = (
            grouped["region"]
            .map(returns_by_region)
            .fillna(0)
        )

    else:

        grouped["returns"] = 0.0

    # =========================================================
    # RETURN RATE
    # =========================================================

    grouped["return_rate"] = np.where(
        grouped["units"] > 0,
        (
            grouped["returns"]
            / grouped["units"]
        ) * 100,
        0
    )

    # =========================================================
    # PERFORMANCE BENCHMARK
    # =========================================================

    revenue_median = (
        grouped["revenue"].median()
        if not grouped.empty
        else 0
    )

    # =========================================================
    # REGIONAL STATUS
    # =========================================================

    def determine_status(row):

        revenue = float(row["revenue"])
        growth = float(row["growth"])
        return_rate = float(row["return_rate"])

        if return_rate >= 8:
            return "Return Risk"

        if (
            growth >= 10
            and revenue >= revenue_median
        ):
            return "Growing"

        if (
            revenue >= revenue_median
            and return_rate < 5
        ):
            return "Strong"

        if (
            growth < -10
            or revenue < revenue_median * 0.5
        ):
            return "Weak"

        return "Stable"

    grouped["status"] = grouped.apply(
        determine_status,
        axis=1
    )

    # =========================================================
    # TOP / LOWEST REGION
    # =========================================================

    revenue_sorted = grouped.sort_values(
        "revenue",
        ascending=False
    )

    if not revenue_sorted.empty:

        top_region = str(
            revenue_sorted.iloc[0]["region"]
        )

        lowest_region = str(
            revenue_sorted.iloc[-1]["region"]
        )

    # =========================================================
    # REGIONAL TABLE
    # =========================================================

    table_df = (
        grouped
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(50)
    )

    for _, row in table_df.iterrows():

        regional_rows.append({

            "region": str(
                row["region"]
            ),

            "revenue": round(
                float(row["revenue"]),
                2
            ),

            "units": round(
                float(row["units"]),
                2
            ),

            "orders": int(
                row["orders"]
            ),

            "growth": round(
                float(row["growth"]),
                2
            ),

            "returns": round(
                float(row["return_rate"]),
                2
            ),

            "status": str(
                row["status"]
            ),

        })

    # =========================================================
    # TOP 10 REGIONS FOR CHART
    # =========================================================

    chart_df = (
        grouped
        .sort_values(
            "revenue",
            ascending=False
        )
        .head(10)
    )

    region_labels = [
        str(value)
        for value in chart_df["region"]
    ]

    region_revenue_values = [
        round(
            float(value),
            2
        )
        for value in chart_df["revenue"]
    ]

    region_quantity_values = [
        round(
            float(value),
            2
        )
        for value in chart_df["units"]
    ]

    # =========================================================
    # AUTOMATIC INSIGHTS
    # =========================================================

    if not grouped.empty:

        growing_regions = grouped[
            grouped["growth"] >= 10
        ]

        declining_regions = grouped[
            grouped["growth"] <= -10
        ]

        return_risk_regions = grouped[
            grouped["return_rate"] >= 8
        ]

        top = grouped.sort_values(
            "revenue",
            ascending=False
        ).iloc[0]

        # Revenue leader

        regional_insights.append({

            "type": "positive",

            "title": "Regional Leader",

            "text": (
                f"{top['region']} is the "
                f"highest-performing region "
                f"with ₹"
                f"{top['revenue']:,.0f} "
                f"in recorded revenue."
            ),

        })

        # Growing regions

        if not growing_regions.empty:

            regional_insights.append({

                "type": "positive",

                "title": "Regional Growth",

                "text": (
                    f"{len(growing_regions)} "
                    f"region(s) show recent "
                    f"growth of at least 10%."
                ),

            })

        # Declining regions

        if not declining_regions.empty:

            regional_insights.append({

                "type": "warning",

                "title": "Declining Regions",

                "text": (
                    f"{len(declining_regions)} "
                    f"region(s) show a recent "
                    f"decline of at least 10%."
                ),

            })

        # Return risk

        if not return_risk_regions.empty:

            regional_insights.append({

                "type": "negative",

                "title": "Regional Return Risk",

                "text": (
                    f"{len(return_risk_regions)} "
                    f"region(s) have return "
                    f"rates of 8% or higher."
                ),

            })

    # =========================================================
    # FINAL CONTEXT
    # =========================================================

    context = {

        "datasets": datasets,

        "selected_dataset":
            selected_dataset,

        "selected_version":
            cleaned_version,

        "has_data":
            True,

        "total_regions":
            total_regions,

        "total_revenue":
            total_revenue,

        "total_units":
            total_units,

        "average_region_revenue":
            average_region_revenue,

        "top_region":
            top_region,

        "lowest_region":
            lowest_region,

        "regional_rows":
            regional_rows,

        "region_labels":
            json.dumps(
                region_labels
            ),

        "region_revenue_values":
            json.dumps(
                region_revenue_values
            ),

        "region_quantity_values":
            json.dumps(
                region_quantity_values
            ),

        "regional_insights":
            regional_insights,

        "region_column":
            region_column,

        "sales_column":
            sales_column,

        "quantity_column":
            quantity_column,

        "date_column":
            date_column,

        "return_column":
            return_column,

    }

    return render(
        request,
        "analytics/regional_intelligence.html",
        context
    )

@login_required
def sales_intelligence(request):
    """
    Sales Intelligence

    Uses the latest cleaned dataset version and produces:

    - Revenue trend
    - Monthly revenue
    - Daily sales growth
    - Monthly sales growth
    - Peak sales period
    - Lowest sales period
    - Average daily revenue
    - Current vs previous period comparison
    - Transaction comparison
    - Business insights
    - Global date-range filtering
    """

    # =========================================================
    # DATASETS
    # =========================================================

    datasets = Dataset.objects.filter(
        owner=request.user
    ).order_by("-uploaded_at")

    # =========================================================
    # GLOBAL DATE RANGE
    # =========================================================

    selected_range = request.GET.get(
        "range",
        "all",
    )

    custom_start = request.GET.get(
        "start",
        "",
    )

    custom_end = request.GET.get(
        "end",
        "",
    )

    if (
        selected_range not in DATE_RANGE_OPTIONS
        and selected_range != "custom"
    ):
        selected_range = "all"

    # =========================================================
    # INITIAL VARIABLES
    # =========================================================

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    total_revenue = 0
    total_orders = 0
    average_daily_revenue = 0
    sales_growth = 0

    peak_period = "-"
    lowest_period = "-"

    # Current vs previous period
    current_period_revenue = 0
    previous_period_revenue = 0
    revenue_change = 0

    current_period_orders = 0
    previous_period_orders = 0
    orders_change = 0

    comparison_available = False

    # Tables
    sales_rows = []

    # Charts
    sales_labels = json.dumps([])
    sales_values = json.dumps([])

    growth_labels = json.dumps([])
    growth_values = json.dumps([])

    monthly_labels = json.dumps([])
    monthly_values = json.dumps([])

    monthly_growth_values = json.dumps([])

    # Insights
    sales_insights = []

    # Column information
    sales_column = ""
    date_column = ""

    # Date range fallback
    date_range = {
        "range_key": selected_range,
        "range_label": DATE_RANGE_OPTIONS.get(
            selected_range,
            "All Data",
        ),
        "start_date": None,
        "end_date": None,
        "days": None,
    }

    # =========================================================
    # CHECK DATASETS
    # =========================================================

    if datasets.exists():

        # -----------------------------------------------------
        # SELECT DATASET
        # -----------------------------------------------------

        dataset_id = request.GET.get(
            "dataset"
        )

        if dataset_id:

            selected_dataset = datasets.filter(
                id=dataset_id
            ).first()

        # Default to latest dataset
        if not selected_dataset:

            selected_dataset = datasets.first()

        # =====================================================
        # GET CLEANED DATASET VERSION
        # =====================================================

        selected_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                version_type="Cleaned",
            )
            .order_by(
                "-version_number",
                "-created_at",
            )
            .first()
        )

        # -----------------------------------------------------
        # FALLBACK TO CURRENT VERSION
        # -----------------------------------------------------

        if not selected_version:

            selected_version = (
                DatasetVersion.objects
                .filter(
                    dataset=selected_dataset,
                    is_current=True,
                )
                .order_by(
                    "-version_number",
                    "-created_at",
                )
                .first()
            )

        # =====================================================
        # PROCESS SELECTED VERSION
        # =====================================================

        if selected_version:

            try:

                # =================================================
                # FILE PATH
                # =================================================

                cleaned_file = selected_version.file

                file_path = cleaned_file.path

                # =================================================
                # READ FILE
                # =================================================

                if file_path.lower().endswith(".csv"):

                    df = pd.read_csv(
                        file_path
                    )

                elif file_path.lower().endswith(
                    (".xlsx", ".xls")
                ):

                    df = pd.read_excel(
                        file_path
                    )

                else:

                    raise ValueError(
                        "Sales Intelligence supports "
                        "CSV and Excel files."
                    )

                # =================================================
                # VALIDATE DATAFRAME
                # =================================================

                if df.empty:

                    raise ValueError(
                        "The selected dataset is empty."
                    )

                # =================================================
                # CLEAN COLUMN NAMES
                # =================================================

                df.columns = [
                    str(column)
                    .strip()
                    .lower()
                    .replace(" ", "_")
                    for column in df.columns
                ]

                # =================================================
                # FIND SALES / REVENUE COLUMN
                # =================================================

                sales_candidates = [

                    "sales",

                    "sale",

                    "revenue",

                    "amount",

                    "total_sales",

                    "total_revenue",

                    "order_value",

                    "net_sales",

                    "sales_amount",

                    "revenue_amount",

                    "gross_sales",

                ]

                sales_column = None

                # -------------------------------------------------
                # EXACT MATCH
                # -------------------------------------------------

                for column in sales_candidates:

                    if column in df.columns:

                        sales_column = column

                        break

                # -------------------------------------------------
                # PARTIAL MATCH
                # -------------------------------------------------

                if not sales_column:

                    sales_keywords = [
                        "sales",
                        "revenue",
                        "amount",
                        "order_value",
                    ]

                    for column in df.columns:

                        if any(
                            keyword in column
                            for keyword in sales_keywords
                        ):

                            sales_column = column

                            break

                # =================================================
                # FIND DATE COLUMN
                # =================================================

                date_candidates = [

                    "date",

                    "order_date",

                    "sales_date",

                    "transaction_date",

                    "purchase_date",

                    "created_at",

                    "invoice_date",

                    "booking_date",

                    "payment_date",

                ]

                date_column = None

                # -------------------------------------------------
                # EXACT MATCH
                # -------------------------------------------------

                for column in date_candidates:

                    if column in df.columns:

                        date_column = column

                        break

                # -------------------------------------------------
                # PARTIAL MATCH
                # -------------------------------------------------

                if not date_column:

                    date_keywords = [
                        "date",
                        "created",
                        "transaction",
                        "purchase",
                        "order",
                    ]

                    for column in df.columns:

                        if any(
                            keyword in column
                            for keyword in date_keywords
                        ):

                            date_column = column

                            break

                # =================================================
                # VALIDATION
                # =================================================

                if not sales_column:

                    raise ValueError(
                        "No sales/revenue column was detected."
                    )

                if not date_column:

                    raise ValueError(
                        "No date column was detected."
                    )

                # =================================================
                # PREPARE SALES COLUMN
                # =================================================

                df[sales_column] = pd.to_numeric(
                    df[sales_column],
                    errors="coerce",
                )

                # =================================================
                # PREPARE DATE COLUMN
                # =================================================

                df[date_column] = pd.to_datetime(
                    df[date_column],
                    errors="coerce",
                )

                # =================================================
                # REMOVE INVALID RECORDS
                # =================================================

                df = df.dropna(
                    subset=[
                        sales_column,
                        date_column,
                    ]
                )

                if df.empty:

                    raise ValueError(
                        "No valid sales records were found "
                        "after cleaning."
                    )

                # =================================================
                # SORT COMPLETE DATASET
                # =================================================

                df = df.sort_values(
                    date_column
                ).reset_index(
                    drop=True
                )

                # =================================================
                # IMPORTANT:
                # KEEP COMPLETE DATASET FOR COMPARISON
                # =================================================

                df_original = df.copy()

                # =================================================
                # APPLY GLOBAL DATE RANGE
                # =================================================

                df, date_range = apply_date_filter(
                    df,
                    date_column,
                    range_key=selected_range,
                    start_date=custom_start,
                    end_date=custom_end,
                )

                # =================================================
                # VALIDATE SELECTED PERIOD
                # =================================================

                if df.empty:

                    raise ValueError(
                        "No sales records exist for the "
                        "selected date range."
                    )

                # =================================================
                # CURRENT PERIOD METRICS
                # =================================================

                current_period_revenue = float(
                    df[sales_column].sum()
                )

                current_period_orders = int(
                    len(df)
                )

                # =================================================
                # PREVIOUS EQUIVALENT PERIOD
                # =================================================

                previous_df = get_previous_period(
                    df_original,
                    date_column,
                    date_range["start_date"],
                    date_range["end_date"],
                )

                if not previous_df.empty:

                    previous_df = previous_df.copy()

                    previous_df[sales_column] = pd.to_numeric(
                        previous_df[sales_column],
                        errors="coerce",
                    )

                    previous_df = previous_df.dropna(
                        subset=[
                            sales_column,
                            date_column,
                        ]
                    )

                    if not previous_df.empty:

                        previous_period_revenue = float(
                            previous_df[sales_column].sum()
                        )

                        previous_period_orders = int(
                            len(previous_df)
                        )

                        # -----------------------------------------
                        # REVENUE CHANGE
                        # -----------------------------------------

                        revenue_change = (
                            calculate_percentage_change(
                                current_period_revenue,
                                previous_period_revenue,
                            )
                        )

                        # -----------------------------------------
                        # ORDER / TRANSACTION CHANGE
                        # -----------------------------------------

                        orders_change = (
                            calculate_percentage_change(
                                current_period_orders,
                                previous_period_orders,
                            )
                        )

                        comparison_available = True

                # =================================================
                # TOTAL METRICS
                # =================================================

                total_revenue = float(
                    df[sales_column].sum()
                )

                total_orders = int(
                    len(df)
                )

                # =================================================
                # DAILY SALES
                # =================================================

                daily_sales = (
                    df.groupby(
                        df[date_column].dt.date
                    )[sales_column]
                    .sum()
                    .reset_index()
                )

                daily_sales.columns = [
                    "date",
                    "revenue",
                ]

                daily_sales["date"] = pd.to_datetime(
                    daily_sales["date"]
                )

                daily_sales = daily_sales.sort_values(
                    "date"
                ).reset_index(
                    drop=True
                )

                # =================================================
                # AVERAGE DAILY REVENUE
                # =================================================

                if not daily_sales.empty:

                    average_daily_revenue = float(
                        daily_sales["revenue"].mean()
                    )

                # =================================================
                # DAILY GROWTH
                # =================================================

                daily_sales["growth"] = (
                    daily_sales["revenue"]
                    .pct_change()
                    .replace(
                        [
                            np.inf,
                            -np.inf,
                        ],
                        np.nan,
                    )
                    .fillna(0)
                    * 100
                )

                # =================================================
                # MONTHLY SALES
                # =================================================

                monthly_sales = (
                    df.set_index(
                        date_column
                    )
                    .resample("ME")[sales_column]
                    .sum()
                    .reset_index()
                )

                monthly_sales.columns = [
                    "date",
                    "revenue",
                ]

                # =================================================
                # MONTHLY GROWTH
                # =================================================

                monthly_sales["growth"] = (
                    monthly_sales["revenue"]
                    .pct_change()
                    .replace(
                        [
                            np.inf,
                            -np.inf,
                        ],
                        np.nan,
                    )
                    .fillna(0)
                    * 100
                )

                # =================================================
                # OVERALL SALES GROWTH
                # =================================================

                if len(monthly_sales) >= 2:

                    latest_revenue = float(
                        monthly_sales.iloc[-1]["revenue"]
                    )

                    previous_revenue = float(
                        monthly_sales.iloc[-2]["revenue"]
                    )

                    if previous_revenue != 0:

                        sales_growth = (
                            (
                                latest_revenue
                                - previous_revenue
                            )
                            / previous_revenue
                        ) * 100

                # =================================================
                # PEAK PERIOD
                # =================================================

                if not monthly_sales.empty:

                    peak_row = monthly_sales.loc[
                        monthly_sales["revenue"].idxmax()
                    ]

                    peak_period = (
                        peak_row["date"].strftime(
                            "%B %Y"
                        )
                    )

                # =================================================
                # LOWEST PERIOD
                # =================================================

                if not monthly_sales.empty:

                    lowest_row = monthly_sales.loc[
                        monthly_sales["revenue"].idxmin()
                    ]

                    lowest_period = (
                        lowest_row["date"].strftime(
                            "%B %Y"
                        )
                    )

                # =================================================
                # DAILY REVENUE CHART
                # =================================================

                sales_labels = json.dumps(
                    [
                        date.strftime("%d %b")
                        for date in daily_sales["date"]
                    ]
                )

                sales_values = json.dumps(
                    [
                        round(
                            float(value),
                            2,
                        )
                        for value in daily_sales["revenue"]
                    ]
                )

                # =================================================
                # DAILY GROWTH CHART
                # =================================================

                growth_labels = json.dumps(
                    [
                        date.strftime("%d %b")
                        for date in daily_sales["date"]
                    ]
                )

                growth_values = json.dumps(
                    [
                        round(
                            float(value),
                            2,
                        )
                        for value in daily_sales["growth"]
                    ]
                )

                # =================================================
                # MONTHLY REVENUE CHART
                # =================================================

                monthly_labels = json.dumps(
                    [
                        date.strftime("%b %Y")
                        for date in monthly_sales["date"]
                    ]
                )

                monthly_values = json.dumps(
                    [
                        round(
                            float(value),
                            2,
                        )
                        for value in monthly_sales["revenue"]
                    ]
                )

                # =================================================
                # MONTHLY GROWTH VALUES
                # =================================================

                monthly_growth_values = json.dumps(
                    [
                        round(
                            float(value),
                            2,
                        )
                        for value in monthly_sales["growth"]
                    ]
                )

                # =================================================
                # MONTHLY TABLE
                # =================================================

                for _, row in monthly_sales.tail(24).iterrows():

                    sales_rows.append(
                        {
                            "period": row["date"].strftime(
                                "%B %Y"
                            ),

                            "revenue": round(
                                float(
                                    row["revenue"]
                                ),
                                2,
                            ),

                            "growth": round(
                                float(
                                    row["growth"]
                                ),
                                2,
                            ),
                        }
                    )

                # =================================================
                # BUSINESS INSIGHTS
                # =================================================

                # -------------------------------------------------
                # REVENUE COMPARISON INSIGHT
                # -------------------------------------------------

                if comparison_available:

                    if revenue_change > 10:

                        sales_insights.append(
                            {
                                "type": "positive",

                                "title": (
                                    "Strong revenue growth"
                                ),

                                "text": (
                                    f"Revenue increased by "
                                    f"{revenue_change:.1f}% "
                                    f"compared with the "
                                    f"previous equivalent period."
                                ),
                            }
                        )

                    elif revenue_change > 0:

                        sales_insights.append(
                            {
                                "type": "positive",

                                "title": (
                                    "Revenue is growing"
                                ),

                                "text": (
                                    f"Revenue increased by "
                                    f"{revenue_change:.1f}% "
                                    f"compared with the "
                                    f"previous equivalent period."
                                ),
                            }
                        )

                    elif revenue_change < -10:

                        sales_insights.append(
                            {
                                "type": "negative",

                                "title": (
                                    "Revenue decline detected"
                                ),

                                "text": (
                                    f"Revenue decreased by "
                                    f"{abs(revenue_change):.1f}% "
                                    f"compared with the "
                                    f"previous equivalent period."
                                ),
                            }
                        )

                    elif revenue_change < 0:

                        sales_insights.append(
                            {
                                "type": "warning",

                                "title": (
                                    "Revenue is declining"
                                ),

                                "text": (
                                    f"Revenue decreased by "
                                    f"{abs(revenue_change):.1f}% "
                                    f"compared with the "
                                    f"previous equivalent period."
                                ),
                            }
                        )

                    else:

                        sales_insights.append(
                            {
                                "type": "neutral",

                                "title": (
                                    "Revenue is stable"
                                ),

                                "text": (
                                    "Revenue remained broadly "
                                    "unchanged compared with "
                                    "the previous equivalent period."
                                ),
                            }
                        )

                else:

                    # Fallback when no previous period exists
                    if sales_growth > 10:

                        sales_insights.append(
                            {
                                "type": "positive",

                                "title": (
                                    "Strong sales growth"
                                ),

                                "text": (
                                    f"Recent monthly revenue "
                                    f"growth is {sales_growth:.1f}%."
                                ),
                            }
                        )

                    elif sales_growth > 0:

                        sales_insights.append(
                            {
                                "type": "positive",

                                "title": (
                                    "Sales are growing"
                                ),

                                "text": (
                                    f"Recent monthly revenue "
                                    f"growth is {sales_growth:.1f}%."
                                ),
                            }
                        )

                    elif sales_growth < -10:

                        sales_insights.append(
                            {
                                "type": "negative",

                                "title": (
                                    "Sales decline detected"
                                ),

                                "text": (
                                    f"Recent monthly revenue "
                                    f"declined by "
                                    f"{abs(sales_growth):.1f}%."
                                ),
                            }
                        )

                    else:

                        sales_insights.append(
                            {
                                "type": "neutral",

                                "title": (
                                    "Sales are relatively stable"
                                ),

                                "text": (
                                    "Recent sales performance "
                                    "shows limited movement."
                                ),
                            }
                        )

                # =================================================
                # TRANSACTION INSIGHT
                # =================================================

                if comparison_available:

                    if orders_change > 10:

                        sales_insights.append(
                            {
                                "type": "positive",

                                "title": (
                                    "Transaction volume increased"
                                ),

                                "text": (
                                    f"Transaction volume increased "
                                    f"by {orders_change:.1f}% "
                                    f"compared with the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                    elif orders_change < -10:

                        sales_insights.append(
                            {
                                "type": "negative",

                                "title": (
                                    "Transaction volume declined"
                                ),

                                "text": (
                                    f"Transaction volume decreased "
                                    f"by {abs(orders_change):.1f}% "
                                    f"compared with the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                # =================================================
                # PEAK SALES INSIGHT
                # =================================================

                if peak_period != "-":

                    sales_insights.append(
                        {
                            "type": "positive",

                            "title": (
                                "Peak sales period"
                            ),

                            "text": (
                                f"{peak_period} generated the "
                                f"highest revenue in the "
                                f"selected analysis period."
                            ),
                        }
                    )

                # =================================================
                # LOWEST SALES INSIGHT
                # =================================================

                if lowest_period != "-":

                    sales_insights.append(
                        {
                            "type": "warning",

                            "title": (
                                "Lowest sales period"
                            ),

                            "text": (
                                f"{lowest_period} recorded the "
                                f"lowest revenue and may require "
                                f"further investigation."
                            ),
                        }
                    )

                # =================================================
                # AVERAGE DAILY REVENUE INSIGHT
                # =================================================

                sales_insights.append(
                    {
                        "type": "info",

                        "title": (
                            "Average daily revenue"
                        ),

                        "text": (
                            f"Average daily revenue is "
                            f"₹{average_daily_revenue:,.2f}."
                        ),
                    }
                )

                # =================================================
                # DATE RANGE INSIGHT
                # =================================================

                if (
                    date_range.get("start_date")
                    and date_range.get("end_date")
                ):

                    start_display = (
                        date_range["start_date"].strftime(
                            "%d %b %Y"
                        )
                    )

                    end_display = (
                        date_range["end_date"].strftime(
                            "%d %b %Y"
                        )
                    )

                    sales_insights.append(
                        {
                            "type": "info",

                            "title": (
                                "Analysis period"
                            ),

                            "text": (
                                f"Sales analysis covers "
                                f"{start_display} to "
                                f"{end_display}."
                            ),
                        }
                    )

                # =================================================
                # FINAL STATUS
                # =================================================

                has_data = True

            except Exception as exc:

                error_message = str(
                    exc
                )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # -----------------------------------------------------
        # DATASET
        # -----------------------------------------------------

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "selected_version": selected_version,

        # -----------------------------------------------------
        # STATUS
        # -----------------------------------------------------

        "has_data": has_data,

        "error_message": error_message,

        # -----------------------------------------------------
        # KPI METRICS
        # -----------------------------------------------------

        "total_revenue": total_revenue,

        "total_orders": total_orders,

        "average_daily_revenue": (
            average_daily_revenue
        ),

        "sales_growth": sales_growth,

        # -----------------------------------------------------
        # PEAK / LOWEST
        # -----------------------------------------------------

        "peak_period": peak_period,

        "lowest_period": lowest_period,

        # -----------------------------------------------------
        # CURRENT VS PREVIOUS PERIOD
        # -----------------------------------------------------

        "current_period_revenue": (
            current_period_revenue
        ),

        "previous_period_revenue": (
            previous_period_revenue
        ),

        "revenue_change": revenue_change,

        "current_period_orders": (
            current_period_orders
        ),

        "previous_period_orders": (
            previous_period_orders
        ),

        "orders_change": orders_change,

        "comparison_available": (
            comparison_available
        ),

        # -----------------------------------------------------
        # TABLE
        # -----------------------------------------------------

        "sales_rows": sales_rows,

        # -----------------------------------------------------
        # CHART DATA
        # -----------------------------------------------------

        "sales_labels": sales_labels,

        "sales_values": sales_values,

        "growth_labels": growth_labels,

        "growth_values": growth_values,

        "monthly_labels": monthly_labels,

        "monthly_values": monthly_values,

        "monthly_growth_values": (
            monthly_growth_values
        ),

        # -----------------------------------------------------
        # INSIGHTS
        # -----------------------------------------------------

        "sales_insights": sales_insights,

        # -----------------------------------------------------
        # COLUMN INFORMATION
        # -----------------------------------------------------

        "sales_column": (
            sales_column or ""
        ),

        "date_column": (
            date_column or ""
        ),

        # -----------------------------------------------------
        # DATE RANGE
        # -----------------------------------------------------

        "date_range_options": (
            DATE_RANGE_OPTIONS
        ),

        "selected_range": (
            selected_range
        ),

        "custom_start": (
            custom_start
        ),

        "custom_end": (
            custom_end
        ),

        "date_range": (
            date_range
            if has_data
            else {
                "range_key": selected_range,

                "range_label": (
                    DATE_RANGE_OPTIONS.get(
                        selected_range,
                        "All Data",
                    )
                ),

                "start_date": None,

                "end_date": None,

                "days": None,
            }
        ),
    }

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "analytics/sales_intelligence.html",
        context,
    )

@login_required
def financial_intelligence(request):
    """
    Financial Intelligence

    Uses the latest cleaned dataset version and produces:

    - Revenue
    - Expenses
    - Profit
    - Profit Margin
    - Revenue vs Expense analysis
    - Profit trend
    - Expense category analysis
    - Highest cost areas
    - Most profitable periods
    - Current vs previous period comparison
    - Financial business insights
    """

    # =========================================================
    # DATASETS
    # =========================================================

    datasets = Dataset.objects.filter(
        owner=request.user
    ).order_by("-uploaded_at")

    # =========================================================
    # GLOBAL DATE RANGE
    # =========================================================

    selected_range = request.GET.get(
        "range",
        "all",
    )

    custom_start = request.GET.get(
        "start",
        "",
    )

    custom_end = request.GET.get(
        "end",
        "",
    )

    if (
        selected_range not in DATE_RANGE_OPTIONS
        and selected_range != "custom"
    ):
        selected_range = "all"

    # =========================================================
    # INITIAL VARIABLES
    # =========================================================

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    # ---------------------------------------------------------
    # MAIN FINANCIAL KPIs
    # ---------------------------------------------------------

    total_revenue = 0
    total_expenses = 0
    total_profit = 0
    profit_margin = 0

    # ---------------------------------------------------------
    # PERIOD COMPARISON
    # ---------------------------------------------------------

    current_period_revenue = 0
    previous_period_revenue = 0
    revenue_change = 0

    current_period_expenses = 0
    previous_period_expenses = 0
    expense_change = 0

    current_period_profit = 0
    previous_period_profit = 0
    profit_change = 0

    current_profit_margin = 0
    previous_profit_margin = 0
    margin_change = 0

    comparison_available = False

    # ---------------------------------------------------------
    # PERIOD INFORMATION
    # ---------------------------------------------------------

    peak_profit_period = "-"
    lowest_profit_period = "-"

    highest_expense_category = "-"
    highest_expense_amount = 0

    # ---------------------------------------------------------
    # TABLES
    # ---------------------------------------------------------

    financial_rows = []
    expense_rows = []

    # ---------------------------------------------------------
    # INSIGHTS
    # ---------------------------------------------------------

    financial_insights = []

    # ---------------------------------------------------------
    # CHART DATA
    # ---------------------------------------------------------

    financial_labels = json.dumps([])
    revenue_values = json.dumps([])
    expense_values = json.dumps([])
    profit_values = json.dumps([])

    expense_category_labels = json.dumps([])
    expense_category_values = json.dumps([])

    profit_labels = json.dumps([])
    profit_trend_values = json.dumps([])

    # ---------------------------------------------------------
    # COLUMN INFORMATION
    # ---------------------------------------------------------

    revenue_column = ""
    expense_column = ""
    category_column = ""
    date_column = ""

    # ---------------------------------------------------------
    # DATE RANGE FALLBACK
    # ---------------------------------------------------------

    date_range = {
        "range_key": selected_range,
        "range_label": DATE_RANGE_OPTIONS.get(
            selected_range,
            "All Data",
        ),
        "start_date": None,
        "end_date": None,
        "days": None,
    }

    # =========================================================
    # CHECK DATASETS
    # =========================================================

    if datasets.exists():

        # =====================================================
        # SELECT DATASET
        # =====================================================

        dataset_id = request.GET.get(
            "dataset"
        )

        if dataset_id:

            selected_dataset = datasets.filter(
                id=dataset_id
            ).first()

        if not selected_dataset:

            selected_dataset = datasets.first()

        # =====================================================
        # GET CLEANED VERSION
        # =====================================================

        selected_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                version_type="Cleaned",
            )
            .order_by(
                "-version_number",
                "-created_at",
            )
            .first()
        )

        # =====================================================
        # FALLBACK TO CURRENT VERSION
        # =====================================================

        if not selected_version:

            selected_version = (
                DatasetVersion.objects
                .filter(
                    dataset=selected_dataset,
                    is_current=True,
                )
                .order_by(
                    "-version_number",
                    "-created_at",
                )
                .first()
            )

        # =====================================================
        # PROCESS DATA
        # =====================================================

        if selected_version:

            try:

                # =================================================
                # FILE
                # =================================================

                cleaned_file = selected_version.file

                file_path = cleaned_file.path

                # =================================================
                # READ FILE
                # =================================================

                if file_path.lower().endswith(".csv"):

                    df = pd.read_csv(
                        file_path
                    )

                elif file_path.lower().endswith(
                    (".xlsx", ".xls")
                ):

                    df = pd.read_excel(
                        file_path
                    )

                else:

                    raise ValueError(
                        "Financial Intelligence supports "
                        "CSV and Excel files."
                    )

                # =================================================
                # EMPTY CHECK
                # =================================================

                if df.empty:

                    raise ValueError(
                        "The selected dataset is empty."
                    )

                # =================================================
                # CLEAN COLUMN NAMES
                # =================================================

                df.columns = [
                    str(column)
                    .strip()
                    .lower()
                    .replace(" ", "_")
                    for column in df.columns
                ]

                # =================================================
                # FIND REVENUE COLUMN
                # =================================================

                revenue_candidates = [

                    "revenue",

                    "sales",

                    "sale",

                    "total_revenue",

                    "total_sales",

                    "net_sales",

                    "sales_amount",

                    "revenue_amount",

                    "order_value",

                    "amount",

                ]

                revenue_column = None

                # -------------------------------------------------
                # EXACT MATCH
                # -------------------------------------------------

                for column in revenue_candidates:

                    if column in df.columns:

                        revenue_column = column

                        break

                # -------------------------------------------------
                # PARTIAL MATCH
                # -------------------------------------------------

                if not revenue_column:

                    revenue_keywords = [
                        "revenue",
                        "sales",
                        "sale",
                    ]

                    for column in df.columns:

                        if any(
                            keyword in column
                            for keyword in revenue_keywords
                        ):

                            revenue_column = column

                            break

                # =================================================
                # FIND EXPENSE COLUMN
                # =================================================

                expense_candidates = [

                    "expense",

                    "expenses",

                    "cost",

                    "costs",

                    "total_expense",

                    "total_expenses",

                    "operating_expense",

                    "operating_expenses",

                    "expense_amount",

                    "cost_amount",

                    "total_cost",

                ]

                expense_column = None

                # -------------------------------------------------
                # EXACT MATCH
                # -------------------------------------------------

                for column in expense_candidates:

                    if column in df.columns:

                        expense_column = column

                        break

                # -------------------------------------------------
                # PARTIAL MATCH
                # -------------------------------------------------

                if not expense_column:

                    expense_keywords = [
                        "expense",
                        "cost",
                    ]

                    for column in df.columns:

                        if any(
                            keyword in column
                            for keyword in expense_keywords
                        ):

                            expense_column = column

                            break

                # =================================================
                # FIND DATE COLUMN
                # =================================================

                date_candidates = [

                    "date",

                    "order_date",

                    "sales_date",

                    "transaction_date",

                    "purchase_date",

                    "created_at",

                    "invoice_date",

                    "payment_date",

                    "expense_date",

                ]

                date_column = None

                # -------------------------------------------------
                # EXACT MATCH
                # -------------------------------------------------

                for column in date_candidates:

                    if column in df.columns:

                        date_column = column

                        break

                # -------------------------------------------------
                # PARTIAL MATCH
                # -------------------------------------------------

                if not date_column:

                    date_keywords = [
                        "date",
                        "created",
                        "transaction",
                        "purchase",
                        "order",
                    ]

                    for column in df.columns:

                        if any(
                            keyword in column
                            for keyword in date_keywords
                        ):

                            date_column = column

                            break

                # =================================================
                # FIND EXPENSE CATEGORY
                # =================================================

                category_candidates = [

                    "expense_category",

                    "expense_type",

                    "category",

                    "cost_category",

                    "cost_type",

                    "department",

                    "expense_group",

                ]

                category_column = None

                for column in category_candidates:

                    if column in df.columns:

                        category_column = column

                        break

                # =================================================
                # VALIDATION
                # =================================================

                if not revenue_column:

                    raise ValueError(
                        "No revenue/sales column was detected."
                    )

                if not expense_column:

                    raise ValueError(
                        "No expense/cost column was detected."
                    )

                if not date_column:

                    raise ValueError(
                        "No date column was detected."
                    )

                # =================================================
                # PREPARE REVENUE
                # =================================================

                df[revenue_column] = pd.to_numeric(
                    df[revenue_column],
                    errors="coerce",
                )

                # =================================================
                # PREPARE EXPENSE
                # =================================================

                df[expense_column] = pd.to_numeric(
                    df[expense_column],
                    errors="coerce",
                )

                # =================================================
                # PREPARE DATE
                # =================================================

                df[date_column] = pd.to_datetime(
                    df[date_column],
                    errors="coerce",
                )

                # =================================================
                # REMOVE INVALID RECORDS
                # =================================================

                df = df.dropna(
                    subset=[
                        revenue_column,
                        expense_column,
                        date_column,
                    ]
                )

                if df.empty:

                    raise ValueError(
                        "No valid financial records were found."
                    )

                # =================================================
                # SORT COMPLETE DATASET
                # =================================================

                df = df.sort_values(
                    date_column
                ).reset_index(
                    drop=True
                )

                # =================================================
                # KEEP COMPLETE DATASET
                # FOR PREVIOUS-PERIOD COMPARISON
                # =================================================

                df_original = df.copy()

                # =================================================
                # APPLY GLOBAL DATE RANGE
                # =================================================

                df, date_range = apply_date_filter(
                    df,
                    date_column,
                    range_key=selected_range,
                    start_date=custom_start,
                    end_date=custom_end,
                )

                if df.empty:

                    raise ValueError(
                        "No financial records exist for "
                        "the selected date range."
                    )

                # =================================================
                # CURRENT PERIOD METRICS
                # =================================================

                current_period_revenue = float(
                    df[revenue_column].sum()
                )

                current_period_expenses = float(
                    df[expense_column].sum()
                )

                current_period_profit = (
                    current_period_revenue
                    - current_period_expenses
                )

                if current_period_revenue != 0:

                    current_profit_margin = (
                        current_period_profit
                        / current_period_revenue
                    ) * 100

                # =================================================
                # PREVIOUS EQUIVALENT PERIOD
                # =================================================

                previous_df = get_previous_period(
                    df_original,
                    date_column,
                    date_range["start_date"],
                    date_range["end_date"],
                )

                if not previous_df.empty:

                    previous_df = previous_df.copy()

                    previous_df[revenue_column] = pd.to_numeric(
                        previous_df[revenue_column],
                        errors="coerce",
                    )

                    previous_df[expense_column] = pd.to_numeric(
                        previous_df[expense_column],
                        errors="coerce",
                    )

                    previous_df = previous_df.dropna(
                        subset=[
                            revenue_column,
                            expense_column,
                            date_column,
                        ]
                    )

                    if not previous_df.empty:

                        previous_period_revenue = float(
                            previous_df[revenue_column].sum()
                        )

                        previous_period_expenses = float(
                            previous_df[expense_column].sum()
                        )

                        previous_period_profit = (
                            previous_period_revenue
                            - previous_period_expenses
                        )

                        if previous_period_revenue != 0:

                            previous_profit_margin = (
                                previous_period_profit
                                / previous_period_revenue
                            ) * 100

                        # -----------------------------------------
                        # REVENUE CHANGE
                        # -----------------------------------------

                        revenue_change = (
                            calculate_percentage_change(
                                current_period_revenue,
                                previous_period_revenue,
                            )
                        )

                        # -----------------------------------------
                        # EXPENSE CHANGE
                        # -----------------------------------------

                        expense_change = (
                            calculate_percentage_change(
                                current_period_expenses,
                                previous_period_expenses,
                            )
                        )

                        # -----------------------------------------
                        # PROFIT CHANGE
                        # -----------------------------------------

                        profit_change = (
                            calculate_percentage_change(
                                current_period_profit,
                                previous_period_profit,
                            )
                        )

                        # -----------------------------------------
                        # MARGIN CHANGE
                        # -----------------------------------------

                        margin_change = (
                            current_profit_margin
                            - previous_profit_margin
                        )

                        comparison_available = True

                # =================================================
                # MAIN KPIs
                # =================================================

                total_revenue = float(
                    df[revenue_column].sum()
                )

                total_expenses = float(
                    df[expense_column].sum()
                )

                total_profit = (
                    total_revenue
                    - total_expenses
                )

                if total_revenue != 0:

                    profit_margin = (
                        total_profit
                        / total_revenue
                    ) * 100

                # =================================================
                # MONTHLY FINANCIAL ANALYSIS
                # =================================================

                monthly_financial = (
                    df.set_index(
                        date_column
                    )
                    .resample("ME")
                    [
                        [
                            revenue_column,
                            expense_column,
                        ]
                    ]
                    .sum()
                    .reset_index()
                )

                monthly_financial.columns = [
                    "date",
                    "revenue",
                    "expenses",
                ]

                monthly_financial["profit"] = (
                    monthly_financial["revenue"]
                    - monthly_financial["expenses"]
                )

                monthly_financial["margin"] = np.where(
                    monthly_financial["revenue"] != 0,
                    (
                        monthly_financial["profit"]
                        / monthly_financial["revenue"]
                    ) * 100,
                    0,
                )

                # =================================================
                # PEAK PROFIT PERIOD
                # =================================================

                if not monthly_financial.empty:

                    peak_profit_row = (
                        monthly_financial.loc[
                            monthly_financial["profit"].idxmax()
                        ]
                    )

                    peak_profit_period = (
                        peak_profit_row["date"].strftime(
                            "%B %Y"
                        )
                    )

                # =================================================
                # LOWEST PROFIT PERIOD
                # =================================================

                if not monthly_financial.empty:

                    lowest_profit_row = (
                        monthly_financial.loc[
                            monthly_financial["profit"].idxmin()
                        ]
                    )

                    lowest_profit_period = (
                        lowest_profit_row["date"].strftime(
                            "%B %Y"
                        )
                    )

                # =================================================
                # MONTHLY TABLE
                # =================================================

                for _, row in monthly_financial.tail(24).iterrows():

                    financial_rows.append(
                        {
                            "period": (
                                row["date"].strftime(
                                    "%B %Y"
                                )
                            ),

                            "revenue": round(
                                float(
                                    row["revenue"]
                                ),
                                2,
                            ),

                            "expenses": round(
                                float(
                                    row["expenses"]
                                ),
                                2,
                            ),

                            "profit": round(
                                float(
                                    row["profit"]
                                ),
                                2,
                            ),

                            "margin": round(
                                float(
                                    row["margin"]
                                ),
                                2,
                            ),
                        }
                    )

                # =================================================
                # MONTHLY CHART DATA
                # =================================================

                financial_labels = json.dumps(
                    [
                        date.strftime("%b %Y")
                        for date in monthly_financial["date"]
                    ]
                )

                revenue_values = json.dumps(
                    [
                        round(
                            float(value),
                            2,
                        )
                        for value in monthly_financial["revenue"]
                    ]
                )

                expense_values = json.dumps(
                    [
                        round(
                            float(value),
                            2,
                        )
                        for value in monthly_financial["expenses"]
                    ]
                )

                profit_values = json.dumps(
                    [
                        round(
                            float(value),
                            2,
                        )
                        for value in monthly_financial["profit"]
                    ]
                )

                # =================================================
                # PROFIT TREND DATA
                # =================================================

                profit_labels = json.dumps(
                    [
                        date.strftime("%b %Y")
                        for date in monthly_financial["date"]
                    ]
                )

                profit_trend_values = json.dumps(
                    [
                        round(
                            float(value),
                            2,
                        )
                        for value in monthly_financial["profit"]
                    ]
                )

                # =================================================
                # EXPENSE CATEGORY ANALYSIS
                # =================================================

                if category_column:

                    df[category_column] = (
                        df[category_column]
                        .fillna("Uncategorized")
                        .astype(str)
                        .str.strip()
                    )

                    df.loc[
                        df[category_column] == "",
                        category_column,
                    ] = "Uncategorized"

                    expense_category = (
                        df.groupby(
                            category_column
                        )[expense_column]
                        .sum()
                        .sort_values(
                            ascending=False
                        )
                        .reset_index()
                    )

                    expense_category.columns = [
                        "category",
                        "expenses",
                    ]

                    # -------------------------------------------------
                    # TOTAL CATEGORY EXPENSE
                    # -------------------------------------------------

                    for _, row in expense_category.iterrows():

                        expense_rows.append(
                            {
                                "category": str(
                                    row["category"]
                                ),

                                "expenses": round(
                                    float(
                                        row["expenses"]
                                    ),
                                    2,
                                ),
                            }
                        )

                    # -------------------------------------------------
                    # HIGHEST EXPENSE CATEGORY
                    # -------------------------------------------------

                    if not expense_category.empty:

                        highest_expense_category = str(
                            expense_category.iloc[0][
                                "category"
                            ]
                        )

                        highest_expense_amount = float(
                            expense_category.iloc[0][
                                "expenses"
                            ]
                        )

                    # -------------------------------------------------
                    # CATEGORY CHART
                    # -------------------------------------------------

                    expense_category_labels = json.dumps(
                        [
                            str(category)
                            for category in expense_category[
                                "category"
                            ].head(10)
                        ]
                    )

                    expense_category_values = json.dumps(
                        [
                            round(
                                float(value),
                                2,
                            )
                            for value in expense_category[
                                "expenses"
                            ].head(10)
                        ]
                    )

                else:

                    # No category column
                    expense_category_labels = json.dumps(
                        []
                    )

                    expense_category_values = json.dumps(
                        []
                    )

                # =================================================
                # INSIGHTS
                # =================================================

                # -------------------------------------------------
                # PROFITABILITY INSIGHT
                # -------------------------------------------------

                if profit_margin >= 30:

                    financial_insights.append(
                        {
                            "type": "positive",

                            "title": (
                                "Strong profitability"
                            ),

                            "text": (
                                f"Current profit margin is "
                                f"{profit_margin:.1f}%, indicating "
                                f"strong profitability."
                            ),
                        }
                    )

                elif profit_margin >= 15:

                    financial_insights.append(
                        {
                            "type": "positive",

                            "title": (
                                "Healthy profit margin"
                            ),

                            "text": (
                                f"Current profit margin is "
                                f"{profit_margin:.1f}%."
                            ),
                        }
                    )

                elif profit_margin > 0:

                    financial_insights.append(
                        {
                            "type": "warning",

                            "title": (
                                "Profit margin is limited"
                            ),

                            "text": (
                                f"Business remains profitable, "
                                f"but the current margin is only "
                                f"{profit_margin:.1f}%."
                            ),
                        }
                    )

                else:

                    financial_insights.append(
                        {
                            "type": "negative",

                            "title": (
                                "Loss detected"
                            ),

                            "text": (
                                f"Expenses exceed revenue, "
                                f"resulting in a loss of "
                                f"₹{abs(total_profit):,.2f}."
                            ),
                        }
                    )

                # -------------------------------------------------
                # PERIOD COMPARISON INSIGHT
                # -------------------------------------------------

                if comparison_available:

                    if profit_change > 10:

                        financial_insights.append(
                            {
                                "type": "positive",

                                "title": (
                                    "Profit improved"
                                ),

                                "text": (
                                    f"Profit increased by "
                                    f"{profit_change:.1f}% "
                                    f"compared with the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                    elif profit_change < -10:

                        financial_insights.append(
                            {
                                "type": "negative",

                                "title": (
                                    "Profit declined"
                                ),

                                "text": (
                                    f"Profit decreased by "
                                    f"{abs(profit_change):.1f}% "
                                    f"compared with the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                    else:

                        financial_insights.append(
                            {
                                "type": "neutral",

                                "title": (
                                    "Profit is relatively stable"
                                ),

                                "text": (
                                    "Profit has not changed "
                                    "significantly compared with "
                                    "the previous equivalent period."
                                ),
                            }
                        )

                # -------------------------------------------------
                # EXPENSE INSIGHT
                # -------------------------------------------------

                if comparison_available:

                    if expense_change > 10:

                        financial_insights.append(
                            {
                                "type": "warning",

                                "title": (
                                    "Expenses increased"
                                ),

                                "text": (
                                    f"Expenses increased by "
                                    f"{expense_change:.1f}% "
                                    f"compared with the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                    elif expense_change < -10:

                        financial_insights.append(
                            {
                                "type": "positive",

                                "title": (
                                    "Expense reduction detected"
                                ),

                                "text": (
                                    f"Expenses decreased by "
                                    f"{abs(expense_change):.1f}% "
                                    f"compared with the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                # -------------------------------------------------
                # HIGHEST COST AREA
                # -------------------------------------------------

                if highest_expense_category != "-":

                    financial_insights.append(
                        {
                            "type": "warning",

                            "title": (
                                "Highest cost area"
                            ),

                            "text": (
                                f"{highest_expense_category} is "
                                f"the largest expense category, "
                                f"accounting for "
                                f"₹{highest_expense_amount:,.2f}."
                            ),
                        }
                    )

                # -------------------------------------------------
                # PEAK PROFIT
                # -------------------------------------------------

                if peak_profit_period != "-":

                    financial_insights.append(
                        {
                            "type": "positive",

                            "title": (
                                "Most profitable period"
                            ),

                            "text": (
                                f"{peak_profit_period} generated "
                                f"the highest profit in the "
                                f"selected analysis period."
                            ),
                        }
                    )

                # -------------------------------------------------
                # LOWEST PROFIT
                # -------------------------------------------------

                if lowest_profit_period != "-":

                    financial_insights.append(
                        {
                            "type": "warning",

                            "title": (
                                "Lowest profitability period"
                            ),

                            "text": (
                                f"{lowest_profit_period} recorded "
                                f"the lowest profit and may require "
                                f"further investigation."
                            ),
                        }
                    )

                # -------------------------------------------------
                # DATE RANGE INSIGHT
                # -------------------------------------------------

                if (
                    date_range.get("start_date")
                    and date_range.get("end_date")
                ):

                    start_display = (
                        date_range["start_date"].strftime(
                            "%d %b %Y"
                        )
                    )

                    end_display = (
                        date_range["end_date"].strftime(
                            "%d %b %Y"
                        )
                    )

                    financial_insights.append(
                        {
                            "type": "info",

                            "title": (
                                "Analysis period"
                            ),

                            "text": (
                                f"Financial analysis covers "
                                f"{start_display} to "
                                f"{end_display}."
                            ),
                        }
                    )

                # =================================================
                # FINAL STATUS
                # =================================================

                has_data = True

            except Exception as exc:

                error_message = str(
                    exc
                )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # -----------------------------------------------------
        # DATASET
        # -----------------------------------------------------

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "selected_version": selected_version,

        # -----------------------------------------------------
        # STATUS
        # -----------------------------------------------------

        "has_data": has_data,

        "error_message": error_message,

        # -----------------------------------------------------
        # MAIN FINANCIAL KPIs
        # -----------------------------------------------------

        "total_revenue": total_revenue,

        "total_expenses": total_expenses,

        "total_profit": total_profit,

        "profit_margin": profit_margin,

        # -----------------------------------------------------
        # PERIOD COMPARISON
        # -----------------------------------------------------

        "current_period_revenue": (
            current_period_revenue
        ),

        "previous_period_revenue": (
            previous_period_revenue
        ),

        "revenue_change": revenue_change,

        "current_period_expenses": (
            current_period_expenses
        ),

        "previous_period_expenses": (
            previous_period_expenses
        ),

        "expense_change": expense_change,

        "current_period_profit": (
            current_period_profit
        ),

        "previous_period_profit": (
            previous_period_profit
        ),

        "profit_change": profit_change,

        "current_profit_margin": (
            current_profit_margin
        ),

        "previous_profit_margin": (
            previous_profit_margin
        ),

        "margin_change": margin_change,

        "comparison_available": (
            comparison_available
        ),

        # -----------------------------------------------------
        # PERIODS
        # -----------------------------------------------------

        "peak_profit_period": (
            peak_profit_period
        ),

        "lowest_profit_period": (
            lowest_profit_period
        ),

        # -----------------------------------------------------
        # EXPENSE CATEGORY
        # -----------------------------------------------------

        "highest_expense_category": (
            highest_expense_category
        ),

        "highest_expense_amount": (
            highest_expense_amount
        ),

        # -----------------------------------------------------
        # TABLES
        # -----------------------------------------------------

        "financial_rows": financial_rows,

        "expense_rows": expense_rows,

        # -----------------------------------------------------
        # CHART DATA
        # -----------------------------------------------------

        "financial_labels": financial_labels,

        "revenue_values": revenue_values,

        "expense_values": expense_values,

        "profit_values": profit_values,

        "expense_category_labels": (
            expense_category_labels
        ),

        "expense_category_values": (
            expense_category_values
        ),

        "profit_labels": profit_labels,

        "profit_trend_values": (
            profit_trend_values
        ),

        # -----------------------------------------------------
        # INSIGHTS
        # -----------------------------------------------------

        "financial_insights": financial_insights,

        # -----------------------------------------------------
        # COLUMN INFORMATION
        # -----------------------------------------------------

        "revenue_column": (
            revenue_column or ""
        ),

        "expense_column": (
            expense_column or ""
        ),

        "category_column": (
            category_column or ""
        ),

        "date_column": (
            date_column or ""
        ),

        # -----------------------------------------------------
        # DATE RANGE
        # -----------------------------------------------------

        "date_range_options": (
            DATE_RANGE_OPTIONS
        ),

        "selected_range": (
            selected_range
        ),

        "custom_start": (
            custom_start
        ),

        "custom_end": (
            custom_end
        ),

        "date_range": (
            date_range
            if has_data
            else {
                "range_key": selected_range,

                "range_label": (
                    DATE_RANGE_OPTIONS.get(
                        selected_range,
                        "All Data",
                    )
                ),

                "start_date": None,

                "end_date": None,

                "days": None,
            }
        ),
    }

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "analytics/financial_intelligence.html",
        context,
    )