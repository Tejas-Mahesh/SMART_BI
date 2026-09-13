from django.urls import path

from . import views


app_name = "reporting"


urlpatterns = [

    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "generate/",
        views.generate_report,
        name="generate_report",
    ),

    path(
        "<int:report_id>/download/pdf/",
        views.download_pdf,
        name="download_pdf",
    ),

    path(
        "<int:report_id>/download/excel/",
        views.download_excel,
        name="download_excel",
    ),

]