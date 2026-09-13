import json

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from data_management.models import Dataset, DatasetVersion

# ============================================================
# ADVANCED INSIGHTS SERVICES
# ============================================================

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
from .services.business_alerts import (
    calculate_alert_summary,
    generate_business_alerts,
)
from .models import BusinessAlert, Scenario
from .models import BusinessAlert, Scenario
# ============================================================
# DECISION INTELLIGENCE SERVICES
# ============================================================

from .services.decision_analyzer import (
    build_decision_recommendations,
)

from .services.what_if import (
    calculate_scenario,
)

from .services.scenario_planning import (
    build_scenario_result,
    scenario_summary,
    rank_scenarios,
    get_best_scenario,
)

from .models import Scenario

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

import pandas as pd

from data_management.models import Dataset

from .models import (
    BusinessAlert,
    BusinessAction,
    Scenario,
)
from .services.impact_measurement import (
    measure_action_impact,
)
from .services.recommendation_learning import (
    build_learning_profile,
)
from .services.recommendation_learning import (
    apply_learning_to_recommendations,
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
    """
    Return datasets that can be used by
    Decision Intelligence.
    """

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
        if str(dataset.dataset_type).strip().lower()
        in ALLOWED_RECOMMENDATION_CATEGORIES
    ]


def get_cleaned_dataset_file(dataset):
    """
    Select the best available dataset file.

    Priority:
        1. Latest Cleaned version
        2. Current version
        3. Original uploaded dataset
    """

    if not dataset:
        return None

    # --------------------------------------------------------
    # Latest cleaned version
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

    if current_version and current_version.file:
        return current_version.file

    # --------------------------------------------------------
    # Original uploaded file
    # --------------------------------------------------------

    if dataset.file:
        return dataset.file

    return None


def load_dataset(dataset):
    """
    Load the selected dataset using the latest
    cleaned/current/original file.
    """

    file_field = get_cleaned_dataset_file(dataset)

    if not file_field:
        raise ValueError(
            "No dataset file is available."
        )

    file_path = file_field.path

    file_name = str(
        file_field.name
    ).lower()

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    if file_name.endswith(".csv"):

        df = pd.read_csv(
            file_path
        )

    # --------------------------------------------------------
    # Excel
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Normalize column names
    # --------------------------------------------------------

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

def get_category_description(category):

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

def run_forecast_analysis(df):

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

def run_anomaly_analysis(df):

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

    return run_opportunity_detection(
        df=df,
        date_column=date_column,
        sales_column=sales_column,
        quantity_column=quantity_column,
        dimension_columns=dimensions,
        category_type=category,
    )


# ============================================================
# RECOMMENDATIONS
# ============================================================

@login_required
def recommendations(request):

    # ========================================================
    # DATASETS
    # ========================================================

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

    # ========================================================
    # LEARNING PROFILE DEFAULT
    # ========================================================

    learning_profile = {
        "total_measured": 0,
        "success_count": 0,
        "failure_count": 0,
        "neutral_count": 0,
        "average_accuracy": 0,
        "learning_score": 0,
        "success_rate": 0,
        "confidence": 0,
        "status": "Insufficient History",
    }

    # ========================================================
    # DATASET SELECTION
    # ========================================================

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

    # ========================================================
    # ANALYSIS
    # ========================================================

    if selected_dataset:

        try:

            # ------------------------------------------------
            # Load cleaned/current dataset
            # ------------------------------------------------

            df = load_dataset(
                selected_dataset
            )

            category = (
                selected_dataset.dataset_type
            )

            # ------------------------------------------------
            # Advanced Insights
            # ------------------------------------------------

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

            # ------------------------------------------------
            # Decision Intelligence Engine
            # ------------------------------------------------

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

            # =================================================
            # RAW RECOMMENDATIONS
            # =================================================

            recommendation_results = (
                recommendation_data.get(
                    "recommendations",
                    [],
                )
            )

            # =================================================
            # DECISION IMPACT LEARNING
            #
            # Completed actions are compared against their
            # measured DecisionImpact records.
            # =================================================

            learning_records = []

            completed_actions = (
                BusinessAction.objects
                .filter(
                    created_by=request.user,
                    status="Completed",
                )
                .select_related("dataset")
                .order_by("-completed_at")
            )

            # -----------------------------------------------
            # Keep learning specific to selected dataset
            # -----------------------------------------------

            if selected_dataset:

                completed_actions = (
                    completed_actions.filter(
                        dataset=selected_dataset
                    )
                )

            # =================================================
            # BUILD LEARNING RECORDS
            # =================================================

            for action in completed_actions:

                try:

                    impact = (
                        DecisionImpact.objects
                        .filter(
                            action=action
                        )
                        .first()
                    )

                    if impact is None:
                        continue

                    learning_records.append({

                        "action": action,

                        "has_measurement": True,

                        "impact": (
                            impact.impact_status
                        ),

                        "result": {

                            "expected": {

                                "revenue_change": (
                                    impact.expected_revenue_change
                                ),

                                "profit_change": (
                                    impact.expected_profit_change
                                ),

                                "units_change": (
                                    impact.expected_units_change
                                ),

                            },

                            "actual": {

                                "revenue_change": (
                                    impact.actual_revenue_change
                                ),

                                "profit_change": (
                                    impact.actual_profit_change
                                ),

                                "units_change": (
                                    impact.actual_units_change
                                ),

                            },

                            "accuracy": {

                                "revenue": (
                                    impact.revenue_accuracy
                                ),

                                "profit": (
                                    impact.profit_accuracy
                                ),

                                "units": (
                                    impact.units_accuracy
                                ),

                            },

                        },

                    })

                except Exception:
                    continue

            # =================================================
            # CALCULATE LEARNING PROFILE
            # =================================================

            learning_profile = (
                build_learning_profile(
                    learning_records
                )
            )

            # =================================================
            # APPLY HISTORICAL LEARNING
            # =================================================

            recommendation_results = (
                apply_learning_to_recommendations(
                    recommendation_results,
                    learning_profile,
                )
            )

            # =================================================
            # SAVE RECOMMENDATIONS INTO ACTION CENTER
            # =================================================

            for recommendation in recommendation_results:

                try:

                    create_action_from_recommendation(
                        user=request.user,
                        dataset=selected_dataset,
                        recommendation=recommendation,
                    )

                except Exception as exc:

                    error_message = (
                        "Recommendations generated successfully, "
                        "but some Action Center items could not "
                        "be created: "
                        f"{exc}"
                    )

        except Exception as exc:

            error_message = (
                "Unable to generate recommendations "
                "from the selected dataset: "
                f"{exc}"
            )

    else:

        error_message = (
            "No recommendation-ready datasets are available. "
            "Upload a Sales, Products, Customers, Regional "
            "or Marketing dataset first."
        )

    # ========================================================
    # FINAL DATA
    # ========================================================

    summary = recommendation_data.get(
        "summary",
        {},
    )

    recommendations_list = (
        recommendation_data.get(
            "recommendations",
            [],
        )
    )

    insights_list = (
        recommendation_data.get(
            "insights",
            [],
        )
    )

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        # ----------------------------------------------------
        # Dataset
        # ----------------------------------------------------

        "datasets": datasets,

        "selected_dataset": (
            selected_dataset
        ),

        "selected_version": None,

        "has_data": bool(
            selected_dataset
        ),

        # ----------------------------------------------------
        # Errors
        # ----------------------------------------------------

        "error_message": (
            error_message
        ),

        # ----------------------------------------------------
        # Recommendations
        # ----------------------------------------------------

        "recommendations": (
            recommendations_list
        ),

        "recommendation_summary": (
            summary
        ),

        "total_recommendations": (
            summary.get(
                "total",
                0,
            )
        ),

        "critical_recommendations": (
            summary.get(
                "critical",
                0,
            )
        ),

        "high_recommendations": (
            summary.get(
                "high",
                0,
            )
        ),

        "medium_recommendations": (
            summary.get(
                "medium",
                0,
            )
        ),

        "low_recommendations": (
            summary.get(
                "low",
                0,
            )
        ),

        "average_recommendation_score": (
            summary.get(
                "average_score",
                0,
            )
        ),

        # ----------------------------------------------------
        # Insights
        # ----------------------------------------------------

        "recommendation_insights": (
            insights_list
        ),

        "insights": (
            insights_list
        ),

        # ----------------------------------------------------
        # Historical Decision Learning
        # ----------------------------------------------------

        "learning_profile": (
            learning_profile
        ),

        # ----------------------------------------------------
        # Dataset information
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

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "decision_intelligence/recommendations.html",
        context,
    )
