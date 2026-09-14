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
import json
import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from data_management.models import Dataset, DatasetVersion

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

# ============================================================
# analytics/views.py
# CUSTOMER INTELLIGENCE
# ============================================================

import json
import re

import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from data_management.models import Dataset, DatasetVersion

from .date_filters import (
    DATE_RANGE_OPTIONS,
    apply_date_filter,
    get_previous_period,
    calculate_percentage_change,
)


# ============================================================
# AUTHORIZATION
# ============================================================

def user_is_approved(request):
    """
    Smart BI authorization.

    Staff/superusers are allowed automatically.
    Normal users must be active and approved.
    """

    user = request.user

    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    return (
        getattr(user, "is_active", False)
        and getattr(user, "approval_status", "") == "Approved"
    )


# ============================================================
# CUSTOMER DATASET ONLY
# ============================================================

def get_customer_datasets(user):
    """
    Customer Intelligence is intentionally restricted to
    Customer datasets only.

    It does NOT use:
        Sales
        Products
        Marketing
        Financial
        Returns
        Regional
    """

    return (
        Dataset.objects
        .filter(
            owner=user,
            dataset_type="Customers",
            is_active=True,
        )
        .order_by("-uploaded_at")
    )


# ============================================================
# CLEANED VERSION
# ============================================================

def get_cleaned_version(dataset):
    """
    Return the best available processed version.

    Priority:
        1. Current Cleaned
        2. Latest Cleaned
        3. Current Validated/Transformed
        4. Latest version
    """

    if not dataset:
        return None

    version = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            version_type="Cleaned",
            is_current=True,
        )
        .order_by("-version_number")
        .first()
    )

    if version:
        return version

    version = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            version_type="Cleaned",
        )
        .order_by("-version_number", "-created_at")
        .first()
    )

    if version:
        return version

    version = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            is_current=True,
        )
        .order_by("-version_number")
        .first()
    )

    if version:
        return version

    return (
        DatasetVersion.objects
        .filter(dataset=dataset)
        .order_by("-version_number", "-created_at")
        .first()
    )


# ============================================================
# READ DATASET
# ============================================================

def read_dataset(source):
    """
    Read CSV/XLS/XLSX from Dataset or DatasetVersion.
    """

    if not source:
        return None

    try:
        file_field = getattr(source, "file", None)

        if not file_field:
            return None

        file_name = str(file_field.name).lower()

        if file_name.endswith(".csv"):
            return pd.read_csv(file_field)

        if file_name.endswith(".xlsx"):
            return pd.read_excel(file_field, engine="openpyxl")

        if file_name.endswith(".xls"):
            return pd.read_excel(file_field)

        return None

    except Exception:
        return None


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

def normalize_column_name(column):
    """
    Convert:

        Customer ID
        customer-id
        CUSTOMER_ID
        customer.id

    into a predictable format.
    """

    value = str(column).strip().lower()

    value = re.sub(r"[^a-z0-9]+", "_", value)

    value = re.sub(r"_+", "_", value)

    return value.strip("_")


def normalize_dataframe_columns(dataframe):
    dataframe = dataframe.copy()

    dataframe.columns = [
        normalize_column_name(column)
        for column in dataframe.columns
    ]

    return dataframe


# ============================================================
# COLUMN DETECTION
# ============================================================

def find_column(dataframe, candidates):
    """
    Find the first matching column using normalized names.
    """

    if dataframe is None or dataframe.empty:
        return None

    normalized = {
        normalize_column_name(column): column
        for column in dataframe.columns
    }

    for candidate in candidates:

        candidate = normalize_column_name(candidate)

        if candidate in normalized:
            return normalized[candidate]

    # Fuzzy contains fallback
    for candidate in candidates:

        candidate = normalize_column_name(candidate)

        for normalized_name, original_name in normalized.items():

            if (
                candidate in normalized_name
                or normalized_name in candidate
            ):
                return original_name

    return None


# ============================================================
# NUMERIC CLEANING
# ============================================================

def clean_numeric(series):
    """
    Safely convert currency/number strings to numeric values.
    """

    return pd.to_numeric(
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace(
            r"^\((.*)\)$",
            r"-\1",
            regex=True,
        ),
        errors="coerce",
    )


# ============================================================
# SAFE JSON
# ============================================================

def json_safe(value):
    """
    Convert numpy/pandas values into JSON-safe values.
    """

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        return float(value)

    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")

    if pd.isna(value):
        return None

    return value


def to_json(value):
    return json.dumps(value, default=json_safe)


# ============================================================
# RFM SCORING
# ============================================================

def create_rfm_scores(rfm):
    """
    Create Recency, Frequency and Monetary scores.

    Score range:
        1 = low
        5 = high
    """

    rfm = rfm.copy()

    customer_count = len(rfm)

    if customer_count >= 5:

        # Recency:
        # lower recency = better
        try:
            rfm["recency_score"] = pd.qcut(
                rfm["recency"].rank(method="first"),
                5,
                labels=False,
                duplicates="drop",
            )

            rfm["recency_score"] = (
                5 - rfm["recency_score"]
            )

        except Exception:
            rfm["recency_score"] = 3

        # Frequency
        try:
            rfm["frequency_score"] = (
                pd.qcut(
                    rfm["frequency"].rank(method="first"),
                    5,
                    labels=False,
                    duplicates="drop",
                )
                + 1
            )

        except Exception:
            rfm["frequency_score"] = 3

        # Monetary
        try:
            rfm["monetary_score"] = (
                pd.qcut(
                    rfm["monetary"].rank(method="first"),
                    5,
                    labels=False,
                    duplicates="drop",
                )
                + 1
            )

        except Exception:
            rfm["monetary_score"] = 3

    else:

        rfm["recency_score"] = 3
        rfm["frequency_score"] = 3
        rfm["monetary_score"] = 3

    for column in [
        "recency_score",
        "frequency_score",
        "monetary_score",
    ]:

        rfm[column] = (
            pd.to_numeric(
                rfm[column],
                errors="coerce",
            )
            .fillna(3)
            .clip(1, 5)
            .astype(int)
        )

    rfm["rfm_score"] = (
        rfm["recency_score"]
        + rfm["frequency_score"]
        + rfm["monetary_score"]
    )

    return rfm


# ============================================================
# CUSTOMER SEGMENTATION
# ============================================================

def classify_customer(row):
    """
    Business-oriented customer segmentation.
    """

    recency = float(row.get("recency", 0))
    frequency = float(row.get("frequency", 0))

    recency_score = int(row.get("recency_score", 1))
    frequency_score = int(row.get("frequency_score", 1))
    monetary_score = int(row.get("monetary_score", 1))

    # --------------------------------------------------------
    # HIGH VALUE
    # --------------------------------------------------------

    if (
        monetary_score >= 4
        and frequency_score >= 4
        and recency_score >= 4
    ):
        return "High Value"

    # --------------------------------------------------------
    # LOYAL
    # --------------------------------------------------------

    if (
        frequency_score >= 4
        and recency_score >= 3
    ):
        return "Loyal"

    # --------------------------------------------------------
    # AT RISK
    # --------------------------------------------------------

    if (
        recency_score <= 2
        and frequency_score >= 3
    ):
        return "At Risk"

    # --------------------------------------------------------
    # NEW
    # --------------------------------------------------------

    if (
        recency <= 30
        and frequency <= 2
    ):
        return "New"

    # --------------------------------------------------------
    # LOW VALUE
    # --------------------------------------------------------

    return "Low Value"


# ============================================================
# CUSTOMER HEALTH
# ============================================================

def calculate_customer_health(
    total_customers,
    repeat_customer_rate,
    at_risk_customers,
):
    if total_customers <= 0:
        return "No Data"

    risk_percentage = (
        at_risk_customers
        / total_customers
        * 100
    )

    if risk_percentage >= 40:
        return "Critical"

    if risk_percentage >= 20:
        return "Needs Attention"

    if repeat_customer_rate >= 60:
        return "Healthy"

    if repeat_customer_rate >= 35:
        return "Stable"

    return "Needs Attention"


# ============================================================
# CUSTOMER INTELLIGENCE
# Smart Business Decision Intelligence Management System
# ============================================================

import json
from datetime import timedelta

import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from data_management.models import Dataset, DatasetVersion

from .date_filters import (
    DATE_RANGE_OPTIONS,
    apply_date_filter,
    get_previous_period,
    calculate_percentage_change,
)


# ============================================================
# CUSTOMER HELPERS
# ============================================================

def customer_json(value):
    """
    Safely convert Python / NumPy / Pandas values into JSON.
    """
    try:
        return json.dumps(
            value,
            default=lambda obj: (
                obj.item()
                if hasattr(obj, "item")
                else str(obj)
            ),
        )
    except Exception:
        return "[]"


def customer_clean_number(series):
    """
    Convert currency / formatted numeric values safely.
    Handles:
        1,200
        ₹1,200
        $1,200
        (1200)
        -1200
    """
    if series is None:
        return pd.Series(dtype=float)

    return pd.to_numeric(
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace(
            r"^\((.*)\)$",
            r"-\1",
            regex=True,
        ),
        errors="coerce",
    )


def customer_find_column(dataframe, candidates):
    """
    Find a column using normalized names and partial matching.
    """

    if dataframe is None or dataframe.empty:
        return None

    columns = list(dataframe.columns)

    normalized = {}

    for column in columns:

        clean = (
            str(column)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
        )

        normalized[clean] = column

    # Exact match first
    for candidate in candidates:

        candidate_clean = (
            str(candidate)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
        )

        if candidate_clean in normalized:
            return normalized[candidate_clean]

    # Partial match second
    for candidate in candidates:

        candidate_clean = (
            str(candidate)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
        )

        for normalized_name, original_name in normalized.items():

            if (
                candidate_clean in normalized_name
                or normalized_name in candidate_clean
            ):
                return original_name

    return None


def customer_get_cleaned_version(dataset):
    """
    Always prefer the cleaned version.

    Priority:
        1. Current Cleaned
        2. Latest Cleaned
        3. Current Validated / Transformed
        4. Latest version
    """

    if dataset is None:
        return None

    versions = DatasetVersion.objects.filter(
        dataset=dataset
    ).order_by(
        "-version_number",
        "-created_at",
    )

    cleaned_current = versions.filter(
        version_type="Cleaned",
        is_current=True,
    ).first()

    if cleaned_current:
        return cleaned_current

    cleaned = versions.filter(
        version_type="Cleaned"
    ).first()

    if cleaned:
        return cleaned

    current = versions.filter(
        is_current=True
    ).first()

    if current:
        return current

    return versions.first()


def customer_read_dataset(source):
    """
    Read CSV / XLS / XLSX from DatasetVersion or Dataset.
    """

    if source is None:
        return None

    try:

        file_field = getattr(
            source,
            "file",
            None
        )

        if not file_field:
            return None

        filename = str(
            getattr(
                file_field,
                "name",
                ""
            )
        ).lower()

        if filename.endswith(".csv"):

            return pd.read_csv(
                file_field.path
            )

        if filename.endswith(".xlsx"):

            return pd.read_excel(
                file_field.path,
                engine="openpyxl"
            )

        if filename.endswith(".xls"):

            return pd.read_excel(
                file_field.path
            )

        return None

    except Exception:
        return None


def customer_dataset_source(dataset, cleaned_version):
    """
    Read cleaned version first.

    If no cleaned version exists, return None.
    This prevents Customer Intelligence from accidentally
    analysing the original uploaded file.
    """

    if cleaned_version is None:
        return None

    return customer_read_dataset(
        cleaned_version
    )


