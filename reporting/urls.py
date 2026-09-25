from django.urls import path

from . import views


app_name = "reporting"


urlpatterns = [
    path(
        "",
        views.reporting_dashboard,
        name="dashboard",
    ),

    path(
        "automated/",
        views.automated_reports,
        name="automated_reports",
    ),

    path(
        "custom/",
        views.custom_reports,
        name="custom_reports",
    ),

    path(
        "history/",
        views.report_history,
        name="report_history",
    ),

    path(
        "export/",
        views.export_center,
        name="export_center",
    ),

    path(
        "<int:report_id>/",
        views.report_detail,
        name="report_detail",
    ),
    path(
    "<int:report_id>/export/pdf/",
    views.export_report_pdf,
    name="export_report_pdf",
),
]