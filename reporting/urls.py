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
path(
    "<int:report_id>/export/excel/",
    views.export_report_excel,
    name="export_report_excel",
),
path(
    "export-history/",
    views.export_history,
    name="export_history",
),
path(
    "<int:report_id>/export/pdf/",
    views.export_pdf,
    name="export_pdf",
),

path(
    "<int:report_id>/export/excel/",
    views.export_excel,
    name="export_excel",
),
]