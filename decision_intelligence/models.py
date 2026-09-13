from django.apps import AppConfig


class DecisionIntelligenceConfig(
    AppConfig
):
    default_auto_field = (
        "django.db.models.BigAutoField"
    )

    name = "decision_intelligence"

from django.conf import settings
from django.db import models


from django.conf import settings
from django.db import models


class Scenario(models.Model):

    DECISION_CHOICES = [
        ("Recommended", "Recommended"),
        ("High Revenue", "High Revenue"),
        ("Lower Profit", "Lower Profit"),
        ("Not Recommended", "Not Recommended"),
        ("Review", "Review"),
    ]

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="scenarios",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_scenarios",
    )

    name = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    # Scenario assumptions
    price_change = models.FloatField(
        default=0
    )

    discount_change = models.FloatField(
        default=0
    )

    marketing_change = models.FloatField(
        default=0
    )

    demand_change = models.FloatField(
        default=0
    )

    # Baseline
    baseline_revenue = models.FloatField(
        default=0
    )

    baseline_profit = models.FloatField(
        default=0
    )

    baseline_units = models.FloatField(
        default=0
    )

    # Scenario output
    scenario_revenue = models.FloatField(
        default=0
    )

    scenario_profit = models.FloatField(
        default=0
    )

    scenario_units = models.FloatField(
        default=0
    )

    # Percentage changes
    revenue_change = models.FloatField(
        default=0
    )

    profit_change = models.FloatField(
        default=0
    )

    units_change = models.FloatField(
        default=0
    )

    # Decision intelligence
    score = models.FloatField(
        default=0
    )

    decision = models.CharField(
        max_length=30,
        choices=DECISION_CHOICES,
        default="Review",
    )

    insights = models.JSONField(
        default=list,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.dataset.name}"

class BusinessAlert(models.Model):
    SEVERITY_CHOICES = [
        ("Critical", "Critical"),
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    STATUS_CHOICES = [
        ("New", "New"),
        ("Acknowledged", "Acknowledged"),
        ("Resolved", "Resolved"),
    ]

    SOURCE_CHOICES = [
        ("Forecasting", "Forecasting"),
        ("Anomaly Detection", "Anomaly Detection"),
        ("Customer Risk", "Customer Risk"),
        ("Opportunity Detection", "Opportunity Detection"),
        ("Root Cause Analysis", "Root Cause Analysis"),
        ("Recommendation Engine", "Recommendation Engine"),
        ("Scenario Planning", "Scenario Planning"),
        ("System", "System"),
    ]

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="business_alerts",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_alerts",
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="Medium",
    )

    source = models.CharField(
        max_length=40,
        choices=SOURCE_CHOICES,
        default="System",
    )

    category = models.CharField(
        max_length=100,
        blank=True,
    )

    metric_name = models.CharField(
        max_length=100,
        blank=True,
    )

    metric_value = models.FloatField(
        null=True,
        blank=True,
    )

    threshold_value = models.FloatField(
        null=True,
        blank=True,
    )

    recommendation = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="New",
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.severity} - {self.title}"

class BusinessAction(models.Model):
    PRIORITY_CHOICES = [
        ("Critical", "Critical"),
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    STATUS_CHOICES = [
        ("Open", "Open"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
        ("Dismissed", "Dismissed"),
    ]

    ACTION_TYPES = [
        ("Recommendation", "Recommendation"),
        ("Alert", "Alert"),
        ("Scenario", "Scenario"),
        ("Manual", "Manual"),
    ]

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="business_actions",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_actions",
    )

    title = models.CharField(max_length=255)

    description = models.TextField(blank=True)
    recommendation_category = models.CharField(
    max_length=50,
    blank=True,
    default="",
)

    action_type = models.CharField(
        max_length=30,
        choices=ACTION_TYPES,
        default="Recommendation",
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="Medium",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Open",
    )

    source_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    expected_impact = models.CharField(
        max_length=255,
        blank=True,
    )

    impact_score = models.FloatField(default=0)
    expected_revenue_change = models.FloatField(default=0)
    expected_profit_change = models.FloatField(default=0)
    expected_units_change = models.FloatField(default=0)

    recommendation = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
class DecisionImpact(models.Model):
    IMPACT_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Measured", "Measured"),
        ("Positive", "Positive"),
        ("Negative", "Negative"),
        ("Neutral", "Neutral"),
    ]

    action = models.OneToOneField(
        "decision_intelligence.BusinessAction",
        on_delete=models.CASCADE,
        related_name="decision_impact",
    )

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="decision_impacts",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="decision_impacts",
    )

    # Expected impact from recommendation/action
    expected_revenue_change = models.FloatField(default=0)
    expected_profit_change = models.FloatField(default=0)
    expected_units_change = models.FloatField(default=0)
    expected_impact_score = models.FloatField(default=0)

    # Actual measured business impact
    actual_revenue_change = models.FloatField(default=0)
    actual_profit_change = models.FloatField(default=0)
    actual_units_change = models.FloatField(default=0)

    # Performance measurement
    revenue_accuracy = models.FloatField(default=0)
    profit_accuracy = models.FloatField(default=0)
    units_accuracy = models.FloatField(default=0)

    actual_impact_score = models.FloatField(default=0)

    impact_status = models.CharField(
        max_length=20,
        choices=IMPACT_STATUS_CHOICES,
        default="Pending",
    )

    measurement_start = models.DateField(null=True, blank=True)
    measurement_end = models.DateField(null=True, blank=True)

    analysis_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Impact - {self.action.title}"
class RecommendationFeedback(models.Model):
    """
    Stores explicit user feedback for a generated recommendation.

    This is separate from DecisionImpact because feedback represents
    the user's immediate assessment, while DecisionImpact represents
    the measurable business outcome after an action is completed.
    """

    FEEDBACK_CHOICES = [
        ("Useful", "Useful"),
        ("Not Useful", "Not Useful"),
        ("Partially Useful", "Partially Useful"),
    ]

    RATING_CHOICES = [
        (1, "1 - Very Poor"),
        (2, "2 - Poor"),
        (3, "3 - Average"),
        (4, "4 - Good"),
        (5, "5 - Excellent"),
    ]

    recommendation_title = models.CharField(
        max_length=255,
    )

    recommendation_category = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    recommendation_source = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="recommendation_feedback",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendation_feedback",
    )

    action = models.ForeignKey(
        "decision_intelligence.BusinessAction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback_records",
    )

    feedback = models.CharField(
        max_length=30,
        choices=FEEDBACK_CHOICES,
    )

    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        default=3,
    )

    comment = models.TextField(
        blank=True,
    )

    recommendation_score = models.FloatField(
        default=0,
    )

    priority = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.recommendation_title} - "
            f"{self.feedback}"
        )