def customer_score_quantile(series, reverse=False):
    """
    Stable 1-5 RFM scoring.

    Works even when many customers have identical values.
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce"
    ).fillna(0)

    count = len(numeric)

    if count == 0:
        return pd.Series(
            dtype=int,
            index=numeric.index
        )

    if count < 2:
        return pd.Series(
            3,
            index=numeric.index,
            dtype=int
        )

    ranks = numeric.rank(
        method="first"
    )

    try:

        scores = pd.qcut(
            ranks,
            q=min(5, count),
            labels=False,
            duplicates="drop"
        )

        scores = (
            pd.to_numeric(
                scores,
                errors="coerce"
            )
            .fillna(0)
            .astype(int)
            + 1
        )

    except Exception:

        scores = pd.Series(
            3,
            index=numeric.index,
            dtype=int
        )

    scores = scores.clip(
        lower=1,
        upper=5
    )

    if reverse:
        scores = 6 - scores

    return scores.astype(int)


def customer_segment(row):

    recency = float(
        row.get("recency", 0)
    )

    frequency = float(
        row.get("frequency", 0)
    )

    monetary = float(
        row.get("monetary", 0)
    )

    recency_score = int(
        row.get("recency_score", 1)
    )

    frequency_score = int(
        row.get("frequency_score", 1)
    )

    monetary_score = int(
        row.get("monetary_score", 1)
    )

    # Highest-value customers
    if (
        monetary_score >= 4
        and frequency_score >= 4
        and recency_score >= 4
    ):
        return "High Value"

    # Strong repeat customers
    if (
        frequency_score >= 4
        and recency_score >= 3
    ):
        return "Loyal"

    # Customers with meaningful historical value
    # but weak recent activity
    if (
        recency_score <= 2
        and (
            frequency_score >= 3
            or monetary_score >= 3
        )
    ):
        return "At Risk"

    # Recent customers with limited purchase history
    if (
        recency <= 30
        and frequency <= 2
    ):
        return "New"

    # Customers with low engagement/value
    if (
        monetary <= 0
        or (
            frequency_score <= 2
            and monetary_score <= 2
        )
    ):
        return "Low Value"

    return "Developing"


def customer_segment_class(segment):

    mapping = {
        "High Value": "badge-high",
        "Loyal": "badge-loyal",
        "New": "badge-new",
        "At Risk": "badge-risk",
        "Low Value": "badge-low",
        "Developing": "badge-developing",
    }

    return mapping.get(
        segment,
        "badge-developing"
    )


def customer_health_status(
    repeat_rate,
    at_risk_rate,
    active_rate,
):
    """
    Customer health based on multiple behavioral indicators.
    """

    health_score = (
        (repeat_rate * 0.40)
        + (active_rate * 0.35)
        + ((100 - at_risk_rate) * 0.25)
    )

    health_score = max(
        0,
        min(
            100,
            health_score
        )
    )

    if health_score >= 75:
        status = "Healthy"

    elif health_score >= 55:
        status = "Needs Attention"

    else:
        status = "Critical"

    return (
        round(health_score, 1),
        status,
    )


# ============================================================
# ANALYTICS - CUSTOMER INTELLIGENCE
# Smart Business Decision Intelligence Management System
# ============================================================

import json
import math
import re
from datetime import timedelta

import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from data_management.models import Dataset, DatasetVersion


# ============================================================
# BASIC HELPERS
# ============================================================

def customer_user_is_allowed(request):
    """
    Customer Intelligence access rule.

    Staff/superusers are allowed.
    Normal users must be active and approved.
    """

    user = request.user

    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    if not user.is_active:
        return False

    return getattr(user, "approval_status", "") == "Approved"


def ci_normalize_column_name(column):
    """
    Normalize a column name for matching.
    """

    value = str(column).strip().lower()

    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    value = value.strip("_")

    return value


def ci_find_column(dataframe, candidates):
    """
    Find a column using normalized aliases.
    """

    if dataframe is None or dataframe.empty:
        return None

    normalized = {}

    for column in dataframe.columns:
        normalized[ci_normalize_column_name(column)] = column

    # Exact normalized match first
    for candidate in candidates:

        candidate_normalized = ci_normalize_column_name(candidate)

        if candidate_normalized in normalized:
            return normalized[candidate_normalized]

    # Partial match
    for candidate in candidates:

        candidate_normalized = ci_normalize_column_name(candidate)

        for normalized_name, original_name in normalized.items():

            if (
                candidate_normalized in normalized_name
                or normalized_name in candidate_normalized
            ):
                return original_name

    return None


def ci_clean_numeric(series):
    """
    Safely convert currency / numeric values.

    Supports:
    1,250
    ₹1250
    $1250
    (1250) -> -1250
    """

    return pd.to_numeric(
        series.astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True),
        errors="coerce",
    )


def ci_json(value):
    """
    Safe JSON serialization for Django templates.
    """

    try:
        return json.dumps(value, default=str)
    except Exception:
        return "[]"


def ci_money(value):
    try:
        return round(float(value), 2)
    except Exception:
        return 0


def ci_int(value):
    try:
        return int(value)
    except Exception:
        return 0


# ============================================================
# DATASET HELPERS
# ============================================================

def ci_get_cleaned_version(dataset):
    """
    Get the best available cleaned/current version.

    Priority:
        1. Current Cleaned
        2. Latest Cleaned
        3. Current version
        4. Latest version
    """

    if dataset is None:
        return None

    versions = DatasetVersion.objects.filter(
        dataset=dataset
    ).order_by("-version_number", "-created_at")

    current_cleaned = versions.filter(
        version_type="Cleaned",
        is_current=True
    ).first()

    if current_cleaned:
        return current_cleaned

    latest_cleaned = versions.filter(
        version_type="Cleaned"
    ).first()

    if latest_cleaned:
        return latest_cleaned

    current_version = versions.filter(
        is_current=True
    ).first()

    if current_version:
        return current_version

    return versions.first()


def ci_read_dataset(source):
    """
    Read Dataset or DatasetVersion file.
    """

    if source is None:
        return None

    try:

        file_field = getattr(source, "file", None)

        if not file_field:
            return None

        filename = str(
            getattr(source, "file_name", None)
            or getattr(source, "original_filename", None)
            or file_field.name
            or ""
        ).lower()

        if filename.endswith(".csv"):

            return pd.read_csv(
                file_field.path
            )

        if filename.endswith(".xlsx"):

            return pd.read_excel(
                file_field.path,
                engine="openpyxl"
            )

        if filename.endswith(".xls"):

            return pd.read_excel(
                file_field.path
            )

        # fallback
        return pd.read_csv(
            file_field.path
        )

    except Exception:
        return None


# ============================================================
# DATE RANGE
# ============================================================

CUSTOMER_DATE_RANGES = {
    "30": "Last 30 Days",
    "90": "Last 3 Months",
    "180": "Last 6 Months",
    "365": "Last 12 Months",
    "all": "All Data",
}


def ci_apply_date_range(
    dataframe,
    date_column,
    range_key="all",
    start_date=None,
    end_date=None,
):
    """
    Apply customer analysis date range.

    Returns:
        filtered_dataframe,
        metadata
    """

    result = dataframe.copy()

    result[date_column] = pd.to_datetime(
        result[date_column],
        errors="coerce"
    )

    result = result.dropna(
        subset=[date_column]
    )

    if result.empty:

        return result, {
            "range_key": range_key,
            "range_label": CUSTOMER_DATE_RANGES.get(
                range_key,
                "All Data"
            ),
            "start": None,
            "end": None,
            "days": 0,
        }

    min_date = result[date_column].min().normalize()
    max_date = result[date_column].max().normalize()

    # --------------------------------------------------------
    # CUSTOM RANGE
    # --------------------------------------------------------

    if range_key == "custom":

        try:

            requested_start = pd.to_datetime(
                start_date
            ).normalize()

            requested_end = pd.to_datetime(
                end_date
            ).normalize()

            if requested_start > requested_end:

                requested_start, requested_end = (
                    requested_end,
                    requested_start
                )

            filter_start = max(
                requested_start,
                min_date
            )

            filter_end = min(
                requested_end,
                max_date
            )

            filtered = result[
                (result[date_column] >= filter_start)
                &
                (
                    result[date_column]
                    < filter_end + timedelta(days=1)
                )
            ].copy()

            return filtered, {
                "range_key": "custom",
                "range_label": "Custom Range",
                "start": filter_start,
                "end": filter_end,
                "days": (
                    filter_end - filter_start
                ).days + 1,
            }

        except Exception:
            range_key = "all"

    # --------------------------------------------------------
    # ALL DATA
    # --------------------------------------------------------

    if range_key == "all":

        filtered = result.copy()

        return filtered, {
            "range_key": "all",
            "range_label": "All Data",
            "start": min_date,
            "end": max_date,
            "days": (
                max_date - min_date
            ).days + 1,
        }

    # --------------------------------------------------------
    # PRESET RANGE
    # --------------------------------------------------------

    try:
        days = int(range_key)
    except Exception:
        days = None

    if days is None:

        filtered = result.copy()

        return filtered, {
            "range_key": "all",
            "range_label": "All Data",
            "start": min_date,
            "end": max_date,
            "days": (
                max_date - min_date
            ).days + 1,
        }

    filter_end = max_date

    filter_start = max(
        max_date - timedelta(days=days - 1),
        min_date
    )

    filtered = result[
        (result[date_column] >= filter_start)
        &
        (result[date_column] <= filter_end)
    ].copy()

    return filtered, {
        "range_key": str(days),
        "range_label": CUSTOMER_DATE_RANGES.get(
            str(days),
            f"Last {days} Days"
        ),
        "start": filter_start,
        "end": filter_end,
        "days": (
            filter_end - filter_start
        ).days + 1,
    }


# ============================================================
# RFM SCORING
# ============================================================

def ci_rfm_score(series, higher_is_better=True):

    if series.empty:
        return pd.Series(
            dtype=int,
            index=series.index
        )

    if len(series) == 1:

        return pd.Series(
            [3],
            index=series.index,
            dtype=int
        )

    ranks = series.rank(
        method="first"
    )

    try:

        scores = pd.qcut(
            ranks,
            q=5,
            labels=False,
            duplicates="drop"
        )

        scores = pd.to_numeric(
            scores,
            errors="coerce"
        ).fillna(2)

        scores = scores + 1

        if not higher_is_better:

            scores = 6 - scores

        return scores.clip(
            1,
            5
        ).astype(int)

    except Exception:

        # fallback percentile method
        percentile = series.rank(
            pct=True,
            method="average"
        )

        scores = np.ceil(
            percentile * 5
        )

        scores = pd.Series(
            scores,
            index=series.index
        ).clip(
            1,
            5
        ).astype(int)

        if not higher_is_better:
            scores = 6 - scores

        return scores


def ci_classify_customer(row):

    recency = float(
        row.get("recency", 0)
    )

    frequency = float(
        row.get("frequency", 0)
    )

    monetary = float(
        row.get("monetary", 0)
    )

    r = int(
        row.get("recency_score", 1)
    )

    f = int(
        row.get("frequency_score", 1)
    )

    m = int(
        row.get("monetary_score", 1)
    )

    # --------------------------------------------------------
    # HIGH VALUE
    # --------------------------------------------------------

    if (
        r >= 4
        and f >= 4
        and m >= 4
    ):
        return "High Value"

    # --------------------------------------------------------
    # LOYAL
    # --------------------------------------------------------

    if (
        f >= 4
        and r >= 3
    ):
        return "Loyal"

    # --------------------------------------------------------
    # AT RISK
    # --------------------------------------------------------

    if (
        r <= 2
        and f >= 3
    ):
        return "At Risk"

    # --------------------------------------------------------
    # NEW
    # --------------------------------------------------------

    if (
        recency <= 30
        and frequency <= 2
    ):
        return "New"

    # --------------------------------------------------------
    # INACTIVE
    # --------------------------------------------------------

    if recency > 180:
        return "Inactive"

    # --------------------------------------------------------
    # LOW VALUE
    # --------------------------------------------------------

    if (
        monetary <= 0
        or (
            f <= 2
            and m <= 2
        )
    ):
        return "Low Value"

    return "Developing"


# ============================================================
# CUSTOMER INTELLIGENCE VIEW
# ============================================================

@login_required
def customer_intelligence(request):

    # ========================================================
    # AUTHORIZATION
    # ========================================================

    if not customer_user_is_allowed(request):

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "access_denied": True,
                "datasets": [],
                "error_message": (
                    "Your account is not approved for "
                    "Customer Intelligence."
                ),
            },
            status=403
        )

    # ========================================================
    # ONLY CUSTOMER CATEGORY DATASET
    # ========================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
            dataset_type="Customers"
        )
        .order_by("-uploaded_at")
    )

    # ========================================================
    # NO CUSTOMER DATA
    # ========================================================

    if not datasets.exists():

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "datasets": [],
                "customer_dataset_only": True,
                "error_message": (
                    "No Customers dataset is available. "
                    "Upload a Customers dataset from "
                    "Data Management."
                ),
            }
        )

    # ========================================================
    # DATASET SELECTION
    # ========================================================

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

    # ========================================================
    # CLEANED VERSION
    # ========================================================

    cleaned_version = ci_get_cleaned_version(
        selected_dataset
    )

    # ========================================================
    # SOURCE
    # ========================================================

    source = (
        cleaned_version
        if cleaned_version is not None
        else selected_dataset
    )

    dataframe = ci_read_dataset(
        source
    )

    # ========================================================
    # DATA READ FAILURE
    # ========================================================

    if dataframe is None or dataframe.empty:

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "cleaned_version": cleaned_version,
                "customer_dataset_only": True,
                "error_message": (
                    "The Customers dataset could not "
                    "be read or contains no records."
                ),
            }
        )

    dataframe = dataframe.copy()

    # ========================================================
    # NORMALIZE COLUMN NAMES
    # ========================================================

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    # ========================================================
    # COLUMN DETECTION
    # ========================================================

    customer_column = ci_find_column(
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

    date_column = ci_find_column(
        dataframe,
        [
            "date",
            "order_date",
            "sales_date",
            "transaction_date",
            "purchase_date",
            "purchase_datetime",
            "transaction_date_time",
            "created_at",
        ]
    )

    sales_column = ci_find_column(
        dataframe,
        [
            "sales",
            "revenue",
            "amount",
            "total_sales",
            "total_revenue",
            "sales_amount",
            "purchase_amount",
            "order_value",
            "customer_spend",
            "spending",
            "value",
        ]
    )

    quantity_column = ci_find_column(
        dataframe,
        [
            "quantity",
            "qty",
            "units",
            "units_sold",
            "purchase_quantity",
        ]
    )

    order_column = ci_find_column(
        dataframe,
        [
            "order_id",
            "order",
            "order_number",
            "transaction_id",
            "invoice_id",
            "invoice",
            "transaction",
        ]
    )

    product_column = ci_find_column(
        dataframe,
        [
            "product_id",
            "product",
            "product_name",
            "item",
            "item_name",
        ]
    )

    region_column = ci_find_column(
        dataframe,
        [
            "region",
            "area",
            "location",
            "city",
            "state",
            "territory",
        ]
    )

    discount_column = ci_find_column(
        dataframe,
        [
            "discount",
            "discount_amount",
            "discount_percent",
            "discount_percentage",
        ]
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    missing_columns = []

    if not customer_column:
        missing_columns.append(
            "Customer ID"
        )

    if not date_column:
        missing_columns.append(
            "Date"
        )

    if not sales_column:
        missing_columns.append(
            "Sales / Revenue / Amount"
        )

    if missing_columns:

        return render(
            request,
            "analytics/customer_intelligence.html",
            {
                "has_data": False,
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "cleaned_version": cleaned_version,
                "customer_dataset_only": True,
                "missing_customer_columns": True,
                "missing_columns": missing_columns,
                "customer_column": customer_column,
                "date_column": date_column,
                "sales_column": sales_column,
                "quantity_column": quantity_column,
                "order_column": order_column,
                "error_message": (
                    "Customer Intelligence requires "
                    "Customer ID, Date and Sales/Revenue."
                ),
            }
        )

    # ========================================================
    # NORMALIZE DATA
    # ========================================================

    dataframe[customer_column] = (
        dataframe[customer_column]
        .astype(str)
        .str.strip()
    )

    dataframe[date_column] = pd.to_datetime(
        dataframe[date_column],
        errors="coerce"
    )

    dataframe[sales_column] = ci_clean_numeric(
        dataframe[sales_column]
    ).fillna(0)

    if quantity_column:

        dataframe[quantity_column] = (
            ci_clean_numeric(
                dataframe[quantity_column]
            ).fillna(0)
        )

    if order_column:

        dataframe[order_column] = (
            dataframe[order_column]
            .astype(str)
            .str.strip()
        )

    if discount_column:

        dataframe[discount_column] = (
            ci_clean_numeric(
                dataframe[discount_column]
            ).fillna(0)
        )

    # ========================================================
    # REMOVE INVALID RECORDS
    # ========================================================

    dataframe = dataframe.dropna(
        subset=[
            customer_column,
            date_column
        ]
    )

    dataframe = dataframe[
        dataframe[customer_column] != ""
    ]

    dataframe = dataframe[
        dataframe[customer_column].str.lower()
        != "nan"
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
                "customer_dataset_only": True,
                "error_message": (
                    "No valid customer transaction "
                    "records were found."
                ),
            }
        )

    # ========================================================
    # FULL DATASET REFERENCE
    #
    # Used for true lifetime calculations.
    # ========================================================

    full_data = dataframe.copy()

    analysis_date = (
        full_data[date_column]
        .max()
        .normalize()
    )

    # ========================================================
    # DATE RANGE
    # ========================================================

    range_key = request.GET.get(
        "range",
        "180"
    )

    start_date = request.GET.get(
        "start_date"
    )

    end_date = request.GET.get(
        "end_date"
    )

    filtered_data, date_meta = (
        ci_apply_date_range(
            full_data,
            date_column,
            range_key,
            start_date,
            end_date,
        )
    )

    # ========================================================
    # FALLBACK
    # ========================================================

    if filtered_data.empty:

        filtered_data = full_data.copy()

        date_meta = {
            "range_key": "all",
            "range_label": "All Data",
            "start": full_data[
                date_column
            ].min().normalize(),
            "end": full_data[
                date_column
            ].max().normalize(),
            "days": (
                full_data[date_column].max().normalize()
                -
                full_data[date_column].min().normalize()
            ).days + 1,
        }

    # ========================================================
    # CUSTOMER TRANSACTION COUNT
    # ========================================================

    if order_column:

        filtered_order_series = (
            filtered_data[order_column]
            .replace("", np.nan)
            .dropna()
        )

        total_orders = int(
            filtered_order_series.nunique()
        )

    else:

        total_orders = int(
            len(filtered_data)
        )

    # ========================================================
    # CUSTOMER MASTER TABLE
    #
    # Lifetime customer behaviour from ALL data.
    # ========================================================

    if order_column:

        frequency_series = (
            full_data
            .groupby(customer_column)[
                order_column
            ]
            .nunique()
        )

    else:

        frequency_series = (
            full_data
            .groupby(customer_column)
            .size()
        )

    customer_master = (
        full_data
        .groupby(customer_column)
        .agg(
            first_purchase=(
                date_column,
                "min"
            ),
            last_purchase=(
                date_column,
                "max"
            ),
            monetary=(
                sales_column,
                "sum"
            ),
            transaction_count=(
                date_column,
                "count"
            ),
        )
        .reset_index()
    )

    customer_master["frequency"] = (
        customer_master[
            customer_column
        ].map(
            frequency_series
        ).fillna(0)
    )

    # ========================================================
    # LIFETIME RECENCY
    # ========================================================

    customer_master["recency"] = (
        analysis_date
        -
        customer_master["last_purchase"]
    ).dt.days

    customer_master["recency"] = (
        customer_master["recency"]
        .fillna(0)
        .clip(lower=0)
        .astype(int)
    )

    customer_master["frequency"] = (
        pd.to_numeric(
            customer_master["frequency"],
            errors="coerce"
        )
        .fillna(0)
        .astype(int)
    )

    customer_master["monetary"] = (
        pd.to_numeric(
            customer_master["monetary"],
            errors="coerce"
        )
        .fillna(0)
    )

    # ========================================================
    # RFM SCORES
    # ========================================================

    customer_master["recency_score"] = (
        ci_rfm_score(
            customer_master["recency"],
            higher_is_better=False
        )
    )

    customer_master["frequency_score"] = (
        ci_rfm_score(
            customer_master["frequency"],
            higher_is_better=True
        )
    )

    customer_master["monetary_score"] = (
        ci_rfm_score(
            customer_master["monetary"],
            higher_is_better=True
        )
    )

    # ========================================================
    # RFM TOTAL
    # ========================================================

    customer_master["rfm_score"] = (
        customer_master["recency_score"]
        +
        customer_master["frequency_score"]
        +
        customer_master["monetary_score"]
    )

    # ========================================================
    # SEGMENTATION
    # ========================================================

    customer_master["segment"] = (
        customer_master.apply(
            ci_classify_customer,
            axis=1
        )
    )

    # ========================================================
    # SELECTED PERIOD CUSTOMER LIST
    # ========================================================

    selected_customers = set(
        filtered_data[
            customer_column
        ].astype(str)
    )

    period_customer_master = (
        customer_master[
            customer_master[
                customer_column
            ].astype(str).isin(
                selected_customers
            )
        ]
        .copy()
    )

    # ========================================================
    # BASIC CUSTOMER KPIs
    # ========================================================

    total_customers = int(
        period_customer_master[
            customer_column
        ].nunique()
    )

    # ========================================================
    # NEW CUSTOMERS
    #
    # A customer is genuinely new when their FIRST-EVER
    # purchase occurs inside the selected period.
    # ========================================================

    if (
        date_meta["start"] is not None
        and date_meta["end"] is not None
    ):

        new_customers = int(
            (
                (
                    customer_master[
                        "first_purchase"
                    ]
                    >= date_meta["start"]
                )
                &
                (
                    customer_master[
                        "first_purchase"
                    ]
                    <= date_meta["end"]
                )
            ).sum()
        )

    else:

        new_customers = 0

    # ========================================================
    # RETURNING CUSTOMERS
    #
    # Customers active during selected period who existed
    # before the period started.
    # ========================================================

    if date_meta["start"] is not None:

        returning_customers = int(
            (
                (
                    customer_master[
                        customer_column
                    ].astype(str)
                    .isin(selected_customers)
                )
                &
                (
                    customer_master[
                        "first_purchase"
                    ]
                    < date_meta["start"]
                )
            ).sum()
        )

    else:

        returning_customers = int(
            (
                period_customer_master[
                    "frequency"
                ] > 1
            ).sum()
        )

    # ========================================================
    # REPEAT CUSTOMERS
    # ========================================================

    repeat_customers = int(
        (
            period_customer_master[
                "frequency"
            ] > 1
        ).sum()
    )

    repeat_customer_rate = (
        repeat_customers
        /
        total_customers
        *
        100
        if total_customers
        else 0
    )

    # ========================================================
    # PURCHASE FREQUENCY
    # ========================================================

    purchase_frequency = (
        total_orders
        /
        total_customers
        if total_customers
        else 0
    )

    # ========================================================
    # PERIOD REVENUE
    # ========================================================

    period_revenue = float(
        filtered_data[
            sales_column
        ].sum()
    )

    # ========================================================
    # AVERAGE CUSTOMER SPENDING
    # ========================================================

    average_customer_spending = (
        period_revenue
        /
        total_customers
        if total_customers
        else 0
    )

    # ========================================================
    # AVERAGE ORDER VALUE
    # ========================================================

    average_order_value = (
        period_revenue
        /
        total_orders
        if total_orders
        else 0
    )

    # ========================================================
    # TOTAL LIFETIME REVENUE
    # ========================================================

    lifetime_revenue = float(
        customer_master[
            "monetary"
        ].sum()
    )

    # ========================================================
    # HISTORICAL CUSTOMER LIFETIME VALUE
    #
    # CLV = lifetime revenue / total customers
    #
    # This is a transparent historical CLV rather than
    # an unsupported future prediction.
    # ========================================================

    customer_lifetime_value = (
        lifetime_revenue
        /
        len(customer_master)
        if len(customer_master)
        else 0
    )

    # ========================================================
    # AVERAGE CUSTOMER LIFESPAN
    # ========================================================

    customer_master["lifespan_days"] = (
        customer_master[
            "last_purchase"
        ]
        -
        customer_master[
            "first_purchase"
        ]
    ).dt.days.clip(
        lower=0
    )

    average_customer_lifespan_days = float(
        customer_master[
            "lifespan_days"
        ].mean()
        if not customer_master.empty
        else 0
    )

    # ========================================================
    # ACTIVE CUSTOMERS
    # ========================================================

    active_customers = int(
        (
            period_customer_master[
                "recency"
            ] <= 90
        ).sum()
    )

    # ========================================================
    # INACTIVE CUSTOMERS
    # ========================================================

    inactive_customers = int(
        (
            period_customer_master[
                "recency"
            ] > 180
        ).sum()
    )

    # ========================================================
    # HIGH VALUE CUSTOMERS
    # ========================================================

    high_value_customers = int(
        (
            period_customer_master[
                "segment"
            ] == "High Value"
        ).sum()
    )

    # ========================================================
    # LOYAL CUSTOMERS
    # ========================================================

    loyal_customers = int(
        (
            period_customer_master[
                "segment"
            ] == "Loyal"
        ).sum()
    )

    # ========================================================
    # AT RISK CUSTOMERS
    # ========================================================

    at_risk_customers = int(
        (
            period_customer_master[
                "segment"
            ] == "At Risk"
        ).sum()
    )

    # ========================================================
    # LOW VALUE CUSTOMERS
    # ========================================================

    low_value_customers = int(
        (
            period_customer_master[
                "segment"
            ] == "Low Value"
        ).sum()
    )

    # ========================================================
    # NEW SEGMENT
    # ========================================================

    new_segment_customers = int(
        (
            period_customer_master[
                "segment"
            ] == "New"
        ).sum()
    )

    # ========================================================
    # DEVELOPING CUSTOMERS
    # ========================================================

    developing_customers = int(
        (
            period_customer_master[
                "segment"
            ] == "Developing"
        ).sum()
    )

    # ========================================================
    # SEGMENT DISTRIBUTION
    # ========================================================

    segment_order = [
        "High Value",
        "Loyal",
        "New",
        "At Risk",
        "Developing",
        "Low Value",
        "Inactive",
    ]

    segment_distribution = []

    for segment in segment_order:

        segment_df = period_customer_master[
            period_customer_master[
                "segment"
            ] == segment
        ]

        count = len(
            segment_df
        )

        revenue = float(
            segment_df[
                "monetary"
            ].sum()
        )

        percentage = (
            count
            /
            total_customers
            *
            100
            if total_customers
            else 0
        )

        revenue_percentage = (
            revenue
            /
            lifetime_revenue
            *
            100
            if lifetime_revenue
            else 0
        )

        segment_distribution.append(
            {
                "name": segment,
                "count": count,
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
                    revenue / count
                    if count
                    else 0,
                    2
                ),
            }
        )

    # ========================================================
    # SEGMENT CHART
    # ========================================================

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

    # ========================================================
    # TOP CUSTOMERS
    # ========================================================

    top_customer_df = (
        period_customer_master
        .sort_values(
            "monetary",
            ascending=False
        )
        .head(10)
    )

    top_customers = []

    for _, row in top_customer_df.iterrows():

        top_customers.append(
            {
                "customer": str(
                    row[customer_column]
                ),
                "frequency": ci_int(
                    row["frequency"]
                ),
                "monetary": ci_money(
                    row["monetary"]
                ),
                "recency": ci_int(
                    row["recency"]
                ),
                "rfm_score": ci_int(
                    row["rfm_score"]
                ),
                "segment": str(
                    row["segment"]
                ),
            }
        )

    # ========================================================
    # INACTIVE CUSTOMERS
    # ========================================================

    inactive_df = (
        period_customer_master[
            period_customer_master[
                "recency"
            ] > 180
        ]
        .sort_values(
            "monetary",
            ascending=False
        )
        .head(10)
    )

    inactive_customer_list = []

    for _, row in inactive_df.iterrows():

        inactive_customer_list.append(
            {
                "customer": str(
                    row[customer_column]
                ),
                "frequency": ci_int(
                    row["frequency"]
                ),
                "monetary": ci_money(
                    row["monetary"]
                ),
                "recency": ci_int(
                    row["recency"]
                ),
                "segment": str(
                    row["segment"]
                ),
            }
        )

    # ========================================================
    # AT-RISK CUSTOMERS
    # ========================================================

    risk_df = (
        period_customer_master[
            period_customer_master[
                "segment"
            ] == "At Risk"
        ]
        .sort_values(
            "monetary",
            ascending=False
        )
        .head(10)
    )

    at_risk_customer_list = []

    for _, row in risk_df.iterrows():

        at_risk_customer_list.append(
            {
                "customer": str(
                    row[customer_column]
                ),
                "frequency": ci_int(
                    row["frequency"]
                ),
                "monetary": ci_money(
                    row["monetary"]
                ),
                "recency": ci_int(
                    row["recency"]
                ),
                "rfm_score": ci_int(
                    row["rfm_score"]
                ),
            }
        )

    # ========================================================
    # RFM SCORE DISTRIBUTION
    # ========================================================

    rfm_score_distribution = []

    for score in range(3, 16):

        count = int(
            (
                period_customer_master[
                    "rfm_score"
                ] == score
            ).sum()
        )

        rfm_score_distribution.append(
            {
                "score": score,
                "count": count,
            }
        )

    rfm_score_labels = [
        item["score"]
        for item in rfm_score_distribution
    ]

    rfm_score_values = [
        item["count"]
        for item in rfm_score_distribution
    ]

    # ========================================================
    # RFM AVERAGES
    # ========================================================

    average_recency = float(
        period_customer_master[
            "recency"
        ].mean()
        if not period_customer_master.empty
        else 0
    )

    average_frequency = float(
        period_customer_master[
            "frequency"
        ].mean()
        if not period_customer_master.empty
        else 0
    )

    average_monetary = float(
        period_customer_master[
            "monetary"
        ].mean()
        if not period_customer_master.empty
        else 0
    )

    average_rfm_score = float(
        period_customer_master[
            "rfm_score"
        ].mean()
        if not period_customer_master.empty
        else 0
    )

    # ========================================================
    # CUSTOMER VALUE CONCENTRATION
    # ========================================================

    sorted_customers = (
        customer_master
        .sort_values(
            "monetary",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )

    sorted_revenue = (
        sorted_customers[
            "monetary"
        ]
        .clip(
            lower=0
        )
    )

    total_positive_revenue = float(
        sorted_revenue.sum()
    )

    if total_positive_revenue > 0:

        cumulative_revenue = (
            sorted_revenue.cumsum()
            /
            total_positive_revenue
            *
            100
        )

        customers_for_80 = (
            int(
                (
                    cumulative_revenue < 80
                ).sum()
            )
            + 1
        )

    else:

        customers_for_80 = 0

    revenue_concentration_20 = 0

    if len(sorted_customers) > 0:

        top_20_count = max(
            1,
            math.ceil(
                len(sorted_customers)
                * 0.20
            )
        )

        revenue_concentration_20 = (
            sorted_customers
            .head(top_20_count)[
                "monetary"
            ]
            .sum()
            /
            total_positive_revenue
            *
            100
            if total_positive_revenue
            else 0
        )

    # ========================================================
    # CUSTOMER HEALTH
    # ========================================================

    if total_customers == 0:

        customer_health = "No Data"

    else:

        at_risk_ratio = (
            at_risk_customers
            /
            total_customers
        )

        inactive_ratio = (
            inactive_customers
            /
            total_customers
        )

        if (
            at_risk_ratio >= 0.30
            or inactive_ratio >= 0.40
        ):

            customer_health = "Critical"

        elif (
            at_risk_ratio >= 0.15
            or inactive_ratio >= 0.25
        ):

            customer_health = "Needs Attention"

        else:

            customer_health = "Healthy"

    # ========================================================
    # CUSTOMER HEALTH SCORE
    # ========================================================

    retention_score = min(
        repeat_customer_rate,
        100
    )

    risk_penalty = (
        (
            at_risk_customers
            /
            total_customers
            *
            100
        )
        if total_customers
        else 0
    )

    inactive_penalty = (
        (
            inactive_customers
            /
            total_customers
            *
            100
        )
        if total_customers
        else 0
    )

    health_score = (
        retention_score * 0.45
        +
        (
            100 - risk_penalty
        ) * 0.30
        +
        (
            100 - inactive_penalty
        ) * 0.25
    )

    health_score = round(
        max(
            0,
            min(
                100,
                health_score
            )
        )
    )

    # ========================================================
    # CUSTOMER INSIGHTS
    # ========================================================

    customer_insights = []

    if new_customers > 0:

        customer_insights.append(
            {
                "type": "positive",
                "title": "New customer acquisition",
                "description": (
                    f"{new_customers:,} customers "
                    "made their first recorded purchase "
                    "during the selected period."
                ),
            }
        )

    if returning_customers > 0:

        customer_insights.append(
            {
                "type": "positive",
                "title": "Returning customer activity",
                "description": (
                    f"{returning_customers:,} existing "
                    "customers returned during the "
                    "selected period."
                ),
            }
        )

    if repeat_customer_rate >= 60:

        customer_insights.append(
            {
                "type": "positive",
                "title": "Strong repeat behaviour",
                "description": (
                    f"{repeat_customer_rate:.1f}% of "
                    "customers have made more than one "
                    "recorded purchase."
                ),
            }
        )

    elif repeat_customer_rate < 30:

        customer_insights.append(
            {
                "type": "warning",
                "title": "Low repeat purchase behaviour",
                "description": (
                    f"Only {repeat_customer_rate:.1f}% "
                    "of customers have made repeat purchases. "
                    "Retention campaigns may improve customer value."
                ),
            }
        )

    if at_risk_customers > 0:

        risk_revenue = float(
            period_customer_master[
                period_customer_master[
                    "segment"
                ] == "At Risk"
            ]["monetary"].sum()
        )

        customer_insights.append(
            {
                "type": "warning",
                "title": "Customers at risk",
                "description": (
                    f"{at_risk_customers:,} customers "
                    f"are currently classified as At Risk, "
                    f"representing ₹{risk_revenue:,.0f} "
                    "of historical customer value."
                ),
            }
        )

    if inactive_customers > 0:

        customer_insights.append(
            {
                "type": "warning",
                "title": "Inactive customer base",
                "description": (
                    f"{inactive_customers:,} customers "
                    "have not purchased for more than "
                    "180 days."
                ),
            }
        )

    if high_value_customers > 0:

        high_value_revenue = float(
            period_customer_master[
                period_customer_master[
                    "segment"
                ] == "High Value"
            ]["monetary"].sum()
        )

        customer_insights.append(
            {
                "type": "positive",
                "title": "High-value opportunity",
                "description": (
                    f"{high_value_customers:,} High Value "
                    f"customers contribute approximately "
                    f"₹{high_value_revenue:,.0f} in "
                    "historical customer revenue."
                ),
            }
        )

    if revenue_concentration_20 >= 60:

        customer_insights.append(
            {
                "type": "warning",
                "title": "Revenue concentration",
                "description": (
                    f"The top 20% of customers generate "
                    f"approximately "
                    f"{revenue_concentration_20:.1f}% "
                    "of customer revenue. Retention of "
                    "high-value customers is important."
                ),
            }
        )

    if purchase_frequency >= 3:

        customer_insights.append(
            {
                "type": "positive",
                "title": "Healthy purchase frequency",
                "description": (
                    f"Customers generate an average of "
                    f"{purchase_frequency:.2f} orders "
                    "during the selected period."
                ),
            }
        )

    # ========================================================
    # RECOMMENDATIONS
    # ========================================================

    customer_recommendations = []

    if at_risk_customers > 0:

        customer_recommendations.append(
            {
                "priority": "High",
                "title": "Launch win-back campaigns",
                "description": (
                    "Target At Risk customers with "
                    "personalized offers and re-engagement "
                    "communication."
                ),
            }
        )

    if inactive_customers > 0:

        customer_recommendations.append(
            {
                "priority": "High",
                "title": "Reactivate inactive customers",
                "description": (
                    "Create a reactivation campaign for "
                    "customers inactive for more than 180 days."
                ),
            }
        )

    if new_customers > 0:

        customer_recommendations.append(
            {
                "priority": "Medium",
                "title": "Convert new customers",
                "description": (
                    "Focus on second-purchase campaigns "
                    "to move new customers toward Loyal status."
                ),
            }
        )

    if high_value_customers > 0:

        customer_recommendations.append(
            {
                "priority": "High",
                "title": "Protect high-value customers",
                "description": (
                    "Use VIP treatment, personalized "
                    "recommendations and loyalty benefits."
                ),
            }
        )

    if repeat_customer_rate < 40:

        customer_recommendations.append(
            {
                "priority": "Medium",
                "title": "Improve repeat purchases",
                "description": (
                    "Introduce loyalty incentives, "
                    "cross-sell offers and personalized follow-ups."
                ),
            }
        )

    # ========================================================
    # MONTHLY CUSTOMER TREND
    # ========================================================

    monthly_customer = (
        filtered_data
        .set_index(date_column)
        .resample("ME")
        .agg(
            revenue=(
                sales_column,
                "sum"
            ),
            transactions=(
                sales_column,
                "count"
            ),
        )
    )

    monthly_unique_customers = (
        filtered_data
        .set_index(date_column)
        .groupby(
            pd.Grouper(
                freq="ME"
            )
        )[customer_column]
        .nunique()
    )

    monthly_labels = [
        date.strftime(
            "%b %Y"
        )
        for date in monthly_customer.index
    ]

    monthly_revenue_values = [
        round(
            float(value),
            2
        )
        for value in monthly_customer[
            "revenue"
        ].values
    ]

    monthly_customer_values = [
        int(value)
        for value in monthly_unique_customers.values
    ]

    monthly_transaction_values = [
        int(value)
        for value in monthly_customer[
            "transactions"
        ].values
    ]

    # ========================================================
    # CUSTOMER SPENDING DISTRIBUTION
    # ========================================================

    spending_bins = [
        0,
        1000,
        5000,
        10000,
        25000,
        50000,
        float("inf"),
    ]

    spending_labels = [
        "₹0–1K",
        "₹1K–5K",
        "₹5K–10K",
        "₹10K–25K",
        "₹25K–50K",
        "₹50K+",
    ]

    spending_distribution = pd.cut(
        period_customer_master[
            "monetary"
        ],
        bins=spending_bins,
        labels=spending_labels,
        include_lowest=True,
        right=False,
    )

    spending_counts = (
        spending_distribution
        .value_counts(
            sort=False
        )
    )

    spending_labels_json = [
        str(label)
        for label in spending_counts.index
    ]

    spending_values_json = [
        int(value)
        for value in spending_counts.values
    ]

    # ========================================================
    # CUSTOMER ACQUISITION TREND
    # ========================================================

    acquisition_series = (
        customer_master
        .set_index(
            "first_purchase"
        )
        .resample("ME")[
            customer_column
        ]
        .nunique()
    )

    acquisition_labels = [
        date.strftime(
            "%b %Y"
        )
        for date in acquisition_series.index
    ]

    acquisition_values = [
        int(value)
        for value in acquisition_series.values
    ]

    # ========================================================
    # CUSTOMER SEGMENT RFM AVERAGES
    # ========================================================

    segment_rfm = []

    for segment in segment_order:

        segment_df = period_customer_master[
            period_customer_master[
                "segment"
            ] == segment
        ]

        if segment_df.empty:
            continue

        segment_rfm.append(
            {
                "segment": segment,
                "recency": round(
                    float(
                        segment_df[
                            "recency"
                        ].mean()
                    ),
                    1
                ),
                "frequency": round(
                    float(
                        segment_df[
                            "frequency"
                        ].mean()
                    ),
                    2
                ),
                "monetary": round(
                    float(
                        segment_df[
                            "monetary"
                        ].mean()
                    ),
                    2
                ),
            }
        )

    # ========================================================
    # FINAL CONTEXT
    # ========================================================

    context = {

        # ----------------------------------------------------
        # PAGE
        # ----------------------------------------------------

        "has_data": True,

        "customer_dataset_only": True,

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "cleaned_version": cleaned_version,

        # ----------------------------------------------------
        # DATE RANGE
        # ----------------------------------------------------

        "range_key": date_meta[
            "range_key"
        ],

        "range_label": date_meta[
            "range_label"
        ],

        "range_start": (
            date_meta["start"].strftime(
                "%d %b %Y"
            )
            if date_meta["start"] is not None
            else ""
        ),

        "range_end": (
            date_meta["end"].strftime(
                "%d %b %Y"
            )
            if date_meta["end"] is not None
            else ""
        ),

        "range_days": date_meta[
            "days"
        ],

        "date_range_options": (
            CUSTOMER_DATE_RANGES
        ),

        "custom_start": start_date or "",

        "custom_end": end_date or "",

        # ----------------------------------------------------
        # COLUMNS
        # ----------------------------------------------------

        "customer_column": customer_column,

        "date_column": date_column,

        "sales_column": sales_column,

        "quantity_column": quantity_column,

        "order_column": order_column,

        "product_column": product_column,

        "region_column": region_column,

        "discount_column": discount_column,

        # ----------------------------------------------------
        # MAIN KPIs
        # ----------------------------------------------------

        "total_customers": total_customers,

        "new_customers": new_customers,

        "returning_customers": returning_customers,

        "repeat_customers": repeat_customers,

        "repeat_customer_rate": round(
            repeat_customer_rate,
            2
        ),

        "purchase_frequency": round(
            purchase_frequency,
            2
        ),

        "average_customer_spending": round(
            average_customer_spending,
            2
        ),

        "average_order_value": round(
            average_order_value,
            2
        ),

        "customer_lifetime_value": round(
            customer_lifetime_value,
            2
        ),

        # ----------------------------------------------------
        # ADDITIONAL KPIs
        # ----------------------------------------------------

        "total_orders": total_orders,

        "period_revenue": round(
            period_revenue,
            2
        ),

        "lifetime_revenue": round(
            lifetime_revenue,
            2
        ),

        "active_customers": active_customers,

        "inactive_customers": inactive_customers,

        "high_value_customers": high_value_customers,

        "loyal_customers": loyal_customers,

        "at_risk_customers": at_risk_customers,

        "low_value_customers": low_value_customers,

        "new_segment_customers": (
            new_segment_customers
        ),

        "developing_customers": (
            developing_customers
        ),

        # ----------------------------------------------------
        # CUSTOMER LIFETIME
        # ----------------------------------------------------

        "average_customer_lifespan_days": round(
            average_customer_lifespan_days,
            1
        ),

        "average_customer_lifespan_months": round(
            average_customer_lifespan_days
            /
            30.44,
            1
        ),

        # ----------------------------------------------------
        # CUSTOMER HEALTH
        # ----------------------------------------------------

        "customer_health": customer_health,

        "health_score": health_score,

        # ----------------------------------------------------
        # REVENUE CONCENTRATION
        # ----------------------------------------------------

        "customers_for_80_percent_revenue": (
            customers_for_80
        ),

        "revenue_concentration_20": round(
            revenue_concentration_20,
            2
        ),

        # ----------------------------------------------------
        # RFM
        # ----------------------------------------------------

        "average_recency": round(
            average_recency,
            1
        ),

        "average_frequency": round(
            average_frequency,
            2
        ),

        "average_monetary": round(
            average_monetary,
            2
        ),

        "average_rfm_score": round(
            average_rfm_score,
            2
        ),

        # ----------------------------------------------------
        # SEGMENTS
        # ----------------------------------------------------

        "segment_distribution": (
            segment_distribution
        ),

        "segment_rfm": segment_rfm,

        # ----------------------------------------------------
        # TOP CUSTOMERS
        # ----------------------------------------------------

        "top_customers": top_customers,

        # ----------------------------------------------------
        # INACTIVE CUSTOMERS
        # ----------------------------------------------------

        "inactive_customer_list": (
            inactive_customer_list
        ),

        # ----------------------------------------------------
        # AT RISK CUSTOMERS
        # ----------------------------------------------------

        "at_risk_customer_list": (
            at_risk_customer_list
        ),

        # ----------------------------------------------------
        # INSIGHTS
        # ----------------------------------------------------

        "customer_insights": (
            customer_insights
        ),

        # ----------------------------------------------------
        # RECOMMENDATIONS
        # ----------------------------------------------------

        "customer_recommendations": (
            customer_recommendations
        ),

        # ----------------------------------------------------
        # CHART JSON
        # ----------------------------------------------------

        "segment_labels": ci_json(
            segment_labels
        ),

        "segment_values": ci_json(
            segment_values
        ),

        "segment_revenue_values": ci_json(
            segment_revenue_values
        ),

        "rfm_score_labels": ci_json(
            rfm_score_labels
        ),

        "rfm_score_values": ci_json(
            rfm_score_values
        ),

        "monthly_labels": ci_json(
            monthly_labels
        ),

        "monthly_revenue_values": ci_json(
            monthly_revenue_values
        ),

        "monthly_customer_values": ci_json(
            monthly_customer_values
        ),

        "monthly_transaction_values": ci_json(
            monthly_transaction_values
        ),

        "spending_labels": ci_json(
            spending_labels_json
        ),

        "spending_values": ci_json(
            spending_values_json
        ),

        "acquisition_labels": ci_json(
            acquisition_labels
        ),

        "acquisition_values": ci_json(
            acquisition_values
        ),

        # ----------------------------------------------------
        # ANALYSIS DATE
        # ----------------------------------------------------

        "analysis_date": analysis_date.strftime(
            "%d %b %Y"
        ),

        "data_start_date": full_data[
            date_column
        ].min().strftime(
            "%d %b %Y"
        ),

        "data_end_date": full_data[
            date_column
        ].max().strftime(
            "%d %b %Y"
        ),

        # ----------------------------------------------------
        # RECORD COUNTS
        # ----------------------------------------------------

        "total_records": len(
            full_data
        ),

        "filtered_records": len(
            filtered_data
        ),
    }

    return render(
        request,
        "analytics/customer_intelligence.html",
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
# ============================================================
# ANALYTICS - PRODUCT INTELLIGENCE
# ============================================================

import json
import re
from datetime import timedelta

import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from data_management.models import Dataset, DatasetVersion


# ============================================================
# PRODUCT INTELLIGENCE - CONSTANTS
# ============================================================

PRODUCT_DATASET_TYPE = "Products"

PRODUCT_DATE_RANGES = {
    "30": "Last 30 Days",
    "90": "Last 3 Months",
    "180": "Last 6 Months",
    "365": "Last 12 Months",
    "all": "All Data",
}


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

def _product_normalize_column_name(value):
    """
    Convert a column name into a normalized comparison form.

    Examples:
        Product Name -> product_name
        product-name -> product_name
        SALES AMOUNT -> sales_amount
    """

    value = str(value).strip().lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    return value.strip("_")


# ============================================================
# COLUMN DETECTION
# ============================================================

def _product_find_column(df, candidates):
    """
    Detect a dataframe column using exact and partial matching.
    """

    if df is None:
        return None

    if len(df.columns) == 0:
        return None

    normalized_columns = {
        _product_normalize_column_name(column): column
        for column in df.columns
    }

    # --------------------------------------------------------
    # Exact match
    # --------------------------------------------------------

    for candidate in candidates:

        normalized_candidate = (
            _product_normalize_column_name(candidate)
        )

        if normalized_candidate in normalized_columns:
            return normalized_columns[
                normalized_candidate
            ]

    # --------------------------------------------------------
    # Partial match
    # --------------------------------------------------------

    for column in df.columns:

        normalized_column = (
            _product_normalize_column_name(column)
        )

        for candidate in candidates:

            normalized_candidate = (
                _product_normalize_column_name(candidate)
            )

            if (
                normalized_candidate in normalized_column
                or normalized_column in normalized_candidate
            ):
                return column

    return None


# ============================================================
# NUMERIC CLEANING
# ============================================================

def _product_clean_numeric(series):
    """
    Convert currency / numeric strings into numeric values.

    Supports:

        ₹1,200
        $1,200
        €1,200
        £1,200
        1,200
        (500) -> -500
        10%
    """

    if series is None:
        return pd.Series(dtype="float64")

    cleaned = (
        series
        .astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace(
            r"^\((.*)\)$",
            r"-\1",
            regex=True,
        )
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce",
    )


# ============================================================
# JSON
# ============================================================

def _product_json(value):
    """
    Convert Python objects to JSON for Chart.js.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
    )


