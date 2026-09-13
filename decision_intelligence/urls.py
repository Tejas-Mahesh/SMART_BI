from django.urls import path

from . import views


app_name = "decision_intelligence"


urlpatterns = [

    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "recommendations/",
        views.recommendations,
        name="recommendations",
    ),

    path(
        "what-if/",
        views.what_if_simulator,
        name="what_if",
    ),

    path(
        "scenario-planning/",
        views.scenario_planning,
        name="scenario_planning",
    ),

    path(
        "business-alerts/",
        views.business_alerts,
        name="business_alerts",
    ),

    path(
        "business-alerts/<int:alert_id>/acknowledge/",
        views.acknowledge_alert,
        name="acknowledge_alert",
    ),

    path(
        "business-alerts/<int:alert_id>/resolve/",
        views.resolve_alert,
        name="resolve_alert",
    ),

    path(
        "action-center/",
        views.action_center,
        name="action_center",
    ),

    path(
        "action-center/<int:action_id>/status/",
        views.update_action_status,
        name="update_action_status",
    ),
    path(
    "decision-impact/",
    views.decision_impact,
    name="decision_impact",
),
path(
    "recommendations/<int:feedback_action_id>/feedback/",
    views.submit_recommendation_feedback,
    name="submit_recommendation_feedback",
),
]