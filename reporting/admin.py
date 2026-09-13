from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "report_type",
        "output_format",
        "status",
        "owner",
        "dataset",
        "created_at",
    )

    list_filter = (
        "report_type",
        "output_format",
        "status",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "owner__username",
        "owner__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )