from django.urls import path

from . import views


app_name = "data_management"


urlpatterns = [

    # ============================================================
    # UPLOAD
    # ============================================================

    path(
        "upload/",
        views.upload_dataset,
        name="upload_data",
    ),


    # ============================================================
    # DATASET PREVIEW
    # ============================================================

    path(
        "preview/<int:dataset_id>/",
        views.dataset_preview,
        name="dataset_preview",
    ),


    # ============================================================
    # DATASET MANAGEMENT
    # ============================================================

    path(
        "datasets/",
        views.dataset_management,
        name="dataset_management",
    ),


    # ============================================================
    # DATA QUALITY
    # ============================================================

    path(
        "quality/",
        views.data_quality,
        name="quality",
    ),


    # ============================================================
    # DATA CLEANING
    # ============================================================

    path(
        "cleaning/",
        views.data_cleaning,
        name="cleaning",
    ),

    path(
        "cleaning/download/<int:dataset_id>/",
        views.download_cleaned_dataset,
        name="download_cleaned_dataset",
    ),


    # ============================================================
    # DATA VALIDATION
    # ============================================================

    path(
        "validation/",
        views.data_validation,
        name="validation",
    ),

    path(
        "validation/download/<int:dataset_id>/",
        views.download_validation_report,
        name="download_validation_report",
    ),


    # ============================================================
    # DATA PROFILING
    # ============================================================

    path(
        "profiling/",
        views.data_profiling,
        name="profiling",
    ),


    # ============================================================
    # DATA TRANSFORMATION
    # ============================================================

    path(
        "transformation/",
        views.data_transformation,
        name="transformation",
    ),

    path(
        "transformation/apply/<int:dataset_id>/",
        views.transform_dataset,
        name="transform_dataset",
    ),


    # ============================================================
    # VERSION HISTORY
    # ============================================================

    path(
        "version-history/",
        views.data_version_history,
        name="data_version_history",
    ),


    # ============================================================
    # VERSION DOWNLOAD
    # ============================================================

    path(
        "version/<int:version_id>/download/",
        views.download_dataset_version,
        name="download_version",
    ),


    # ============================================================
    # DELETE DATASET
    # ============================================================

    path(
        "datasets/delete/<int:dataset_id>/",
        views.delete_dataset,
        name="delete_dataset",
    ),
]