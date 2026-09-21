from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    return render(request, "core/home.html")


def about(request):
    return render(request, "core/about.html")


def how_it_works(request):
    return render(request, "core/how_it_works.html")


def contact(request):
    return render(request, "core/contact.html")

def features(request):
    return render(request,"core/feature.html")


from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from data_management.models import Dataset, DatasetVersion

import pandas as pd
import numpy as np


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return default

        return value
    except (TypeError, ValueError):
        return default


def detect_column(df, candidates):
    """
    Detect a column using common business-data column names.
    """

    if df is None or df.empty:
        return None

    columns = list(df.columns)

    normalized = {
        str(column).strip().lower().replace(" ", "_"): column
        for column in columns
    }

    # Exact normalized match
    for candidate in candidates:
        key = candidate.strip().lower().replace(" ", "_")

        if key in normalized:
            return normalized[key]

    # Partial match
    for candidate in candidates:
        candidate_key = candidate.strip().lower().replace(" ", "_")

        for normalized_name, original_name in normalized.items():

            if candidate_key in normalized_name:
                return original_name

    return None


def load_dataset_dataframe(dataset):
    """
    Load the current cleaned dataset when available.
    Falls back to the original uploaded dataset.
    """

    if dataset is None:
        return pd.DataFrame(), "none"

    # --------------------------------------------------------
    # Prefer current DatasetVersion
    # --------------------------------------------------------

    current_version = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            is_current=True,
        )
        .order_by("-version_number")
        .first()
    )

    if current_version and current_version.file:
        try:
            file_path = current_version.file.path
            filename = current_version.file.name.lower()

            if filename.endswith(".csv"):
                df = pd.read_csv(file_path)

            elif filename.endswith(".xlsx"):
                df = pd.read_excel(file_path)

            elif filename.endswith(".xls"):
                df = pd.read_excel(file_path)

            else:
                df = pd.DataFrame()

            return df, "cleaned"

        except Exception:
            pass

    # --------------------------------------------------------
    # Fall back to original dataset
    # --------------------------------------------------------

    if dataset.file:

        try:
            file_path = dataset.file.path
            filename = dataset.file.name.lower()

            if filename.endswith(".csv"):
                df = pd.read_csv(file_path)

            elif filename.endswith(".xlsx"):
                df = pd.read_excel(file_path)

            elif filename.endswith(".xls"):
                df = pd.read_excel(file_path)

            else:
                df = pd.DataFrame()

            return df, "original"

        except Exception:
            pass

    return pd.DataFrame(), "none"


def calculate_business_health(
    revenue_growth=0,
    profit_margin=0,
    customer_growth=0,
    return_rate=0,
):
    """
    Business Health Score out of 100.

    This is a dashboard-level composite score.
    """

    growth_score = min(max(50 + revenue_growth, 0), 100)

    margin_score = min(
        max(profit_margin * 2, 0),
        100,
    )

    customer_score = min(
        max(50 + customer_growth, 0),
        100,
    )

    return_score = min(
        max(100 - (return_rate * 2), 0),
        100,
    )

    score = (
        growth_score * 0.30
        + margin_score * 0.30
        + customer_score * 0.20
        + return_score * 0.20
    )

    return round(min(max(score, 0), 100), 1)


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

