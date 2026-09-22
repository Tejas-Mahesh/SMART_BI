from django.urls import path

from . import views


app_name = "decision_intelligence"


urlpatterns = [
    path(
        "recommendations/",
        views.recommendations,
        name="recommendations",
    ),
    path( "what-if/", views.what_if_simulator, name="what_if_simulator", ),
    path( "scenario-planning/", views.scenario_planning, name="scenario_planning", ),
    path( "business-alerts/", views.business_alerts, name="business_alerts", ),
    path( "action-center/", views.action_center, name="action_center", ),
    path(
    "decision-impact-analysis/",
    views.decision_impact_analysis,
    name="decision_impact_analysis",
),
]