
from django.conf import settings
from django.db import models


# ============================================================
# AUTOMATED REPORT
# ============================================================

class AutomatedReport(models.Model):

    REPORT_TYPE_CHOICES = [
        ("Executive", "Executive"),
        ("Sales", "Sales"),
        ("Customer", "Customer"),
        ("Product", "Product"),
        ("Regional", "Regional"),
        ("Marketing", "Marketing"),
        ("Financial", "Financial"),
        ("Returns", "Returns"),
        ("Operational", "Operational"),
    ]

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Generating", "Generating"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    FORMAT_CHOICES = [
        ("Dashboard", "Dashboard"),
        ("PDF", "PDF"),
        ("Excel", "Excel"),
    ]

    # --------------------------------------------------------
    # DATA SOURCE
    # --------------------------------------------------------

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="automated_reports",
    )

    dataset_version = models.ForeignKey(
        "data_management.DatasetVersion",
        on_delete=models.CASCADE,
        related_name="automated_reports",
    )

    # --------------------------------------------------------
    # USER
    # --------------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="automated_reports",
    )

    # --------------------------------------------------------
    # REPORT INFORMATION
    # --------------------------------------------------------

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    report_type = models.CharField(
        max_length=30,
        choices=REPORT_TYPE_CHOICES,
        default="Executive",
    )

    # --------------------------------------------------------
    # REPORT STATUS / FORMAT
    # --------------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Draft",
    )

    output_format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        default="Dashboard",
    )

    # --------------------------------------------------------
    # GENERATED REPORT CONTENT
    # --------------------------------------------------------

    summary = models.JSONField(
        default=dict,
        blank=True,
    )

    kpis = models.JSONField(
    default=list,
    blank=True,
)

    sections = models.JSONField(
        default=list,
        blank=True,
    )

    charts = models.JSONField(
        default=list,
        blank=True,
    )

    insights = models.JSONField(
        default=list,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    # --------------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------------

    error_message = models.TextField(
        blank=True,
        default="",
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # --------------------------------------------------------
    # MODEL META
    # --------------------------------------------------------

    class Meta:
        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "dataset",
                    "dataset_version",
                ]
            ),
            models.Index(
                fields=[
                    "created_by",
                ]
            ),
            models.Index(
                fields=[
                    "report_type",
                ]
            ),
            models.Index(
                fields=[
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "output_format",
                ]
            ),
            models.Index(
                fields=[
                    "generated_at",
                ]
            ),
            models.Index(
                fields=[
                    "created_at",
                ]
            ),
        ]

    # --------------------------------------------------------
    # STRING REPRESENTATION
    # --------------------------------------------------------

    def __str__(self):
        return self.title

class CustomReport(models.Model):

    REPORT_TYPE_CHOICES = [
        ("Executive", "Executive"),
        ("Sales", "Sales"),
        ("Customer", "Customer"),
        ("Product", "Product"),
        ("Regional", "Regional"),
        ("Marketing", "Marketing"),
        ("Financial", "Financial"),
        ("Returns", "Returns"),
        ("Operational", "Operational"),
    ]

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Generating", "Generating"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    OUTPUT_FORMAT_CHOICES = [
        ("Dashboard", "Dashboard"),
        ("PDF", "PDF"),
        ("Excel", "Excel"),
    ]

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="custom_reports",
    )

    dataset_version = models.ForeignKey(
        "data_management.DatasetVersion",
        on_delete=models.CASCADE,
        related_name="custom_reports",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custom_reports",
    )

    title = models.CharField(max_length=255)

    description = models.TextField(
        blank=True,
        default="",
    )

    report_type = models.CharField(
        max_length=30,
        choices=REPORT_TYPE_CHOICES,
        default="Executive",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Draft",
    )

    output_format = models.CharField(
        max_length=20,
        choices=OUTPUT_FORMAT_CHOICES,
        default="Dashboard",
    )

    # User-selected report configuration
    selected_columns = models.JSONField(
        default=list,
        blank=True,
    )

    selected_metrics = models.JSONField(
        default=list,
        blank=True,
    )

    selected_dimensions = models.JSONField(
        default=list,
        blank=True,
    )

    filters = models.JSONField(
        default=list,
        blank=True,
    )

    sort_configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    chart_configuration = models.JSONField(
        default=list,
        blank=True,
    )

    # Generated report data
    summary = models.JSONField(
        default=dict,
        blank=True,
    )

    kpis = models.JSONField(
        default=list,
        blank=True,
    )

    sections = models.JSONField(
        default=list,
        blank=True,
    )

    charts = models.JSONField(
        default=list,
        blank=True,
    )

    insights = models.JSONField(
        default=list,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["dataset", "dataset_version"]
            ),
            models.Index(
                fields=["created_by"]
            ),
            models.Index(
                fields=["report_type"]
            ),
            models.Index(
                fields=["status"]
            ),
            models.Index(
                fields=["output_format"]
            ),
            models.Index(
                fields=["generated_at"]
            ),
            models.Index(
                fields=["created_at"]
            ),
        ]

    def __str__(self):
        return self.title