@login_required
def decision_dashboard(request):

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


# ============================================================
# WHAT-IF SIMULATOR
# ============================================================

WHAT_IF_REVENUE_COLUMNS = [
    "revenue",
    "sales",
    "sale",
    "total_revenue",
    "total_sales",
    "net_sales",
    "sales_amount",
    "sale_amount",
    "order_value",
    "total_amount",
    "amount",
]

WHAT_IF_PROFIT_COLUMNS = [
    "profit",
    "net_profit",
    "gross_profit",
    "operating_profit",
    "profit_amount",
]

WHAT_IF_COST_COLUMNS = [
    "cost",
    "total_cost",
    "cost_amount",
    "product_cost",
    "purchase_cost",
    "cogs",
    "cost_of_goods_sold",
]

WHAT_IF_QUANTITY_COLUMNS = [
    "quantity",
    "qty",
    "units",
    "units_sold",
    "order_quantity",
    "total_quantity",
]

WHAT_IF_PRICE_COLUMNS = [
    "price",
    "unit_price",
    "selling_price",
    "sale_price",
]


def normalize_column_name(column):
    """
    Normalize column names for reliable detection.

    Example:
        Total Sales -> total_sales
        Unit Price  -> unit_price
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def detect_what_if_column(
    df,
    candidates,
):
    """
    Automatically detect a business column.
    """

    if df is None or df.empty:

        return None

    normalized_columns = {
        normalize_column_name(column): column
        for column in df.columns
    }

    # --------------------------------------------------------
    # Exact match
    # --------------------------------------------------------

    for candidate in candidates:

        normalized_candidate = (
            normalize_column_name(
                candidate
            )
        )

        if (
            normalized_candidate
            in normalized_columns
        ):

            return normalized_columns[
                normalized_candidate
            ]

    # --------------------------------------------------------
    # Partial match
    # --------------------------------------------------------

    for column in df.columns:

        normalized_column = (
            normalize_column_name(
                column
            )
        )

        for candidate in candidates:

            normalized_candidate = (
                normalize_column_name(
                    candidate
                )
            )

            if (
                normalized_candidate
                in normalized_column
                or
                normalized_column
                in normalized_candidate
            ):

                return column

    return None


def numeric_series(
    df,
    column,
):
    """
    Safely convert a dataframe column to numeric.
    """

    if (
        df is None
        or column is None
        or column not in df.columns
    ):

        return pd.Series(
            dtype="float64"
        )

    return pd.to_numeric(
        df[column],
        errors="coerce",
    ).fillna(0)


def calculate_what_if_baseline(df):
    """
    Calculate the actual business baseline.

    Priority:

        Revenue:
            Revenue/Sales column

        Units:
            Quantity column
            OR transaction count

        Profit:
            Explicit Profit column
            OR Revenue - Cost
            OR 20% fallback estimate
    """

    if df is None or df.empty:

        raise ValueError(
            "The selected dataset is empty."
        )

    # --------------------------------------------------------
    # Detect columns
    # --------------------------------------------------------

    revenue_column = detect_what_if_column(
        df,
        WHAT_IF_REVENUE_COLUMNS,
    )

    profit_column = detect_what_if_column(
        df,
        WHAT_IF_PROFIT_COLUMNS,
    )

    cost_column = detect_what_if_column(
        df,
        WHAT_IF_COST_COLUMNS,
    )

    quantity_column = detect_what_if_column(
        df,
        WHAT_IF_QUANTITY_COLUMNS,
    )

    price_column = detect_what_if_column(
        df,
        WHAT_IF_PRICE_COLUMNS,
    )

    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    if not revenue_column:

        raise ValueError(
            "No Revenue/Sales column was detected "
            "in this dataset."
        )

    revenue = float(
        numeric_series(
            df,
            revenue_column,
        ).sum()
    )

    # --------------------------------------------------------
    # Units
    # --------------------------------------------------------

    if quantity_column:

        units = float(
            numeric_series(
                df,
                quantity_column,
            ).sum()
        )

        if units <= 0:

            units = float(
                len(df)
            )

    else:

        units = float(
            len(df)
        )

    # --------------------------------------------------------
    # Profit
    # --------------------------------------------------------

    if profit_column:

        profit = float(
            numeric_series(
                df,
                profit_column,
            ).sum()
        )

        profit_source = (
            f"Calculated from '{profit_column}'"
        )

        baseline_source = (
            "Revenue + Profit + Quantity columns"
        )

    elif cost_column:

        total_cost = float(
            numeric_series(
                df,
                cost_column,
            ).sum()
        )

        profit = (
            revenue
            - total_cost
        )

        profit_source = (
            f"Revenue - '{cost_column}'"
        )

        baseline_source = (
            "Revenue + Cost + Quantity columns"
        )

    else:

        profit = (
            revenue
            * 0.20
        )

        profit_source = (
            "Estimated using 20% operating margin"
        )

        baseline_source = (
            "Revenue + Quantity columns "
            "(profit estimated)"
        )

    # --------------------------------------------------------
    # Safety
    # --------------------------------------------------------

    revenue = max(
        revenue,
        0,
    )

    units = max(
        units,
        1,
    )

    profit = float(
        profit
    )

    return {

        "revenue": round(
            revenue,
            2,
        ),

        "profit": round(
            profit,
            2,
        ),

        "units": round(
            units,
            2,
        ),

        "revenue_column": revenue_column,

        "profit_column": profit_column,

        "cost_column": cost_column,

        "quantity_column": quantity_column,

        "price_column": price_column,

        "profit_source": profit_source,

        "baseline_source": baseline_source,
    }


@login_required
def what_if_simulator(request):
    """
    What-If Simulator.

    Uses the actual selected dataset as the baseline,
    then applies scenario changes.
    """

    # --------------------------------------------------------
    # User datasets
    # --------------------------------------------------------

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:

        selected_dataset = (
            datasets
            .filter(
                id=dataset_id
            )
            .first()
        )

    if selected_dataset is None:

        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # Scenario inputs
    # --------------------------------------------------------

    price_change = request.POST.get(
        "price_change",
        0,
    )

    discount_change = request.POST.get(
        "discount_change",
        0,
    )

    marketing_change = request.POST.get(
        "marketing_change",
        0,
    )

    demand_change = request.POST.get(
        "demand_change",
        0,
    )

    # --------------------------------------------------------
    # Defaults
    # --------------------------------------------------------

    baseline = {
        "revenue": 0,
        "profit": 0,
        "units": 0,
        "revenue_column": None,
        "profit_column": None,
        "cost_column": None,
        "quantity_column": None,
        "price_column": None,
        "profit_source": "",
        "baseline_source": "",
    }

    result = None

    error_message = ""

    # --------------------------------------------------------
    # Calculate baseline
    # --------------------------------------------------------

    if selected_dataset:

        try:

            df = load_dataset(
                selected_dataset
            )

            baseline = calculate_what_if_baseline(
                df
            )

            # ------------------------------------------------
            # Calculate scenario
            # ------------------------------------------------

            result = calculate_scenario(

                base_revenue=baseline[
                    "revenue"
                ],

                base_profit=baseline[
                    "profit"
                ],

                base_units=baseline[
                    "units"
                ],

                price_change=price_change,

                discount_change=discount_change,

                marketing_change=marketing_change,

                demand_change=demand_change,
            )

        except Exception as exc:

            error_message = (
                "Unable to calculate the What-If "
                f"baseline: {exc}"
            )

    else:

        error_message = (
            "No active dataset is available. "
            "Upload a dataset from Data Management first."
        )

    # --------------------------------------------------------
    # Context
    # --------------------------------------------------------

    context = {

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "baseline": baseline,

        "base_revenue": baseline[
            "revenue"
        ],

        "base_profit": baseline[
            "profit"
        ],

        "base_units": baseline[
            "units"
        ],

        "price_change": price_change,

        "discount_change": discount_change,

        "marketing_change": marketing_change,

        "demand_change": demand_change,

        "result": result,

        "error_message": error_message,
    }

    return render(
        request,
        "decision_intelligence/what_if.html",
        context,
    )


# ============================================================
# SCENARIO PLANNING
# ============================================================

@login_required
def scenario_planning(request):

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True,
    ).order_by("-uploaded_at")

    selected_dataset = None

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        selected_dataset = datasets.filter(
            id=dataset_id
        ).first()

    if selected_dataset is None:
        selected_dataset = datasets.first()

    error_message = ""
    baseline_error = ""

    # =========================================================
    # BASELINE
    # =========================================================

    baseline = {
        "revenue": 0,
        "profit": 0,
        "units": 0,
    }

    if selected_dataset:

        try:

            df = load_dataset(
                selected_dataset
            )

            baseline_result = calculate_what_if_baseline(
                df
            )

            baseline = {
                "revenue": float(
                    baseline_result.get(
                        "revenue",
                        0
                    )
                ),

                "profit": float(
                    baseline_result.get(
                        "profit",
                        0
                    )
                ),

                "units": float(
                    baseline_result.get(
                        "units",
                        0
                    )
                ),
            }

        except Exception as exc:

            baseline_error = str(exc)

    # =========================================================
    # CREATE SCENARIO
    # =========================================================

    if request.method == "POST" and selected_dataset:

        scenario_name = (
            request.POST.get(
                "scenario_name"
            )
            or "Business Scenario"
        ).strip()

        description = (
            request.POST.get(
                "description"
            )
            or ""
        ).strip()

        try:

            price_change = float(
                request.POST.get(
                    "price_change",
                    0
                )
            )

            discount_change = float(
                request.POST.get(
                    "discount_change",
                    0
                )
            )

            marketing_change = float(
                request.POST.get(
                    "marketing_change",
                    0
                )
            )

            demand_change = float(
                request.POST.get(
                    "demand_change",
                    0
                )
            )

        except (TypeError, ValueError):

            error_message = (
                "Please enter valid scenario values."
            )

        if not error_message:

            try:

                df = load_dataset(
                    selected_dataset
                )

                baseline_result = (
                    calculate_what_if_baseline(
                        df
                    )
                )

                result = build_scenario_result(
                    baseline_result,

                    price_change=price_change,

                    discount_change=discount_change,

                    marketing_change=marketing_change,

                    demand_change=demand_change,
                )

                summary = scenario_summary(
                    scenario_name,
                    result,
                )

                Scenario.objects.create(

                    dataset=selected_dataset,

                    created_by=request.user,

                    name=scenario_name,

                    description=description,

                    price_change=price_change,

                    discount_change=discount_change,

                    marketing_change=marketing_change,

                    demand_change=demand_change,

                    baseline_revenue=summary[
                        "baseline_revenue"
                    ],

                    baseline_profit=summary[
                        "baseline_profit"
                    ],

                    baseline_units=summary[
                        "baseline_units"
                    ],

                    scenario_revenue=summary[
                        "scenario_revenue"
                    ],

                    scenario_profit=summary[
                        "scenario_profit"
                    ],

                    scenario_units=summary[
                        "scenario_units"
                    ],

                    revenue_change=summary[
                        "revenue_change"
                    ],

                    profit_change=summary[
                        "profit_change"
                    ],

                    units_change=summary[
                        "units_change"
                    ],

                    score=summary[
                        "score"
                    ],

                    decision=summary[
                        "decision"
                    ],

                    insights=summary[
                        "insights"
                    ],
                )

                return redirect(
                    f"{request.path}?dataset={selected_dataset.id}"
                )

            except Exception as exc:

                error_message = (
                    "Unable to create scenario: "
                    f"{exc}"
                )

    # =========================================================
    # LOAD SAVED SCENARIOS
    # =========================================================

    saved_scenarios = []

    if selected_dataset:

        saved_scenarios = list(

            Scenario.objects.filter(

                dataset=selected_dataset,

                created_by=request.user,

            ).values(

                "id",

                "name",

                "description",

                "price_change",

                "discount_change",

                "marketing_change",

                "demand_change",

                "baseline_revenue",

                "baseline_profit",

                "baseline_units",

                "scenario_revenue",

                "scenario_profit",

                "scenario_units",

                "revenue_change",

                "profit_change",

                "units_change",

                "score",

                "decision",

                "insights",

                "created_at",
            )
        )

        saved_scenarios = rank_scenarios(
            saved_scenarios
        )

    # =========================================================
    # BEST SCENARIO
    # =========================================================

    best_scenario = get_best_scenario(
        saved_scenarios
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "scenarios": saved_scenarios,

        "best_scenario": best_scenario,

        "scenario_count": len(
            saved_scenarios
        ),

        "baseline": baseline,

        "baseline_error": baseline_error,

        "error_message": error_message,
    }

    # =========================================================
    # VERY IMPORTANT:
    # ALWAYS RETURN HTTP RESPONSE
    # =========================================================

    return render(
        request,
        "decision_intelligence/scenario_planning.html",
        context,
    )
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Scenario
@login_required
def duplicate_scenario(request, scenario_id):
    scenario = get_object_or_404(
        Scenario,
        id=scenario_id,
        created_by=request.user,
    )

    duplicated = Scenario.objects.create(
        dataset=scenario.dataset,
        created_by=request.user,
        name=f"{scenario.name} - Copy",
        description=scenario.description,

        price_change=scenario.price_change,
        discount_change=scenario.discount_change,
        marketing_change=scenario.marketing_change,
        demand_change=scenario.demand_change,

        baseline_revenue=scenario.baseline_revenue,
        baseline_profit=scenario.baseline_profit,
        baseline_units=scenario.baseline_units,

        scenario_revenue=scenario.scenario_revenue,
        scenario_profit=scenario.scenario_profit,
        scenario_units=scenario.scenario_units,

        revenue_change=scenario.revenue_change,
        profit_change=scenario.profit_change,
        units_change=scenario.units_change,

        score=scenario.score,
        decision=scenario.decision,
        insights=scenario.insights,
    )

    return redirect(
        f"/decisions/scenario-planning/?dataset={scenario.dataset_id}"
    )
@login_required
def delete_scenario(request, scenario_id):
    scenario = get_object_or_404(
        Scenario,
        id=scenario_id,
        created_by=request.user,
    )

    dataset_id = scenario.dataset_id

    if request.method == "POST":
        scenario.delete()

    return redirect(
        f"/decisions/scenario-planning/?dataset={dataset_id}"
    )

@login_required
def business_alerts(request):

    # ============================================================
    # DATASETS
    # ============================================================

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
        selected_dataset = datasets.filter(
            id=dataset_id
        ).first()

    if selected_dataset is None:
        selected_dataset = datasets.first()

    # ============================================================
    # INITIAL RESULTS
    # ============================================================

    forecast_result = {
        "summary": {},
        "trend": {},
    }

    anomaly_result = {
        "summary": {},
        "anomaly_data": pd.DataFrame(),
    }

    opportunity_result = {
        "opportunities": [],
        "summary": {},
        "insights": [],
    }

    customer_risk_result = {
        "data": pd.DataFrame(),
        "summary": {},
        "distribution": [],
        "insights": [],
    }

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

    error_messages = []

    # ============================================================
    # ANALYZE SELECTED DATASET
    # ============================================================

    if selected_dataset:

        try:

            df = load_dataset(
                selected_dataset
            )

            category = (
                selected_dataset.dataset_type
            )

            # ====================================================
            # FORECASTING
            # ====================================================

            try:

                forecast_result = (
                    run_forecast_analysis(
                        df
                    )
                )

            except Exception as exc:

                error_messages.append(
                    f"Forecasting: {exc}"
                )

            # ====================================================
            # ANOMALY DETECTION
            # ====================================================

            try:

                anomaly_result = (
                    run_anomaly_analysis(
                        df
                    )
                )

            except Exception as exc:

                error_messages.append(
                    f"Anomaly Detection: {exc}"
                )

            # ====================================================
            # OPPORTUNITY DETECTION
            # ====================================================

            try:

                opportunity_result = (
                    run_opportunity_analysis(
                        df,
                        category,
                    )
                )

            except Exception as exc:

                error_messages.append(
                    f"Opportunity Detection: {exc}"
                )

            # ====================================================
            # CUSTOMER RISK
            # ====================================================

            try:

                customer_risk_result = (
                    run_customer_risk(
                        df,
                        category,
                    )
                )

            except Exception as exc:

                error_messages.append(
                    f"Customer Risk: {exc}"
                )

            # ====================================================
            # RECOMMENDATION ENGINE
            # ====================================================

            try:

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

                        root_cause_results=[],

                        root_cause_change=0,
                    )
                )

            except Exception as exc:

                error_messages.append(
                    f"Recommendation Engine: {exc}"
                )

        except Exception as exc:

            error_messages.append(
                f"Dataset analysis: {exc}"
            )

    else:

        error_messages.append(
            "No active dataset is available. "
            "Upload a dataset from Data Management first."
        )

    # ============================================================
    # EXTRACT RECOMMENDATIONS
    # ============================================================

    if isinstance(
        recommendation_data,
        dict,
    ):

        recommendation_results = (
            recommendation_data.get(
                "recommendations",
                [],
            )
        )

    else:

        recommendation_results = []

    # ============================================================
    # GENERATE BUSINESS ALERTS
    # ============================================================

    try:

        generated_alerts = (
            generate_business_alerts(

                forecast_results=(
                    forecast_result
                ),

                anomaly_results=(
                    anomaly_result
                ),

                risk_results=(
                    customer_risk_result
                ),

                opportunity_results=(
                    opportunity_result
                ),

                recommendation_results=(
                    recommendation_results
                ),
            )
        )

    except Exception as exc:

        generated_alerts = []

        error_messages.append(
            f"Business Alert Engine: {exc}"
        )

    # ============================================================
    # LOAD EXISTING ALERTS
    # ============================================================

    existing_alerts = (
        BusinessAlert.objects
        .filter(
            created_by=request.user,
        )
    )

    if selected_dataset:

        existing_alerts = (
            existing_alerts.filter(
                dataset=selected_dataset,
            )
        )

    # ============================================================
    # CREATE NEW ALERTS
    # ============================================================

    existing_keys = set(
        existing_alerts.values_list(
            "title",
            "source",
        )
    )

    new_alerts = []

    for alert in generated_alerts:

        title = str(
            alert.get(
                "title",
                "Business Alert",
            )
        ).strip()

        source = str(
            alert.get(
                "source",
                "System",
            )
        ).strip()

        key = (
            title,
            source,
        )

        if key in existing_keys:
            continue

        new_alerts.append(
            BusinessAlert(

                dataset=selected_dataset,

                created_by=request.user,

                title=title,

                message=alert.get(
                    "message",
                    "",
                ),

                severity=alert.get(
                    "severity",
                    "Medium",
                ),

                source=source,

                category=alert.get(
                    "category",
                    "",
                ),

                metric_name=alert.get(
                    "metric_name",
                    "",
                ),

                metric_value=alert.get(
                    "metric_value",
                ),

                threshold_value=alert.get(
                    "threshold_value",
                ),

                recommendation=alert.get(
                    "recommendation",
                    "",
                ),

                metadata=alert.get(
                    "metadata",
                    {},
                ),
            )
        )

        existing_keys.add(key)

    if new_alerts:

        BusinessAlert.objects.bulk_create(
            new_alerts
        )

    # ============================================================
    # FETCH FINAL ALERT LIST
    # ============================================================

    alerts_queryset = (
        BusinessAlert.objects
        .filter(
            created_by=request.user,
        )
    )

    if selected_dataset:

        alerts_queryset = (
            alerts_queryset.filter(
                dataset=selected_dataset,
            )
        )

    alerts_queryset = (
        alerts_queryset
        .order_by("-created_at")
    )

    # ============================================================
    # CREATE ACTIONS FROM ALERTS
    # ============================================================

    for alert in alerts_queryset:

        try:

            create_action_from_alert(
                user=request.user,
                alert=alert,
            )

        except Exception as exc:

            error_messages.append(
                f"Action Center: {exc}"
            )

    # ============================================================
    # CREATE ACTIONS FROM RECOMMENDATIONS
    # ============================================================

    if selected_dataset:

        for recommendation in recommendation_results:

            try:

                create_action_from_recommendation(
                    user=request.user,
                    dataset=selected_dataset,
                    recommendation=recommendation,
                )

            except Exception as exc:

                error_messages.append(
                    f"Recommendation Action: {exc}"
                )

    # ============================================================
    # TEMPLATE DATA
    # ============================================================

    alerts = []

    for alert in alerts_queryset:

        alerts.append({

            "id": alert.id,

            "title": alert.title,

            "message": alert.message,

            "severity": alert.severity,

            "source": alert.source,

            "category": alert.category,

            "metric_name": alert.metric_name,

            "metric_value": alert.metric_value,

            "threshold_value": (
                alert.threshold_value
            ),

            "recommendation": (
                alert.recommendation
            ),

            "status": alert.status,

            "is_read": alert.is_read,

            "created_at": alert.created_at,

        })

    # ============================================================
    # SUMMARY
    # ============================================================

    alert_summary = (
        calculate_alert_summary(
            alerts
        )
    )

    # ============================================================
    # CONTEXT
    # ============================================================

    context = {

        "datasets": datasets,

        "selected_dataset": (
            selected_dataset
        ),

        "alerts": alerts,

        "alert_summary": (
            alert_summary
        ),

        "error_messages": (
            error_messages
        ),

    }

    # ============================================================
    # RESPONSE
    # ============================================================

    return render(
        request,
        "decision_intelligence/business_alerts.html",
        context,
    )
@login_required
def acknowledge_alert(request, alert_id):

    if request.method != "POST":

        return redirect(
            "decision_intelligence:business_alerts"
        )

    alert = (
        BusinessAlert.objects
        .filter(
            id=alert_id,
            created_by=request.user,
        )
        .first()
    )

    if alert:

        alert.status = "Acknowledged"

        alert.is_read = True

        alert.save(
            update_fields=[
                "status",
                "is_read",
                "updated_at",
            ]
        )

    return redirect(
        "decision_intelligence:business_alerts"
    )


@login_required
def resolve_alert(request, alert_id):

    if request.method != "POST":

        return redirect(
            "decision_intelligence:business_alerts"
        )

    alert = (
        BusinessAlert.objects
        .filter(
            id=alert_id,
            created_by=request.user,
        )
        .first()
    )

    if alert:

        alert.status = "Resolved"

        alert.is_read = True

        alert.save(
            update_fields=[
                "status",
                "is_read",
                "updated_at",
            ]
        )

    return redirect(
        "decision_intelligence:business_alerts"
    )


@login_required
def resolve_alert(request, alert_id):
    if request.method != "POST":
        return redirect(
            "decision_intelligence:business_alerts"
        )

    alert = BusinessAlert.objects.filter(
        id=alert_id,
        created_by=request.user,
    ).first()

    if alert:
        alert.status = "Resolved"
        alert.is_read = True
        alert.save(
            update_fields=[
                "status",
                "is_read",
                "updated_at",
            ]
        )

    return redirect(
        "decision_intelligence:business_alerts"
    )


@login_required
def dashboard(request):
    return render(
        request,
        "decision_intelligence/dashboard.html",
    )

from .models import BusinessAlert, BusinessAction, Scenario
from django.utils import timezone
@login_required
def action_center(request):

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:

        selected_dataset = (
            datasets
            .filter(id=dataset_id)
            .first()
        )

    if selected_dataset is None:

        selected_dataset = datasets.first()

    actions = (
        BusinessAction.objects
        .filter(
            created_by=request.user
        )
    )

    if selected_dataset:

        actions = actions.filter(
            dataset=selected_dataset
        )

    status_filter = (
        request.GET
        .get("status", "")
        .strip()
    )

    priority_filter = (
        request.GET
        .get("priority", "")
        .strip()
    )

    if status_filter:

        actions = actions.filter(
            status=status_filter
        )

    if priority_filter:

        actions = actions.filter(
            priority=priority_filter
        )

    actions = (
        actions
        .order_by("-created_at")
    )

    total_actions = actions.count()

    critical_count = (
        actions
        .filter(priority="Critical")
        .count()
    )

    high_count = (
        actions
        .filter(priority="High")
        .count()
    )

    medium_count = (
        actions
        .filter(priority="Medium")
        .count()
    )

    low_count = (
        actions
        .filter(priority="Low")
        .count()
    )

    open_count = (
        actions
        .filter(status="Open")
        .count()
    )

    in_progress_count = (
        actions
        .filter(status="In Progress")
        .count()
    )

    completed_count = (
        actions
        .filter(status="Completed")
        .count()
    )

    dismissed_count = (
        actions
        .filter(status="Dismissed")
        .count()
    )

    context = {

        "datasets": datasets,

        "selected_dataset": (
            selected_dataset
        ),

        "actions": actions,

        "total_actions": total_actions,

        "critical_count": critical_count,

        "high_count": high_count,

        "medium_count": medium_count,

        "low_count": low_count,

        "open_count": open_count,

        "in_progress_count": (
            in_progress_count
        ),

        "completed_count": (
            completed_count
        ),

        "dismissed_count": (
            dismissed_count
        ),

        "status_filter": status_filter,

        "priority_filter": priority_filter,
    }

    return render(
        request,
        "decision_intelligence/action_center.html",
        context,
    )


@login_required
def update_action_status(
    request,
    action_id,
):

    if request.method != "POST":

        return redirect(
            "decision_intelligence:action_center"
        )

    action = (
        BusinessAction.objects
        .filter(
            id=action_id,
            created_by=request.user,
        )
        .first()
    )

    if action is None:

        return redirect(
            "decision_intelligence:action_center"
        )

    new_status = (
        request.POST
        .get("status", "")
        .strip()
    )

    allowed_statuses = {
        "Open",
        "In Progress",
        "Completed",
        "Dismissed",
    }

    if new_status not in allowed_statuses:

        return redirect(
            "decision_intelligence:action_center"
        )

    action.status = new_status

    if new_status == "Completed":

        action.completed_at = timezone.now()

    else:

        action.completed_at = None

    action.save()

    return redirect(
        "decision_intelligence:action_center"
    )


@login_required
def update_action_status(request, action_id):
    """
    Update the lifecycle status of a business action.
    """

    if request.method != "POST":
        return redirect(
            "decision_intelligence:action_center"
        )

    action = BusinessAction.objects.filter(
        id=action_id,
        created_by=request.user,
    ).first()

    if action is None:
        return redirect(
            "decision_intelligence:action_center"
        )

    new_status = request.POST.get(
        "status",
        ""
    ).strip()

    allowed_statuses = {
        "Open",
        "In Progress",
        "Completed",
        "Dismissed",
    }

    if new_status not in allowed_statuses:
        return redirect(
            "decision_intelligence:action_center"
        )

    action.status = new_status

    if new_status == "Completed":
        action.completed_at = timezone.now()
    else:
        action.completed_at = None

    action.save()

    return redirect(
        "decision_intelligence:action_center"
    )

def create_action_from_recommendation(
    *,
    user,
    dataset,
    recommendation,
):
    """
    Convert a generated recommendation into
    an Action Center item.
    """

    if not user or not dataset or not recommendation:
        return None

    title = str(
        recommendation.get(
            "title"
        )
        or "Business Recommendation"
    ).strip()

    description = str(
        recommendation.get(
            "reason"
        )
        or recommendation.get(
            "recommendation"
        )
        or ""
    ).strip()

    priority = str(
        recommendation.get(
            "priority"
        )
        or "Medium"
    ).strip()

    if priority not in {
        "Critical",
        "High",
        "Medium",
        "Low",
    }:
        priority = "Medium"

    expected_impact = str(
        recommendation.get(
            "expected_impact"
        )
        or ""
    ).strip()

    recommendation_text = str(
        recommendation.get(
            "recommendation"
        )
        or ""
    ).strip()

    score = recommendation.get(
        "score",
        0,
    )

    try:
        score = float(score)

    except (
        TypeError,
        ValueError,
    ):
        score = 0

    source_id = recommendation.get(
        "source_id"
    )

    metadata = recommendation.get(
        "metadata",
        {}
    )

    if not isinstance(metadata, dict):
        metadata = {}

    def get_float(
        key,
        default=0.0,
    ):
        try:
            value = float(
                metadata.get(
                    key,
                    default,
                )
            )

            if value != value:
                return default

            return value

        except (
            TypeError,
            ValueError,
        ):
            return default

    expected_revenue_change = get_float(
        "expected_revenue_change"
    )

    expected_profit_change = get_float(
        "expected_profit_change"
    )

    expected_units_change = get_float(
        "expected_units_change"
    )

    existing = (
        BusinessAction.objects
        .filter(
            created_by=user,
            dataset=dataset,
            title=title,
            action_type="Recommendation",
            status__in=[
                "Open",
                "In Progress",
            ],
        )
        .first()
    )

    if existing:
        return existing

    return BusinessAction.objects.create(
        dataset=dataset,
        created_by=user,
        title=title,
        description=description,
        action_type="Recommendation",
        priority=priority,
        status="Open",
        source_id=source_id,
        expected_impact=expected_impact,
        impact_score=score,

        expected_revenue_change=(
            expected_revenue_change
        ),

        expected_profit_change=(
            expected_profit_change
        ),

        expected_units_change=(
            expected_units_change
        ),

        recommendation=recommendation_text,
    )
def create_action_from_alert(
    *,
    user,
    alert,
):
    """
    Convert an important BusinessAlert into
    an Action Center item.
    """

    if not user or not alert:
        return None

    if alert.severity not in {
        "Critical",
        "High",
        "Medium",
    }:
        return None

    priority = alert.severity

    title = (
        alert.title
        or "Business Alert Action"
    )

    description = (
        alert.message
        or alert.recommendation
        or ""
    )

    existing = (
        BusinessAction.objects
        .filter(
            created_by=user,
            dataset=alert.dataset,
            title=title,
            action_type="Alert",
            status__in=[
                "Open",
                "In Progress",
            ],
        )
        .first()
    )

    if existing:
        return existing

    return BusinessAction.objects.create(
        dataset=alert.dataset,
        created_by=user,
        title=title,
        description=description,
        action_type="Alert",
        priority=priority,
        status="Open",
        source_id=alert.id,
        expected_impact=(
            alert.recommendation
            or ""
        ),
        impact_score=0,
        recommendation=(
            alert.recommendation
            or ""
        ),
    )
from datetime import timedelta

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from data_management.models import Dataset

from .models import (
    BusinessAction,
    BusinessAlert,
    DecisionImpact,
    Scenario,
)
from .services.decision_impact import build_complete_impact_analysis
def calculate_decision_intelligence(impact_records):
    """
    Converts measured decision impacts into executive-level
    rankings, success metrics, and business learning insights.
    """

    best_decisions = []
    underperforming_decisions = []
    accurate_decisions = []

    measured_records = []

    for record in impact_records:

        result = record.get("result", {})

        expected = result.get("expected", {})
        actual = result.get("actual", {})
        accuracy = result.get("accuracy", {})

        status = record.get("impact", "Pending")

        if not record.get("has_measurement"):
            continue

        expected_profit = float(
            expected.get("profit_change", 0) or 0
        )

        actual_profit = float(
            actual.get("profit_change", 0) or 0
        )

        expected_revenue = float(
            expected.get("revenue_change", 0) or 0
        )

        actual_revenue = float(
            actual.get("revenue_change", 0) or 0
        )

        expected_units = float(
            expected.get("units_change", 0) or 0
        )

        actual_units = float(
            actual.get("units_change", 0) or 0
        )

        profit_accuracy = float(
            accuracy.get("profit", 0) or 0
        )

        revenue_accuracy = float(
            accuracy.get("revenue", 0) or 0
        )

        units_accuracy = float(
            accuracy.get("units", 0) or 0
        )

        accuracy_score = (
            profit_accuracy
            + revenue_accuracy
            + units_accuracy
        ) / 3

        # Overall decision performance score.
        performance_score = (
            max(0, min(100, actual_profit + 50))
            * 0.45
            + max(0, min(100, accuracy_score))
            * 0.35
            + max(0, min(100, actual_revenue + 50))
            * 0.20
        )

        item = {
            "action": record.get("action"),
            "status": status,

            "expected_profit": expected_profit,
            "actual_profit": actual_profit,

            "expected_revenue": expected_revenue,
            "actual_revenue": actual_revenue,

            "expected_units": expected_units,
            "actual_units": actual_units,

            "profit_accuracy": profit_accuracy,
            "revenue_accuracy": revenue_accuracy,
            "units_accuracy": units_accuracy,

            "accuracy_score": round(
                accuracy_score,
                2,
            ),

            "performance_score": round(
                performance_score,
                2,
            ),
        }

        measured_records.append(item)

        if status == "Positive":
            best_decisions.append(item)

        elif status == "Negative":
            underperforming_decisions.append(item)

        if accuracy_score >= 80:
            accurate_decisions.append(item)

    best_decisions.sort(
        key=lambda x: (
            x["performance_score"],
            x["actual_profit"],
        ),
        reverse=True,
    )

    underperforming_decisions.sort(
        key=lambda x: (
            x["performance_score"],
            x["actual_profit"],
        )
    )

    accurate_decisions.sort(
        key=lambda x: x["accuracy_score"],
        reverse=True,
    )

    measured_count = len(measured_records)

    if measured_count:
        success_count = sum(
            1
            for item in measured_records
            if item["status"] == "Positive"
        )

        decision_success_rate = (
            success_count
            / measured_count
        ) * 100

        average_accuracy = sum(
            item["accuracy_score"]
            for item in measured_records
        ) / measured_count

        average_performance = sum(
            item["performance_score"]
            for item in measured_records
        ) / measured_count

    else:
        decision_success_rate = 0
        average_accuracy = 0
        average_performance = 0

    insights = []

    if best_decisions:
        best = best_decisions[0]

        insights.append(
            f"Best measured decision: "
            f"{best['action'].title} with an "
            f"impact performance score of "
            f"{best['performance_score']:.1f}."
        )

    if underperforming_decisions:
        weakest = underperforming_decisions[0]

        insights.append(
            f"Decision requiring review: "
            f"{weakest['action'].title} produced "
            f"the weakest measured performance."
        )

    if average_accuracy >= 80:
        insights.append(
            "Decision expectations are strongly aligned "
            "with observed business outcomes."
        )

    elif measured_count:
        insights.append(
            "Prediction accuracy can be improved by "
            "learning from historical decision outcomes."
        )

    if decision_success_rate >= 70:
        insights.append(
            "The majority of measured decisions generated "
            "positive business impact."
        )

    elif measured_count:
        insights.append(
            "A significant share of decisions requires "
            "strategy refinement."
        )

    return {
        "best_decisions": best_decisions[:5],
        "underperforming_decisions": underperforming_decisions[:5],
        "accurate_decisions": accurate_decisions[:5],

        "measured_count": measured_count,

        "decision_success_rate": round(
            decision_success_rate,
            2,
        ),

        "average_accuracy": round(
            average_accuracy,
            2,
        ),

        "average_performance": round(
            average_performance,
            2,
        ),

        "insights": insights,
    }
@login_required
def decision_impact(request):
    """
    Decision Impact dashboard.

    Completed actions are measured against
    business performance before and after
    the action completion date.
    """

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:
        selected_dataset = (
            datasets
            .filter(
                id=dataset_id
            )
            .first()
        )

    if selected_dataset is None:
        selected_dataset = datasets.first()

    completed_actions = (
        BusinessAction.objects
        .filter(
            created_by=request.user,
            status="Completed",
        )
        .select_related(
            "dataset"
        )
        .order_by(
            "-completed_at",
            "-updated_at",
        )
    )

    if selected_dataset:

        completed_actions = (
            completed_actions.filter(
                dataset=selected_dataset
            )
        )

    impact_records = []

    positive_count = 0
    negative_count = 0
    neutral_count = 0
    pending_count = 0
    measured_count = 0

    total_expected_profit = 0.0
    total_actual_profit = 0.0

    for action in completed_actions:

        impact = None

        # --------------------------------------------------
        # AUTOMATIC MEASUREMENT
        # --------------------------------------------------

        try:

            df = load_dataset(
                action.dataset
            )

            impact = (
                measure_decision_impact_for_action(
                    action=action,
                    df=df,
                )
            )

        except Exception:
            impact = None

        # --------------------------------------------------
        # SAVED IMPACT EXISTS
        # --------------------------------------------------

        if impact:

            result = {
                "expected": {
                    "revenue_change": (
                        impact.expected_revenue_change
                    ),

                    "profit_change": (
                        impact.expected_profit_change
                    ),

                    "units_change": (
                        impact.expected_units_change
                    ),

                    "impact_score": (
                        impact.expected_impact_score
                    ),
                },

                "actual": {
                    "revenue_change": (
                        impact.actual_revenue_change
                    ),

                    "profit_change": (
                        impact.actual_profit_change
                    ),

                    "units_change": (
                        impact.actual_units_change
                    ),

                    "impact_score": (
                        impact.actual_impact_score
                    ),
                },

                "accuracy": {
                    "revenue": (
                        impact.revenue_accuracy
                    ),

                    "profit": (
                        impact.profit_accuracy
                    ),

                    "units": (
                        impact.units_accuracy
                    ),
                },

                "impact_status": (
                    impact.impact_status
                ),
            }

            try:

                insights = (
                    build_complete_impact_analysis(
                        expected_revenue_change=(
                            impact.expected_revenue_change
                        ),

                        expected_profit_change=(
                            impact.expected_profit_change
                        ),

                        expected_units_change=(
                            impact.expected_units_change
                        ),

                        actual_revenue_change=(
                            impact.actual_revenue_change
                        ),

                        actual_profit_change=(
                            impact.actual_profit_change
                        ),

                        actual_units_change=(
                            impact.actual_units_change
                        ),

                        expected_impact_score=(
                            impact.expected_impact_score
                        ),
                    )
                    .get(
                        "insights",
                        [],
                    )
                )

            except Exception:

                insights = []

        # --------------------------------------------------
        # IMPACT NOT YET AVAILABLE
        # --------------------------------------------------

        else:

            result = {
                "expected": {
                    "revenue_change": (
                        action.expected_revenue_change
                    ),

                    "profit_change": (
                        action.expected_profit_change
                    ),

                    "units_change": (
                        action.expected_units_change
                    ),

                    "impact_score": (
                        action.impact_score
                    ),
                },

                "actual": {
                    "revenue_change": 0,
                    "profit_change": 0,
                    "units_change": 0,
                    "impact_score": 0,
                },

                "accuracy": {
                    "revenue": 0,
                    "profit": 0,
                    "units": 0,
                },

                "impact_status": "Pending",
            }

            insights = [
                (
                    "Actual business impact cannot "
                    "be measured yet."
                ),

                (
                    "Smart BI requires sufficient "
                    "post-completion data."
                ),

                (
                    "The system compares a 30-day "
                    "period before and after the "
                    "completed action."
                ),
            ]

        # --------------------------------------------------
        # STATUS COUNTS
        # --------------------------------------------------

        status = result.get(
            "impact_status",
            "Pending",
        )

        if status == "Positive":

            positive_count += 1

        elif status == "Negative":

            negative_count += 1

        elif status == "Neutral":

            neutral_count += 1

        elif status == "Measured":

            measured_count += 1

        else:

            pending_count += 1

        # --------------------------------------------------
        # PROFIT SUMMARY
        # --------------------------------------------------

        expected_profit = float(
            result
            .get(
                "expected",
                {},
            )
            .get(
                "profit_change",
                0,
            )
            or 0
        )

        actual_profit = float(
            result
            .get(
                "actual",
                {},
            )
            .get(
                "profit_change",
                0,
            )
            or 0
        )

        total_expected_profit += (
            expected_profit
        )

        total_actual_profit += (
            actual_profit
        )

        # --------------------------------------------------
        # RECORD
        # --------------------------------------------------

        impact_records.append(
            {
                "action": action,

                "result": result,

                "insights": insights,

                "impact": status,

                "has_measurement": (
                    impact is not None
                ),
            }
        )

    # ------------------------------------------------------
    # OVERALL PROFIT ACCURACY
    # ------------------------------------------------------

    if total_expected_profit != 0:

        overall_profit_accuracy = (
            total_actual_profit
            / total_expected_profit
        ) * 100

        overall_profit_accuracy = max(
            0,
            min(
                100,
                overall_profit_accuracy,
            ),
        )

    else:

        overall_profit_accuracy = 0

    # ------------------------------------------------------
    # CONTEXT
    # ------------------------------------------------------
    decision_intelligence = calculate_decision_intelligence(
    impact_records)
    learning_profile = build_learning_profile(
    impact_records
)

    context = {
        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "impact_records": impact_records,

        "total_actions": len(
            impact_records
        ),

        "positive_count": positive_count,

        "negative_count": negative_count,

        "neutral_count": neutral_count,

        "measured_count": measured_count,

        "pending_count": pending_count,

        "total_expected_profit": (
            total_expected_profit
        ),

        "total_actual_profit": (
            total_actual_profit
        ),

        "overall_profit_accuracy": round(
            overall_profit_accuracy,
            2,
        ),
        "decision_intelligence": decision_intelligence,
        "learning_profile": learning_profile,
    }

    return render(
        request,
        "decision_intelligence/decision_impact.html",
        context,
    )
def measure_decision_impact_for_action(
    action,
    df,
):
    """
    Measure and persist actual business impact
    for a completed BusinessAction.
    """

    if action is None:
        return None

    if action.status != "Completed":
        return None

    if df is None or df.empty:
        return None

    if not action.completed_at:
        return None

    try:
        result = measure_action_impact(
            df=df,

            completed_at=action.completed_at,

            expected_revenue_change=(
                action.expected_revenue_change
            ),

            expected_profit_change=(
                action.expected_profit_change
            ),

            expected_units_change=(
                action.expected_units_change
            ),

            expected_impact_score=(
                action.impact_score
            ),

            period_days=30,
        )

    except Exception:
        return None

    if not result.get("success"):
        return None

    analysis = result.get(
        "analysis",
        {},
    )

    expected = analysis.get(
        "expected",
        {},
    )

    actual = analysis.get(
        "actual",
        {},
    )

    accuracy = analysis.get(
        "accuracy",
        {},
    )

    impact_status = analysis.get(
        "impact_status",
        "Neutral",
    )

    period = result.get(
        "period",
        {},
    )

    impact, created = (
        DecisionImpact.objects.get_or_create(
            action=action,
            defaults={
                "dataset": action.dataset,

                "created_by": action.created_by,

                "expected_revenue_change": (
                    expected.get(
                        "revenue_change",
                        0,
                    )
                ),

                "expected_profit_change": (
                    expected.get(
                        "profit_change",
                        0,
                    )
                ),

                "expected_units_change": (
                    expected.get(
                        "units_change",
                        0,
                    )
                ),

                "expected_impact_score": (
                    expected.get(
                        "impact_score",
                        0,
                    )
                ),

                "actual_revenue_change": (
                    actual.get(
                        "revenue_change",
                        0,
                    )
                ),

                "actual_profit_change": (
                    actual.get(
                        "profit_change",
                        0,
                    )
                ),

                "actual_units_change": (
                    actual.get(
                        "units_change",
                        0,
                    )
                ),

                "revenue_accuracy": (
                    accuracy.get(
                        "revenue",
                        0,
                    )
                ),

                "profit_accuracy": (
                    accuracy.get(
                        "profit",
                        0,
                    )
                ),

                "units_accuracy": (
                    accuracy.get(
                        "units",
                        0,
                    )
                ),

                "actual_impact_score": (
                    actual.get(
                        "impact_score",
                        0,
                    )
                ),

                "impact_status": impact_status,

                "measurement_start": (
                    period.get(
                        "after_start"
                    )
                ),

                "measurement_end": (
                    period.get(
                        "after_end"
                    )
                ),
            },
        )
    )

    if not created:

        impact.dataset = action.dataset

        impact.created_by = action.created_by

        impact.expected_revenue_change = (
            expected.get(
                "revenue_change",
                0,
            )
        )

        impact.expected_profit_change = (
            expected.get(
                "profit_change",
                0,
            )
        )

        impact.expected_units_change = (
            expected.get(
                "units_change",
                0,
            )
        )

        impact.expected_impact_score = (
            expected.get(
                "impact_score",
                0,
            )
        )

        impact.actual_revenue_change = (
            actual.get(
                "revenue_change",
                0,
            )
        )

        impact.actual_profit_change = (
            actual.get(
                "profit_change",
                0,
            )
        )

        impact.actual_units_change = (
            actual.get(
                "units_change",
                0,
            )
        )

        impact.revenue_accuracy = (
            accuracy.get(
                "revenue",
                0,
            )
        )

        impact.profit_accuracy = (
            accuracy.get(
                "profit",
                0,
            )
        )

        impact.units_accuracy = (
            accuracy.get(
                "units",
                0,
            )
        )

        impact.actual_impact_score = (
            actual.get(
                "impact_score",
                0,
            )
        )

        impact.impact_status = impact_status

        impact.measurement_start = (
            period.get(
                "after_start"
            )
        )

        impact.measurement_end = (
            period.get(
                "after_end"
            )
        )

        impact.save()

    return impact