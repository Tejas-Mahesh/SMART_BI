import json

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from data_management.models import Dataset, DatasetVersion

from advanced_insights.services.forecasting import (
    detect_column as forecast_detect_column,
    prepare_time_series,
    calculate_trend,
    forecast_series,
    calculate_forecast_summary,
)

from advanced_insights.services.anomaly_detection import (
    detect_column as anomaly_detect_column,
    prepare_daily_series,
    detect_anomalies,
    calculate_anomaly_summary,
)

from advanced_insights.services.root_cause import (
    detect_column as root_detect_column,
    prepare_data as prepare_root_data,
    calculate_periods as calculate_root_periods,
    calculate_percentage_change as root_percentage_change,
    find_root_causes,
)

from advanced_insights.services.customer_risk import (
    detect_column as risk_detect_column,
    run_customer_risk_analysis,
)

from advanced_insights.services.opportunity_detection import (
    detect_column as opportunity_detect_column,
    run_opportunity_detection,
)

from .services.decision_analyzer import (
    build_decision_recommendations,
)


# ============================================================
# DATASET HELPERS
# ============================================================

ALLOWED_RECOMMENDATION_CATEGORIES = {
    "sales",
    "products",
    "customers",
    "regional",
    "marketing",
}


def get_recommendation_datasets(user):

    datasets = (
        Dataset.objects
        .filter(
            owner=user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    return [
        dataset
        for dataset in datasets
        if str(
            dataset.dataset_type
        ).strip().lower()
        in ALLOWED_RECOMMENDATION_CATEGORIES
    ]


def get_cleaned_dataset_file(dataset):

    if not dataset:
        return None

    # --------------------------------------------------------
    # Prefer latest cleaned version
    # --------------------------------------------------------

    cleaned_version = (
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

    if cleaned_version and cleaned_version.file:
        return cleaned_version.file

    # --------------------------------------------------------
    # Current version fallback
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

    if current_version and current_version.file:
        return current_version.file

    # --------------------------------------------------------
    # Original dataset fallback
    # --------------------------------------------------------

    if dataset.file:
        return dataset.file

    return None


def load_dataset(dataset):

    file_field = get_cleaned_dataset_file(
        dataset
    )

    if not file_field:
        raise ValueError(
            "No dataset file is available."
        )

    file_path = file_field.path

    file_name = str(
        file_field.name
    ).lower()

    if file_name.endswith(".csv"):

        df = pd.read_csv(
            file_path
        )

    elif (
        file_name.endswith(".xlsx")
        or file_name.endswith(".xls")
    ):

        df = pd.read_excel(
            file_path
        )

    else:

        raise ValueError(
            "Unsupported dataset format. "
            "Use CSV or Excel."
        )

    if df is None or df.empty:

        raise ValueError(
            "The selected dataset is empty."
        )

    # Clean column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ============================================================
# COLUMN DETECTION
# ============================================================

DATE_CANDIDATES = [
    "date",
    "order_date",
    "sale_date",
    "sales_date",
    "transaction_date",
    "purchase_date",
    "created_at",
]

SALES_CANDIDATES = [
    "sales",
    "sale",
    "revenue",
    "amount",
    "total_sales",
    "total_revenue",
    "order_value",
    "net_sales",
]

QUANTITY_CANDIDATES = [
    "quantity",
    "qty",
    "units",
    "units_sold",
    "order_quantity",
    "total_quantity",
]

CUSTOMER_CANDIDATES = [
    "customer",
    "customer_id",
    "customer_name",
    "client",
    "client_id",
    "user_id",
]

PRODUCT_CANDIDATES = [
    "product",
    "product_id",
    "product_name",
    "item",
    "item_name",
    "sku",
]

REGION_CANDIDATES = [
    "region",
    "state",
    "city",
    "area",
    "territory",
    "zone",
    "market",
]

CAMPAIGN_CANDIDATES = [
    "campaign",
    "campaign_name",
    "campaign_id",
    "marketing_campaign",
]

CHANNEL_CANDIDATES = [
    "channel",
    "marketing_channel",
    "campaign_channel",
    "ad_channel",
    "source",
    "medium",
]


# ============================================================
# CATEGORY DESCRIPTION
# ============================================================

def get_category_description(
    category
):

    descriptions = {

        "Sales": (
            "Sales performance, trends, "
            "forecasting and business drivers."
        ),

        "Products": (
            "Product growth, demand signals "
            "and high-potential products."
        ),

        "Customers": (
            "Customer value, retention risk "
            "and growth opportunities."
        ),

        "Regional": (
            "Regional growth, market performance "
            "and expansion opportunities."
        ),

        "Marketing": (
            "Campaign and channel performance, "
            "ROI and growth opportunities."
        ),
    }

    return descriptions.get(
        category,
        "Business decision intelligence."
    )


# ============================================================
# FORECASTING
# ============================================================

def run_forecast_analysis(
    df
):

    date_column = forecast_detect_column(
        df,
        DATE_CANDIDATES,
    )

    metric_column = forecast_detect_column(
        df,
        SALES_CANDIDATES,
    )

    if not date_column or not metric_column:

        return {
            "summary": {},
            "trend": {},
        }

    series = prepare_time_series(
        df,
        date_column,
        metric_column,
    )

    if series.empty:

        return {
            "summary": {},
            "trend": {},
        }

    trend = calculate_trend(
        series
    )

    forecast_result = forecast_series(
        series,
        periods=30,
    )

    forecast = forecast_result.get(
        "forecast",
        pd.Series(dtype=float),
    )

    summary = calculate_forecast_summary(
        series,
        forecast,
    )

    summary["model"] = forecast_result.get(
        "model",
        "Unavailable",
    )

    summary["confidence"] = forecast_result.get(
        "confidence",
        "Low",
    )

    summary["historical_points"] = len(
        series
    )

    summary["forecast_points"] = len(
        forecast
    )

    return {
        "summary": summary,
        "trend": trend,
    }


# ============================================================
# ANOMALY ANALYSIS
# ============================================================

def run_anomaly_analysis(
    df
):

    date_column = anomaly_detect_column(
        df,
        DATE_CANDIDATES,
    )

    metric_column = anomaly_detect_column(
        df,
        SALES_CANDIDATES,
    )

    if not date_column or not metric_column:

        return {
            "summary": {},
            "anomaly_data": pd.DataFrame(),
        }

    series = prepare_daily_series(
        df,
        date_column,
        metric_column,
    )

    if series.empty:

        return {
            "summary": {},
            "anomaly_data": pd.DataFrame(),
        }

    anomaly_data = detect_anomalies(
        series
    )

    summary = calculate_anomaly_summary(
        series,
        anomaly_data,
    )

    return {
        "summary": summary,
        "anomaly_data": anomaly_data,
    }


# ============================================================
# ROOT CAUSE ANALYSIS
# ============================================================

def run_root_cause_analysis(
    df,
    category,
):

    date_column = root_detect_column(
        df,
        DATE_CANDIDATES,
    )

    metric_column = root_detect_column(
        df,
        SALES_CANDIDATES,
    )

    if not date_column or not metric_column:

        return {
            "results": [],
            "overall_change": 0,
        }

    data = prepare_root_data(
        df,
        date_column,
        metric_column,
    )

    if data.empty:

        return {
            "results": [],
            "overall_change": 0,
        }

    (
        current,
        previous,
        current_start,
        current_end,
        previous_start,
        previous_end,
    ) = calculate_root_periods(
        data,
        date_column,
        period_days=30,
    )

    if current.empty:

        return {
            "results": [],
            "overall_change": 0,
        }

    current_total = current[
        metric_column
    ].sum()

    previous_total = previous[
        metric_column
    ].sum()

    overall_change = (
        current_total
        -
        previous_total
    )

    # --------------------------------------------------------
    # Category-specific dimensions
    # --------------------------------------------------------

    dimensions = []

    category_lower = str(
        category
    ).strip().lower()

    if category_lower == "products":

        dimensions = [
            root_detect_column(
                df,
                PRODUCT_CANDIDATES,
            )
        ]

    elif category_lower == "customers":

        dimensions = [
            root_detect_column(
                df,
                CUSTOMER_CANDIDATES,
            )
        ]

    elif category_lower == "regional":

        dimensions = [
            root_detect_column(
                df,
                REGION_CANDIDATES,
            )
        ]

    elif category_lower == "marketing":

        dimensions = [
            root_detect_column(
                df,
                CAMPAIGN_CANDIDATES,
            ),
            root_detect_column(
                df,
                CHANNEL_CANDIDATES,
            ),
        ]

    else:

        dimensions = [
            root_detect_column(
                df,
                PRODUCT_CANDIDATES,
            ),
            root_detect_column(
                df,
                REGION_CANDIDATES,
            ),
            root_detect_column(
                df,
                CUSTOMER_CANDIDATES,
            ),
        ]

    dimensions = [
        dimension
        for dimension in dimensions
        if dimension
    ]

    results = find_root_causes(
        current=current,
        previous=previous,
        metric_column=metric_column,
        dimensions=dimensions,
    )

    return {
        "results": results,
        "overall_change": overall_change,
        "current_start": current_start,
        "current_end": current_end,
        "previous_start": previous_start,
        "previous_end": previous_end,
        "metric_column": metric_column,
    }


# ============================================================
# CUSTOMER RISK
# ============================================================

def run_customer_risk(
    df,
    category,
):

    if str(category).strip().lower() != "customers":

        return {
            "data": pd.DataFrame(),
            "summary": {},
            "distribution": [],
            "insights": [],
        }

    customer_column = risk_detect_column(
        df,
        CUSTOMER_CANDIDATES,
    )

    date_column = risk_detect_column(
        df,
        DATE_CANDIDATES,
    )

    metric_column = risk_detect_column(
        df,
        SALES_CANDIDATES,
    )

    quantity_column = risk_detect_column(
        df,
        QUANTITY_CANDIDATES,
    )

    if not customer_column or not date_column:

        return {
            "data": pd.DataFrame(),
            "summary": {},
            "distribution": [],
            "insights": [],
        }

    (
        risk_data,
        summary,
        distribution,
        insights,
    ) = run_customer_risk_analysis(
        df=df,
        customer_column=customer_column,
        date_column=date_column,
        metric_column=metric_column,
        quantity_column=quantity_column,
    )

    return {
        "data": risk_data,
        "summary": summary,
        "distribution": distribution,
        "insights": insights,
    }


# ============================================================
# OPPORTUNITY DETECTION
# ============================================================

def run_opportunity_analysis(
    df,
    category,
):

    category_lower = str(
        category
    ).strip().lower()

    # Opportunity Detection is intended for:
    # Products, Customers, Regional, Marketing.

    if category_lower not in {
        "products",
        "customers",
        "regional",
        "marketing",
    }:

        return {
            "opportunities": [],
            "summary": {},
            "insights": [],
        }

    date_column = opportunity_detect_column(
        df,
        DATE_CANDIDATES,
    )

    sales_column = opportunity_detect_column(
        df,
        SALES_CANDIDATES,
    )

    quantity_column = opportunity_detect_column(
        df,
        QUANTITY_CANDIDATES,
    )

    if not date_column or not sales_column:

        return {
            "opportunities": [],
            "summary": {},
            "insights": [],
        }

    dimensions = []

    if category_lower == "products":

        dimensions = [
            opportunity_detect_column(
                df,
                PRODUCT_CANDIDATES,
            )
        ]

    elif category_lower == "customers":

        dimensions = [
            opportunity_detect_column(
                df,
                CUSTOMER_CANDIDATES,
            )
        ]

    elif category_lower == "regional":

        dimensions = [
            opportunity_detect_column(
                df,
                REGION_CANDIDATES,
            )
        ]

    elif category_lower == "marketing":

        dimensions = [
            opportunity_detect_column(
                df,
                CAMPAIGN_CANDIDATES,
            ),
            opportunity_detect_column(
                df,
                CHANNEL_CANDIDATES,
            ),
        ]

    dimensions = [
        dimension
        for dimension in dimensions
        if dimension
    ]

    if not dimensions:

        return {
            "opportunities": [],
            "summary": {},
            "insights": [],
        }

    result = run_opportunity_detection(
        df=df,
        date_column=date_column,
        sales_column=sales_column,
        quantity_column=quantity_column,
        dimension_columns=dimensions,
        category_type=category,
    )

    return result


# ============================================================
# MAIN RECOMMENDATIONS VIEW
# ============================================================

@login_required
def recommendations(
    request
):

    datasets = get_recommendation_datasets(
        request.user
    )

    selected_dataset = None

    error_message = ""

    recommendation_data = {
        "recommendations": [],
        "summary": {
            "total": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "average_score": 0,
        },
        "insights": [],
    }

    # --------------------------------------------------------
    # Dataset selection
    # --------------------------------------------------------

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:

        try:

            selected_dataset = next(
                (
                    dataset
                    for dataset in datasets
                    if str(dataset.id)
                    == str(dataset_id)
                ),
                None,
            )

        except Exception:

            selected_dataset = None

    # --------------------------------------------------------
    # Default latest dataset
    # --------------------------------------------------------

    if not selected_dataset and datasets:

        selected_dataset = datasets[0]

    # --------------------------------------------------------
    # Analyze
    # --------------------------------------------------------

    if selected_dataset:

        try:

            df = load_dataset(
                selected_dataset
            )

            category = (
                selected_dataset.dataset_type
            )

            # ==================================================
            # ACTUAL ADVANCED INSIGHTS
            # ==================================================

            opportunity_result = (
                run_opportunity_analysis(
                    df,
                    category,
                )
            )

            customer_risk_result = (
                run_customer_risk(
                    df,
                    category,
                )
            )

            anomaly_result = (
                run_anomaly_analysis(
                    df
                )
            )

            forecast_result = (
                run_forecast_analysis(
                    df
                )
            )

            root_cause_result = (
                run_root_cause_analysis(
                    df,
                    category,
                )
            )

            # ==================================================
            # DECISION INTELLIGENCE
            # ==================================================

            recommendation_data = (
                build_decision_recommendations(

                    opportunity_results=(
                        opportunity_result.get(
                            "opportunities",
                            [],
                        )
                    ),

                    customer_risk_data=(
                        customer_risk_result.get(
                            "data",
                            pd.DataFrame(),
                        )
                    ),

                    customer_risk_summary=(
                        customer_risk_result.get(
                            "summary",
                            {},
                        )
                    ),

                    anomaly_summary=(
                        anomaly_result.get(
                            "summary",
                            {},
                        )
                    ),

                    forecast_summary=(
                        forecast_result.get(
                            "summary",
                            {},
                        )
                    ),

                    root_cause_results=(
                        root_cause_result.get(
                            "results",
                            [],
                        )
                    ),

                    root_cause_change=(
                        root_cause_result.get(
                            "overall_change",
                            0,
                        )
                    ),
                )
            )

        except Exception as exc:

            error_message = (
                "Unable to generate recommendations "
                f"from the selected dataset: {exc}"
            )

    else:

        if not datasets:

            error_message = (
                "No recommendation-ready datasets are available. "
                "Upload a Sales, Products, Customers, Regional "
                "or Marketing dataset first."
            )

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "selected_version": None,

        "has_data": bool(
            selected_dataset
        ),

        "error_message": error_message,

        # ----------------------------------------------------
        # Recommendations
        # ----------------------------------------------------

        "recommendations": (
            recommendation_data[
                "recommendations"
            ]
        ),

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        "recommendation_summary": (
            recommendation_data[
                "summary"
            ]
        ),

        "total_recommendations": (
            recommendation_data[
                "summary"
            ].get(
                "total",
                0,
            )
        ),

        "critical_recommendations": (
            recommendation_data[
                "summary"
            ].get(
                "critical",
                0,
            )
        ),

        "high_recommendations": (
            recommendation_data[
                "summary"
            ].get(
                "high",
                0,
            )
        ),

        "medium_recommendations": (
            recommendation_data[
                "summary"
            ].get(
                "medium",
                0,
            )
        ),

        "low_recommendations": (
            recommendation_data[
                "summary"
            ].get(
                "low",
                0,
            )
        ),

        "average_recommendation_score": (
            recommendation_data[
                "summary"
            ].get(
                "average_score",
                0,
            )
        ),

        # ----------------------------------------------------
        # Insights
        # ----------------------------------------------------

        "recommendation_insights": (
            recommendation_data[
                "insights"
            ]
        ),

        "insights": (
            recommendation_data[
                "insights"
            ]
        ),

        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------

        "dataset_category": (
            selected_dataset.dataset_type
            if selected_dataset
            else ""
        ),

        "category_description": (
            get_category_description(
                selected_dataset.dataset_type
            )
            if selected_dataset
            else ""
        ),
    }

    return render(
        request,
        "decision_intelligence/recommendations.html",
        context,
    )


# ============================================================
# DECISION DASHBOARD
# ============================================================

@login_required
def decision_dashboard(
    request
):

    datasets = get_recommendation_datasets(
        request.user
    )

    selected_dataset = None

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:

        selected_dataset = next(
            (
                dataset
                for dataset in datasets
                if str(dataset.id)
                == str(dataset_id)
            ),
            None,
        )

    if not selected_dataset and datasets:

        selected_dataset = datasets[0]

    context = {

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "has_data": bool(
            selected_dataset
        ),

        "dataset_category": (
            selected_dataset.dataset_type
            if selected_dataset
            else ""
        ),

        "category_description": (
            get_category_description(
                selected_dataset.dataset_type
            )
            if selected_dataset
            else ""
        ),
    }

    return render(
        request,
        "decision_intelligence/dashboard.html",
        context,
    )