# ============================================================
# CLEANED VERSION
# ============================================================

def _product_get_cleaned_version(dataset):
    """
    Version priority:

        1. Current cleaned version
        2. Latest cleaned version
        3. Current version
        4. Latest version

    The original Dataset file is used only if no version exists.
    """

    if not dataset:
        return None

    # --------------------------------------------------------
    # Current cleaned
    # --------------------------------------------------------

    current_cleaned = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            version_type="Cleaned",
            is_current=True,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
        .first()
    )

    if current_cleaned:
        return current_cleaned

    # --------------------------------------------------------
    # Latest cleaned
    # --------------------------------------------------------

    latest_cleaned = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            version_type="Cleaned",
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
        .first()
    )

    if latest_cleaned:
        return latest_cleaned

    # --------------------------------------------------------
    # Current version
    # --------------------------------------------------------

    current_version = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            is_current=True,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
        .first()
    )

    if current_version:
        return current_version

    # --------------------------------------------------------
    # Latest version
    # --------------------------------------------------------

    return (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
        .first()
    )


# ============================================================
# READ DATASET
# ============================================================

def _product_read_dataset(dataset, version=None):
    """
    Read CSV / XLS / XLSX.
    """

    file_field = None

    if version and version.file:
        file_field = version.file

    elif dataset and dataset.file:
        file_field = dataset.file

    if not file_field:
        raise ValueError(
            "No dataset file is available."
        )

    try:
        file_path = file_field.path
    except Exception:
        file_path = str(file_field)

    extension = file_path.lower()

    if extension.endswith(".csv"):

        return pd.read_csv(
            file_path,
            low_memory=False,
        )

    if extension.endswith(".xlsx"):

        return pd.read_excel(
            file_path,
        )

    if extension.endswith(".xls"):

        return pd.read_excel(
            file_path,
        )

    raise ValueError(
        "Unsupported file format. "
        "Product Intelligence supports CSV and Excel files."
    )


# ============================================================
# DATE FILTER
# ============================================================

def _product_date_filter(
    df,
    date_column,
    range_key="all",
    start_date=None,
    end_date=None,
):
    """
    Apply date-range filtering.

    Returns:

        filtered dataframe
        metadata dictionary
    """

    if (
        not date_column
        or date_column not in df.columns
    ):

        return (
            df.copy(),
            {
                "range_key": "all",
                "range_label": "All Data",
                "start_date": None,
                "end_date": None,
                "days": None,
            },
        )

    working = df.copy()

    working[date_column] = pd.to_datetime(
        working[date_column],
        errors="coerce",
    )

    working = working.dropna(
        subset=[date_column]
    )

    if working.empty:

        return (
            working,
            {
                "range_key": range_key,
                "range_label": "No Valid Dates",
                "start_date": None,
                "end_date": None,
                "days": 0,
            },
        )

    min_date = (
        working[date_column]
        .min()
        .normalize()
    )

    max_date = (
        working[date_column]
        .max()
        .normalize()
    )

    # ========================================================
    # CUSTOM
    # ========================================================

    if range_key == "custom":

        try:

            requested_start = (
                pd.to_datetime(
                    start_date
                ).normalize()
            )

            requested_end = (
                pd.to_datetime(
                    end_date
                ).normalize()
            )

            if requested_start > requested_end:

                requested_start, requested_end = (
                    requested_end,
                    requested_start,
                )

            filter_start = max(
                requested_start,
                min_date,
            )

            filter_end = min(
                requested_end,
                max_date,
            )

            if filter_start > filter_end:

                return (
                    working.iloc[0:0].copy(),
                    {
                        "range_key": "custom",
                        "range_label": "Custom Range",
                        "start_date": filter_start,
                        "end_date": filter_end,
                        "days": 0,
                    },
                )

            filtered = working[
                (
                    working[date_column]
                    >= filter_start
                )
                &
                (
                    working[date_column]
                    <= filter_end
                )
            ].copy()

            return (
                filtered,
                {
                    "range_key": "custom",
                    "range_label": "Custom Range",
                    "start_date": filter_start,
                    "end_date": filter_end,
                    "days": (
                        filter_end
                        - filter_start
                    ).days + 1,
                },
            )

        except (
            ValueError,
            TypeError,
        ):

            range_key = "all"

    # ========================================================
    # ALL DATA
    # ========================================================

    if range_key == "all":

        return (
            working.copy(),
            {
                "range_key": "all",
                "range_label": "All Data",
                "start_date": min_date,
                "end_date": max_date,
                "days": (
                    max_date
                    - min_date
                ).days + 1,
            },
        )

    # ========================================================
    # PREDEFINED
    # ========================================================

    try:

        days = int(range_key)

    except (
        ValueError,
        TypeError,
    ):

        days = None

    if not days:

        return (
            working.copy(),
            {
                "range_key": "all",
                "range_label": "All Data",
                "start_date": min_date,
                "end_date": max_date,
                "days": (
                    max_date
                    - min_date
                ).days + 1,
            },
        )

    filter_end = max_date

    filter_start = max(
        max_date - timedelta(
            days=days - 1
        ),
        min_date,
    )

    filtered = working[
        (
            working[date_column]
            >= filter_start
        )
        &
        (
            working[date_column]
            <= filter_end
        )
    ].copy()

    return (
        filtered,
        {
            "range_key": str(days),
            "range_label": PRODUCT_DATE_RANGES.get(
                str(days),
                f"Last {days} Days",
            ),
            "start_date": filter_start,
            "end_date": filter_end,
            "days": (
                filter_end
                - filter_start
            ).days + 1,
        },
    )


# ============================================================
# PREVIOUS PERIOD
# ============================================================

def _product_previous_period(
    df,
    date_column,
    current_start,
    current_end,
):
    """
    Return an equal-length previous period.

    Example:

        Current:
            1 Jun - 30 Jun

        Previous:
            2 May - 31 May
    """

    if (
        not date_column
        or date_column not in df.columns
        or current_start is None
        or current_end is None
    ):

        return df.iloc[0:0].copy()

    current_start = pd.to_datetime(
        current_start
    ).normalize()

    current_end = pd.to_datetime(
        current_end
    ).normalize()

    period_days = (
        current_end
        - current_start
    ).days + 1

    if period_days <= 0:
        return df.iloc[0:0].copy()

    previous_end = (
        current_start
        - timedelta(days=1)
    )

    previous_start = (
        previous_end
        - timedelta(days=period_days - 1)
    )

    dates = pd.to_datetime(
        df[date_column],
        errors="coerce",
    )

    return df[
        (
            dates >= previous_start
        )
        &
        (
            dates <= previous_end
        )
    ].copy()


# ============================================================
# PERCENTAGE CHANGE
# ============================================================

def _product_percentage_change(
    current,
    previous,
):
    """
    Calculate percentage change.

    If previous == 0 and current > 0,
    return 100%.

    This avoids division-by-zero errors.
    """

    try:

        current = float(current)
        previous = float(previous)

    except (
        ValueError,
        TypeError,
    ):

        return 0.0

    if previous == 0:

        if current == 0:
            return 0.0

        return 100.0

    return (
        (current - previous)
        / abs(previous)
    ) * 100.0


# ============================================================
# SAFE FLOAT
# ============================================================

def _product_safe_float(value):
    try:
        value = float(value)

        if not np.isfinite(value):
            return 0.0

        return value

    except (
        ValueError,
        TypeError,
    ):
        return 0.0


# ============================================================
# DATE FORMAT
# ============================================================

def _product_format_date(value):
    if value is None:
        return ""

    try:

        return pd.to_datetime(
            value
        ).strftime(
            "%d %b %Y"
        )

    except Exception:

        return ""


# ============================================================
# RETURN COLUMN PROCESSING
# ============================================================

def _product_prepare_returns(
    df,
    return_column,
):
    """
    Detect whether return information is:

        numeric quantity
        boolean
        yes/no text

    Returns:

        return_mode
        prepared_return_series
    """

    if (
        not return_column
        or return_column not in df.columns
    ):

        return (
            "none",
            pd.Series(
                0.0,
                index=df.index,
            ),
        )

    series = df[return_column]

    # --------------------------------------------------------
    # Try numeric interpretation
    # --------------------------------------------------------

    numeric = _product_clean_numeric(
        series
    )

    numeric_valid_ratio = (
        numeric.notna().mean()
        if len(series) > 0
        else 0
    )

    if numeric_valid_ratio >= 0.80:

        return (
            "quantity",
            numeric.fillna(0),
        )

    # --------------------------------------------------------
    # Text return flags
    # --------------------------------------------------------

    normalized = (
        series
        .astype(str)
        .str.strip()
        .str.lower()
    )

    positive_values = {
        "yes",
        "y",
        "true",
        "returned",
        "return",
        "1",
        "refund",
        "refunded",
    }

    flag_series = normalized.isin(
        positive_values
    ).astype(float)

    return (
        "flag",
        flag_series,
    )


# ============================================================
# PRODUCT INTELLIGENCE VIEW
# ============================================================

