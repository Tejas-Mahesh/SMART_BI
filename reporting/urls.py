from django.urls import path

from . import views

app_name = "reporting"

urlpatterns = [


# ============================================================
# AUTOMATED REPORTS
# ============================================================

path(
    "automated-reports/",
    views.automated_reports,
    name="automated_reports",
),

# ============================================================
# CUSTOM REPORTS
# ============================================================

path(
    "custom-reports/",
    views.custom_reports,
    name="custom_reports",
),

# ============================================================
# CUSTOM REPORT PDF EXPORT
# ============================================================

path(
    "custom-reports/<int:report_id>/pdf/",
    views.custom_report_pdf,
    name="custom_report_pdf",
),

]
