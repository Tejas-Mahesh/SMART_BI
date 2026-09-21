from django.conf import settings
from django.db import models


# ============================================================
# ADVANCED INSIGHT RUN
# ============================================================

class InsightRun(models.Model):

    INSIGHT_TYPES = [
        ("Future Trends", "Future Trends"),
        ("Forecasting", "Forecasting"),
        ("Anomaly Detection", "Anomaly Detection"),
        ("Root Cause Analysis", "Root Cause Analysis"),
        ("Customer Segmentation", "Customer Segmentation"),
        ("Churn Risk", "Churn / Risk Analysis"),
        ("Opportunity Detection", "Opportunity Detection"),
    ]

    STATUS_CHOICES = [
        ("Running", "Running"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    # --------------------------------------------------------
    # SOURCE DATASET
    # --------------------------------------------------------

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="insight_runs",
    )

    dataset_version = models.ForeignKey(
        "data_management.DatasetVersion",
        on_delete=models.CASCADE,
        related_name="insight_runs",
    )

    # --------------------------------------------------------
    # INSIGHT INFORMATION
    # --------------------------------------------------------

    insight_type = models.CharField(
        max_length=100,
        choices=INSIGHT_TYPES,
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="Running",
    )

    # Parameters used for the analysis.
    #
    # Example:
    # {
    #     "date_column": "Order Date",
    #     "metric_column": "Revenue",
    #     "frequency": "M"
    # }
    parameters = models.JSONField(
        default=dict,
        blank=True,
    )

    # --------------------------------------------------------
    # ERROR INFORMATION
    # --------------------------------------------------------

    error_message = models.TextField(
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insight_runs",
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        ordering = [
            "-started_at"
        ]

    def __str__(self):

        return (
            f"{self.insight_type} - "
            f"{self.dataset.name}"
        )


# ============================================================
# FUTURE TRENDS RESULT
# ============================================================

class TrendResult(models.Model):

    insight_run = models.OneToOneField(
        InsightRun,
        on_delete=models.CASCADE,
        related_name="trend_result",
    )

    # --------------------------------------------------------
    # ANALYSIS PARAMETERS
    # --------------------------------------------------------

    date_column = models.CharField(
        max_length=255
    )

    metric_column = models.CharField(
        max_length=255
    )

    frequency = models.CharField(
        max_length=20
    )

    # --------------------------------------------------------
    # TREND RESULTS
    # --------------------------------------------------------

    trend_direction = models.CharField(
        max_length=50
    )

    trend_strength = models.CharField(
        max_length=50
    )

    percentage_change = models.FloatField(
        null=True,
        blank=True,
    )

    average_value = models.FloatField(
        null=True,
        blank=True,
    )

    minimum_value = models.FloatField(
        null=True,
        blank=True,
    )

    maximum_value = models.FloatField(
        null=True,
        blank=True,
    )

    first_period_value = models.FloatField(
        null=True,
        blank=True,
    )

    latest_period_value = models.FloatField(
        null=True,
        blank=True,
    )

    recent_direction = models.CharField(
        max_length=50,
        blank=True,
    )

    # Human-readable interpretation.
    summary = models.TextField(
        blank=True,
    )

    # Chart-ready time-series data.
    #
    # Example:
    # [
    #     {
    #         "period": "2026-01",
    #         "value": 125000
    #     }
    # ]
    chart_data = models.JSONField(
        default=list,
        blank=True,
    )

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "-created_at"
        ]

    def __str__(self):

        return (
            f"{self.metric_column} - "
            f"{self.trend_direction}"
        )

# ============================================================
# FORECAST RESULT
# ============================================================

class ForecastResult(models.Model):

    METHOD_CHOICES = [
        ("Linear Trend", "Linear Trend"),
        ("Moving Average", "Moving Average"),
    ]

    insight_run = models.OneToOneField(
        InsightRun,
        on_delete=models.CASCADE,
        related_name="forecast_result",
    )

    date_column = models.CharField(
        max_length=255
    )

    metric_column = models.CharField(
        max_length=255
    )

    frequency = models.CharField(
        max_length=20
    )

    method = models.CharField(
        max_length=50
    )

    horizon = models.PositiveIntegerField(
        default=3
    )

    historical_periods = models.PositiveIntegerField(
        default=0
    )

    forecast_periods = models.PositiveIntegerField(
        default=0
    )

    last_actual_value = models.FloatField(
        null=True,
        blank=True
    )

    first_forecast_value = models.FloatField(
        null=True,
        blank=True
    )

    latest_forecast_value = models.FloatField(
        null=True,
        blank=True
    )

    forecast_change_percentage = models.FloatField(
        null=True,
        blank=True
    )

    average_forecast_value = models.FloatField(
        null=True,
        blank=True
    )

    minimum_forecast_value = models.FloatField(
        null=True,
        blank=True
    )

    maximum_forecast_value = models.FloatField(
        null=True,
        blank=True
    )

    confidence_level = models.FloatField(
        null=True,
        blank=True
    )

    summary = models.TextField(
        blank=True
    )

    chart_data = models.JSONField(
        default=list,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.metric_column} - "
            f"{self.method} Forecast"
        )

