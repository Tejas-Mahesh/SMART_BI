
from django.contrib import admin
from .models import Scenario, BusinessAlert

from .models import RecommendationFeedback
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
@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):

    list_display = (
        "recommendation_title",
        "recommendation_category",
        "feedback",
        "rating",
        "recommendation_score",
        "user",
        "created_at",
    )

    list_filter = (
        "feedback",
        "rating",
        "recommendation_category",
        "created_at",
    )

    search_fields = (
        "recommendation_title",
        "recommendation_category",
        "recommendation_source",
        "comment",
        "user__username",
    )

    ordering = (
        "-created_at",
    )