@login_required
def product_intelligence(request):

    # ========================================================
    # ONLY PRODUCT DATASETS
    # ========================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            dataset_type=PRODUCT_DATASET_TYPE,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    # ========================================================
    # BASE CONTEXT
    # ========================================================

    context = {

        # ----------------------------------------------------
        # Dataset
        # ----------------------------------------------------

        "datasets": datasets,

        "selected_dataset": None,

        "selected_version": None,

        "has_data": False,

        "error_message": "",

        # ----------------------------------------------------
        # Main KPIs
        # ----------------------------------------------------

        "total_products": 0,

        "total_revenue": 0,

        "total_units": 0,

        "total_profit": 0,

        "average_product_revenue": 0,

        "average_selling_price": 0,

        "profit_margin": 0,

        "return_rate": 0,

        "total_return_units": 0,

        # ----------------------------------------------------
        # Performance
        # ----------------------------------------------------

        "revenue_growth": 0,

        "unit_growth": 0,

        "profit_growth": 0,

        "growth_available": False,

        "growing_products": 0,

        "declining_products": 0,

        "low_performing_products": 0,

        "return_risk_products": 0,

        # ----------------------------------------------------
        # Leaders
        # ----------------------------------------------------

        "best_selling_product": "-",

        "highest_revenue_product": "-",

        "highest_profit_product": "-",

        "fastest_growing_product": "-",

        "highest_return_product": "-",

        # ----------------------------------------------------
        # Product table
        # ----------------------------------------------------

        "product_rows": [],

        # ----------------------------------------------------
        # Chart data
        # ----------------------------------------------------

        "product_labels": _product_json([]),

        "product_revenue_values": _product_json([]),

        "product_quantity_values": _product_json([]),

        "product_profit_values": _product_json([]),

        "product_growth_values": _product_json([]),

        # ----------------------------------------------------
        # Trend
        # ----------------------------------------------------

        "trend_labels": _product_json([]),

        "trend_revenue": _product_json([]),

        "trend_profit": _product_json([]),

        "trend_units": _product_json([]),

        # ----------------------------------------------------
        # Pareto / concentration
        # ----------------------------------------------------

        "pareto_labels": _product_json([]),

        "pareto_values": _product_json([]),

        "revenue_concentration": 0,

        "top_product_share": 0,

        # ----------------------------------------------------
        # Scatter
        # ----------------------------------------------------

        "scatter_points": _product_json([]),

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        "status_labels": _product_json([]),

        "status_values": _product_json([]),

        # ----------------------------------------------------
        # Insights
        # ----------------------------------------------------

        "product_insights": [],

        # ----------------------------------------------------
        # Column detection
        # ----------------------------------------------------

        "product_column": None,

        "sales_column": None,

        "quantity_column": None,

        "profit_column": None,

        "cost_column": None,

        "return_column": None,

        "date_column": None,

        # ----------------------------------------------------
        # Date filter
        # ----------------------------------------------------

        "range_key": "all",

        "range_label": "All Data",

        "start_date": "",

        "end_date": "",

        "filter_days": None,

        "available_start_date": "",

        "available_end_date": "",

        # ----------------------------------------------------
        # Dataset information
        # ----------------------------------------------------

        "source_rows": 0,

        "source_columns": 0,

        "analysis_rows": 0,

        "analysis_products": 0,

        "analysis_period": "All Data",

    }

    # ========================================================
    # NO DATASET
    # ========================================================

    if not datasets.exists():

        context["error_message"] = (
            "No Product dataset is available. "
            "Upload a dataset with type 'Products' "
            "from Data Management."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # ========================================================
    # SELECT DATASET
    # ========================================================

    requested_dataset = request.GET.get(
        "dataset"
    )

    selected_dataset = None

    if requested_dataset:

        selected_dataset = (
            datasets
            .filter(
                id=requested_dataset
            )
            .first()
        )

    if not selected_dataset:

        selected_dataset = datasets.first()

    context[
        "selected_dataset"
    ] = selected_dataset

    # ========================================================
    # GET CLEANED VERSION
    # ========================================================

    selected_version = (
        _product_get_cleaned_version(
            selected_dataset
        )
    )

    context[
        "selected_version"
    ] = selected_version

    # ========================================================
    # READ DATA
    # ========================================================

    try:

        df = _product_read_dataset(
            selected_dataset,
            selected_version,
        )

    except Exception as exc:

        context["error_message"] = (
            f"Unable to read Product dataset: {exc}"
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # ========================================================
    # EMPTY DATA
    # ========================================================

    if df is None or df.empty:

        context["error_message"] = (
            "The selected Product dataset "
            "contains no records."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # ========================================================
    # SOURCE INFORMATION
    # ========================================================

    context["source_rows"] = int(
        len(df)
    )

    context["source_columns"] = int(
        len(df.columns)
    )

    # ========================================================
    # CLEAN COLUMN NAMES
    # ========================================================

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # ========================================================
    # DETECT PRODUCT COLUMN
    # ========================================================

    product_column = _product_find_column(
        df,
        [
            "product",
            "product name",
            "product_name",
            "product id",
            "product_id",
            "item",
            "item name",
            "item_name",
            "sku",
            "sku code",
            "sku_code",
            "product code",
            "product_code",
        ],
    )

    # ========================================================
    # DETECT SALES / REVENUE
    # ========================================================

    sales_column = _product_find_column(
        df,
        [
            "sales",
            "revenue",
            "sales amount",
            "sales_amount",
            "total sales",
            "total_sales",
            "net sales",
            "net_sales",
            "amount",
            "order value",
            "order_value",
            "selling amount",
            "selling_amount",
            "sales revenue",
            "sales_revenue",
        ],
    )

    # ========================================================
    # DETECT QUANTITY
    # ========================================================

    quantity_column = _product_find_column(
        df,
        [
            "quantity",
            "qty",
            "units",
            "units sold",
            "units_sold",
            "quantity sold",
            "quantity_sold",
            "volume",
            "sales quantity",
            "sales_quantity",
        ],
    )

    # ========================================================
    # DETECT PROFIT
    # ========================================================

    profit_column = _product_find_column(
        df,
        [
            "profit",
            "net profit",
            "net_profit",
            "gross profit",
            "gross_profit",
            "profit amount",
            "profit_amount",
            "profit value",
            "profit_value",
        ],
    )

    # ========================================================
    # DETECT COST
    # ========================================================

    cost_column = _product_find_column(
        df,
        [
            "cost",
            "cost price",
            "cost_price",
            "cost of goods",
            "cost_of_goods",
            "cogs",
            "purchase cost",
            "purchase_cost",
            "total cost",
            "total_cost",
        ],
    )

    # ========================================================
    # DETECT RETURNS
    # ========================================================

    return_column = _product_find_column(
        df,
        [
            "return",
            "returns",
            "returned",
            "return quantity",
            "return_quantity",
            "returned quantity",
            "returned_quantity",
            "return flag",
            "return_flag",
            "is returned",
            "is_returned",
        ],
    )

    # ========================================================
    # DETECT DATE
    # ========================================================

    date_column = _product_find_column(
        df,
        [
            "date",
            "order date",
            "order_date",
            "sales date",
            "sales_date",
            "transaction date",
            "transaction_date",
            "invoice date",
            "invoice_date",
            "purchase date",
            "purchase_date",
            "created date",
            "created_date",
        ],
    )

    context.update({

        "product_column":
            product_column,

        "sales_column":
            sales_column,

        "quantity_column":
            quantity_column,

        "profit_column":
            profit_column,

        "cost_column":
            cost_column,

        "return_column":
            return_column,

        "date_column":
            date_column,
    })

    # ========================================================
    # PRODUCT COLUMN REQUIRED
    # ========================================================

    if not product_column:

        context["error_message"] = (
            "Product Intelligence could not detect "
            "a Product, Product Name, SKU or Item column."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # ========================================================
    # SALES COLUMN REQUIRED
    # ========================================================

    if not sales_column:

        context["error_message"] = (
            "Product Intelligence requires a Sales "
            "or Revenue column."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # ========================================================
    # WORKING DATA
    # ========================================================

    work_df = df.copy()

    # ========================================================
    # PRODUCT CLEANING
    # ========================================================

    work_df = work_df[
        work_df[product_column].notna()
    ].copy()

    work_df[product_column] = (
        work_df[product_column]
        .astype(str)
        .str.strip()
    )

    invalid_products = {
        "",
        "nan",
        "none",
        "null",
        "na",
        "n/a",
        "-",
        "unknown",
    }

    work_df = work_df[
        ~work_df[product_column]
        .str.lower()
        .isin(invalid_products)
    ].copy()

    # ========================================================
    # SALES
    # ========================================================

    work_df[sales_column] = (
        _product_clean_numeric(
            work_df[sales_column]
        )
        .fillna(0)
    )

    # ========================================================
    # QUANTITY
    # ========================================================

    if quantity_column:

        work_df[quantity_column] = (
            _product_clean_numeric(
                work_df[quantity_column]
            )
            .fillna(0)
        )

    else:

        # One row = one product transaction
        # when no quantity column exists.
        work_df[
            "_product_units_"
        ] = 1.0

        quantity_column = (
            "_product_units_"
        )

        context[
            "quantity_column"
        ] = "Not detected — calculated as records"

    # ========================================================
    # PROFIT
    # ========================================================

    if profit_column:

        work_df[profit_column] = (
            _product_clean_numeric(
                work_df[profit_column]
            )
            .fillna(0)
        )

    elif cost_column:

        work_df[cost_column] = (
            _product_clean_numeric(
                work_df[cost_column]
            )
            .fillna(0)
        )

        work_df[
            "_product_profit_"
        ] = (
            work_df[sales_column]
            - work_df[cost_column]
        )

        profit_column = (
            "_product_profit_"
        )

        context[
            "profit_column"
        ] = "Calculated: Sales - Cost"

    else:

        work_df[
            "_product_profit_"
        ] = 0.0

        profit_column = (
            "_product_profit_"
        )

        context[
            "profit_column"
        ] = "Not detected"

    # ========================================================
    # RETURNS
    # ========================================================

    return_mode, return_series = (
        _product_prepare_returns(
            work_df,
            return_column,
        )
    )

    work_df[
        "_product_return_value_"
    ] = return_series

    # ========================================================
    # DATE
    # ========================================================

    if date_column:

        work_df[date_column] = (
            pd.to_datetime(
                work_df[date_column],
                errors="coerce",
            )
        )

        valid_dates = work_df[
            work_df[date_column].notna()
        ]

        if not valid_dates.empty:

            context[
                "available_start_date"
            ] = _product_format_date(
                valid_dates[
                    date_column
                ].min()
            )

            context[
                "available_end_date"
            ] = _product_format_date(
                valid_dates[
                    date_column
                ].max()
            )

    # ========================================================
    # DATE FILTER
    # ========================================================

    requested_range = request.GET.get(
        "range",
        "all",
    )

    requested_start = request.GET.get(
        "start_date",
        "",
    )

    requested_end = request.GET.get(
        "end_date",
        "",
    )

    filtered_df, filter_info = (
        _product_date_filter(
            work_df,
            date_column,
            requested_range,
            requested_start,
            requested_end,
        )
    )

    # ========================================================
    # FILTER CONTEXT
    # ========================================================

    context.update({

        "range_key":
            filter_info["range_key"],

        "range_label":
            filter_info["range_label"],

        "filter_days":
            filter_info["days"],

        "start_date":
            _product_format_date(
                filter_info["start_date"]
            ),

        "end_date":
            _product_format_date(
                filter_info["end_date"]
            ),

        "analysis_period":
            filter_info["range_label"],
    })

    # ========================================================
    # NO DATA AFTER FILTER
    # ========================================================

    if filtered_df.empty:

        context["error_message"] = (
            "No Product records are available "
            "for the selected date range."
        )

        return render(
            request,
            "analytics/product_intelligence.html",
            context,
        )

    # ========================================================
    # ANALYSIS ROWS
    # ========================================================

    context["analysis_rows"] = int(
        len(filtered_df)
    )

    # ========================================================
    # PRODUCT AGGREGATION
    # ========================================================

    grouped = (
        filtered_df
        .groupby(
            product_column,
            dropna=False,
        )
        .agg(

            revenue=(
                sales_column,
                "sum",
            ),

            units=(
                quantity_column,
                "sum",
            ),

            profit=(
                profit_column,
                "sum",
            ),

            records=(
                product_column,
                "size",
            ),

            return_value=(
                "_product_return_value_",
                "sum",
            ),
        )
        .reset_index()
    )

    grouped.rename(
        columns={
            product_column: "product",
        },
        inplace=True,
    )

    # ========================================================
    # RETURN RATE
    # ========================================================

    if return_mode == "quantity":

        grouped["return_units"] = (
            grouped["return_value"]
            .clip(lower=0)
        )

        grouped["return_rate"] = np.where(
            grouped["units"] > 0,

            (
                grouped["return_units"]
                / grouped["units"]
            ) * 100,

            0,
        )

        return_rate_denominator = (
            "units"
        )

    elif return_mode == "flag":

        grouped["return_units"] = (
            grouped["return_value"]
            .clip(lower=0)
        )

        grouped["return_rate"] = np.where(
            grouped["records"] > 0,

            (
                grouped["return_value"]
                / grouped["records"]
            ) * 100,

            0,
        )

        return_rate_denominator = (
            "records"
        )

    else:

        grouped["return_units"] = 0.0

        grouped["return_rate"] = 0.0

        return_rate_denominator = (
            "none"
        )

    # ========================================================
    # PRODUCT COUNT
    # ========================================================

    total_products = int(
        grouped["product"].nunique()
    )

    # ========================================================
    # TOTAL REVENUE
    # ========================================================

    total_revenue = (
        _product_safe_float(
            grouped["revenue"].sum()
        )
    )

    # ========================================================
    # TOTAL UNITS
    # ========================================================

    total_units = (
        _product_safe_float(
            grouped["units"].sum()
        )
    )

    # ========================================================
    # TOTAL PROFIT
    # ========================================================

    total_profit = (
        _product_safe_float(
            grouped["profit"].sum()
        )
    )

    # ========================================================
    # TOTAL RETURNS
    # ========================================================

    total_return_units = (
        _product_safe_float(
            grouped["return_units"].sum()
        )
    )

    # ========================================================
    # AVERAGE PRODUCT REVENUE
    # ========================================================

    average_product_revenue = (

        total_revenue
        / total_products

        if total_products > 0

        else 0
    )

    # ========================================================
    # AVERAGE SELLING PRICE
    # ========================================================

    average_selling_price = (

        total_revenue
        / total_units

        if total_units > 0

        else 0
    )

    # ========================================================
    # PROFIT MARGIN
    # ========================================================

    profit_margin = (

        (
            total_profit
            / total_revenue
        ) * 100

        if total_revenue != 0

        else 0
    )

    # ========================================================
    # OVERALL RETURN RATE
    # ========================================================

    if return_rate_denominator == "units":

        return_rate = (

            (
                total_return_units
                / total_units
            ) * 100

            if total_units > 0

            else 0
        )

    elif return_rate_denominator == "records":

        total_records = len(
            filtered_df
        )

        return_rate = (

            (
                total_return_units
                / total_records
            ) * 100

            if total_records > 0

            else 0
        )

    else:

        return_rate = 0

    # ========================================================
    # PREVIOUS PERIOD
    # ========================================================

    previous_df = (
        _product_previous_period(
            work_df,
            date_column,
            filter_info["start_date"],
            filter_info["end_date"],
        )
    )

    growth_available = (
        not previous_df.empty
        and date_column is not None
    )

    previous_revenue = 0.0

    previous_units = 0.0

    previous_profit = 0.0

    previous_product_revenue = (
        pd.Series(dtype="float64")
    )

    if growth_available:

        previous_revenue = (
            _product_safe_float(
                previous_df[
                    sales_column
                ].sum()
            )
        )

        previous_units = (
            _product_safe_float(
                previous_df[
                    quantity_column
                ].sum()
            )
        )

        previous_profit = (
            _product_safe_float(
                previous_df[
                    profit_column
                ].sum()
            )
        )

        previous_product_revenue = (
            previous_df
            .groupby(product_column)[
                sales_column
            ]
            .sum()
        )

    # ========================================================
    # OVERALL GROWTH
    # ========================================================

    revenue_growth = (
        _product_percentage_change(
            total_revenue,
            previous_revenue,
        )
        if growth_available
        else 0
    )

    unit_growth = (
        _product_percentage_change(
            total_units,
            previous_units,
        )
        if growth_available
        else 0
    )

    profit_growth = (
        _product_percentage_change(
            total_profit,
            previous_profit,
        )
        if growth_available
        else 0
    )

    # ========================================================
    # PRODUCT GROWTH
    # ========================================================

    if growth_available:

        grouped["growth"] = (
            grouped["product"]
            .map(
                lambda product: (
                    _product_percentage_change(
                        grouped.loc[
                            grouped["product"]
                            == product,
                            "revenue",
                        ].sum(),

                        previous_product_revenue.get(
                            product,
                            0,
                        ),
                    )
                )
            )
        )

    else:

        grouped["growth"] = 0.0

    # ========================================================
    # PRODUCT PROFIT MARGIN
    # ========================================================

    grouped["profit_margin"] = np.where(

        grouped["revenue"] != 0,

        (
            grouped["profit"]
            / grouped["revenue"]
        ) * 100,

        0,
    )

    # ========================================================
    # BENCHMARKS
    # ========================================================

    revenue_median = (
        _product_safe_float(
            grouped["revenue"].median()
        )
    )

    units_median = (
        _product_safe_float(
            grouped["units"].median()
        )
    )

    profit_median = (
        _product_safe_float(
            grouped["profit"].median()
        )
    )

    # ========================================================
    # PRODUCT STATUS
    # ========================================================

    def determine_status(row):

        revenue = _product_safe_float(
            row["revenue"]
        )

        units = _product_safe_float(
            row["units"]
        )

        profit = _product_safe_float(
            row["profit"]
        )

        growth = _product_safe_float(
            row["growth"]
        )

        product_return_rate = (
            _product_safe_float(
                row["return_rate"]
            )
        )

        # ----------------------------------------------------
        # Return risk has highest priority
        # ----------------------------------------------------

        if product_return_rate >= 10:

            return "Return Risk"

        # ----------------------------------------------------
        # Growing
        # ----------------------------------------------------

        if (
            growth >= 10
            and revenue >= revenue_median
        ):

            return "Growing"

        # ----------------------------------------------------
        # Strong
        # ----------------------------------------------------

        if (
            revenue >= revenue_median
            and units >= units_median
            and profit >= profit_median
            and product_return_rate < 5
        ):

            return "Strong"

        # ----------------------------------------------------
        # Weak
        # ----------------------------------------------------

        if (
            growth <= -10
            or (
                revenue_median > 0
                and revenue
                < revenue_median * 0.50
            )
        ):

            return "Weak"

        # ----------------------------------------------------
        # Stable
        # ----------------------------------------------------

        return "Stable"

    grouped["status"] = grouped.apply(
        determine_status,
        axis=1,
    )

    # ========================================================
    # ADVANCED PRODUCT SCORE
    # ========================================================

    def calculate_product_score(row):

        revenue = _product_safe_float(
            row["revenue"]
        )

        units = _product_safe_float(
            row["units"]
        )

        profit = _product_safe_float(
            row["profit"]
        )

        growth = _product_safe_float(
            row["growth"]
        )

        product_return_rate = (
            _product_safe_float(
                row["return_rate"]
            )
        )

        # ----------------------------------------------------
        # Revenue component - 30
        # ----------------------------------------------------

        if revenue_median > 0:

            revenue_score = min(
                (
                    revenue
                    / revenue_median
                ) * 30,
                30,
            )

        else:

            revenue_score = 0

        # ----------------------------------------------------
        # Volume component - 20
        # ----------------------------------------------------

        if units_median > 0:

            volume_score = min(
                (
                    units
                    / units_median
                ) * 20,
                20,
            )

        else:

            volume_score = 0

        # ----------------------------------------------------
        # Growth component - 20
        # ----------------------------------------------------

        if growth_available:

            growth_score = max(
                min(
                    (
                        (
                            growth
                            + 20
                        )
                        / 40
                    ) * 20,
                    20,
                ),
                0,
            )

        else:

            growth_score = 10

        # ----------------------------------------------------
        # Profit component - 20
        # ----------------------------------------------------

        if profit_median > 0:

            profit_score = min(
                (
                    profit
                    / profit_median
                ) * 20,
                20,
            )

        else:

            profit_score = (
                20
                if profit > 0
                else 0
            )

        # ----------------------------------------------------
        # Return risk penalty - 10
        # ----------------------------------------------------

        if product_return_rate >= 10:

            risk_penalty = 10

        elif product_return_rate >= 8:

            risk_penalty = 7

        elif product_return_rate >= 5:

            risk_penalty = 4

        else:

            risk_penalty = 0

        score = (
            revenue_score
            + volume_score
            + growth_score
            + profit_score
            - risk_penalty
        )

        return round(
            max(
                min(
                    score,
                    100,
                ),
                0,
            ),
            1,
        )

    grouped["score"] = grouped.apply(
        calculate_product_score,
        axis=1,
    )

    # ========================================================
    # SORTED DATA
    # ========================================================

    revenue_sorted = (
        grouped
        .sort_values(
            "revenue",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    units_sorted = (
        grouped
        .sort_values(
            "units",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    profit_sorted = (
        grouped
        .sort_values(
            "profit",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    growth_sorted = (
        grouped
        .sort_values(
            "growth",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    return_sorted = (
        grouped
        .sort_values(
            "return_rate",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    # ========================================================
    # LEADERS
    # ========================================================

    highest_revenue_product = "-"

    best_selling_product = "-"

    highest_profit_product = "-"

    fastest_growing_product = "-"

    highest_return_product = "-"

    if not revenue_sorted.empty:

        highest_revenue_product = str(
            revenue_sorted.iloc[0][
                "product"
            ]
        )

    if not units_sorted.empty:

        best_selling_product = str(
            units_sorted.iloc[0][
                "product"
            ]
        )

    if not profit_sorted.empty:

        highest_profit_product = str(
            profit_sorted.iloc[0][
                "product"
            ]
        )

    if growth_available:

        positive_growth = growth_sorted[
            growth_sorted["growth"] > 0
        ]

        if not positive_growth.empty:

            fastest_growing_product = str(
                positive_growth.iloc[0][
                    "product"
                ]
            )

    if return_column and not return_sorted.empty:

        if (
            _product_safe_float(
                return_sorted.iloc[0][
                    "return_rate"
                ]
            ) > 0
        ):

            highest_return_product = str(
                return_sorted.iloc[0][
                    "product"
                ]
            )

    # ========================================================
    # STATUS COUNTS
    # ========================================================

    growing_products = int(
        (
            grouped["status"]
            == "Growing"
        ).sum()
    )

    declining_products = int(
        (
            grouped["growth"]
            <= -10
        ).sum()
        if growth_available
        else 0
    )

    low_performing_products = int(
        (
            grouped["status"]
            == "Weak"
        ).sum()
    )

    return_risk_products = int(
        (
            grouped["status"]
            == "Return Risk"
        ).sum()
    )

    # ========================================================
    # REVENUE CONCENTRATION / PARETO
    # ========================================================

    pareto_df = (
        grouped
        .sort_values(
            "revenue",
            ascending=False,
        )
        .reset_index(drop=True)
        .copy()
    )

    if total_revenue > 0:

        pareto_df[
            "revenue_share"
        ] = (
            pareto_df["revenue"]
            / total_revenue
        ) * 100

        pareto_df[
            "cumulative_share"
        ] = (
            pareto_df[
                "revenue_share"
            ]
            .cumsum()
        )

        top_20_count = max(
            int(
                np.ceil(
                    len(pareto_df)
                    * 0.20
                )
            ),
            1,
        )

        top_product_share = (
            _product_safe_float(
                pareto_df
                .head(top_20_count)[
                    "revenue_share"
                ]
                .sum()
            )
        )

    else:

        pareto_df[
            "revenue_share"
        ] = 0.0

        pareto_df[
            "cumulative_share"
        ] = 0.0

        top_product_share = 0.0

    revenue_concentration = round(
        top_product_share,
        2,
    )

    # ========================================================
    # TOP 12 PARETO
    # ========================================================

    pareto_top = pareto_df.head(12)

    pareto_labels = [
        str(value)
        for value in pareto_top[
            "product"
        ]
    ]

    pareto_values = [
        round(
            _product_safe_float(value),
            2,
        )
        for value in pareto_top[
            "cumulative_share"
        ]
    ]

    # ========================================================
    # TOP 10 PRODUCT CHART
    # ========================================================

    top10 = revenue_sorted.head(10)

    product_labels = [
        str(value)
        for value in top10[
            "product"
        ]
    ]

    product_revenue_values = [
        round(
            _product_safe_float(value),
            2,
        )
        for value in top10[
            "revenue"
        ]
    ]

    product_quantity_values = [
        round(
            _product_safe_float(value),
            2,
        )
        for value in top10[
            "units"
        ]
    ]

    product_profit_values = [
        round(
            _product_safe_float(value),
            2,
        )
        for value in top10[
            "profit"
        ]
    ]

    product_growth_values = [
        round(
            _product_safe_float(value),
            2,
        )
        for value in top10[
            "growth"
        ]
    ]

    # ========================================================
    # PRODUCT SCATTER
    # ========================================================

    scatter_df = (
        grouped
        .sort_values(
            "revenue",
            ascending=False,
        )
        .head(100)
    )

    scatter_points = []

    for _, row in scatter_df.iterrows():

        scatter_points.append({

            "x": round(
                _product_safe_float(
                    row["units"]
                ),
                2,
            ),

            "y": round(
                _product_safe_float(
                    row["revenue"]
                ),
                2,
            ),

            "profit": round(
                _product_safe_float(
                    row["profit"]
                ),
                2,
            ),

            "growth": round(
                _product_safe_float(
                    row["growth"]
                ),
                2,
            ),

            "returnRate": round(
                _product_safe_float(
                    row["return_rate"]
                ),
                2,
            ),

            "label": str(
                row["product"]
            ),
        })

    # ========================================================
    # STATUS DISTRIBUTION
    # ========================================================

    status_order = [
        "Growing",
        "Strong",
        "Stable",
        "Weak",
        "Return Risk",
    ]

    status_labels = []

    status_values = []

    for status in status_order:

        count = int(
            (
                grouped["status"]
                == status
            ).sum()
        )

        if count > 0:

            status_labels.append(
                status
            )

            status_values.append(
                count
            )

    # ========================================================
    # MONTHLY TREND
    # ========================================================

    trend_labels = []

    trend_revenue = []

    trend_profit = []

    trend_units = []

    if date_column:

        trend_work = (
            filtered_df
            .copy()
        )

        trend_work[
            "_product_month_"
        ] = (
            trend_work[
                date_column
            ]
            .dt.to_period("M")
            .astype(str)
        )

        trend = (
            trend_work
            .groupby(
                "_product_month_"
            )
            .agg(

                revenue=(
                    sales_column,
                    "sum",
                ),

                profit=(
                    profit_column,
                    "sum",
                ),

                units=(
                    quantity_column,
                    "sum",
                ),
            )
            .reset_index()
            .sort_values(
                "_product_month_"
            )
        )

        trend_labels = [
            str(value)
            for value in trend[
                "_product_month_"
            ]
        ]

        trend_revenue = [
            round(
                _product_safe_float(value),
                2,
            )
            for value in trend[
                "revenue"
            ]
        ]

        trend_profit = [
            round(
                _product_safe_float(value),
                2,
            )
            for value in trend[
                "profit"
            ]
        ]

        trend_units = [
            round(
                _product_safe_float(value),
                2,
            )
            for value in trend[
                "units"
            ]
        ]

    # ========================================================
    # PRODUCT TABLE
    # ========================================================

    product_rows = []

    table_df = (
        revenue_sorted
        .head(50)
    )

    for _, row in table_df.iterrows():

        product_rows.append({

            "product": str(
                row["product"]
            ),

            "revenue": round(
                _product_safe_float(
                    row["revenue"]
                ),
                2,
            ),

            "units": round(
                _product_safe_float(
                    row["units"]
                ),
                2,
            ),

            "profit": round(
                _product_safe_float(
                    row["profit"]
                ),
                2,
            ),

            "growth": round(
                _product_safe_float(
                    row["growth"]
                ),
                2,
            ),

            "returns": round(
                _product_safe_float(
                    row["return_rate"]
                ),
                2,
            ),

            "return_units": round(
                _product_safe_float(
                    row["return_units"]
                ),
                2,
            ),

            "margin": round(
                _product_safe_float(
                    row["profit_margin"]
                ),
                2,
            ),

            "score": round(
                _product_safe_float(
                    row["score"]
                ),
                1,
            ),

            "status": str(
                row["status"]
            ),
        })

    # ========================================================
    # AUTOMATIC PRODUCT INSIGHTS
    # ========================================================

    product_insights = []

    # --------------------------------------------------------
    # Revenue leader
    # --------------------------------------------------------

    if not revenue_sorted.empty:

        leader = revenue_sorted.iloc[0]

        leader_share = (

            (
                _product_safe_float(
                    leader["revenue"]
                )
                / total_revenue
            ) * 100

            if total_revenue > 0

            else 0
        )

        product_insights.append({

            "type": "positive",

            "icon": "◈",

            "title":
                "Revenue Leader",

            "text": (
                f"{leader['product']} "
                f"generates ₹"
                f"{_product_safe_float(leader['revenue']):,.0f} "
                f"in revenue, representing "
                f"{leader_share:.1f}% of the "
                f"selected product revenue."
            ),
        })

    # --------------------------------------------------------
    # Volume leader
    # --------------------------------------------------------

    if not units_sorted.empty:

        volume_leader = (
            units_sorted.iloc[0]
        )

        product_insights.append({

            "type": "positive",

            "icon": "↑",

            "title":
                "Volume Leader",

            "text": (
                f"{volume_leader['product']} "
                f"has the highest sales volume "
                f"with "
                f"{_product_safe_float(volume_leader['units']):,.0f} "
                f"units recorded."
            ),
        })

    # --------------------------------------------------------
    # Profit leader
    # --------------------------------------------------------

    if not profit_sorted.empty:

        profit_leader = (
            profit_sorted.iloc[0]
        )

        if (
            _product_safe_float(
                profit_leader["profit"]
            ) > 0
        ):

            product_insights.append({

                "type": "positive",

                "icon": "₹",

                "title":
                    "Profit Leader",

                "text": (
                    f"{profit_leader['product']} "
                    f"generates the highest product "
                    f"profit of ₹"
                    f"{_product_safe_float(profit_leader['profit']):,.0f}."
                ),
            })

    # --------------------------------------------------------
    # Fastest growing
    # --------------------------------------------------------

    if growth_available:

        positive_growth = growth_sorted[
            growth_sorted["growth"] > 0
        ]

        if not positive_growth.empty:

            fastest = (
                positive_growth.iloc[0]
            )

            product_insights.append({

                "type": "positive",

                "icon": "↗",

                "title":
                    "Fastest Growing Product",

                "text": (
                    f"{fastest['product']} "
                    f"is growing by "
                    f"{_product_safe_float(fastest['growth']):.1f}% "
                    f"versus the previous comparable "
                    f"period."
                ),
            })

    # --------------------------------------------------------
    # Declining products
    # --------------------------------------------------------

    if growth_available and declining_products > 0:

        product_insights.append({

            "type": "warning",

            "icon": "↓",

            "title":
                "Demand Decline",

            "text": (
                f"{declining_products} product(s) "
                f"experienced a decline of at least "
                f"10% compared with the previous "
                f"comparable period."
            ),
        })

    # --------------------------------------------------------
    # Return risk
    # --------------------------------------------------------

    if return_risk_products > 0:

        product_insights.append({

            "type": "negative",

            "icon": "⚠",

            "title":
                "Return Risk Detected",

            "text": (
                f"{return_risk_products} product(s) "
                f"have return rates of 10% or higher. "
                f"These products should be investigated "
                f"for quality, description, pricing or "
                f"customer-expectation problems."
            ),
        })

    # --------------------------------------------------------
    # Overall return rate
    # --------------------------------------------------------

    if return_rate >= 8:

        product_insights.append({

            "type": "negative",

            "icon": "⚠",

            "title":
                "High Overall Return Rate",

            "text": (
                f"The overall product return rate "
                f"is {return_rate:.1f}%, which indicates "
                f"a significant return-related business "
                f"risk in the selected period."
            ),
        })

    elif return_rate >= 5:

        product_insights.append({

            "type": "warning",

            "icon": "!",

            "title":
                "Return Rate Requires Monitoring",

            "text": (
                f"The overall product return rate "
                f"is {return_rate:.1f}%. "
                f"Products with unusually high return "
                f"rates should be reviewed."
            ),
        })

    # --------------------------------------------------------
    # Revenue concentration
    # --------------------------------------------------------

    if revenue_concentration >= 70:

        product_insights.append({

            "type": "warning",

            "icon": "◐",

            "title":
                "High Revenue Concentration",

            "text": (
                f"The top 20% of products generate "
                f"approximately "
                f"{revenue_concentration:.1f}% "
                f"of product revenue. "
                f"The business is strongly dependent "
                f"on a small group of products."
            ),
        })

    elif revenue_concentration >= 50:

        product_insights.append({

            "type": "positive",

            "icon": "◐",

            "title":
                "Core Product Base",

            "text": (
                f"The top 20% of products contribute "
                f"approximately "
                f"{revenue_concentration:.1f}% "
                f"of product revenue."
            ),
        })

    # --------------------------------------------------------
    # Low performers
    # --------------------------------------------------------

    if low_performing_products > 0:

        product_insights.append({

            "type": "warning",

            "icon": "!",

            "title":
                "Low Performing Products",

            "text": (
                f"{low_performing_products} product(s) "
                f"are currently classified as weak "
                f"performers based on revenue and "
                f"growth performance."
            ),
        })

    # --------------------------------------------------------
    # Negative profit
    # --------------------------------------------------------

    loss_products = int(
        (
            grouped["profit"]
            < 0
        ).sum()
    )

    if loss_products > 0:

        product_insights.append({

            "type": "negative",

            "icon": "−",

            "title":
                "Loss-Making Products",

            "text": (
                f"{loss_products} product(s) "
                f"have negative calculated profit "
                f"in the selected period."
            ),
        })

    # ========================================================
    # FINAL CONTEXT
    # ========================================================

    context.update({

        "has_data": True,

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        "total_products":
            total_products,

        "total_revenue":
            total_revenue,

        "total_units":
            total_units,

        "total_profit":
            total_profit,

        "average_product_revenue":
            average_product_revenue,

        "average_selling_price":
            average_selling_price,

        "profit_margin":
            profit_margin,

        "return_rate":
            return_rate,

        "total_return_units":
            total_return_units,

        # ----------------------------------------------------
        # Growth
        # ----------------------------------------------------

        "revenue_growth":
            revenue_growth,

        "unit_growth":
            unit_growth,

        "profit_growth":
            profit_growth,

        "growth_available":
            growth_available,

        # ----------------------------------------------------
        # Performance
        # ----------------------------------------------------

        "growing_products":
            growing_products,

        "declining_products":
            declining_products,

        "low_performing_products":
            low_performing_products,

        "return_risk_products":
            return_risk_products,

        # ----------------------------------------------------
        # Leaders
        # ----------------------------------------------------

        "best_selling_product":
            best_selling_product,

        "highest_revenue_product":
            highest_revenue_product,

        "highest_profit_product":
            highest_profit_product,

        "fastest_growing_product":
            fastest_growing_product,

        "highest_return_product":
            highest_return_product,

        # ----------------------------------------------------
        # Table
        # ----------------------------------------------------

        "product_rows":
            product_rows,

        # ----------------------------------------------------
        # Charts
        # ----------------------------------------------------

        "product_labels":
            _product_json(
                product_labels
            ),

        "product_revenue_values":
            _product_json(
                product_revenue_values
            ),

        "product_quantity_values":
            _product_json(
                product_quantity_values
            ),

        "product_profit_values":
            _product_json(
                product_profit_values
            ),

        "product_growth_values":
            _product_json(
                product_growth_values
            ),

        # ----------------------------------------------------
        # Trend
        # ----------------------------------------------------

        "trend_labels":
            _product_json(
                trend_labels
            ),

        "trend_revenue":
            _product_json(
                trend_revenue
            ),

        "trend_profit":
            _product_json(
                trend_profit
            ),

        "trend_units":
            _product_json(
                trend_units
            ),

        # ----------------------------------------------------
        # Pareto
        # ----------------------------------------------------

        "pareto_labels":
            _product_json(
                pareto_labels
            ),

        "pareto_values":
            _product_json(
                pareto_values
            ),

        "revenue_concentration":
            revenue_concentration,

        "top_product_share":
            revenue_concentration,

        # ----------------------------------------------------
        # Scatter
        # ----------------------------------------------------

        "scatter_points":
            _product_json(
                scatter_points
            ),

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        "status_labels":
            _product_json(
                status_labels
            ),

        "status_values":
            _product_json(
                status_values
            ),

        # ----------------------------------------------------
        # Insights
        # ----------------------------------------------------

        "product_insights":
            product_insights,
    })

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "analytics/product_intelligence.html",
        context,
    )
# ============================================================
# REGIONAL INTELLIGENCE
# ============================================================

@login_required
def regional_intelligence(request):

    # --------------------------------------------------------
    # IMPORTS USED BY THIS VIEW
    # --------------------------------------------------------
    import json
    import numpy as np
    import pandas as pd

    from django.shortcuts import render

    # --------------------------------------------------------
    # DATASET SCOPE
    # IMPORTANT:
    # Regional Intelligence uses ONLY Regional datasets.
    # --------------------------------------------------------
    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            dataset_type="Regional",
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    # --------------------------------------------------------
    # DEFAULT VALUES
    # --------------------------------------------------------
    total_regions = 0
    total_revenue = 0.0
    total_units = 0.0
    total_orders = 0
    average_region_revenue = 0.0

    top_region = "-"
    lowest_region = "-"
    fastest_growing_region = "-"
    highest_return_region = "-"

    revenue_concentration = 0.0
    top_region_contribution = 0.0
    average_growth = 0.0
    average_return_rate = 0.0

    regional_rows = []
    regional_insights = []

    region_labels = []
    region_revenue_values = []
    region_quantity_values = []
    region_growth_values = []
    region_return_values = []

    # --------------------------------------------------------
    # COLUMN INFORMATION
    # --------------------------------------------------------
    region_column = None
    sales_column = None
    quantity_column = None
    date_column = None
    return_column = None
    order_column = None

    # --------------------------------------------------------
    # FILTER VALUES
    # --------------------------------------------------------
    selected_range = request.GET.get("range", "all")
    selected_start = request.GET.get("start_date", "")
    selected_end = request.GET.get("end_date", "")
    selected_region = request.GET.get("region", "all")

    # --------------------------------------------------------
    # EMPTY RESPONSE HELPER
    # --------------------------------------------------------
    def empty_context(message=""):

        return {
            "datasets": datasets,
            "selected_dataset": selected_dataset,
            "selected_version": selected_version,
            "has_data": False,
            "error_message": message,

            "selected_range": selected_range,
            "selected_start": selected_start,
            "selected_end": selected_end,
            "selected_region": selected_region,

            "available_regions": [],

            "total_regions": 0,
            "total_revenue": 0,
            "total_units": 0,
            "total_orders": 0,
            "average_region_revenue": 0,

            "top_region": "-",
            "lowest_region": "-",
            "fastest_growing_region": "-",
            "highest_return_region": "-",

            "revenue_concentration": 0,
            "top_region_contribution": 0,
            "average_growth": 0,
            "average_return_rate": 0,

            "regional_rows": [],
            "regional_insights": [],

            "region_labels": "[]",
            "region_revenue_values": "[]",
            "region_quantity_values": "[]",
            "region_growth_values": "[]",
            "region_return_values": "[]",

            "region_column": None,
            "sales_column": None,
            "quantity_column": None,
            "date_column": None,
            "return_column": None,
            "order_column": None,

            "date_filter_label": "All Data",
            "analysis_start_date": None,
            "analysis_end_date": None,
        }

    # ========================================================
    # SELECT DATASET
    # ========================================================

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        selected_dataset = (
            datasets
            .filter(id=dataset_id)
            .first()
        )

    if not selected_dataset:
        selected_dataset = datasets.first()

    if not selected_dataset:

        return render(
            request,
            "analytics/regional_intelligence.html",
            empty_context(
                "No Regional dataset is available. "
                "Upload a Regional dataset from Data Management first."
            )
        )

    # ========================================================
    # SELECT CLEANED VERSION
    # ========================================================

    selected_version = (
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
    if not selected_version:

        selected_version = (
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

    if not selected_version:

        return render(
            request,
            "analytics/regional_intelligence.html",
            empty_context(
                "This Regional dataset does not have a cleaned "
                "or current dataset version available."
            )
        )

    # ========================================================
    # CHECK FILE
    # ========================================================

    if not selected_version.file:

        return render(
            request,
            "analytics/regional_intelligence.html",
            empty_context(
                "The selected Regional dataset file is unavailable."
            )
        )

    # ========================================================
    # READ FILE
    # ========================================================

    try:

        file_path = selected_version.file.path

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
                empty_context(
                    "Unsupported Regional dataset format. "
                    "Use CSV or Excel."
                )
            )

    except Exception as exc:

        return render(
            request,
            "analytics/regional_intelligence.html",
            empty_context(
                f"Unable to read the cleaned Regional dataset: {exc}"
            )
        )

    # ========================================================
    # BASIC DATA CHECK
    # ========================================================

    if df is None or df.empty:

        return render(
            request,
            "analytics/regional_intelligence.html",
            empty_context(
                "The cleaned Regional dataset contains no records."
            )
        )

    # ========================================================
    # NORMALIZE COLUMN NAMES
    # ========================================================

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    normalized_columns = {
        str(column).lower().strip(): column
        for column in df.columns
    }

    def normalize_name(value):

        return (
            str(value)
            .lower()
            .strip()
            .replace("-", "_")
            .replace(" ", "_")
        )

    normalized_fuzzy = {
        normalize_name(column): column
        for column in df.columns
    }

    def find_column(candidates):

        # Exact match
        for candidate in candidates:

            candidate_lower = (
                str(candidate)
                .lower()
                .strip()
            )

            if candidate_lower in normalized_columns:
                return normalized_columns[candidate_lower]

        # Normalized exact match
        for candidate in candidates:

            candidate_normalized = normalize_name(
                candidate
            )

            if candidate_normalized in normalized_fuzzy:
                return normalized_fuzzy[
                    candidate_normalized
                ]

        # Fuzzy match
        for column in df.columns:

            column_lower = (
                str(column)
                .lower()
                .strip()
            )

            for candidate in candidates:

                candidate_lower = (
                    str(candidate)
                    .lower()
                    .strip()
                )

                if candidate_lower in column_lower:
                    return column

        return None

    # ========================================================
    # DETECT REGIONAL COLUMNS
    # ========================================================

    region_column = find_column([
        "region",
        "region name",
        "region_name",
        "regional",
        "area",
        "area name",
        "area_name",
        "territory",
        "zone",
        "sales region",
        "sales_region",
        "location",
        "state",
        "state name",
        "state_name",
        "city",
        "district",
    ])

    sales_column = find_column([
        "sales",
        "revenue",
        "sales revenue",
        "sales_revenue",
        "total sales",
        "total_sales",
        "net sales",
        "net_sales",
        "amount",
        "total amount",
        "total_amount",
        "order value",
        "order_value",
        "sales amount",
        "sales_amount",
    ])

    quantity_column = find_column([
        "quantity",
        "qty",
        "units",
        "units sold",
        "units_sold",
        "quantity sold",
        "quantity_sold",
        "volume",
    ])

    date_column = find_column([
        "date",
        "order date",
        "order_date",
        "sales date",
        "sales_date",
        "transaction date",
        "transaction_date",
        "invoice date",
        "invoice_date",
    ])

    return_column = find_column([
        "return",
        "returns",
        "returned",
        "return quantity",
        "return_quantity",
        "returned quantity",
        "returned_quantity",
        "return count",
        "return_count",
    ])

    order_column = find_column([
        "order id",
        "order_id",
        "order number",
        "order_number",
        "transaction id",
        "transaction_id",
        "invoice id",
        "invoice_id",
        "invoice number",
        "invoice_number",
    ])

    # ========================================================
    # REQUIRED COLUMNS
    # ========================================================

    if not region_column or not sales_column:

        return render(
            request,
            "analytics/regional_intelligence.html",
            empty_context(
                "Regional Intelligence requires at least "
                "a Region column and a Sales/Revenue column."
            )
        )

    # ========================================================
    # WORKING DATA
    # ========================================================

    work_df = df.copy()

    # --------------------------------------------------------
    # REGION
    # --------------------------------------------------------

    work_df = work_df[
        work_df[region_column].notna()
    ].copy()

    work_df[region_column] = (
        work_df[region_column]
        .astype(str)
        .str.strip()
    )

    work_df = work_df[
        ~work_df[region_column]
        .str.lower()
        .isin([
            "",
            "nan",
            "none",
            "null",
            "na",
            "n/a",
            "-",
        ])
    ].copy()

    # --------------------------------------------------------
    # NUMERIC CLEANER
    # --------------------------------------------------------

    def clean_numeric(series):

        return pd.to_numeric(
            series
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("₹", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("€", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.replace(
                r"^\((.*)\)$",
                r"-\1",
                regex=True
            ),
            errors="coerce"
        )

    # --------------------------------------------------------
    # SALES
    # --------------------------------------------------------

    work_df[sales_column] = (
        clean_numeric(
            work_df[sales_column]
        )
        .fillna(0)
    )

    # --------------------------------------------------------
    # QUANTITY
    # --------------------------------------------------------

    if quantity_column:

        work_df[quantity_column] = (
            clean_numeric(
                work_df[quantity_column]
            )
            .fillna(0)
        )

    else:

        # One row represents one unit
        work_df["_regional_units_"] = 1
        quantity_column = "_regional_units_"

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    if return_column:

        work_df[return_column] = (
            clean_numeric(
                work_df[return_column]
            )
            .fillna(0)
        )

    else:

        work_df["_regional_returns_"] = 0
        return_column = "_regional_returns_"

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if date_column:

        work_df[date_column] = pd.to_datetime(
            work_df[date_column],
            errors="coerce"
        )

    # ========================================================
    # REMOVE INVALID SALES ROWS
    # ========================================================

    work_df = work_df[
        work_df[sales_column].notna()
    ].copy()

    if work_df.empty:

        return render(
            request,
            "analytics/regional_intelligence.html",
            empty_context(
                "No valid Regional sales records were found."
            )
        )

    # ========================================================
    # DATE FILTER
    # ========================================================

    date_filter_label = "All Data"
    analysis_start_date = None
    analysis_end_date = None

    if date_column:

        valid_date_df = work_df[
            work_df[date_column].notna()
        ].copy()

        if not valid_date_df.empty:

            data_min_date = (
                valid_date_df[date_column]
                .min()
                .normalize()
            )

            data_max_date = (
                valid_date_df[date_column]
                .max()
                .normalize()
            )

            if selected_range == "custom":

                try:

                    requested_start = pd.to_datetime(
                        selected_start
                    ).normalize()

                    requested_end = pd.to_datetime(
                        selected_end
                    ).normalize()

                    if requested_start > requested_end:

                        requested_start, requested_end = (
                            requested_end,
                            requested_start
                        )

                    analysis_start_date = max(
                        requested_start,
                        data_min_date
                    )

                    analysis_end_date = min(
                        requested_end,
                        data_max_date
                    )

                    work_df = work_df[
                        (
                            work_df[date_column]
                            >= analysis_start_date
                        )
                        &
                        (
                            work_df[date_column]
                            < (
                                analysis_end_date
                                + pd.Timedelta(days=1)
                            )
                        )
                    ].copy()

                    date_filter_label = (
                        "Custom Range"
                    )

                except (
                    ValueError,
                    TypeError,
                ):

                    selected_range = "all"

            if selected_range != "custom":

                if selected_range == "all":

                    analysis_start_date = data_min_date
                    analysis_end_date = data_max_date

                    date_filter_label = "All Data"

                else:

                    try:

                        days = int(
                            selected_range
                        )

                        analysis_end_date = data_max_date

                        analysis_start_date = max(
                            data_max_date
                            - pd.Timedelta(
                                days=days - 1
                            ),
                            data_min_date
                        )

                        work_df = work_df[
                            (
                                work_df[date_column]
                                >= analysis_start_date
                            )
                            &
                            (
                                work_df[date_column]
                                <= analysis_end_date
                            )
                        ].copy()

                        date_filter_names = {
                            "30": "Last 30 Days",
                            "90": "Last 3 Months",
                            "180": "Last 6 Months",
                            "365": "Last 12 Months",
                        }

                        date_filter_label = (
                            date_filter_names.get(
                                str(days),
                                f"Last {days} Days"
                            )
                        )

                    except (
                        ValueError,
                        TypeError,
                    ):

                        selected_range = "all"

                        analysis_start_date = data_min_date
                        analysis_end_date = data_max_date

                        date_filter_label = "All Data"

    # ========================================================
    # REGION FILTER
    # ========================================================

    available_regions = sorted(
        [
            str(value)
            for value in work_df[
                region_column
            ].dropna().unique()
        ]
    )

    if (
        selected_region != "all"
        and selected_region in available_regions
    ):

        work_df = work_df[
            work_df[region_column]
            == selected_region
        ].copy()

    elif selected_region != "all":

        selected_region = "all"

    # ========================================================
    # FINAL EMPTY CHECK
    # ========================================================

    if work_df.empty:

        context = empty_context(
            "No Regional records match the selected filters."
        )

        context.update({
            "available_regions": available_regions,
            "selected_range": selected_range,
            "selected_start": selected_start,
            "selected_end": selected_end,
            "selected_region": selected_region,
            "date_filter_label": date_filter_label,
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
        })

        return render(
            request,
            "analytics/regional_intelligence.html",
            context
        )

    # ========================================================
    # GROUP BY REGION
    # ========================================================

    aggregation = {
        "revenue": (
            sales_column,
            "sum"
        ),
        "units": (
            quantity_column,
            "sum"
        ),
        "returns": (
            return_column,
            "sum"
        ),
    }

    if order_column:

        aggregation["orders"] = (
            order_column,
            "nunique"
        )

    else:

        aggregation["orders"] = (
            region_column,
            "count"
        )

    grouped = (
        work_df
        .groupby(
            region_column,
            dropna=False
        )
        .agg(**aggregation)
        .reset_index()
    )

    grouped.rename(
        columns={
            region_column: "region"
        },
        inplace=True
    )

    # ========================================================
    # CLEAN GROUPED DATA
    # ========================================================

    for column in [
        "revenue",
        "units",
        "returns",
        "orders",
    ]:

        grouped[column] = pd.to_numeric(
            grouped[column],
            errors="coerce"
        ).fillna(0)

    # ========================================================
    # RETURN RATE
    # ========================================================

    grouped["return_rate"] = np.where(
        grouped["units"] > 0,
        (
            grouped["returns"]
            / grouped["units"]
        ) * 100,
        0
    )

    # ========================================================
    # REGIONAL GROWTH
    # ========================================================

    grouped["growth"] = 0.0

    if date_column:

        try:

            dated = work_df[
                work_df[date_column].notna()
            ].copy()

            if not dated.empty:

                latest_date = (
                    dated[date_column]
                    .max()
                    .normalize()
                )

                current_start = (
                    latest_date
                    - pd.Timedelta(days=29)
                )

                previous_end = (
                    current_start
                    - pd.Timedelta(days=1)
                )

                previous_start = (
                    previous_end
                    - pd.Timedelta(days=29)
                )

                current_df = dated[
                    (
                        dated[date_column]
                        >= current_start
                    )
                    &
                    (
                        dated[date_column]
                        <= latest_date
                    )
                ]

                previous_df = dated[
                    (
                        dated[date_column]
                        >= previous_start
                    )
                    &
                    (
                        dated[date_column]
                        <= previous_end
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
                            (
                                current
                                - previous
                            )
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

    # ========================================================
    # REVENUE CONTRIBUTION
    # ========================================================

    grouped["revenue_contribution"] = np.where(
        grouped["revenue"].sum() > 0,
        (
            grouped["revenue"]
            / grouped["revenue"].sum()
        ) * 100,
        0
    )

    # ========================================================
    # REVENUE PER UNIT
    # ========================================================

    grouped["revenue_per_unit"] = np.where(
        grouped["units"] > 0,
        grouped["revenue"]
        / grouped["units"],
        0
    )

    # ========================================================
    # BENCHMARKS
    # ========================================================

    revenue_median = (
        grouped["revenue"].median()
        if not grouped.empty
        else 0
    )

    growth_median = (
        grouped["growth"].median()
        if not grouped.empty
        else 0
    )

    # ========================================================
    # PERFORMANCE STATUS
    # ========================================================

    def determine_status(row):

        revenue = float(
            row["revenue"]
        )

        growth = float(
            row["growth"]
        )

        return_rate = float(
            row["return_rate"]
        )

        if return_rate >= 10:

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
            growth <= -10
            or revenue < revenue_median * 0.5
        ):

            return "Weak"

        return "Stable"

    grouped["status"] = grouped.apply(
        determine_status,
        axis=1
    )

    # ========================================================
    # SORT
    # ========================================================

    grouped = grouped.sort_values(
        "revenue",
        ascending=False
    ).reset_index(drop=True)

    # ========================================================
    # BASIC KPIs
    # ========================================================

    total_regions = int(
        grouped["region"].nunique()
    )

    total_revenue = float(
        grouped["revenue"].sum()
    )

    total_units = float(
        grouped["units"].sum()
    )

    total_orders = int(
        grouped["orders"].sum()
    )

    average_region_revenue = (
        total_revenue / total_regions
        if total_regions
        else 0
    )

    average_growth = float(
        grouped["growth"].mean()
    )

    average_return_rate = float(
        grouped["return_rate"].mean()
    )

    # ========================================================
    # TOP / LOWEST
    # ========================================================

    if not grouped.empty:

        top_row = grouped.iloc[0]

        lowest_row = grouped.iloc[-1]

        top_region = str(
            top_row["region"]
        )

        lowest_region = str(
            lowest_row["region"]
        )

        top_region_contribution = float(
            top_row["revenue_contribution"]
        )

        growth_sorted = grouped.sort_values(
            "growth",
            ascending=False
        )

        fastest_growing_region = str(
            growth_sorted.iloc[0]["region"]
        )

        return_sorted = grouped.sort_values(
            "return_rate",
            ascending=False
        )

        highest_return_region = str(
            return_sorted.iloc[0]["region"]
        )

    # ========================================================
    # REVENUE CONCENTRATION
    # TOP 20% REGION REVENUE SHARE
    # ========================================================

    if not grouped.empty:

        top_count = max(
            1,
            int(
                np.ceil(
                    len(grouped) * 0.20
                )
            )
        )

        revenue_concentration = (
            grouped.head(top_count)["revenue"].sum()
            / total_revenue
            * 100
            if total_revenue > 0
            else 0
        )

    # ========================================================
    # REGIONAL TABLE
    # ========================================================

    for _, row in grouped.head(100).iterrows():

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

            "return_units": round(
                float(row["returns"]),
                2
            ),

            "contribution": round(
                float(
                    row[
                        "revenue_contribution"
                    ]
                ),
                2
            ),

            "revenue_per_unit": round(
                float(
                    row[
                        "revenue_per_unit"
                    ]
                ),
                2
            ),

            "status": str(
                row["status"]
            ),

        })

    # ========================================================
    # CHART DATA
    # ========================================================

    chart_df = grouped.head(12).copy()

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

    region_growth_values = [
        round(
            float(value),
            2
        )
        for value in chart_df["growth"]
    ]

    region_return_values = [
        round(
            float(value),
            2
        )
        for value in chart_df["return_rate"]
    ]

    # ========================================================
    # AUTOMATIC BUSINESS INSIGHTS
    # ========================================================

    # --------------------------------------------------------
    # 1. REGIONAL LEADER
    # --------------------------------------------------------

    if not grouped.empty:

        regional_insights.append({

            "type": "positive",

            "icon": "🏆",

            "title": "Regional Leader",

            "text": (
                f"{top_region} is the strongest "
                f"revenue contributor, generating "
                f"₹{float(top_row['revenue']):,.0f} "
                f"and contributing "
                f"{float(top_region_contribution):.1f}% "
                f"of regional revenue."
            ),

        })

    # --------------------------------------------------------
    # 2. GROWTH OPPORTUNITY
    # --------------------------------------------------------

    growing_regions = grouped[
        grouped["growth"] >= 10
    ]

    if not growing_regions.empty:

        growth_leader = (
            growing_regions
            .sort_values(
                "growth",
                ascending=False
            )
            .iloc[0]
        )

        regional_insights.append({

            "type": "positive",

            "icon": "📈",

            "title": "Growth Opportunity",

            "text": (
                f"{growth_leader['region']} "
                f"is showing the strongest recent "
                f"growth at "
                f"{float(growth_leader['growth']):.1f}%. "
                f"This region deserves attention for "
                f"further expansion."
            ),

        })

    # --------------------------------------------------------
    # 3. DECLINING REGIONS
    # --------------------------------------------------------

    declining_regions = grouped[
        grouped["growth"] <= -10
    ]

    if not declining_regions.empty:

        worst_growth = (
            declining_regions
            .sort_values(
                "growth"
            )
            .iloc[0]
        )

        regional_insights.append({

            "type": "warning",

            "icon": "📉",

            "title": "Declining Region",

            "text": (
                f"{worst_growth['region']} has declined "
                f"by "
                f"{abs(float(worst_growth['growth'])):.1f}% "
                f"in the recent comparison period. "
                f"Investigate pricing, demand, "
                f"distribution and local competition."
            ),

        })

    # --------------------------------------------------------
    # 4. RETURN RISK
    # --------------------------------------------------------

    return_risk_regions = grouped[
        grouped["return_rate"] >= 8
    ]

    if not return_risk_regions.empty:

        highest_return = (
            return_risk_regions
            .sort_values(
                "return_rate",
                ascending=False
            )
            .iloc[0]
        )

        regional_insights.append({

            "type": "negative",

            "icon": "⚠️",

            "title": "Return Risk",

            "text": (
                f"{highest_return['region']} has the "
                f"highest return rate at "
                f"{float(highest_return['return_rate']):.1f}%. "
                f"Review product quality, customer "
                f"expectations and fulfilment issues."
            ),

        })

    # --------------------------------------------------------
    # 5. CONCENTRATION RISK
    # --------------------------------------------------------

    if revenue_concentration >= 70:

        regional_insights.append({

            "type": "warning",

            "icon": "🎯",

            "title": "Revenue Concentration",

            "text": (
                f"The top 20% of regions generate "
                f"{revenue_concentration:.1f}% of "
                f"regional revenue. The business may "
                f"be highly dependent on a small number "
                f"of markets."
            ),

        })

    elif revenue_concentration >= 50:

        regional_insights.append({

            "type": "warning",

            "icon": "📊",

            "title": "Moderate Concentration",

            "text": (
                f"The top 20% of regions contribute "
                f"{revenue_concentration:.1f}% of revenue. "
                f"Consider developing secondary regions "
                f"to improve geographic balance."
            ),

        })

    else:

        regional_insights.append({

            "type": "positive",

            "icon": "🌍",

            "title": "Balanced Regional Base",

            "text": (
                f"The top 20% of regions contribute "
                f"{revenue_concentration:.1f}% of revenue, "
                f"suggesting revenue is relatively "
                f"distributed across the regional network."
            ),

        })

    # --------------------------------------------------------
    # 6. LOW PERFORMER
    # --------------------------------------------------------

    if not grouped.empty:

        low_performer = (
            grouped
            .sort_values(
                "revenue"
            )
            .iloc[0]
        )

        regional_insights.append({

            "type": "warning",

            "icon": "🔎",

            "title": "Lowest Revenue Region",

            "text": (
                f"{low_performer['region']} has the "
                f"lowest recorded revenue at "
                f"₹{float(low_performer['revenue']):,.0f}. "
                f"Review whether this represents an "
                f"underperforming market or an emerging "
                f"growth opportunity."
            ),

        })

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        # Dataset
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "selected_version": selected_version,
        "has_data": True,
        "error_message": "",

        # Filters
        "selected_range": selected_range,
        "selected_start": selected_start,
        "selected_end": selected_end,
        "selected_region": selected_region,
        "available_regions": available_regions,

        # Date information
        "date_filter_label": date_filter_label,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,

        # KPIs
        "total_regions": total_regions,
        "total_revenue": total_revenue,
        "total_units": total_units,
        "total_orders": total_orders,
        "average_region_revenue": average_region_revenue,

        "top_region": top_region,
        "lowest_region": lowest_region,
        "fastest_growing_region": fastest_growing_region,
        "highest_return_region": highest_return_region,

        "revenue_concentration": revenue_concentration,
        "top_region_contribution": top_region_contribution,
        "average_growth": average_growth,
        "average_return_rate": average_return_rate,

        # Table
        "regional_rows": regional_rows,

        # Insights
        "regional_insights": regional_insights,

        # Charts
        "region_labels": json.dumps(
            region_labels
        ),

        "region_revenue_values": json.dumps(
            region_revenue_values
        ),

        "region_quantity_values": json.dumps(
            region_quantity_values
        ),

        "region_growth_values": json.dumps(
            region_growth_values
        ),

        "region_return_values": json.dumps(
            region_return_values
        ),

        # Detected columns
        "region_column": region_column,
        "sales_column": sales_column,
        "quantity_column": quantity_column,
        "date_column": date_column,
        "return_column": return_column,
        "order_column": order_column,
    }

    return render(
        request,
        "analytics/regional_intelligence.html",
        context
    )

import json
import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render

from data_management.models import Dataset, DatasetVersion

from .date_filters import (
    DATE_RANGE_OPTIONS,
    apply_date_filter,
    get_previous_period,
    calculate_percentage_change,
)
@login_required
def sales_intelligence(request):
    """
    Advanced Sales Intelligence

    Uses ONLY Sales-category datasets.

    Features:
    - Total sales
    - Number of orders
    - Average order value
    - Average daily sales
    - Average weekly sales
    - Daily sales
    - Weekly sales
    - Monthly sales
    - Sales growth
    - Product-wise sales
    - Category-wise sales
    - Region-wise sales
    - Salesperson ranking
    - Peak sales period
    - Lowest sales period
    - Period comparison
    - Advanced business insights
    """

    # =========================================================
    # ACCESS CONTROL
    # =========================================================

    user = request.user

    if not user.is_authenticated:
        return HttpResponseForbidden("Authentication required.")

    # Staff/admin users are allowed.
    # Normal users must be approved.
    if not (
        user.is_staff
        or user.is_superuser
        or (
            user.is_active
            and getattr(user, "approval_status", "") == "Approved"
        )
    ):
        return HttpResponseForbidden(
            "Your account is not approved to access Sales Intelligence."
        )

    # =========================================================
    # HELPER FUNCTIONS
    # =========================================================

    def normalize_column_name(value):
        return (
            str(value)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("/", "_")
        )

    def clean_numeric(series):
        """
        Convert currency/number strings safely into numeric values.
        Handles:
        1,20,000
        ₹120000
        $120000
        (120000)
        """
        return pd.to_numeric(
            series.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("₹", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("€", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.replace(
                r"^\((.*)\)$",
                r"-\1",
                regex=True,
            )
            .str.strip(),
            errors="coerce",
        )

    def find_column(df, candidates, keywords=None):
        """
        Detect a column using:
        1. Exact aliases
        2. Keyword matching
        """

        candidates = [
            normalize_column_name(column)
            for column in candidates
        ]

        for candidate in candidates:
            if candidate in df.columns:
                return candidate

        if keywords:
            keywords = [
                normalize_column_name(keyword)
                for keyword in keywords
            ]

            for column in df.columns:
                if any(keyword in column for keyword in keywords):
                    return column

        return None

    def safe_float(value):
        try:
            value = float(value)

            if not np.isfinite(value):
                return 0.0

            return value

        except (TypeError, ValueError):
            return 0.0

    def json_list(values):
        return json.dumps(
            [
                value
                for value in values
            ],
            default=str,
        )

    def json_numbers(values):
        return json.dumps(
            [
                round(safe_float(value), 2)
                for value in values
            ]
        )

    def format_period(date_value, mode="month"):
        if pd.isna(date_value):
            return "-"

        if mode == "day":
            return pd.to_datetime(date_value).strftime("%d %b %Y")

        if mode == "week":
            return pd.to_datetime(date_value).strftime("%d %b %Y")

        return pd.to_datetime(date_value).strftime("%b %Y")

    # =========================================================
    # DATASET LIST
    # =========================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            dataset_type="Sales",
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    # =========================================================
    # DATE FILTER
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

    # KPI
    total_revenue = 0.0
    total_orders = 0
    average_order_value = 0.0
    average_daily_revenue = 0.0
    average_weekly_revenue = 0.0
    sales_growth = 0.0

    # Comparison
    comparison_available = False

    current_period_revenue = 0.0
    previous_period_revenue = 0.0
    revenue_change = 0.0

    current_period_orders = 0
    previous_period_orders = 0
    orders_change = 0.0

    current_period_aov = 0.0
    previous_period_aov = 0.0
    aov_change = 0.0

    # Peak / low
    peak_period = "-"
    lowest_period = "-"

    peak_revenue = 0.0
    lowest_revenue = 0.0

    # Leaders
    best_product = "-"
    best_product_sales = 0.0

    best_category = "-"
    best_category_sales = 0.0

    best_region = "-"
    best_region_sales = 0.0

    best_salesperson = "-"
    best_salesperson_sales = 0.0

    # Concentration
    top_product_share = 0.0
    top_region_share = 0.0
    top_category_share = 0.0

    # Columns
    sales_column = ""
    date_column = ""
    order_column = ""
    quantity_column = ""
    product_column = ""
    category_column = ""
    region_column = ""
    salesperson_column = ""

    # Date range
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
    # CHART DATA
    # =========================================================

    daily_labels = json.dumps([])
    daily_values = json.dumps([])

    weekly_labels = json.dumps([])
    weekly_values = json.dumps([])

    monthly_labels = json.dumps([])
    monthly_values = json.dumps([])

    growth_labels = json.dumps([])
    growth_values = json.dumps([])

    product_labels = json.dumps([])
    product_values = json.dumps([])

    category_labels = json.dumps([])
    category_values = json.dumps([])

    region_labels = json.dumps([])
    region_values = json.dumps([])

    salesperson_labels = json.dumps([])
    salesperson_values = json.dumps([])

    # =========================================================
    # TABLES
    # =========================================================

    monthly_rows = []
    product_rows = []
    category_rows = []
    region_rows = []
    salesperson_rows = []

    # =========================================================
    # INSIGHTS
    # =========================================================

    sales_insights = []

    # =========================================================
    # EMPTY DATASET CHECK
    # =========================================================

    if not datasets.exists():

        error_message = (
            "No Sales-category dataset is available. "
            "Upload a Sales dataset through Data Management."
        )

    else:

        # =====================================================
        # SELECT DATASET
        # =====================================================

        dataset_id = request.GET.get(
            "dataset"
        )

        if dataset_id:

            selected_dataset = (
                datasets
                .filter(id=dataset_id)
                .first()
            )

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

        if not selected_version:

            error_message = (
                "The selected Sales dataset does not have "
                "a cleaned or current version yet."
            )

        else:

            try:

                # =================================================
                # READ FILE
                # =================================================

                file_path = selected_version.file.path

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

                if df.empty:

                    raise ValueError(
                        "The selected Sales dataset is empty."
                    )

                # =================================================
                # NORMALIZE COLUMNS
                # =================================================

                df.columns = [
                    normalize_column_name(column)
                    for column in df.columns
                ]

                # =================================================
                # DETECT COLUMNS
                # =================================================

                sales_column = find_column(
                    df,
                    [
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
                        "net_revenue",
                    ],
                    [
                        "sales",
                        "revenue",
                        "amount",
                    ],
                )

                date_column = find_column(
                    df,
                    [
                        "date",
                        "order_date",
                        "sales_date",
                        "transaction_date",
                        "purchase_date",
                        "invoice_date",
                        "created_at",
                        "payment_date",
                    ],
                    [
                        "date",
                        "order_date",
                        "transaction",
                        "purchase",
                    ],
                )

                order_column = find_column(
                    df,
                    [
                        "order_id",
                        "orderid",
                        "transaction_id",
                        "transactionid",
                        "invoice_id",
                        "invoice_no",
                        "invoice_number",
                        "sale_id",
                    ],
                    [
                        "order_id",
                        "transaction_id",
                        "invoice",
                    ],
                )

                quantity_column = find_column(
                    df,
                    [
                        "quantity",
                        "qty",
                        "units",
                        "units_sold",
                        "sales_quantity",
                    ],
                    [
                        "quantity",
                        "qty",
                        "units",
                    ],
                )

                product_column = find_column(
                    df,
                    [
                        "product",
                        "product_name",
                        "product_id",
                        "item",
                        "item_name",
                        "sku",
                        "product_title",
                    ],
                    [
                        "product",
                        "item",
                        "sku",
                    ],
                )

                category_column = find_column(
                    df,
                    [
                        "category",
                        "product_category",
                        "category_name",
                        "product_type",
                        "segment",
                    ],
                    [
                        "category",
                        "segment",
                    ],
                )

                region_column = find_column(
                    df,
                    [
                        "region",
                        "sales_region",
                        "area",
                        "territory",
                        "zone",
                        "location",
                    ],
                    [
                        "region",
                        "territory",
                        "zone",
                    ],
                )

                salesperson_column = find_column(
                    df,
                    [
                        "salesperson",
                        "sales_person",
                        "salesperson_name",
                        "sales_rep",
                        "sales_representative",
                        "representative",
                        "employee",
                        "employee_name",
                        "agent",
                    ],
                    [
                        "salesperson",
                        "sales_rep",
                        "representative",
                    ],
                )

                # =================================================
                # REQUIRED COLUMNS
                # =================================================

                if not sales_column:

                    raise ValueError(
                        "No sales/revenue column was detected "
                        "in the Sales dataset."
                    )

                if not date_column:

                    raise ValueError(
                        "No date column was detected "
                        "in the Sales dataset."
                    )

                # =================================================
                # CLEAN NUMERIC DATA
                # =================================================

                df[sales_column] = clean_numeric(
                    df[sales_column]
                )

                if quantity_column:

                    df[quantity_column] = clean_numeric(
                        df[quantity_column]
                    )

                # =================================================
                # CLEAN DATE
                # =================================================

                df[date_column] = pd.to_datetime(
                    df[date_column],
                    errors="coerce",
                )

                # =================================================
                # REMOVE INVALID REQUIRED RECORDS
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
                # SORT
                # =================================================

                df = (
                    df
                    .sort_values(date_column)
                    .reset_index(drop=True)
                )

                df_original = df.copy()

                # =================================================
                # APPLY DATE FILTER
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
                        "No sales records exist for "
                        "the selected date range."
                    )

                # =================================================
                # CURRENT PERIOD REVENUE
                # =================================================

                total_revenue = safe_float(
                    df[sales_column].sum()
                )

                current_period_revenue = (
                    total_revenue
                )

                # =================================================
                # ORDER COUNT
                # =================================================

                if order_column:

                    order_values = (
                        df[order_column]
                        .astype(str)
                        .str.strip()
                    )

                    order_values = (
                        order_values[
                            order_values.ne("")
                            & order_values.ne("nan")
                        ]
                    )

                    if not order_values.empty:

                        total_orders = int(
                            order_values.nunique()
                        )

                    else:

                        total_orders = int(
                            len(df)
                        )

                else:

                    total_orders = int(
                        len(df)
                    )

                current_period_orders = (
                    total_orders
                )

                # =================================================
                # AVERAGE ORDER VALUE
                # =================================================

                if total_orders > 0:

                    average_order_value = (
                        total_revenue
                        / total_orders
                    )

                current_period_aov = (
                    average_order_value
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

                    previous_df = (
                        previous_df.copy()
                    )

                    previous_df[sales_column] = (
                        clean_numeric(
                            previous_df[
                                sales_column
                            ]
                        )
                    )

                    previous_df = (
                        previous_df
                        .dropna(
                            subset=[
                                sales_column,
                                date_column,
                            ]
                        )
                    )

                    if not previous_df.empty:

                        previous_period_revenue = (
                            safe_float(
                                previous_df[
                                    sales_column
                                ].sum()
                            )
                        )

                        if order_column:

                            previous_orders = (
                                previous_df[
                                    order_column
                                ]
                                .astype(str)
                                .str.strip()
                            )

                            previous_orders = (
                                previous_orders[
                                    previous_orders.ne("")
                                    & previous_orders.ne("nan")
                                ]
                            )

                            if not previous_orders.empty:

                                previous_period_orders = int(
                                    previous_orders.nunique()
                                )

                            else:

                                previous_period_orders = int(
                                    len(previous_df)
                                )

                        else:

                            previous_period_orders = int(
                                len(previous_df)
                            )

                        if previous_period_orders > 0:

                            previous_period_aov = (
                                previous_period_revenue
                                / previous_period_orders
                            )

                        revenue_change = (
                            calculate_percentage_change(
                                current_period_revenue,
                                previous_period_revenue,
                            )
                        )

                        orders_change = (
                            calculate_percentage_change(
                                current_period_orders,
                                previous_period_orders,
                            )
                        )

                        aov_change = (
                            calculate_percentage_change(
                                current_period_aov,
                                previous_period_aov,
                            )
                        )

                        comparison_available = True

                # =================================================
                # DAILY SALES
                # =================================================

                daily_sales = (
                    df
                    .groupby(
                        df[date_column].dt.date
                    )[sales_column]
                    .sum()
                    .reset_index()
                )

                daily_sales.columns = [
                    "date",
                    "revenue",
                ]

                daily_sales["date"] = (
                    pd.to_datetime(
                        daily_sales["date"]
                    )
                )

                daily_sales = (
                    daily_sales
                    .sort_values("date")
                    .reset_index(drop=True)
                )

                if not daily_sales.empty:

                    average_daily_revenue = (
                        safe_float(
                            daily_sales[
                                "revenue"
                            ].mean()
                        )
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
                # WEEKLY SALES
                # =================================================

                weekly_sales = (
                    df
                    .set_index(date_column)
                    .resample("W")[
                        sales_column
                    ]
                    .sum()
                    .reset_index()
                )

                weekly_sales.columns = [
                    "date",
                    "revenue",
                ]

                weekly_sales["growth"] = (
                    weekly_sales["revenue"]
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

                if not weekly_sales.empty:

                    average_weekly_revenue = (
                        safe_float(
                            weekly_sales[
                                "revenue"
                            ].mean()
                        )
                    )

                # =================================================
                # MONTHLY SALES
                # =================================================

                monthly_sales = (
                    df
                    .set_index(date_column)
                    .resample("ME")[
                        sales_column
                    ]
                    .sum()
                    .reset_index()
                )

                monthly_sales.columns = [
                    "date",
                    "revenue",
                ]

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
                # LATEST MONTH GROWTH
                # =================================================

                if len(monthly_sales) >= 2:

                    latest_month = safe_float(
                        monthly_sales.iloc[-1][
                            "revenue"
                        ]
                    )

                    previous_month = safe_float(
                        monthly_sales.iloc[-2][
                            "revenue"
                        ]
                    )

                    sales_growth = (
                        calculate_percentage_change(
                            latest_month,
                            previous_month,
                        )
                    )

                # =================================================
                # PEAK / LOW PERIOD
                # =================================================

                if not monthly_sales.empty:

                    peak_row = monthly_sales.loc[
                        monthly_sales[
                            "revenue"
                        ].idxmax()
                    ]

                    lowest_row = monthly_sales.loc[
                        monthly_sales[
                            "revenue"
                        ].idxmin()
                    ]

                    peak_period = (
                        pd.to_datetime(
                            peak_row["date"]
                        ).strftime(
                            "%B %Y"
                        )
                    )

                    lowest_period = (
                        pd.to_datetime(
                            lowest_row["date"]
                        ).strftime(
                            "%B %Y"
                        )
                    )

                    peak_revenue = safe_float(
                        peak_row["revenue"]
                    )

                    lowest_revenue = safe_float(
                        lowest_row["revenue"]
                    )

                # =================================================
                # PRODUCT ANALYSIS
                # =================================================

                if product_column:

                    product_df = (
                        df
                        .assign(
                            __product=
                            df[product_column]
                            .astype(str)
                            .str.strip()
                        )
                    )

                    product_df = (
                        product_df[
                            ~product_df[
                                "__product"
                            ].isin(
                                [
                                    "",
                                    "nan",
                                    "None",
                                ]
                            )
                        ]
                    )

                    product_sales = (
                        product_df
                        .groupby(
                            "__product"
                        )[sales_column]
                        .sum()
                        .sort_values(
                            ascending=False
                        )
                    )

                    if not product_sales.empty:

                        best_product = str(
                            product_sales.index[0]
                        )

                        best_product_sales = (
                            safe_float(
                                product_sales.iloc[0]
                            )
                        )

                        if total_revenue > 0:

                            top_product_share = (
                                best_product_sales
                                / total_revenue
                                * 100
                            )

                        product_top = (
                            product_sales
                            .head(10)
                        )

                        product_labels = json.dumps(
                            [
                                str(index)
                                for index in product_top.index
                            ]
                        )

                        product_values = json.dumps(
                            [
                                round(
                                    safe_float(value),
                                    2,
                                )
                                for value
                                in product_top.values
                            ]
                        )

                        for index, value in (
                            product_sales
                            .head(15)
                            .items()
                        ):

                            share = (
                                safe_float(value)
                                / total_revenue
                                * 100
                                if total_revenue
                                else 0
                            )

                            product_rows.append(
                                {
                                    "name": str(index),
                                    "sales": safe_float(value),
                                    "share": share,
                                }
                            )

                # =================================================
                # CATEGORY ANALYSIS
                # =================================================

                if category_column:

                    category_df = (
                        df
                        .assign(
                            __category=
                            df[category_column]
                            .astype(str)
                            .str.strip()
                        )
                    )

                    category_df = (
                        category_df[
                            ~category_df[
                                "__category"
                            ].isin(
                                [
                                    "",
                                    "nan",
                                    "None",
                                ]
                            )
                        ]
                    )

                    category_sales = (
                        category_df
                        .groupby(
                            "__category"
                        )[sales_column]
                        .sum()
                        .sort_values(
                            ascending=False
                        )
                    )

                    if not category_sales.empty:

                        best_category = str(
                            category_sales.index[0]
                        )

                        best_category_sales = (
                            safe_float(
                                category_sales.iloc[0]
                            )
                        )

                        if total_revenue > 0:

                            top_category_share = (
                                best_category_sales
                                / total_revenue
                                * 100
                            )

                        category_top = (
                            category_sales
                            .head(10)
                        )

                        category_labels = json.dumps(
                            [
                                str(index)
                                for index
                                in category_top.index
                            ]
                        )

                        category_values = json.dumps(
                            [
                                round(
                                    safe_float(value),
                                    2,
                                )
                                for value
                                in category_top.values
                            ]
                        )

                        for index, value in (
                            category_sales
                            .head(15)
                            .items()
                        ):

                            share = (
                                safe_float(value)
                                / total_revenue
                                * 100
                                if total_revenue
                                else 0
                            )

                            category_rows.append(
                                {
                                    "name": str(index),
                                    "sales": safe_float(value),
                                    "share": share,
                                }
                            )

                # =================================================
                # REGION ANALYSIS
                # =================================================

                if region_column:

                    region_df = (
                        df
                        .assign(
                            __region=
                            df[region_column]
                            .astype(str)
                            .str.strip()
                        )
                    )

                    region_df = (
                        region_df[
                            ~region_df[
                                "__region"
                            ].isin(
                                [
                                    "",
                                    "nan",
                                    "None",
                                ]
                            )
                        ]
                    )

                    region_sales = (
                        region_df
                        .groupby(
                            "__region"
                        )[sales_column]
                        .sum()
                        .sort_values(
                            ascending=False
                        )
                    )

                    if not region_sales.empty:

                        best_region = str(
                            region_sales.index[0]
                        )

                        best_region_sales = (
                            safe_float(
                                region_sales.iloc[0]
                            )
                        )

                        if total_revenue > 0:

                            top_region_share = (
                                best_region_sales
                                / total_revenue
                                * 100
                            )

                        region_top = (
                            region_sales
                            .head(10)
                        )

                        region_labels = json.dumps(
                            [
                                str(index)
                                for index
                                in region_top.index
                            ]
                        )

                        region_values = json.dumps(
                            [
                                round(
                                    safe_float(value),
                                    2,
                                )
                                for value
                                in region_top.values
                            ]
                        )

                        for index, value in (
                            region_sales
                            .head(15)
                            .items()
                        ):

                            share = (
                                safe_float(value)
                                / total_revenue
                                * 100
                                if total_revenue
                                else 0
                            )

                            region_rows.append(
                                {
                                    "name": str(index),
                                    "sales": safe_float(value),
                                    "share": share,
                                }
                            )

                # =================================================
                # SALESPERSON ANALYSIS
                # =================================================

                if salesperson_column:

                    salesperson_df = (
                        df
                        .assign(
                            __salesperson=
                            df[salesperson_column]
                            .astype(str)
                            .str.strip()
                        )
                    )

                    salesperson_df = (
                        salesperson_df[
                            ~salesperson_df[
                                "__salesperson"
                            ].isin(
                                [
                                    "",
                                    "nan",
                                    "None",
                                ]
                            )
                        ]
                    )

                    salesperson_sales = (
                        salesperson_df
                        .groupby(
                            "__salesperson"
                        )[sales_column]
                        .sum()
                        .sort_values(
                            ascending=False
                        )
                    )

                    if not salesperson_sales.empty:

                        best_salesperson = str(
                            salesperson_sales.index[0]
                        )

                        best_salesperson_sales = (
                            safe_float(
                                salesperson_sales.iloc[0]
                            )
                        )

                        salesperson_top = (
                            salesperson_sales
                            .head(10)
                        )

                        salesperson_labels = json.dumps(
                            [
                                str(index)
                                for index
                                in salesperson_top.index
                            ]
                        )

                        salesperson_values = json.dumps(
                            [
                                round(
                                    safe_float(value),
                                    2,
                                )
                                for value
                                in salesperson_top.values
                            ]
                        )

                        for index, value in (
                            salesperson_sales
                            .head(15)
                            .items()
                        ):

                            salesperson_rows.append(
                                {
                                    "name": str(index),
                                    "sales": safe_float(value),
                                }
                            )

                # =================================================
                # CHART DATA
                # =================================================

                daily_labels = json.dumps(
                    [
                        date.strftime("%d %b")
                        for date
                        in daily_sales["date"]
                    ]
                )

                daily_values = json.dumps(
                    [
                        round(
                            safe_float(value),
                            2,
                        )
                        for value
                        in daily_sales["revenue"]
                    ]
                )

                weekly_labels = json.dumps(
                    [
                        date.strftime("%d %b")
                        for date
                        in weekly_sales["date"]
                    ]
                )

                weekly_values = json.dumps(
                    [
                        round(
                            safe_float(value),
                            2,
                        )
                        for value
                        in weekly_sales["revenue"]
                    ]
                )

                monthly_labels = json.dumps(
                    [
                        date.strftime("%b %Y")
                        for date
                        in monthly_sales["date"]
                    ]
                )

                monthly_values = json.dumps(
                    [
                        round(
                            safe_float(value),
                            2,
                        )
                        for value
                        in monthly_sales["revenue"]
                    ]
                )

                growth_labels = json.dumps(
                    [
                        date.strftime("%b %Y")
                        for date
                        in monthly_sales["date"]
                    ]
                )

                growth_values = json.dumps(
                    [
                        round(
                            safe_float(value),
                            2,
                        )
                        for value
                        in monthly_sales["growth"]
                    ]
                )

                # =================================================
                # MONTHLY TABLE
                # =================================================

                for _, row in (
                    monthly_sales
                    .tail(24)
                    .iterrows()
                ):

                    monthly_rows.append(
                        {
                            "period": pd.to_datetime(
                                row["date"]
                            ).strftime(
                                "%B %Y"
                            ),
                            "revenue": safe_float(
                                row["revenue"]
                            ),
                            "growth": safe_float(
                                row["growth"]
                            ),
                        }
                    )

                # =================================================
                # BUSINESS INSIGHTS
                # =================================================

                # -------------------------------------------------
                # REVENUE GROWTH
                # -------------------------------------------------

                if comparison_available:

                    if revenue_change >= 10:

                        sales_insights.append(
                            {
                                "type": "positive",
                                "title": "Strong revenue momentum",
                                "text": (
                                    f"Sales increased by "
                                    f"{revenue_change:.1f}% "
                                    f"versus the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                    elif revenue_change > 0:

                        sales_insights.append(
                            {
                                "type": "positive",
                                "title": "Revenue is growing",
                                "text": (
                                    f"Sales increased by "
                                    f"{revenue_change:.1f}% "
                                    f"compared with the "
                                    f"previous period."
                                ),
                            }
                        )

                    elif revenue_change <= -10:

                        sales_insights.append(
                            {
                                "type": "negative",
                                "title": "Significant revenue decline",
                                "text": (
                                    f"Sales decreased by "
                                    f"{abs(revenue_change):.1f}% "
                                    f"versus the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                    elif revenue_change < 0:

                        sales_insights.append(
                            {
                                "type": "warning",
                                "title": "Revenue is declining",
                                "text": (
                                    f"Sales decreased by "
                                    f"{abs(revenue_change):.1f}% "
                                    f"compared with the "
                                    f"previous period."
                                ),
                            }
                        )

                    else:

                        sales_insights.append(
                            {
                                "type": "neutral",
                                "title": "Revenue is stable",
                                "text": (
                                    "Sales remained broadly "
                                    "unchanged compared with "
                                    "the previous equivalent period."
                                ),
                            }
                        )

                elif len(monthly_sales) >= 2:

                    if sales_growth > 10:

                        sales_insights.append(
                            {
                                "type": "positive",
                                "title": "Strong recent growth",
                                "text": (
                                    f"The latest month grew by "
                                    f"{sales_growth:.1f}% "
                                    f"compared with the previous month."
                                ),
                            }
                        )

                    elif sales_growth > 0:

                        sales_insights.append(
                            {
                                "type": "positive",
                                "title": "Recent sales growth",
                                "text": (
                                    f"The latest month grew by "
                                    f"{sales_growth:.1f}%."
                                ),
                            }
                        )

                    elif sales_growth < -10:

                        sales_insights.append(
                            {
                                "type": "negative",
                                "title": "Recent sales decline",
                                "text": (
                                    f"The latest month declined by "
                                    f"{abs(sales_growth):.1f}%."
                                ),
                            }
                        )

                    else:

                        sales_insights.append(
                            {
                                "type": "neutral",
                                "title": "Stable recent sales",
                                "text": (
                                    "Recent monthly sales show "
                                    "limited movement."
                                ),
                            }
                        )

                # -------------------------------------------------
                # AOV
                # -------------------------------------------------

                if average_order_value > 0:

                    sales_insights.append(
                        {
                            "type": "info",
                            "title": "Average order value",
                            "text": (
                                f"Each order generates an average "
                                f"of ₹{average_order_value:,.2f}."
                            ),
                        }
                    )

                # -------------------------------------------------
                # BEST PRODUCT
                # -------------------------------------------------

                if best_product != "-":

                    sales_insights.append(
                        {
                            "type": "positive",
                            "title": "Top-selling product",
                            "text": (
                                f"{best_product} is the leading "
                                f"product with sales of "
                                f"₹{best_product_sales:,.2f}, "
                                f"representing approximately "
                                f"{top_product_share:.1f}% of revenue."
                            ),
                        }
                    )

                # -------------------------------------------------
                # CATEGORY
                # -------------------------------------------------

                if best_category != "-":

                    sales_insights.append(
                        {
                            "type": "info",
                            "title": "Best-performing category",
                            "text": (
                                f"{best_category} generated the "
                                f"highest category sales at "
                                f"₹{best_category_sales:,.2f}."
                            ),
                        }
                    )

                # -------------------------------------------------
                # REGION
                # -------------------------------------------------

                if best_region != "-":

                    if top_region_share >= 40:

                        sales_insights.append(
                            {
                                "type": "warning",
                                "title": "Regional concentration",
                                "text": (
                                    f"{best_region} contributes "
                                    f"{top_region_share:.1f}% "
                                    f"of total sales. High dependence "
                                    f"on one region may increase "
                                    f"regional risk."
                                ),
                            }
                        )

                    else:

                        sales_insights.append(
                            {
                                "type": "positive",
                                "title": "Regional leader",
                                "text": (
                                    f"{best_region} is the strongest "
                                    f"region with sales of "
                                    f"₹{best_region_sales:,.2f}."
                                ),
                            }
                        )

                # -------------------------------------------------
                # SALESPERSON
                # -------------------------------------------------

                if best_salesperson != "-":

                    sales_insights.append(
                        {
                            "type": "positive",
                            "title": "Top salesperson",
                            "text": (
                                f"{best_salesperson} generated the "
                                f"highest sales at "
                                f"₹{best_salesperson_sales:,.2f}."
                            ),
                        }
                    )

                # -------------------------------------------------
                # PEAK PERIOD
                # -------------------------------------------------

                if peak_period != "-":

                    sales_insights.append(
                        {
                            "type": "positive",
                            "title": "Peak sales period",
                            "text": (
                                f"{peak_period} recorded the "
                                f"highest monthly sales of "
                                f"₹{peak_revenue:,.2f}."
                            ),
                        }
                    )

                # -------------------------------------------------
                # LOWEST PERIOD
                # -------------------------------------------------

                if lowest_period != "-":

                    sales_insights.append(
                        {
                            "type": "warning",
                            "title": "Lowest sales period",
                            "text": (
                                f"{lowest_period} recorded the "
                                f"lowest monthly sales of "
                                f"₹{lowest_revenue:,.2f}. "
                                f"This period should be investigated "
                                f"for possible demand or operational causes."
                            ),
                        }
                    )

                # -------------------------------------------------
                # TRANSACTION CHANGE
                # -------------------------------------------------

                if comparison_available:

                    if orders_change >= 10:

                        sales_insights.append(
                            {
                                "type": "positive",
                                "title": "Order volume increased",
                                "text": (
                                    f"Order volume increased by "
                                    f"{orders_change:.1f}%."
                                ),
                            }
                        )

                    elif orders_change <= -10:

                        sales_insights.append(
                            {
                                "type": "negative",
                                "title": "Order volume declined",
                                "text": (
                                    f"Order volume decreased by "
                                    f"{abs(orders_change):.1f}%."
                                ),
                            }
                        )

                # -------------------------------------------------
                # AOV CHANGE
                # -------------------------------------------------

                if comparison_available:

                    if aov_change >= 10:

                        sales_insights.append(
                            {
                                "type": "positive",
                                "title": "Customers are spending more",
                                "text": (
                                    f"Average order value increased "
                                    f"by {aov_change:.1f}% compared "
                                    f"with the previous period."
                                ),
                            }
                        )

                    elif aov_change <= -10:

                        sales_insights.append(
                            {
                                "type": "warning",
                                "title": "Average order value weakened",
                                "text": (
                                    f"Average order value decreased "
                                    f"by {abs(aov_change):.1f}%."
                                ),
                            }
                        )

                # -------------------------------------------------
                # PRODUCT CONCENTRATION
                # -------------------------------------------------

                if top_product_share >= 50:

                    sales_insights.append(
                        {
                            "type": "warning",
                            "title": "Product concentration risk",
                            "text": (
                                f"The leading product contributes "
                                f"{top_product_share:.1f}% of total "
                                f"sales. Consider reducing dependence "
                                f"on a single product."
                            ),
                        }
                    )

                # -------------------------------------------------
                # ANALYSIS PERIOD
                # -------------------------------------------------

                if (
                    date_range.get("start_date")
                    and date_range.get("end_date")
                ):

                    sales_insights.append(
                        {
                            "type": "info",
                            "title": "Analysis period",
                            "text": (
                                f"Sales analysis covers "
                                f"{date_range['start_date'].strftime('%d %b %Y')} "
                                f"to "
                                f"{date_range['end_date'].strftime('%d %b %Y')}."
                            ),
                        }
                    )

                # =================================================
                # FINAL STATUS
                # =================================================

                has_data = True

            except Exception as exc:

                error_message = str(exc)

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # Dataset
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "selected_version": selected_version,

        # Status
        "has_data": has_data,
        "error_message": error_message,

        # KPI
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "average_order_value": average_order_value,
        "average_daily_revenue": average_daily_revenue,
        "average_weekly_revenue": average_weekly_revenue,
        "sales_growth": sales_growth,

        # Comparison
        "comparison_available": comparison_available,

        "current_period_revenue": current_period_revenue,
        "previous_period_revenue": previous_period_revenue,
        "revenue_change": revenue_change,

        "current_period_orders": current_period_orders,
        "previous_period_orders": previous_period_orders,
        "orders_change": orders_change,

        "current_period_aov": current_period_aov,
        "previous_period_aov": previous_period_aov,
        "aov_change": aov_change,

        # Peak / Low
        "peak_period": peak_period,
        "lowest_period": lowest_period,
        "peak_revenue": peak_revenue,
        "lowest_revenue": lowest_revenue,

        # Leaders
        "best_product": best_product,
        "best_product_sales": best_product_sales,

        "best_category": best_category,
        "best_category_sales": best_category_sales,

        "best_region": best_region,
        "best_region_sales": best_region_sales,

        "best_salesperson": best_salesperson,
        "best_salesperson_sales": best_salesperson_sales,

        # Concentration
        "top_product_share": top_product_share,
        "top_category_share": top_category_share,
        "top_region_share": top_region_share,

        # Tables
        "monthly_rows": monthly_rows,
        "product_rows": product_rows,
        "category_rows": category_rows,
        "region_rows": region_rows,
        "salesperson_rows": salesperson_rows,

        # Charts
        "daily_labels": daily_labels,
        "daily_values": daily_values,

        "weekly_labels": weekly_labels,
        "weekly_values": weekly_values,

        "monthly_labels": monthly_labels,
        "monthly_values": monthly_values,

        "growth_labels": growth_labels,
        "growth_values": growth_values,

        "product_labels": product_labels,
        "product_values": product_values,

        "category_labels": category_labels,
        "category_values": category_values,

        "region_labels": region_labels,
        "region_values": region_values,

        "salesperson_labels": salesperson_labels,
        "salesperson_values": salesperson_values,

        # Insights
        "sales_insights": sales_insights,

        # Columns
        "sales_column": sales_column or "",
        "date_column": date_column or "",
        "order_column": order_column or "",
        "quantity_column": quantity_column or "",
        "product_column": product_column or "",
        "category_column": category_column or "",
        "region_column": region_column or "",
        "salesperson_column": salesperson_column or "",

        # Date filter
        "date_range_options": DATE_RANGE_OPTIONS,
        "selected_range": selected_range,
        "custom_start": custom_start,
        "custom_end": custom_end,

        "date_range": (
            date_range
            if has_data
            else {
                "range_key": selected_range,
                "range_label": DATE_RANGE_OPTIONS.get(
                    selected_range,
                    "All Data",
                ),
                "start_date": None,
                "end_date": None,
                "days": None,
            }
        ),
    }

    return render(
        request,
        "analytics/sales_intelligence.html",
        context,
    )
import json
import numpy as np
import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


# ================================================================
# FINANCIAL INTELLIGENCE
# ================================================================

@login_required
def financial_intelligence(request):

    """
    Advanced Financial Intelligence

    Features:
    - Financial-domain-only filtering
    - Financial category filter
    - Date range filter
    - Revenue
    - Expenses
    - COGS
    - Gross Profit
    - Net Profit
    - Gross Margin
    - Net Margin
    - Operating Expenses
    - Expense breakdown
    - Revenue vs Expense
    - Profit trend
    - Cash-flow indicators
    - Period comparison
    - Advanced financial insights
    - Chart.js datasets
    """

    # ============================================================
    # DATASETS
    # ============================================================

    datasets = (
        Dataset.objects
        .filter(owner=request.user)
        .order_by("-uploaded_at")
    )

    # ============================================================
    # FILTERS
    # ============================================================

    selected_range = request.GET.get("range", "all")

    custom_start = request.GET.get("start", "")
    custom_end = request.GET.get("end", "")

    selected_category = request.GET.get(
        "financial_category",
        "all"
    )

    if (
        selected_range not in DATE_RANGE_OPTIONS
        and selected_range != "custom"
    ):
        selected_range = "all"

    # ============================================================
    # INITIAL STATE
    # ============================================================

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    # ============================================================
    # CORE KPIs
    # ============================================================

    total_revenue = 0.0
    total_expenses = 0.0

    cogs = 0.0
    gross_profit = 0.0
    net_profit = 0.0

    gross_margin = 0.0
    net_margin = 0.0

    operating_expenses = 0.0

    # ============================================================
    # CASH FLOW
    # ============================================================

    cash_inflow = 0.0
    cash_outflow = 0.0
    net_cash_flow = 0.0
    cash_flow_margin = 0.0

    cash_flow_available = False

    # ============================================================
    # PERIOD COMPARISON
    # ============================================================

    current_period_revenue = 0.0
    previous_period_revenue = 0.0
    revenue_change = 0.0

    current_period_expenses = 0.0
    previous_period_expenses = 0.0
    expense_change = 0.0

    current_period_profit = 0.0
    previous_period_profit = 0.0
    profit_change = 0.0

    current_net_margin = 0.0
    previous_net_margin = 0.0
    margin_change = 0.0

    comparison_available = False

    # ============================================================
    # HIGHLIGHTS
    # ============================================================

    peak_profit_period = "-"
    lowest_profit_period = "-"

    highest_expense_category = "-"
    highest_expense_amount = 0.0

    # ============================================================
    # TABLES
    # ============================================================

    financial_rows = []
    expense_rows = []

    # ============================================================
    # INSIGHTS
    # ============================================================

    financial_insights = []

    # ============================================================
    # FILTER INFORMATION
    # ============================================================

    financial_categories = []

    financial_domain_column = ""
    financial_category_column = ""

    financial_domain_filtered = False

    # ============================================================
    # COLUMN INFORMATION
    # ============================================================

    revenue_column = ""
    expense_column = ""
    cogs_column = ""
    operating_expense_column = ""

    cash_inflow_column = ""
    cash_outflow_column = ""

    date_column = ""

    # ============================================================
    # CHART DATA
    # ============================================================

    financial_labels = json.dumps([])

    revenue_values = json.dumps([])
    expense_values = json.dumps([])
    profit_values = json.dumps([])

    gross_profit_values = json.dumps([])
    net_margin_values = json.dumps([])

    expense_category_labels = json.dumps([])
    expense_category_values = json.dumps([])

    profit_labels = json.dumps([])
    profit_trend_values = json.dumps([])

    margin_labels = json.dumps([])
    margin_trend_values = json.dumps([])

    cash_flow_labels = json.dumps([])
    cash_inflow_values = json.dumps([])
    cash_outflow_values = json.dumps([])
    net_cash_flow_values = json.dumps([])

    # ============================================================
    # DATE RANGE FALLBACK
    # ============================================================

    date_range = {
        "range_key": selected_range,
        "range_label": DATE_RANGE_OPTIONS.get(
            selected_range,
            "All Data"
        ),
        "start_date": None,
        "end_date": None,
        "days": None,
    }

    # ============================================================
    # DATASET SELECTION
    # ============================================================

    if datasets.exists():

        dataset_id = request.GET.get("dataset")

        if dataset_id:
            selected_dataset = (
                datasets
                .filter(id=dataset_id)
                .first()
            )

        if not selected_dataset:
            selected_dataset = datasets.first()

        # ========================================================
        # CLEANED VERSION
        # ========================================================

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

        # ========================================================
        # CURRENT VERSION FALLBACK
        # ========================================================

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

        # ========================================================
        # PROCESS DATA
        # ========================================================

        if selected_version:

            try:

                file_path = selected_version.file.path

                # =================================================
                # READ CSV / EXCEL
                # =================================================

                if file_path.lower().endswith(".csv"):

                    df = pd.read_csv(file_path)

                elif file_path.lower().endswith(
                    (".xlsx", ".xls")
                ):

                    df = pd.read_excel(file_path)

                else:

                    raise ValueError(
                        "Financial Intelligence supports "
                        "CSV and Excel files."
                    )

                if df.empty:

                    raise ValueError(
                        "The selected dataset is empty."
                    )

                # =================================================
                # NORMALIZE COLUMN NAMES
                # =================================================

                df.columns = [
                    str(column)
                    .strip()
                    .lower()
                    .replace(" ", "_")
                    .replace("-", "_")
                    for column in df.columns
                ]

                # =================================================
                # COLUMN DETECTOR
                # =================================================

                def detect_column(candidates, keywords=None):

                    keywords = keywords or []

                    # Exact
                    for candidate in candidates:

                        if candidate in df.columns:
                            return candidate

                    # Partial
                    for column in df.columns:

                        for keyword in keywords:

                            if keyword in column:
                                return column

                    return None

                # =================================================
                # REVENUE
                # =================================================

                revenue_column = detect_column(
                    [
                        "revenue",
                        "total_revenue",
                        "sales",
                        "sale",
                        "total_sales",
                        "net_sales",
                        "sales_amount",
                        "revenue_amount",
                        "order_value",
                        "income",
                    ],
                    [
                        "revenue",
                        "sales",
                    ],
                )

                # =================================================
                # EXPENSE
                # =================================================

                expense_column = detect_column(
                    [
                        "total_expense",
                        "total_expenses",
                        "expense",
                        "expenses",
                        "cost",
                        "costs",
                        "expense_amount",
                        "cost_amount",
                        "total_cost",
                    ],
                    [
                        "expense",
                        "cost",
                    ],
                )

                # =================================================
                # COGS
                # =================================================

                cogs_column = detect_column(
                    [
                        "cogs",
                        "cost_of_goods_sold",
                        "cost_of_goods",
                        "direct_cost",
                        "direct_costs",
                        "cost_of_sales",
                    ],
                    [
                        "cogs",
                        "cost_of_goods",
                        "direct_cost",
                    ],
                )

                # =================================================
                # OPERATING EXPENSE
                # =================================================

                operating_expense_column = detect_column(
                    [
                        "operating_expense",
                        "operating_expenses",
                        "opex",
                        "operating_cost",
                        "operating_costs",
                    ],
                    [
                        "operating_expense",
                        "operating_cost",
                        "opex",
                    ],
                )

                # =================================================
                # DATE
                # =================================================

                date_column = detect_column(
                    [
                        "date",
                        "order_date",
                        "sales_date",
                        "transaction_date",
                        "purchase_date",
                        "created_at",
                        "invoice_date",
                        "payment_date",
                        "expense_date",
                    ],
                    [
                        "date",
                        "transaction",
                        "purchase",
                        "order",
                        "created",
                    ],
                )

                # =================================================
                # EXPENSE CATEGORY
                # =================================================

                expense_category_column = detect_column(
                    [
                        "expense_category",
                        "expense_type",
                        "cost_category",
                        "cost_type",
                        "expense_group",
                        "expense_class",
                    ],
                    [
                        "expense_category",
                        "cost_category",
                        "expense_type",
                    ],
                )

                # =================================================
                # GENERIC CATEGORY
                # =================================================

                generic_category_column = detect_column(
                    [
                        "category",
                        "business_category",
                        "financial_category",
                        "data_category",
                        "analytics_category",
                        "category_type",
                        "record_type",
                    ],
                    [
                        "category",
                    ],
                )

                # =================================================
                # FINANCIAL DOMAIN COLUMN
                #
                # This is different from expense category.
                #
                # Example:
                # category = Financial / Customer / Product
                # =================================================

                financial_domain_column = detect_column(
                    [
                        "domain",
                        "data_domain",
                        "business_domain",
                        "analytics_domain",
                        "module",
                        "section",
                        "data_category",
                        "analytics_category",
                        "business_category",
                        "category_type",
                    ],
                    [
                        "domain",
                        "data_category",
                        "analytics_category",
                        "business_category",
                    ],
                ) or ""

                # Do not accidentally use expense category as domain.
                if (
                    financial_domain_column
                    == expense_category_column
                ):
                    financial_domain_column = ""

                # =================================================
                # CATEGORY FILTER COLUMN
                # =================================================

                financial_category_column = (
                    generic_category_column
                    or expense_category_column
                    or ""
                )

                # =================================================
                # CASH INFLOW
                # =================================================

                cash_inflow_column = detect_column(
                    [
                        "cash_inflow",
                        "cash_inflows",
                        "cash_received",
                        "cash_received_amount",
                        "inflow",
                        "cash_income",
                        "receipts",
                    ],
                    [
                        "cash_inflow",
                        "cash_received",
                        "inflow",
                    ],
                )

                # =================================================
                # CASH OUTFLOW
                # =================================================

                cash_outflow_column = detect_column(
                    [
                        "cash_outflow",
                        "cash_outflows",
                        "cash_paid",
                        "cash_paid_amount",
                        "outflow",
                        "cash_expense",
                        "payments",
                    ],
                    [
                        "cash_outflow",
                        "cash_paid",
                        "outflow",
                    ],
                )

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
                # NUMERIC CONVERSION
                # =================================================

                numeric_columns = [
                    revenue_column,
                    expense_column,
                    cogs_column,
                    operating_expense_column,
                    cash_inflow_column,
                    cash_outflow_column,
                ]

                for column in numeric_columns:

                    if column and column in df.columns:

                        df[column] = pd.to_numeric(
                            df[column],
                            errors="coerce"
                        )

                # =================================================
                # DATE CONVERSION
                # =================================================

                df[date_column] = pd.to_datetime(
                    df[date_column],
                    errors="coerce"
                )

                # =================================================
                # REQUIRED DATA CLEANING
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
                # SORT
                # =================================================

                df = (
                    df
                    .sort_values(date_column)
                    .reset_index(drop=True)
                )

                # =================================================
                # FINANCIAL DOMAIN FILTER
                #
                # If a domain/category column explicitly contains
                # Financial, ONLY those rows are used.
                # =================================================

                if financial_domain_column:

                    domain_values = (
                        df[financial_domain_column]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                    )

                    financial_mask = (
                        domain_values
                        .str.lower()
                        .isin(
                            [
                                "financial",
                                "finance",
                                "financials",
                                "financial intelligence",
                            ]
                        )
                    )

                    if financial_mask.any():

                        df = df.loc[
                            financial_mask
                        ].copy()

                        financial_domain_filtered = True

                if df.empty:

                    raise ValueError(
                        "No Financial category records were "
                        "found in the selected dataset."
                    )

                # =================================================
                # AVAILABLE FINANCIAL CATEGORIES
                # =================================================

                if (
                    financial_category_column
                    and financial_category_column in df.columns
                ):

                    category_values = (
                        df[
                            financial_category_column
                        ]
                        .fillna("Uncategorized")
                        .astype(str)
                        .str.strip()
                    )

                    category_values = (
                        category_values
                        .replace("", "Uncategorized")
                    )

                    df[
                        financial_category_column
                    ] = category_values

                    financial_categories = sorted(
                        category_values
                        .dropna()
                        .unique()
                        .tolist()
                    )

                    # =============================================
                    # USER CATEGORY FILTER
                    # =============================================

                    if (
                        selected_category != "all"
                        and selected_category
                        in financial_categories
                    ):

                        df = df[
                            df[
                                financial_category_column
                            ]
                            == selected_category
                        ].copy()

                # =================================================
                # KEEP COMPLETE FINANCIAL DATA
                # =================================================

                df_original = df.copy()

                # =================================================
                # DATE FILTER
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
                        "No financial records exist for the "
                        "selected filters."
                    )

                # =================================================
                # BASIC VALUES
                # =================================================

                total_revenue = float(
                    df[revenue_column].sum()
                )

                total_expenses = float(
                    df[expense_column].sum()
                )

                # =================================================
                # COGS
                # =================================================

                if cogs_column:

                    cogs = float(
                        df[cogs_column]
                        .fillna(0)
                        .sum()
                    )

                else:

                    # When COGS does not exist, use zero rather
                    # than incorrectly calling all expenses COGS.
                    cogs = 0.0

                # =================================================
                # GROSS PROFIT
                # =================================================

                gross_profit = (
                    total_revenue - cogs
                )

                # =================================================
                # OPERATING EXPENSES
                # =================================================

                if operating_expense_column:

                    operating_expenses = float(
                        df[
                            operating_expense_column
                        ]
                        .fillna(0)
                        .sum()
                    )

                else:

                    # If no explicit OPEX column exists,
                    # estimate OPEX as expenses after COGS.
                    operating_expenses = max(
                        total_expenses - cogs,
                        0
                    )

                # =================================================
                # NET PROFIT
                # =================================================

                net_profit = (
                    total_revenue
                    - total_expenses
                )

                # =================================================
                # MARGINS
                # =================================================

                if total_revenue:

                    gross_margin = (
                        gross_profit
                        / total_revenue
                    ) * 100

                    net_margin = (
                        net_profit
                        / total_revenue
                    ) * 100

                # =================================================
                # CASH FLOW
                # =================================================

                if (
                    cash_inflow_column
                    and cash_outflow_column
                ):

                    cash_inflow = float(
                        df[
                            cash_inflow_column
                        ]
                        .fillna(0)
                        .sum()
                    )

                    cash_outflow = float(
                        df[
                            cash_outflow_column
                        ]
                        .fillna(0)
                        .sum()
                    )

                    net_cash_flow = (
                        cash_inflow
                        - cash_outflow
                    )

                    if cash_inflow:

                        cash_flow_margin = (
                            net_cash_flow
                            / cash_inflow
                        ) * 100

                    cash_flow_available = True

                # =================================================
                # PREVIOUS PERIOD
                # =================================================

                previous_df = get_previous_period(
                    df_original,
                    date_column,
                    date_range["start_date"],
                    date_range["end_date"],
                )

                if not previous_df.empty:

                    previous_df = previous_df.copy()

                    previous_df[
                        revenue_column
                    ] = pd.to_numeric(
                        previous_df[
                            revenue_column
                        ],
                        errors="coerce"
                    )

                    previous_df[
                        expense_column
                    ] = pd.to_numeric(
                        previous_df[
                            expense_column
                        ],
                        errors="coerce"
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
                            previous_df[
                                revenue_column
                            ].sum()
                        )

                        previous_period_expenses = float(
                            previous_df[
                                expense_column
                            ].sum()
                        )

                        previous_period_profit = (
                            previous_period_revenue
                            - previous_period_expenses
                        )

                        if previous_period_revenue:

                            previous_net_margin = (
                                previous_period_profit
                                / previous_period_revenue
                            ) * 100

                        else:

                            previous_net_margin = 0

                        revenue_change = (
                            calculate_percentage_change(
                                total_revenue,
                                previous_period_revenue,
                            )
                        )

                        expense_change = (
                            calculate_percentage_change(
                                total_expenses,
                                previous_period_expenses,
                            )
                        )

                        profit_change = (
                            calculate_percentage_change(
                                net_profit,
                                previous_period_profit,
                            )
                        )

                        margin_change = (
                            net_margin
                            - previous_net_margin
                        )

                        comparison_available = True

                current_period_revenue = total_revenue
                current_period_expenses = total_expenses
                current_period_profit = net_profit
                current_net_margin = net_margin

                # =================================================
                # MONTHLY ANALYSIS
                # =================================================

                monthly_financial = (
                    df
                    .set_index(date_column)
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

                # =================================================
                # MONTHLY MARGIN
                # =================================================

                monthly_financial["margin"] = np.where(
                    monthly_financial["revenue"] != 0,
                    (
                        monthly_financial["profit"]
                        / monthly_financial["revenue"]
                    ) * 100,
                    0,
                )

                # =================================================
                # GROSS PROFIT MONTHLY
                # =================================================

                if cogs_column:

                    monthly_cogs = (
                        df
                        .set_index(date_column)
                        .resample("ME")[cogs_column]
                        .sum()
                        .reset_index()
                    )

                    monthly_cogs.columns = [
                        "date",
                        "cogs",
                    ]

                    monthly_financial = (
                        monthly_financial
                        .merge(
                            monthly_cogs,
                            on="date",
                            how="left",
                        )
                    )

                    monthly_financial["gross_profit"] = (
                        monthly_financial["revenue"]
                        - monthly_financial["cogs"]
                    )

                else:

                    monthly_financial[
                        "gross_profit"
                    ] = monthly_financial[
                        "profit"
                    ]

                # =================================================
                # PEAK / LOWEST PERIOD
                # =================================================

                if not monthly_financial.empty:

                    peak_row = monthly_financial.loc[
                        monthly_financial[
                            "profit"
                        ].idxmax()
                    ]

                    lowest_row = monthly_financial.loc[
                        monthly_financial[
                            "profit"
                        ].idxmin()
                    ]

                    peak_profit_period = (
                        peak_row["date"]
                        .strftime("%B %Y")
                    )

                    lowest_profit_period = (
                        lowest_row["date"]
                        .strftime("%B %Y")
                    )

                # =================================================
                # MONTHLY TABLE
                # =================================================

                for _, row in (
                    monthly_financial
                    .tail(24)
                    .iterrows()
                ):

                    financial_rows.append(
                        {
                            "period": row[
                                "date"
                            ].strftime(
                                "%B %Y"
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

                            "gross_profit": round(
                                float(
                                    row["gross_profit"]
                                ),
                                2,
                            ),
                        }
                    )

                # =================================================
                # MAIN CHART DATA
                # =================================================

                financial_labels = json.dumps(
                    [
                        d.strftime("%b %Y")
                        for d in monthly_financial[
                            "date"
                        ]
                    ]
                )

                revenue_values = json.dumps(
                    [
                        round(float(v), 2)
                        for v in monthly_financial[
                            "revenue"
                        ]
                    ]
                )

                expense_values = json.dumps(
                    [
                        round(float(v), 2)
                        for v in monthly_financial[
                            "expenses"
                        ]
                    ]
                )

                profit_values = json.dumps(
                    [
                        round(float(v), 2)
                        for v in monthly_financial[
                            "profit"
                        ]
                    ]
                )

                gross_profit_values = json.dumps(
                    [
                        round(float(v), 2)
                        for v in monthly_financial[
                            "gross_profit"
                        ]
                    ]
                )

                # =================================================
                # PROFIT TREND
                # =================================================

                profit_labels = json.dumps(
                    [
                        d.strftime("%b %Y")
                        for d in monthly_financial[
                            "date"
                        ]
                    ]
                )

                profit_trend_values = json.dumps(
                    [
                        round(float(v), 2)
                        for v in monthly_financial[
                            "profit"
                        ]
                    ]
                )

                # =================================================
                # MARGIN TREND
                # =================================================

                margin_labels = json.dumps(
                    [
                        d.strftime("%b %Y")
                        for d in monthly_financial[
                            "date"
                        ]
                    ]
                )

                margin_trend_values = json.dumps(
                    [
                        round(float(v), 2)
                        for v in monthly_financial[
                            "margin"
                        ]
                    ]
                )

                net_margin_values = json.dumps(
                    [
                        round(float(v), 2)
                        for v in monthly_financial[
                            "margin"
                        ]
                    ]
                )

                # =================================================
                # EXPENSE BREAKDOWN
                # =================================================

                if expense_category_column:

                    expense_category = (
                        df
                        .groupby(
                            expense_category_column
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

                    for _, row in (
                        expense_category.iterrows()
                    ):

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

                    if not expense_category.empty:

                        highest_expense_category = (
                            str(
                                expense_category.iloc[
                                    0
                                ]["category"]
                            )
                        )

                        highest_expense_amount = float(
                            expense_category.iloc[
                                0
                            ]["expenses"]
                        )

                    expense_category_labels = json.dumps(
                        [
                            str(x)
                            for x in expense_category[
                                "category"
                            ].head(12)
                        ]
                    )

                    expense_category_values = json.dumps(
                        [
                            round(float(x), 2)
                            for x in expense_category[
                                "expenses"
                            ].head(12)
                        ]
                    )

                # =================================================
                # CASH FLOW MONTHLY
                # =================================================

                if cash_flow_available:

                    cash_monthly = (
                        df
                        .set_index(date_column)
                        .resample("ME")
                        [
                            [
                                cash_inflow_column,
                                cash_outflow_column,
                            ]
                        ]
                        .sum()
                        .reset_index()
                    )

                    cash_monthly["net_cash"] = (
                        cash_monthly[
                            cash_inflow_column
                        ]
                        - cash_monthly[
                            cash_outflow_column
                        ]
                    )

                    cash_flow_labels = json.dumps(
                        [
                            d.strftime("%b %Y")
                            for d in cash_monthly[
                                date_column
                            ]
                        ]
                    )

                    cash_inflow_values = json.dumps(
                        [
                            round(float(x), 2)
                            for x in cash_monthly[
                                cash_inflow_column
                            ]
                        ]
                    )

                    cash_outflow_values = json.dumps(
                        [
                            round(float(x), 2)
                            for x in cash_monthly[
                                cash_outflow_column
                            ]
                        ]
                    )

                    net_cash_flow_values = json.dumps(
                        [
                            round(float(x), 2)
                            for x in cash_monthly[
                                "net_cash"
                            ]
                        ]
                    )

                # =================================================
                # ADVANCED INSIGHTS
                # =================================================

                # ------------------------------------------------
                # PROFITABILITY
                # ------------------------------------------------

                if net_margin >= 30:

                    financial_insights.append(
                        {
                            "type": "positive",
                            "icon": "fa-chart-line",
                            "title": "Strong net profitability",
                            "text": (
                                f"Net margin is "
                                f"{net_margin:.1f}%, "
                                f"indicating strong "
                                f"profit generation."
                            ),
                        }
                    )

                elif net_margin >= 15:

                    financial_insights.append(
                        {
                            "type": "positive",
                            "icon": "fa-circle-check",
                            "title": "Healthy profitability",
                            "text": (
                                f"Net margin is "
                                f"{net_margin:.1f}%. "
                                f"The business is "
                                f"maintaining a healthy "
                                f"profit level."
                            ),
                        }
                    )

                elif net_margin > 0:

                    financial_insights.append(
                        {
                            "type": "warning",
                            "icon": "fa-triangle-exclamation",
                            "title": "Thin profit margin",
                            "text": (
                                f"Net margin is only "
                                f"{net_margin:.1f}%. "
                                f"Small increases in "
                                f"expenses could materially "
                                f"reduce profitability."
                            ),
                        }
                    )

                else:

                    financial_insights.append(
                        {
                            "type": "negative",
                            "icon": "fa-arrow-trend-down",
                            "title": "Net loss detected",
                            "text": (
                                f"Expenses exceed revenue "
                                f"by ₹{abs(net_profit):,.2f}."
                            ),
                        }
                    )

                # ------------------------------------------------
                # GROSS MARGIN
                # ------------------------------------------------

                if cogs_column:

                    if gross_margin >= 50:

                        gross_text = (
                            f"Gross margin is "
                            f"{gross_margin:.1f}%, "
                            f"showing strong economics "
                            f"before operating expenses."
                        )

                        gross_type = "positive"

                    elif gross_margin >= 25:

                        gross_text = (
                            f"Gross margin is "
                            f"{gross_margin:.1f}%. "
                            f"Monitor direct costs "
                            f"closely."
                        )

                        gross_type = "warning"

                    else:

                        gross_text = (
                            f"Gross margin is only "
                            f"{gross_margin:.1f}%, "
                            f"indicating pressure "
                            f"from direct costs."
                        )

                        gross_type = "negative"

                    financial_insights.append(
                        {
                            "type": gross_type,
                            "icon": "fa-layer-group",
                            "title": "Gross margin analysis",
                            "text": gross_text,
                        }
                    )

                # ------------------------------------------------
                # EXPENSE RATIO
                # ------------------------------------------------

                if total_revenue:

                    expense_ratio = (
                        total_expenses
                        / total_revenue
                    ) * 100

                    if expense_ratio > 85:

                        financial_insights.append(
                            {
                                "type": "negative",
                                "icon": "fa-wallet",
                                "title": "High expense burden",
                                "text": (
                                    f"Expenses consume "
                                    f"{expense_ratio:.1f}% "
                                    f"of revenue."
                                ),
                            }
                        )

                    elif expense_ratio > 70:

                        financial_insights.append(
                            {
                                "type": "warning",
                                "icon": "fa-scale-balanced",
                                "title": "Expense pressure",
                                "text": (
                                    f"Expenses represent "
                                    f"{expense_ratio:.1f}% "
                                    f"of revenue."
                                ),
                            }
                        )

                # ------------------------------------------------
                # PERIOD PROFIT CHANGE
                # ------------------------------------------------

                if comparison_available:

                    if profit_change > 10:

                        financial_insights.append(
                            {
                                "type": "positive",
                                "icon": "fa-arrow-trend-up",
                                "title": "Profit improved",
                                "text": (
                                    f"Net profit increased "
                                    f"by {profit_change:.1f}% "
                                    f"versus the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                    elif profit_change < -10:

                        financial_insights.append(
                            {
                                "type": "negative",
                                "icon": "fa-arrow-trend-down",
                                "title": "Profit declined",
                                "text": (
                                    f"Net profit decreased "
                                    f"by {abs(profit_change):.1f}% "
                                    f"versus the previous "
                                    f"equivalent period."
                                ),
                            }
                        )

                    else:

                        financial_insights.append(
                            {
                                "type": "neutral",
                                "icon": "fa-minus",
                                "title": "Profit relatively stable",
                                "text": (
                                    "Profit has not changed "
                                    "significantly compared "
                                    "with the previous "
                                    "equivalent period."
                                ),
                            }
                        )

                # ------------------------------------------------
                # EXPENSE CHANGE
                # ------------------------------------------------

                if comparison_available:

                    if expense_change > 10:

                        financial_insights.append(
                            {
                                "type": "warning",
                                "icon": "fa-arrow-up",
                                "title": "Expenses increased",
                                "text": (
                                    f"Expenses increased "
                                    f"by {expense_change:.1f}%."
                                ),
                            }
                        )

                    elif expense_change < -10:

                        financial_insights.append(
                            {
                                "type": "positive",
                                "icon": "fa-arrow-down",
                                "title": "Expense reduction",
                                "text": (
                                    f"Expenses decreased "
                                    f"by {abs(expense_change):.1f}%."
                                ),
                            }
                        )

                # ------------------------------------------------
                # HIGHEST COST
                # ------------------------------------------------

                if highest_expense_category != "-":

                    expense_share = 0

                    if total_expenses:

                        expense_share = (
                            highest_expense_amount
                            / total_expenses
                        ) * 100

                    financial_insights.append(
                        {
                            "type": "warning",
                            "icon": "fa-ranking-star",
                            "title": "Largest expense category",
                            "text": (
                                f"{highest_expense_category} "
                                f"accounts for "
                                f"₹{highest_expense_amount:,.2f} "
                                f"({expense_share:.1f}% "
                                f"of total expenses)."
                            ),
                        }
                    )

                # ------------------------------------------------
                # CASH FLOW
                # ------------------------------------------------

                if cash_flow_available:

                    if net_cash_flow > 0:

                        financial_insights.append(
                            {
                                "type": "positive",
                                "icon": "fa-money-bill-transfer",
                                "title": "Positive cash flow",
                                "text": (
                                    f"Net cash flow is "
                                    f"positive at "
                                    f"₹{net_cash_flow:,.2f}."
                                ),
                            }
                        )

                    elif net_cash_flow < 0:

                        financial_insights.append(
                            {
                                "type": "negative",
                                "icon": "fa-money-bill-trend-down",
                                "title": "Negative cash flow",
                                "text": (
                                    f"Cash outflows exceed "
                                    f"inflows by "
                                    f"₹{abs(net_cash_flow):,.2f}."
                                ),
                            }
                        )

                # ------------------------------------------------
                # PROFIT PEAK
                # ------------------------------------------------

                if peak_profit_period != "-":

                    financial_insights.append(
                        {
                            "type": "positive",
                            "icon": "fa-trophy",
                            "title": "Most profitable period",
                            "text": (
                                f"{peak_profit_period} "
                                f"generated the highest "
                                f"monthly profit."
                            ),
                        }
                    )

                # ------------------------------------------------
                # LOWEST PROFIT
                # ------------------------------------------------

                if lowest_profit_period != "-":

                    financial_insights.append(
                        {
                            "type": "warning",
                            "icon": "fa-magnifying-glass-chart",
                            "title": "Lowest profitability period",
                            "text": (
                                f"{lowest_profit_period} "
                                f"recorded the lowest "
                                f"monthly profit and "
                                f"should be investigated."
                            ),
                        }
                    )

                # ------------------------------------------------
                # FINANCIAL DOMAIN
                # ------------------------------------------------

                if financial_domain_filtered:

                    financial_insights.append(
                        {
                            "type": "info",
                            "icon": "fa-filter",
                            "title": "Financial data isolation",
                            "text": (
                                "Only records classified as "
                                "Financial were included in "
                                "this analysis."
                            ),
                        }
                    )

                # ------------------------------------------------
                # DATE RANGE
                # ------------------------------------------------

                if (
                    date_range.get("start_date")
                    and date_range.get("end_date")
                ):

                    financial_insights.append(
                        {
                            "type": "info",
                            "icon": "fa-calendar-days",
                            "title": "Analysis period",
                            "text": (
                                "Financial analysis covers "
                                f"{date_range['start_date'].strftime('%d %b %Y')} "
                                "to "
                                f"{date_range['end_date'].strftime('%d %b %Y')}."
                            ),
                        }
                    )

                # =================================================
                # SUCCESS
                # =================================================

                has_data = True

            except Exception as exc:

                error_message = str(exc)

    # ============================================================
    # CONTEXT
    # ============================================================

    context = {

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "selected_version": selected_version,

        "has_data": has_data,

        "error_message": error_message,

        # --------------------------------------------------------
        # FILTERS
        # --------------------------------------------------------

        "selected_range": selected_range,

        "custom_start": custom_start,

        "custom_end": custom_end,

        "selected_category": selected_category,

        "financial_categories": financial_categories,

        "financial_domain_column": (
            financial_domain_column
        ),

        "financial_category_column": (
            financial_category_column
        ),

        "financial_domain_filtered": (
            financial_domain_filtered
        ),

        # --------------------------------------------------------
        # KPIs
        # --------------------------------------------------------

        "total_revenue": total_revenue,

        "total_expenses": total_expenses,

        "cogs": cogs,

        "gross_profit": gross_profit,

        "net_profit": net_profit,

        "gross_margin": gross_margin,

        "net_margin": net_margin,

        "operating_expenses": operating_expenses,

        # --------------------------------------------------------
        # CASH FLOW
        # --------------------------------------------------------

        "cash_inflow": cash_inflow,

        "cash_outflow": cash_outflow,

        "net_cash_flow": net_cash_flow,

        "cash_flow_margin": cash_flow_margin,

        "cash_flow_available": cash_flow_available,

        # --------------------------------------------------------
        # COMPARISON
        # --------------------------------------------------------

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

        "current_net_margin": (
            current_net_margin
        ),

        "previous_net_margin": (
            previous_net_margin
        ),

        "margin_change": margin_change,

        "comparison_available": (
            comparison_available
        ),

        # --------------------------------------------------------
        # HIGHLIGHTS
        # --------------------------------------------------------

        "peak_profit_period": (
            peak_profit_period
        ),

        "lowest_profit_period": (
            lowest_profit_period
        ),

        "highest_expense_category": (
            highest_expense_category
        ),

        "highest_expense_amount": (
            highest_expense_amount
        ),

        # --------------------------------------------------------
        # TABLES
        # --------------------------------------------------------

        "financial_rows": financial_rows,

        "expense_rows": expense_rows,

        # --------------------------------------------------------
        # CHART DATA
        # --------------------------------------------------------

        "financial_labels": financial_labels,

        "revenue_values": revenue_values,

        "expense_values": expense_values,

        "profit_values": profit_values,

        "gross_profit_values": gross_profit_values,

        "net_margin_values": net_margin_values,

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

        "margin_labels": margin_labels,

        "margin_trend_values": (
            margin_trend_values
        ),

        "cash_flow_labels": cash_flow_labels,

        "cash_inflow_values": (
            cash_inflow_values
        ),

        "cash_outflow_values": (
            cash_outflow_values
        ),

        "net_cash_flow_values": (
            net_cash_flow_values
        ),

        # --------------------------------------------------------
        # INSIGHTS
        # --------------------------------------------------------

        "financial_insights": (
            financial_insights
        ),

        # --------------------------------------------------------
        # COLUMNS
        # --------------------------------------------------------

        "revenue_column": (
            revenue_column or ""
        ),

        "expense_column": (
            expense_column or ""
        ),

        "cogs_column": (
            cogs_column or ""
        ),

        "operating_expense_column": (
            operating_expense_column or ""
        ),

        "cash_inflow_column": (
            cash_inflow_column or ""
        ),

        "cash_outflow_column": (
            cash_outflow_column or ""
        ),

        "date_column": (
            date_column or ""
        ),

        # --------------------------------------------------------
        # DATE RANGE
        # --------------------------------------------------------

        "date_range_options": (
            DATE_RANGE_OPTIONS
        ),

        "date_range": (
            date_range
            if has_data
            else {
                "range_key": selected_range,
                "range_label": DATE_RANGE_OPTIONS.get(
                    selected_range,
                    "All Data",
                ),
                "start_date": None,
                "end_date": None,
                "days": None,
            }
        ),
    }

    return render(
        request,
        "analytics/financial_intelligence.html",
        context,
    )

@login_required
def marketing_intelligence(request):
    datasets = Dataset.objects.filter(
        owner=request.user
    ).order_by("-uploaded_at")

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    total_marketing_spend = 0
    total_revenue = 0
    marketing_roi = 0
    marketing_roas = 0

    current_period_spend = 0
    previous_period_spend = 0
    spend_change = 0

    current_period_revenue = 0
    previous_period_revenue = 0
    revenue_change = 0

    comparison_available = False

    peak_period = "-"
    lowest_period = "-"

    campaign_rows = []
    marketing_insights = []

    marketing_labels = []
    marketing_spend_values = []
    marketing_revenue_values = []

    channel_labels = []
    channel_spend_values = []
    channel_revenue_values = []

    campaign_column = ""
    spend_column = ""
    revenue_column = ""
    channel_column = ""
    date_column = ""

    selected_range = request.GET.get("range", "all")
    custom_start = request.GET.get("start", "")
    custom_end = request.GET.get("end", "")

    if selected_range not in DATE_RANGE_OPTIONS and selected_range != "custom":
        selected_range = "all"

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        selected_dataset = datasets.filter(
            id=dataset_id
        ).first()
    else:
        selected_dataset = datasets.first()

    try:
        if not selected_dataset:
            raise ValueError(
                "No dataset is available. Please upload a dataset first."
            )

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

        if not selected_version:
            raise ValueError(
                "No cleaned dataset is available for analysis."
            )

        file_path = selected_version.file.path

        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)

        elif file_path.lower().endswith(
            (".xlsx", ".xls")
        ):
            df = pd.read_excel(file_path)

        else:
            raise ValueError(
                "Unsupported file format."
            )

        if df.empty:
            raise ValueError(
                "The selected dataset contains no records."
            )

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        def find_column(candidates):
            normalized = {
                str(column).strip().lower(): column
                for column in df.columns
            }

            # Exact match
            for candidate in candidates:
                candidate_lower = candidate.lower()

                if candidate_lower in normalized:
                    return normalized[candidate_lower]

            # Partial match
            for column in df.columns:
                column_lower = str(column).lower()

                for candidate in candidates:
                    if candidate.lower() in column_lower:
                        return column

            return None

        # -------------------------------------------------
        # Detect columns
        # -------------------------------------------------

        date_column = find_column([
            "date",
            "order_date",
            "transaction_date",
            "campaign_date",
            "marketing_date",
            "created_at",
        ])

        spend_column = find_column([
            "marketing_spend",
            "marketing_expense",
            "ad_spend",
            "advertising_spend",
            "campaign_spend",
            "marketing_cost",
            "advertising_cost",
            "campaign_cost",
            "marketing_expense",
            "ad_cost",
        ])

        revenue_column = find_column([
            "revenue",
            "sales",
            "sale",
            "total_sales",
            "total_revenue",
            "net_sales",
            "order_value",
            "sales_amount",
        ])

        campaign_column = find_column([
            "campaign",
            "campaign_name",
            "campaign_id",
            "marketing_campaign",
        ])

        channel_column = find_column([
            "channel",
            "marketing_channel",
            "campaign_channel",
            "ad_channel",
            "source",
            "medium",
        ])

        if not spend_column:
            raise ValueError(
                "Marketing spend column was not found. "
                "Expected columns such as marketing_spend, "
                "ad_spend, campaign_spend or marketing_cost."
            )

        if not revenue_column:
            raise ValueError(
                "Revenue/Sales column was not found."
            )

        if not date_column:
            raise ValueError(
                "Date column was not found."
            )

        # -------------------------------------------------
        # Preserve original cleaned data
        # -------------------------------------------------

        df[date_column] = pd.to_datetime(
            df[date_column],
            errors="coerce",
        )

        df[spend_column] = pd.to_numeric(
            df[spend_column],
            errors="coerce",
        )

        df[revenue_column] = pd.to_numeric(
            df[revenue_column],
            errors="coerce",
        )

        df = df.dropna(
            subset=[
                date_column,
                spend_column,
                revenue_column,
            ]
        )

        if df.empty:
            raise ValueError(
                "No valid marketing records were found."
            )

        df = df.sort_values(date_column)

        df_original = df.copy()

        # -------------------------------------------------
        # Date range
        # -------------------------------------------------

        df, date_range = apply_date_filter(
            df,
            date_column,
            range_key=selected_range,
            start_date=custom_start,
            end_date=custom_end,
        )

        if df.empty:
            raise ValueError(
                "No marketing records exist for "
                "the selected date range."
            )

        # -------------------------------------------------
        # Current period
        # -------------------------------------------------

        total_marketing_spend = float(
            df[spend_column].sum()
        )

        total_revenue = float(
            df[revenue_column].sum()
        )

        marketing_profit = (
            total_revenue -
            total_marketing_spend
        )

        if total_marketing_spend > 0:
            marketing_roi = (
                marketing_profit /
                total_marketing_spend
            ) * 100

            marketing_roas = (
                total_revenue /
                total_marketing_spend
            )
        else:
            marketing_roi = 0
            marketing_roas = 0

        # -------------------------------------------------
        # Previous period comparison
        # -------------------------------------------------

        previous_df = get_previous_period(
            df_original,
            date_column,
            date_range["start_date"],
            date_range["end_date"],
        )

        if not previous_df.empty:

            previous_period_spend = float(
                previous_df[spend_column].sum()
            )

            previous_period_revenue = float(
                previous_df[revenue_column].sum()
            )

            spend_change = calculate_percentage_change(
                total_marketing_spend,
                previous_period_spend,
            )

            revenue_change = calculate_percentage_change(
                total_revenue,
                previous_period_revenue,
            )

            comparison_available = True

        # -------------------------------------------------
        # Daily marketing trend
        # -------------------------------------------------

        daily = (
            df.groupby(
                df[date_column].dt.date
            )
            .agg({
                spend_column: "sum",
                revenue_column: "sum",
            })
            .reset_index()
        )

        daily.columns = [
            "date",
            "spend",
            "revenue",
        ]

        daily["date"] = daily[
            "date"
        ].astype(str)

        marketing_labels = (
            daily["date"].tolist()
        )

        marketing_spend_values = [
            round(float(value), 2)
            for value in daily["spend"]
        ]

        marketing_revenue_values = [
            round(float(value), 2)
            for value in daily["revenue"]
        ]

        # -------------------------------------------------
        # Campaign analysis
        # -------------------------------------------------

        if campaign_column:

            campaign_df = (
                df.groupby(campaign_column)
                .agg({
                    spend_column: "sum",
                    revenue_column: "sum",
                })
                .reset_index()
            )

            campaign_df.columns = [
                "campaign",
                "spend",
                "revenue",
            ]

            campaign_df["roi"] = np.where(
                campaign_df["spend"] > 0,
                (
                    (
                        campaign_df["revenue"]
                        - campaign_df["spend"]
                    )
                    /
                    campaign_df["spend"]
                ) * 100,
                0,
            )

            campaign_df["roas"] = np.where(
                campaign_df["spend"] > 0,
                campaign_df["revenue"]
                / campaign_df["spend"],
                0,
            )

            median_roi = campaign_df[
                "roi"
            ].median()

            for _, row in campaign_df.iterrows():

                roi = float(row["roi"])

                if roi >= max(
                    100,
                    median_roi,
                ):
                    status = "High Performer"

                elif roi < 0:
                    status = "Loss Making"

                elif roi < 30:
                    status = "Low Performer"

                else:
                    status = "Moderate"

                campaign_rows.append({
                    "campaign": str(
                        row["campaign"]
                    ),
                    "spend": float(
                        row["spend"]
                    ),
                    "revenue": float(
                        row["revenue"]
                    ),
                    "roi": roi,
                    "roas": float(
                        row["roas"]
                    ),
                    "status": status,
                })

            campaign_rows = sorted(
                campaign_rows,
                key=lambda x: x["roi"],
                reverse=True,
            )[:50]

        # -------------------------------------------------
        # Channel analysis
        # -------------------------------------------------

        if channel_column:

            channel_df = (
                df.groupby(channel_column)
                .agg({
                    spend_column: "sum",
                    revenue_column: "sum",
                })
                .reset_index()
            )

            channel_df.columns = [
                "channel",
                "spend",
                "revenue",
            ]

            channel_df = channel_df.sort_values(
                "revenue",
                ascending=False,
            )

            channel_labels = [
                str(value)
                for value in channel_df["channel"]
            ]

            channel_spend_values = [
                round(float(value), 2)
                for value in channel_df["spend"]
            ]

            channel_revenue_values = [
                round(float(value), 2)
                for value in channel_df["revenue"]
            ]

        # -------------------------------------------------
        # Monthly performance
        # -------------------------------------------------

        monthly = (
            df.assign(
                month=df[date_column]
                .dt.to_period("M")
                .astype(str)
            )
            .groupby("month")
            .agg({
                spend_column: "sum",
                revenue_column: "sum",
            })
            .reset_index()
        )

        monthly["profit"] = (
            monthly[revenue_column]
            - monthly[spend_column]
        )

        if not monthly.empty:

            peak_row = monthly.loc[
                monthly["profit"].idxmax()
            ]

            lowest_row = monthly.loc[
                monthly["profit"].idxmin()
            ]

            peak_period = (
                peak_row["month"]
            )

            lowest_period = (
                lowest_row["month"]
            )

        # -------------------------------------------------
        # Automatic insights
        # -------------------------------------------------

        if marketing_roi > 100:
            marketing_insights.append(
                f"Marketing generated a strong "
                f"overall ROI of "
                f"{marketing_roi:.1f}%."
            )

        elif marketing_roi < 0:
            marketing_insights.append(
                "Marketing spend is currently "
                "higher than the revenue generated."
            )

        else:
            marketing_insights.append(
                f"Marketing ROI is "
                f"{marketing_roi:.1f}%, indicating "
                f"positive campaign contribution."
            )

        if spend_change > 20:
            marketing_insights.append(
                f"Marketing spend increased by "
                f"{spend_change:.1f}% versus the "
                f"previous comparable period."
            )

        if revenue_change > spend_change:
            marketing_insights.append(
                "Revenue is growing faster than "
                "marketing spend, indicating improving "
                "marketing efficiency."
            )

        elif spend_change > revenue_change:
            marketing_insights.append(
                "Marketing spend is growing faster "
                "than revenue. Campaign efficiency "
                "should be reviewed."
            )

        if campaign_rows:

            best_campaign = campaign_rows[0]

            marketing_insights.append(
                f"Top campaign by ROI is "
                f"{best_campaign['campaign']} "
                f"with {best_campaign['roi']:.1f}% ROI."
            )

            loss_campaigns = [
                row for row in campaign_rows
                if row["roi"] < 0
            ]

            if loss_campaigns:
                marketing_insights.append(
                    f"{len(loss_campaigns)} campaign(s) "
                    f"are currently loss making."
                )

        has_data = True

    except Exception as exc:
        error_message = str(exc)

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "selected_version": selected_version,

        "has_data": has_data,
        "error_message": error_message,

        "total_marketing_spend":
            total_marketing_spend,

        "total_revenue":
            total_revenue,

        "marketing_roi":
            marketing_roi,

        "marketing_roas":
            marketing_roas,

        "comparison_available":
            comparison_available,

        "current_period_spend":
            total_marketing_spend,

        "previous_period_spend":
            previous_period_spend,

        "spend_change":
            spend_change,

        "current_period_revenue":
            total_revenue,

        "previous_period_revenue":
            previous_period_revenue,

        "revenue_change":
            revenue_change,

        "peak_period":
            peak_period,

        "lowest_period":
            lowest_period,

        "campaign_rows":
            campaign_rows,

        "marketing_insights":
            marketing_insights,

        "marketing_labels":
            json.dumps(marketing_labels),

        "marketing_spend_values":
            json.dumps(marketing_spend_values),

        "marketing_revenue_values":
            json.dumps(marketing_revenue_values),

        "channel_labels":
            json.dumps(channel_labels),

        "channel_spend_values":
            json.dumps(channel_spend_values),

        "channel_revenue_values":
            json.dumps(channel_revenue_values),

        "campaign_column":
            campaign_column or "",

        "spend_column":
            spend_column or "",

        "revenue_column":
            revenue_column or "",

        "channel_column":
            channel_column or "",

        "date_column":
            date_column or "",

        "date_range_options":
            DATE_RANGE_OPTIONS,

        "selected_range":
            selected_range,

        "custom_start":
            custom_start,

        "custom_end":
            custom_end,

        "date_range":
            date_range if has_data else {
                "range_key": selected_range,
                "range_label": DATE_RANGE_OPTIONS.get(
                    selected_range,
                    "All Data",
                ),
                "start_date": None,
                "end_date": None,
                "days": None,
            },
    }

    return render(
        request,
        "analytics/marketing_intelligence.html",
        context,
    )

@login_required
def returns_intelligence(request):
    datasets = Dataset.objects.filter(
        owner=request.user
    ).order_by("-uploaded_at")

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    total_returns = 0
    total_revenue = 0
    returned_revenue = 0
    return_rate = 0

    current_period_returns = 0
    previous_period_returns = 0
    returns_change = 0

    current_period_revenue = 0
    previous_period_revenue = 0
    revenue_change = 0

    comparison_available = False

    return_rows = []
    product_return_rows = []
    regional_return_rows = []
    return_insights = []

    trend_labels = []
    trend_values = []

    product_labels = []
    product_return_values = []

    region_labels = []
    region_return_values = []

    date_column = ""
    returns_column = ""
    revenue_column = ""
    product_column = ""
    region_column = ""

    selected_range = request.GET.get("range", "all")
    custom_start = request.GET.get("start", "")
    custom_end = request.GET.get("end", "")

    if selected_range not in DATE_RANGE_OPTIONS and selected_range != "custom":
        selected_range = "all"

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        selected_dataset = datasets.filter(
            id=dataset_id
        ).first()
    else:
        selected_dataset = datasets.first()

    try:
        if not selected_dataset:
            raise ValueError(
                "No dataset is available. Please upload a dataset first."
            )

        # -----------------------------------------
        # Get cleaned dataset
        # -----------------------------------------

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

        if not selected_version:
            raise ValueError(
                "No cleaned dataset is available for analysis."
            )

        file_path = selected_version.file.path

        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)

        elif file_path.lower().endswith(
            (".xlsx", ".xls")
        ):
            df = pd.read_excel(file_path)

        else:
            raise ValueError(
                "Unsupported file format."
            )

        if df.empty:
            raise ValueError(
                "The selected dataset contains no records."
            )

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        # -----------------------------------------
        # Column detector
        # -----------------------------------------

        def find_column(candidates):

            normalized = {
                str(column).strip().lower(): column
                for column in df.columns
            }

            # Exact match
            for candidate in candidates:

                if candidate.lower() in normalized:
                    return normalized[
                        candidate.lower()
                    ]

            # Partial match
            for column in df.columns:

                column_lower = str(
                    column
                ).lower()

                for candidate in candidates:

                    if candidate.lower() in column_lower:
                        return column

            return None

        date_column = find_column([
            "date",
            "order_date",
            "transaction_date",
            "return_date",
            "created_at",
        ])

        returns_column = find_column([
            "returns",
            "return",
            "returned",
            "return_count",
            "returned_quantity",
            "refund_count",
        ])

        revenue_column = find_column([
            "revenue",
            "sales",
            "sale",
            "total_sales",
            "total_revenue",
            "net_sales",
            "order_value",
        ])

        product_column = find_column([
            "product",
            "product_name",
            "product_id",
            "item",
            "item_name",
        ])

        region_column = find_column([
            "region",
            "region_name",
            "area",
            "territory",
            "location",
        ])

        if not returns_column:
            raise ValueError(
                "Returns column was not found. "
                "Expected columns such as returns, "
                "return_count or returned_quantity."
            )

        if not date_column:
            raise ValueError(
                "Date column was not found."
            )

        # -----------------------------------------
        # Clean numeric/date data
        # -----------------------------------------

        df[date_column] = pd.to_datetime(
            df[date_column],
            errors="coerce",
        )

        df[returns_column] = pd.to_numeric(
            df[returns_column],
            errors="coerce",
        )

        if revenue_column:
            df[revenue_column] = pd.to_numeric(
                df[revenue_column],
                errors="coerce",
            )

        df = df.dropna(
            subset=[
                date_column,
                returns_column,
            ]
        )

        if df.empty:
            raise ValueError(
                "No valid return records were found."
            )

        df = df.sort_values(
            date_column
        )

        # Keep complete cleaned dataset
        df_original = df.copy()

        # -----------------------------------------
        # Date filter
        # -----------------------------------------

        df, date_range = apply_date_filter(
            df,
            date_column,
            range_key=selected_range,
            start_date=custom_start,
            end_date=custom_end,
        )

        if df.empty:
            raise ValueError(
                "No return records exist for "
                "the selected date range."
            )

        # -----------------------------------------
        # Overall return metrics
        # -----------------------------------------

        total_returns = int(
            df[returns_column].sum()
        )

        if revenue_column:

            total_revenue = float(
                df[revenue_column].sum()
            )

            # Approximate returned revenue
            # using return proportion where
            # return quantity exists.
            total_units = len(df)

            if total_units > 0:
                returned_revenue = (
                    total_revenue
                    *
                    min(
                        total_returns / total_units,
                        1
                    )
                )

            return_rate = (
                total_returns
                /
                total_units
            ) * 100 if total_units else 0

        else:

            total_revenue = 0
            returned_revenue = 0

            total_records = len(df)

            return_rate = (
                total_returns
                /
                total_records
            ) * 100 if total_records else 0

        # -----------------------------------------
        # Previous period
        # -----------------------------------------

        current_period_returns = total_returns
        current_period_revenue = total_revenue

        previous_df = get_previous_period(
            df_original,
            date_column,
            date_range["start_date"],
            date_range["end_date"],
        )

        if not previous_df.empty:

            previous_period_returns = int(
                previous_df[
                    returns_column
                ].sum()
            )

            if revenue_column:
                previous_period_revenue = float(
                    previous_df[
                        revenue_column
                    ].sum()
                )

            returns_change = calculate_percentage_change(
                current_period_returns,
                previous_period_returns,
            )

            revenue_change = calculate_percentage_change(
                current_period_revenue,
                previous_period_revenue,
            )

            comparison_available = True

        # -----------------------------------------
        # Daily return trend
        # -----------------------------------------

        daily = (
            df.groupby(
                df[date_column].dt.date
            )[returns_column]
            .sum()
            .reset_index()
        )

        daily.columns = [
            "date",
            "returns",
        ]

        trend_labels = [
            str(value)
            for value in daily["date"]
        ]

        trend_values = [
            int(value)
            for value in daily["returns"]
        ]

        # -----------------------------------------
        # Product return analysis
        # -----------------------------------------

        if product_column:

            product_df = (
                df.groupby(product_column)
                .agg({
                    returns_column: "sum",
                })
                .reset_index()
            )

            product_df.columns = [
                "product",
                "returns",
            ]

            product_df = product_df.sort_values(
                "returns",
                ascending=False,
            )

            product_labels = [
                str(value)
                for value in product_df.head(15)["product"]
            ]

            product_return_values = [
                int(value)
                for value in product_df.head(15)["returns"]
            ]

            for _, row in product_df.head(50).iterrows():

                returns = int(
                    row["returns"]
                )

                if returns >= max(
                    5,
                    product_df["returns"].median()
                ):
                    status = "High Return Risk"

                else:
                    status = "Normal"

                product_return_rows.append({
                    "product": str(
                        row["product"]
                    ),
                    "returns": returns,
                    "status": status,
                })

        # -----------------------------------------
        # Regional return analysis
        # -----------------------------------------

        if region_column:

            region_df = (
                df.groupby(region_column)
                .agg({
                    returns_column: "sum",
                })
                .reset_index()
            )

            region_df.columns = [
                "region",
                "returns",
            ]

            region_df = region_df.sort_values(
                "returns",
                ascending=False,
            )

            region_labels = [
                str(value)
                for value in region_df["region"]
            ]

            region_return_values = [
                int(value)
                for value in region_df["returns"]
            ]

            for _, row in region_df.iterrows():

                regional_return_rows.append({
                    "region": str(
                        row["region"]
                    ),
                    "returns": int(
                        row["returns"]
                    ),
                })

        # -----------------------------------------
        # Return status
        # -----------------------------------------

        if return_rate >= 10:

            overall_status = "Critical"

        elif return_rate >= 5:

            overall_status = "High Risk"

        elif return_rate >= 2:

            overall_status = "Moderate"

        else:

            overall_status = "Healthy"

        # -----------------------------------------
        # Insights
        # -----------------------------------------

        if return_rate >= 10:

            return_insights.append(
                f"Return rate is {return_rate:.1f}%, "
                "which requires immediate investigation."
            )

        elif return_rate >= 5:

            return_insights.append(
                f"Return rate is {return_rate:.1f}%. "
                "Review high-return products and regions."
            )

        else:

            return_insights.append(
                f"Return rate is {return_rate:.1f}%, "
                "indicating relatively controlled returns."
            )

        if returns_change > 20:

            return_insights.append(
                f"Returns increased by "
                f"{returns_change:.1f}% "
                "versus the previous comparable period."
            )

        elif returns_change < -10:

            return_insights.append(
                f"Returns decreased by "
                f"{abs(returns_change):.1f}%, "
                "indicating improving return performance."
            )

        if product_return_rows:

            highest_product = (
                product_return_rows[0]
            )

            return_insights.append(
                f"{highest_product['product']} "
                f"has the highest number of returns "
                f"with {highest_product['returns']}."
            )

        if region_labels:

            highest_region = (
                regional_return_rows[0]
            )

            return_insights.append(
                f"{highest_region['region']} "
                f"has the highest return volume "
                f"with {highest_region['returns']}."
            )

        if revenue_column and returned_revenue > 0:

            return_insights.append(
                f"Estimated revenue affected by "
                f"returns is approximately "
                f"₹{returned_revenue:,.0f}."
            )

        has_data = True

    except Exception as exc:

        error_message = str(exc)

    context = {

        "datasets": datasets,

        "selected_dataset":
            selected_dataset,

        "selected_version":
            selected_version,

        "has_data":
            has_data,

        "error_message":
            error_message,

        "total_returns":
            total_returns,

        "total_revenue":
            total_revenue,

        "returned_revenue":
            returned_revenue,

        "return_rate":
            return_rate,

        "overall_status":
            locals().get(
                "overall_status",
                "Unknown"
            ),

        "comparison_available":
            comparison_available,

        "current_period_returns":
            current_period_returns,

        "previous_period_returns":
            previous_period_returns,

        "returns_change":
            returns_change,

        "current_period_revenue":
            current_period_revenue,

        "previous_period_revenue":
            previous_period_revenue,

        "revenue_change":
            revenue_change,

        "product_return_rows":
            product_return_rows,

        "regional_return_rows":
            regional_return_rows,

        "return_insights":
            return_insights,

        "trend_labels":
            json.dumps(trend_labels),

        "trend_values":
            json.dumps(trend_values),

        "product_labels":
            json.dumps(product_labels),

        "product_return_values":
            json.dumps(product_return_values),

        "region_labels":
            json.dumps(region_labels),

        "region_return_values":
            json.dumps(region_return_values),

        "date_column":
            date_column or "",

        "returns_column":
            returns_column or "",

        "revenue_column":
            revenue_column or "",

        "product_column":
            product_column or "",

        "region_column":
            region_column or "",

        "date_range_options":
            DATE_RANGE_OPTIONS,

        "selected_range":
            selected_range,

        "custom_start":
            custom_start,

        "custom_end":
            custom_end,

        "date_range":
            date_range if has_data else {
                "range_key": selected_range,
                "range_label": DATE_RANGE_OPTIONS.get(
                    selected_range,
                    "All Data",
                ),
                "start_date": None,
                "end_date": None,
                "days": None,
            },
    }

    return render(
        request,
        "analytics/returns_intelligence.html",
        context,
    )