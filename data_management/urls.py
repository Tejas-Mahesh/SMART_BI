from django.urls import path
from . import views

app_name = "data_management"

urlpatterns = [

    # Upload
        path(
        "upload/",
        views.upload_dataset,
        name="upload_data",
    ),

    # Dataset preview
    path(
        "preview/<int:dataset_id>/",
        views.dataset_preview,
        name="dataset_preview"
    ),

    # Dataset management
    path(
        "datasets/",
        views.dataset_management,
        name="dataset_management"
    ),

    # Data quality
    path(
        "quality/",
        views.data_quality,
        name="quality"
    ),

    # Data cleaning
    path(
        "cleaning/",
        views.data_cleaning,
        name="cleaning"
    ),

    path(
        "cleaning/download/<int:dataset_id>/",
        views.download_cleaned_dataset,
        name="download_cleaned_dataset"
    ),

    # Data validation
    path(
        "validation/",
        views.data_validation,
        name="validation"
    ),

    path(
        "validation/download/<int:dataset_id>/",
        views.download_validation_report,
        name="download_validation_report"
    ),

    # Data profiling
    path(
        "profiling/",
        views.data_profiling,
        name="profiling"
    ),

    # Data transformation
    path(
        "transformation/",
        views.data_transformation,
        name="transformation"
    ),

    path(
        "transformation/apply/<int:dataset_id>/",
        views.transform_dataset,
        name="transform_dataset"
    ),

    # Version history
    path(
        "version-history/",
        views.data_version_history,
        name="version_history"
    ),

    # IMPORTANT:
    # Original / Cleaned version download
    path(
        "version/<int:version_id>/download/",
        views.download_dataset_version,
        name="download_version"
    ),

    # Delete dataset
    path(
        "datasets/delete/<int:dataset_id>/",
        views.delete_dataset,
        name="delete_dataset"
    ),
]