# ============================================================
# ANOMALY DETECTION RESULT
# ============================================================

class AnomalyResult(models.Model):

    DETECTION_METHOD_CHOICES = [
        ("Z-Score", "Z-Score"),
    ]

    insight_run = models.OneToOneField(
        InsightRun,
        on_delete=models.CASCADE,
        related_name="anomaly_result",
    )

    # --------------------------------------------------------
    # SOURCE COLUMNS
    # --------------------------------------------------------

    date_column = models.CharField(
        max_length=255,
        blank=True,
    )

    metric_column = models.CharField(
        max_length=255,
    )

    # --------------------------------------------------------
    # DETECTION SETTINGS
    # --------------------------------------------------------

    detection_method = models.CharField(
        max_length=50,
        choices=DETECTION_METHOD_CHOICES,
        default="Z-Score",
    )

    threshold = models.FloatField(
        default=2.5,
    )

    # --------------------------------------------------------
    # DATA SUMMARY
    # --------------------------------------------------------

    total_records = models.PositiveIntegerField(
        default=0,
    )

    normal_records = models.PositiveIntegerField(
        default=0,
    )

    anomaly_count = models.PositiveIntegerField(
        default=0,
    )

    anomaly_percentage = models.FloatField(
        default=0,
    )

    # --------------------------------------------------------
    # STATISTICAL VALUES
    # --------------------------------------------------------

    average_value = models.FloatField(
        null=True,
        blank=True,
    )

    standard_deviation = models.FloatField(
        null=True,
        blank=True,
    )

    minimum_value = models.FloatField(
        null=True,
        blank=True,
    )

    maximum_value = models.FloatField(
        null=True,
        blank=True,
    )

    highest_anomaly_value = models.FloatField(
        null=True,
        blank=True,
    )

    lowest_anomaly_value = models.FloatField(
        null=True,
        blank=True,
    )

    # --------------------------------------------------------
    # ANALYSIS OUTPUT
    # --------------------------------------------------------

    summary = models.TextField(
        blank=True,
    )

    chart_data = models.JSONField(
        default=list,
        blank=True,
    )

    anomaly_data = models.JSONField(
        default=list,
        blank=True,
    )

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.metric_column} - "
            f"{self.detection_method} "
            f"({self.anomaly_count} anomalies)"
        )
# ============================================================
# ROOT CAUSE ANALYSIS RESULT
# ============================================================

class RootCauseResult(models.Model):

    insight_run = models.OneToOneField(
        InsightRun,
        on_delete=models.CASCADE,
        related_name="root_cause_result",
    )

    # ========================================================
    # SOURCE COLUMNS
    # ========================================================

    metric_column = models.CharField(
        max_length=255,
    )

    date_column = models.CharField(
        max_length=255,
        blank=True,
    )

    dimension_column = models.CharField(
        max_length=255,
        blank=True,
    )

    # ========================================================
    # ANALYSIS SETTINGS
    # ========================================================

    analysis_type = models.CharField(
        max_length=50,
        default="Contribution Analysis",
    )

    target_period = models.CharField(
        max_length=100,
        blank=True,
    )

    comparison_period = models.CharField(
        max_length=100,
        blank=True,
    )

    # ========================================================
    # OVERALL RESULT
    # ========================================================

    total_value = models.FloatField(
        null=True,
        blank=True,
    )

    comparison_value = models.FloatField(
        null=True,
        blank=True,
    )

    change_value = models.FloatField(
        null=True,
        blank=True,
    )

    change_percentage = models.FloatField(
        null=True,
        blank=True,
    )

    # ========================================================
    # ROOT CAUSE INFORMATION
    # ========================================================

    primary_cause = models.CharField(
        max_length=255,
        blank=True,
    )

    primary_cause_contribution = models.FloatField(
        null=True,
        blank=True,
    )

    cause_count = models.PositiveIntegerField(
        default=0,
    )

    # ========================================================
    # ANALYSIS OUTPUT
    # ========================================================

    summary = models.TextField(
        blank=True,
    )

    cause_data = models.JSONField(
        default=list,
        blank=True,
    )

    chart_data = models.JSONField(
        default=list,
        blank=True,
    )

    # ========================================================
    # TIMESTAMP
    # ========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.metric_column} - "
            f"Root Cause Analysis"
        )
# ============================================================
# CUSTOMER SEGMENTATION RESULT
# ============================================================

