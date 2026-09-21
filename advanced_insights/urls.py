from django.urls import path

from . import views

app_name = "advanced_insights"


urlpatterns = [

    # --------------------------------------------------------
    # FUTURE TRENDS
    # --------------------------------------------------------

    path(
        "future-trends/",
        views.future_trends,
        name="future_trends",
    ),

    path(
        "future-trends/history/",
        views.future_trends_history,
        name="future_trends_history",
    ),

    # --------------------------------------------------------
    # FORECASTING
    # --------------------------------------------------------

    path(
        "forecasting/",
        views.forecasting,
        name="forecasting",
    ),

    # --------------------------------------------------------
    # ANOMALY DETECTION
    # --------------------------------------------------------

    path(
        "anomaly-detection/",
        views.anomaly_detection,
        name="anomaly_detection",
    ),

    # --------------------------------------------------------
    # ROOT CAUSE ANALYSIS
    # --------------------------------------------------------

    path(
        "root-cause-analysis/",
        views.root_cause_analysis,
        name="root_cause_analysis",
    ),

    # ========================================================
    # CUSTOMER SEGMENTATION
    # ========================================================

    path(
        "customer-segmentation/",
        views.customer_segmentation,
        name="customer_segmentation",
    ),
    path(
    "churn-risk-analysis/",
    views.churn_risk_analysis,
    name="churn_risk_analysis",
),
path(
    "opportunity-detection/",
    views.opportunity_detection,
    name="opportunity_detection",
),
]