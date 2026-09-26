from django.contrib import admin
from django.urls import include, path

from django.conf import settings
from django.conf.urls.static import static
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
        "advanced-insights/",
        include(
            "advanced_insights.urls"
        ),
    ),

    path(
        "decision-intelligence/",
        include(
            "decision_intelligence.urls"
        ),
    ),
path("reporting/", include("reporting.urls")),
]
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )