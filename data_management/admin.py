from django.contrib import admin

from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "dataset_type",
        "owner",
        "total_rows",
        "total_columns",
        "quality_score",
        "uploaded_at",
    )

    list_filter = (
        "dataset_type",
        "uploaded_at",
        "is_active",
    )

    search_fields = (
        "name",
        "original_filename",
        "owner__username",
        "owner__email",
    )

    readonly_fields = (
        "file_size",
        "total_rows",
        "total_columns",
        "missing_values",
        "duplicate_rows",
        "quality_score",
        "uploaded_at",
        "updated_at",
    )

    ordering = (
        "-uploaded_at",
    )