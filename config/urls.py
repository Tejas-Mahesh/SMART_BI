from django.contrib import admin
from django.urls import include, path


urlpatterns = [

    path(
        "admin/",
        admin.site.urls
    ),

    path(
        "",
        include("core.urls")
    ),

    path(
        "accounts/",
        include("accounts.urls")
    ),

    path(
        "data/",
        include("data_management.urls")
    ),

    path(
        "analytics/",
        include("analytics.urls")
    ),

    path(
        "admin-dashboard/",
        include("admin_dashboard.urls")
    ),
    path(
    "insights/",
    include("advanced_insights.urls"),
),
path(
    "decisions/",
    include("decision_intelligence.urls"),
),
path(
    "reports/",
    include("reporting.urls"),
),
]