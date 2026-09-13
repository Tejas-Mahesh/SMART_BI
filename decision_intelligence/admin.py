
from django.contrib import admin
from .models import Scenario, BusinessAlert


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "dataset",
        "created_by",
        "score",
        "decision",
        "created_at",
    )

    list_filter = (
        "decision",
        "created_at",
    )

    search_fields = (
        "name",
        "dataset__name",
        "created_by__username",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

@admin.register(BusinessAlert)
class BusinessAlertAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "severity",
        "source",
        "category",
        "status",
        "is_read",
        "created_at",
    )

    list_filter = (
        "severity",
        "source",
        "status",
        "is_read",
        "created_at",
    )

    search_fields = (
        "title",
        "message",
        "category",
        "metric_name",
        "recommendation",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )