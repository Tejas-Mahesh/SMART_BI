
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


urlpatterns = [

    # ========================================================
    # Django Admin
    # ========================================================

    path(
        "admin/",
        admin.site.urls,
    ),

    # ========================================================
    # Core / Dashboard / Public Pages
    # ========================================================

    path(
        "",
        include("core.urls"),
    ),

    # ========================================================
    # Authentication
    # ========================================================

    path(
        "accounts/",
        include("accounts.urls"),
    ),

    # ========================================================
    # Data Management
    # ========================================================

    path(
        "data/",
        include("data_management.urls"),
    ),

    # ========================================================
    # Business Analytics
    # ========================================================

    path(
        "analytics/",
        include("analytics.urls"),
    ),

    # ========================================================
    # Admin Dashboard
    # ========================================================

    path(
        "admin-dashboard/",
        include("admin_dashboard.urls"),
    ),

    # ========================================================
    # Advanced Insights
    # ========================================================

    path(
        "advanced-insights/",
        include("advanced_insights.urls"),
    ),

    # ========================================================
    # Decision Intelligence
    # ========================================================

    path(
        "decision-intelligence/",
        include("decision_intelligence.urls"),
    ),

    # ========================================================
    # Reporting
    # ========================================================

    path(
        "reporting/",
        include("reporting.urls"),
    ),
]


# ============================================================
# DEVELOPMENT MEDIA FILES
# ============================================================
#
# Django serves uploaded media locally while DEBUG=True.
#
# In production, uploaded files should use persistent/external
# storage rather than relying on the web service filesystem.
#
# ============================================================

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