class CustomerSegmentationResult(models.Model):
    """
    Stores the result of a Customer Segmentation analysis.

    The analysis is linked to the exact InsightRun and therefore
    to the exact DatasetVersion used for the segmentation.
    """

    insight_run = models.OneToOneField(
        InsightRun,
        on_delete=models.CASCADE,
        related_name="customer_segmentation_result",
    )

    # --------------------------------------------------------
    # Source columns
    # --------------------------------------------------------

    customer_column = models.CharField(
        max_length=255,
    )

    metric_columns = models.JSONField(
        default=list,
        blank=True,
    )

    # --------------------------------------------------------
    # Segmentation configuration
    # --------------------------------------------------------

    segmentation_method = models.CharField(
        max_length=100,
        default="RFM",
    )

    number_of_segments = models.PositiveIntegerField(
        default=4,
    )

    # --------------------------------------------------------
    # Dataset statistics
    # --------------------------------------------------------

    total_records = models.PositiveIntegerField(
        default=0,
    )

    total_customers = models.PositiveIntegerField(
        default=0,
    )

    segmented_customers = models.PositiveIntegerField(
        default=0,
    )

    # --------------------------------------------------------
    # Segment summary
    # --------------------------------------------------------

    segment_count = models.PositiveIntegerField(
        default=0,
    )

    largest_segment = models.CharField(
        max_length=255,
        blank=True,
    )

    largest_segment_count = models.PositiveIntegerField(
        default=0,
    )

    # --------------------------------------------------------
    # Overall summary
    # --------------------------------------------------------

    summary = models.TextField(
        blank=True,
    )

    # --------------------------------------------------------
    # Detailed segmentation data
    # --------------------------------------------------------

    segment_data = models.JSONField(
        default=list,
        blank=True,
    )

    customer_data = models.JSONField(
        default=list,
        blank=True,
    )

    chart_data = models.JSONField(
        default=list,
        blank=True,
    )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.segmentation_method} - "
            f"{self.segment_count} segments"
        )
class ChurnRiskResult(models.Model):
    insight_run = models.OneToOneField(
        InsightRun,
        on_delete=models.CASCADE,
        related_name="churn_risk_result",
    )

    customer_column = models.CharField(max_length=255)

    date_column = models.CharField(
        max_length=255,
        blank=True,
    )

    metric_columns = models.JSONField(
        default=list,
        blank=True,
    )

    risk_method = models.CharField(
        max_length=100,
        default="Activity-Based Risk Analysis",
    )

    total_records = models.PositiveIntegerField(
        default=0,
    )

    total_customers = models.PositiveIntegerField(
        default=0,
    )

    assessed_customers = models.PositiveIntegerField(
        default=0,
    )

    high_risk_customers = models.PositiveIntegerField(
        default=0,
    )

    medium_risk_customers = models.PositiveIntegerField(
        default=0,
    )

    low_risk_customers = models.PositiveIntegerField(
        default=0,
    )

    high_risk_percentage = models.FloatField(
        default=0,
    )

    average_risk_score = models.FloatField(
        default=0,
    )

    highest_risk_customer = models.CharField(
        max_length=255,
        blank=True,
    )

    highest_risk_score = models.FloatField(
        default=0,
    )

    summary = models.TextField(
        blank=True,
    )

    risk_data = models.JSONField(
        default=list,
        blank=True,
    )

    customer_data = models.JSONField(
        default=list,
        blank=True,
    )

    chart_data = models.JSONField(
        default=list,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.risk_method} - "
            f"{self.high_risk_customers} high-risk customers"
        )
# ============================================================
# OPPORTUNITY DETECTION RESULT
# ============================================================

class OpportunityDetectionResult(models.Model):
    """
    Stores the result of an Opportunity Detection analysis.

    The analysis is always linked to the exact dataset and
    dataset version used, so historical results remain traceable.
    """

    insight_run = models.OneToOneField(
        InsightRun,
        on_delete=models.CASCADE,
        related_name="opportunity_detection_result",
    )

    # --------------------------------------------------------
    # SELECTED COLUMNS
    # --------------------------------------------------------

    dimension_column = models.CharField(
        max_length=255,
        blank=True,
    )

    value_column = models.CharField(
        max_length=255,
        blank=True,
    )

    date_column = models.CharField(
        max_length=255,
        blank=True,
    )

    # --------------------------------------------------------
    # ANALYSIS METHOD
    # --------------------------------------------------------

    opportunity_method = models.CharField(
        max_length=255,
        blank=True,
    )

    # --------------------------------------------------------
    # RECORD COUNTS
    # --------------------------------------------------------

    total_records = models.PositiveIntegerField(
        default=0,
    )

    total_opportunities = models.PositiveIntegerField(
        default=0,
    )

    high_opportunities = models.PositiveIntegerField(
        default=0,
    )

    medium_opportunities = models.PositiveIntegerField(
        default=0,
    )

    low_opportunities = models.PositiveIntegerField(
        default=0,
    )

    # --------------------------------------------------------
    # OPPORTUNITY METRICS
    # --------------------------------------------------------

    opportunity_percentage = models.FloatField(
        default=0,
    )

    average_opportunity_score = models.FloatField(
        default=0,
    )

    highest_opportunity = models.CharField(
        max_length=255,
        blank=True,
    )

    highest_opportunity_score = models.FloatField(
        default=0,
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = models.TextField(
        blank=True,
    )

    # --------------------------------------------------------
    # STORED ANALYSIS DATA
    # --------------------------------------------------------

    opportunity_data = models.JSONField(
        default=list,
        blank=True,
    )

    opportunity_details = models.JSONField(
        default=list,
        blank=True,
    )

    chart_data = models.JSONField(
        default=dict,
        blank=True,
    )

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return (
            f"Opportunity Detection - "
            f"{self.insight_run_id}"
        )