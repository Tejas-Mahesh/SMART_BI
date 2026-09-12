from django.urls import path

from . import views


app_name = "advanced_insights"


urlpatterns = [

    # Advanced Insights main page
    path(
        "",
        views.advanced_insights_dashboard,
        name="dashboard",
    ),

    # Forecasting
    path(
        "forecasting/",
        views.forecasting,
        name="forecasting",
    ),

    # Anomaly Detection
    path(
        "anomaly-detection/",
        views.anomaly_detection,
        name="anomaly_detection",
    ),

    # Root Cause Analysis
    path(
        "root-cause/",
        views.root_cause_analysis,
        name="root_cause_analysis",
    ),

    # Customer Risk Analysis
    path(
        "customer-risk/",
        views.customer_risk_analysis,
        name="customer_risk_analysis",
    ),
path(
    "opportunity-detection/",
    views.opportunity_detection,
    name="opportunity_detection",
),
]