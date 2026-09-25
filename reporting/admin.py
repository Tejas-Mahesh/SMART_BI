from django.contrib import admin

from .models import (
    Report,
    CustomReport,
    ReportExport,
)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "dataset",
        "dataset_version",
        "report_type",
        "status",
        "created_at",
        "completed_at",
    )

    list_filter = (
        "report_type",
        "status",
        "created_at",
    )

    search_fields = (
        "name",
        "description",
        "owner__username",
        "dataset__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "completed_at",
    )

    ordering = (
        "-created_at",
    )


@admin.register(CustomReport)
class CustomReportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "dataset",
        "dataset_version",
        "is_active",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "description",
        "owner__username",
        "dataset__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-updated_at",
    )


@admin.register(ReportExport)
class ReportExportAdmin(admin.ModelAdmin):
    list_display = (
        "report",
        "export_type",
        "status",
        "created_at",
        "completed_at",
    )

    list_filter = (
        "export_type",
        "status",
        "created_at",
    )

    search_fields = (
        "report__name",
    )

    readonly_fields = (
        "created_at",
        "completed_at",
    )

    ordering = (
        "-created_at",
    )