@login_required
def dashboard(request):

    # ========================================================
    # DATASETS
    # ========================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None

    dataset_id = request.GET.get("dataset")

    if dataset_id:

        selected_dataset = (
            datasets
            .filter(id=dataset_id)
            .first()
        )

    if selected_dataset is None:
        selected_dataset = datasets.first()

    # ========================================================
    # DEFAULT DASHBOARD VALUES
    # ========================================================

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,

        "has_data": False,

        "data_source": "none",

        "total_revenue": 0,
        "profit_margin": 0,
        "revenue_growth": 0,
        "customer_count": 0,
        "business_health": 0,

        "total_orders": 0,
        "total_units": 0,
        "total_returns": 0,
        "return_rate": 0,

        "revenue_chart_labels": [],
        "revenue_chart_values": [],

        "customer_chart_labels": [],
        "customer_chart_values": [],

        "top_products": [],
        "top_regions": [],

        "rows": 0,
        "columns": 0,

        "missing_values": 0,
        "duplicate_rows": 0,
        "quality_score": 0,

        "readiness_uploaded": False,
        "readiness_cleaned": False,
        "readiness_analyzed": False,
        "readiness_decision": False,

        "active_readiness": 0,
    }

    # ========================================================
    # NO DATASET
    # ========================================================

    if selected_dataset is None:
        return render(
            request,
            "dashboard/dashboard.html",
            context,
        )

    # ========================================================
    # LOAD DATA
    # ========================================================

    df, data_source = load_dataset_dataframe(
        selected_dataset
    )

    context["data_source"] = data_source

    if df.empty:
        return render(
            request,
            "dashboard/dashboard.html",
            context,
        )

    # ========================================================
    # BASIC DATA INFORMATION
    # ========================================================

    context["has_data"] = True

    context["rows"] = int(len(df))

    context["columns"] = int(len(df.columns))

    context["missing_values"] = int(
        df.isna().sum().sum()
    )

    context["duplicate_rows"] = int(
        df.duplicated().sum()
    )

    total_cells = len(df) * len(df.columns)

    if total_cells > 0:

        missing_ratio = (
            context["missing_values"]
            / total_cells
        )

        duplicate_ratio = (
            context["duplicate_rows"]
            / len(df)
        )

        quality = (
            100
            - (missing_ratio * 60)
            - (duplicate_ratio * 40)
        )

        context["quality_score"] = round(
            min(max(quality, 0), 100),
            1,
        )

    # ========================================================
    # COLUMN DETECTION
    # ========================================================

    date_column = detect_column(
        df,
        [
            "date",
            "order_date",
            "sales_date",
            "transaction_date",
            "invoice_date",
            "created_at",
        ],
    )

    revenue_column = detect_column(
        df,
        [
            "revenue",
            "sales",
            "sales_amount",
            "total_sales",
            "amount",
            "total_amount",
            "order_value",
        ],
    )

    profit_column = detect_column(
        df,
        [
            "profit",
            "net_profit",
            "gross_profit",
            "profit_amount",
        ],
    )

    cost_column = detect_column(
        df,
        [
            "cost",
            "total_cost",
            "expense",
            "expenses",
            "cost_amount",
        ],
    )

    quantity_column = detect_column(
        df,
        [
            "quantity",
            "qty",
            "units",
            "units_sold",
        ],
    )

    customer_column = detect_column(
        df,
        [
            "customer_id",
            "customer",
            "customer_name",
            "client_id",
        ],
    )

    order_column = detect_column(
        df,
        [
            "order_id",
            "order",
            "transaction_id",
            "invoice_id",
        ],
    )

    return_column = detect_column(
        df,
        [
            "return",
            "returns",
            "return_id",
            "returned",
            "return_quantity",
        ],
    )

    product_column = detect_column(
        df,
        [
            "product",
            "product_name",
            "product_id",
            "item",
        ],
    )

    region_column = detect_column(
        df,
        [
            "region",
            "area",
            "location",
            "state",
            "city",
        ],
    )

    # ========================================================
    # NUMERIC CONVERSION
    # ========================================================

    if revenue_column:

        df[revenue_column] = pd.to_numeric(
            df[revenue_column],
            errors="coerce",
        ).fillna(0)

    if profit_column:

        df[profit_column] = pd.to_numeric(
            df[profit_column],
            errors="coerce",
        ).fillna(0)

    if cost_column:

        df[cost_column] = pd.to_numeric(
            df[cost_column],
            errors="coerce",
        ).fillna(0)

    if quantity_column:

        df[quantity_column] = pd.to_numeric(
            df[quantity_column],
            errors="coerce",
        ).fillna(0)

    # ========================================================
    # TOTAL REVENUE
    # ========================================================

    total_revenue = 0

    if revenue_column:

        total_revenue = safe_float(
            df[revenue_column].sum()
        )

    context["total_revenue"] = total_revenue

    # ========================================================
    # PROFIT
    # ========================================================

    total_profit = 0

    if profit_column:

        total_profit = safe_float(
            df[profit_column].sum()
        )

    elif revenue_column and cost_column:

        total_profit = (
            total_revenue
            - safe_float(
                df[cost_column].sum()
            )
        )

    if total_revenue > 0:

        profit_margin = (
            total_profit
            / total_revenue
        ) * 100

    else:

        profit_margin = 0

    context["profit_margin"] = round(
        profit_margin,
        1,
    )

    # ========================================================
    # CUSTOMERS
    # ========================================================

    if customer_column:

        customer_count = int(
            df[customer_column]
            .nunique()
        )

    else:

        customer_count = 0

    context["customer_count"] = customer_count

    # ========================================================
    # ORDERS
    # ========================================================

    if order_column:

        total_orders = int(
            df[order_column]
            .nunique()
        )

    else:

        total_orders = int(len(df))

    context["total_orders"] = total_orders

    # ========================================================
    # UNITS
    # ========================================================

    if quantity_column:

        context["total_units"] = safe_float(
            df[quantity_column].sum()
        )

    # ========================================================
    # RETURNS
    # ========================================================

    if return_column:

        if pd.api.types.is_numeric_dtype(
            df[return_column]
        ):

            total_returns = safe_float(
                df[return_column].sum()
            )

        else:

            return_values = (
                df[return_column]
                .astype(str)
                .str.lower()
                .isin(
                    [
                        "yes",
                        "true",
                        "returned",
                        "1",
                    ]
                )
            )

            total_returns = int(
                return_values.sum()
            )

    else:

        total_returns = 0

    context["total_returns"] = total_returns

    if total_orders > 0:

        return_rate = (
            total_returns
            / total_orders
        ) * 100

    else:

        return_rate = 0

    context["return_rate"] = round(
        return_rate,
        1,
    )

    # ========================================================
    # REVENUE GROWTH
    # ========================================================

    revenue_growth = 0

    if date_column and revenue_column:

        working = df.copy()

        working[date_column] = pd.to_datetime(
            working[date_column],
            errors="coerce",
        )

        working = working.dropna(
            subset=[date_column]
        )

        if not working.empty:

            working["__revenue__"] = (
                working[revenue_column]
            )

            daily = (
                working
                .groupby(
                    working[date_column].dt.date
                )["__revenue__"]
                .sum()
                .sort_index()
            )

            if len(daily) >= 2:

                midpoint = len(daily) // 2

                previous = safe_float(
                    daily.iloc[:midpoint].sum()
                )

                current = safe_float(
                    daily.iloc[midpoint:].sum()
                )

                if previous != 0:

                    revenue_growth = (
                        (current - previous)
                        / abs(previous)
                    ) * 100

    context["revenue_growth"] = round(
        revenue_growth,
        1,
    )

    # ========================================================
    # REVENUE TREND
    # ========================================================

    if date_column and revenue_column:

        chart_df = df.copy()

        chart_df[date_column] = pd.to_datetime(
            chart_df[date_column],
            errors="coerce",
        )

        chart_df = chart_df.dropna(
            subset=[date_column]
        )

        if not chart_df.empty:

            chart_df["__revenue__"] = (
                chart_df[revenue_column]
            )

            monthly = (
                chart_df
                .groupby(
                    chart_df[date_column]
                    .dt.to_period("M")
                )["__revenue__"]
                .sum()
                .sort_index()
            )

            context["revenue_chart_labels"] = [
                str(period)
                for period in monthly.index
            ]

            context["revenue_chart_values"] = [
                round(
                    safe_float(value),
                    2,
                )
                for value in monthly.values
            ]

    # ========================================================
    # CUSTOMER TREND
    # ========================================================

    if date_column and customer_column:

        customer_df = df.copy()

        customer_df[date_column] = pd.to_datetime(
            customer_df[date_column],
            errors="coerce",
        )

        customer_df = customer_df.dropna(
            subset=[date_column]
        )

        if not customer_df.empty:

            monthly_customers = (
                customer_df
                .groupby(
                    customer_df[date_column]
                    .dt.to_period("M")
                )[customer_column]
                .nunique()
            )

            context["customer_chart_labels"] = [
                str(period)
                for period in monthly_customers.index
            ]

            context["customer_chart_values"] = [
                int(value)
                for value in monthly_customers.values
            ]

    # ========================================================
    # TOP PRODUCTS
    # ========================================================

    if product_column and revenue_column:

        product_data = (
            df.groupby(product_column)[
                revenue_column
            ]
            .sum()
            .sort_values(
                ascending=False
            )
            .head(5)
        )

        context["top_products"] = [
            {
                "name": str(name),
                "revenue": round(
                    safe_float(value),
                    2,
                ),
            }
            for name, value
            in product_data.items()
        ]

    # ========================================================
    # TOP REGIONS
    # ========================================================

    if region_column and revenue_column:

        region_data = (
            df.groupby(region_column)[
                revenue_column
            ]
            .sum()
            .sort_values(
                ascending=False
            )
            .head(5)
        )

        context["top_regions"] = [
            {
                "name": str(name),
                "revenue": round(
                    safe_float(value),
                    2,
                ),
            }
            for name, value
            in region_data.items()
        ]

    # ========================================================
    # BUSINESS HEALTH
    # ========================================================

    customer_growth = 0

    if (
        date_column
        and customer_column
    ):

        if len(context["customer_chart_values"]) >= 2:

            values = context[
                "customer_chart_values"
            ]

            midpoint = len(values) // 2

            previous_customers = sum(
                values[:midpoint]
            )

            current_customers = sum(
                values[midpoint:]
            )

            if previous_customers:

                customer_growth = (
                    (
                        current_customers
                        - previous_customers
                    )
                    / previous_customers
                ) * 100

    health_score = calculate_business_health(
        revenue_growth=revenue_growth,
        profit_margin=profit_margin,
        customer_growth=customer_growth,
        return_rate=return_rate,
    )

    context["business_health"] = health_score

    # ========================================================
    # PLATFORM READINESS
    # ========================================================

    readiness_uploaded = True

    readiness_cleaned = (
        data_source == "cleaned"
        or DatasetVersion.objects.filter(
            dataset=selected_dataset,
            version_type__in=[
                "Cleaned",
                "Validated",
                "Transformed",
            ],
        ).exists()
    )

    readiness_analyzed = bool(
        revenue_column
        or customer_column
        or product_column
    )

    readiness_decision = (
        readiness_analyzed
        and health_score > 0
    )

    context["readiness_uploaded"] = (
        readiness_uploaded
    )

    context["readiness_cleaned"] = (
        readiness_cleaned
    )

    context["readiness_analyzed"] = (
        readiness_analyzed
    )

    context["readiness_decision"] = (
        readiness_decision
    )

    context["active_readiness"] = sum(
        [
            readiness_uploaded,
            readiness_cleaned,
            readiness_analyzed,
            readiness_decision,
        ]
    )

    return render(
        request,
        "dashboard/dashboard.html",
        context,
    )