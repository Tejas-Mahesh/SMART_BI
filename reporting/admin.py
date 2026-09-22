
from django.contrib import admin

from .models import AutomatedReport


@admin.register(AutomatedReport)
class AutomatedReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "report_type",
        "dataset",
        "dataset_version",
        "status",
        "output_format",
        "created_by",
        "generated_at",
        "created_at",
    )

    list_filter = (
        "report_type",
        "status",
        "output_format",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "dataset__name",
        "created_by__username",
    )

    readonly_fields = (
        "generated_at",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )
