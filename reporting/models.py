from django.conf import settings
from django.db import models


class Report(models.Model):
    """
    Stores a generated report and the exact dataset version
    used to generate it.
    """

    REPORT_TYPE_CHOICES = [
        ("Automated", "Automated"),
        ("Custom", "Custom"),
    ]

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Generating", "Generating"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    dataset = models.ForeignKey(
        "data_management.Dataset",
        on_delete=models.CASCADE,
        related_name="reports",
    )

    dataset_version = models.ForeignKey(
        "data_management.DatasetVersion",
        on_delete=models.CASCADE,
        related_name="reports",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default="Automated",
    )

    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Stores the report configuration, filters, "
            "metrics, dimensions, date range, and chart settings."
        ),
    )

    generated_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Stores the generated report summary, KPIs, "
            "tables, trends, and other report results."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Draft",
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "owner",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "dataset",
                    "dataset_version",
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
        ]

    def __str__(self):
        return self.name


class CustomReport(models.Model):
    """
    Stores a reusable custom report definition.

    This model stores the user's configuration rather than
    duplicating the underlying dataset.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="custom_reports",
    )

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

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Stores selected columns, metrics, dimensions, "
            "filters, date range, charts, and layout settings."
        ),
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]

        indexes = [
            models.Index(
                fields=[
                    "owner",
                    "is_active",
                ]
            ),
            models.Index(
                fields=[
                    "dataset",
                    "dataset_version",
                ]
            ),
            models.Index(
                fields=[
                    "created_at",
                ]
            ),
        ]

    def __str__(self):
        return self.name


class ReportExport(models.Model):
    """
    Stores PDF and Excel exports generated from a report.
    """

    EXPORT_TYPE_CHOICES = [
        ("PDF", "PDF"),
        ("Excel", "Excel"),
    ]

    STATUS_CHOICES = [
        ("Generating", "Generating"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="exports",
    )

    export_type = models.CharField(
        max_length=10,
        choices=EXPORT_TYPE_CHOICES,
    )

    file = models.FileField(
        upload_to="reports/exports/",
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Generating",
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "report",
                    "export_type",
                ]
            ),
            models.Index(
                fields=[
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "created_at",
                ]
            ),
        ]

    def __str__(self):
        return f"{self.report.name} - {self.export_type}"