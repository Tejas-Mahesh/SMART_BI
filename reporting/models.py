from django.conf import settings
from django.db import models


class Report(models.Model):

    REPORT_TYPE_CHOICES = [
        ("Business Summary", "Business Summary"),
        ("Sales Report", "Sales Report"),
        ("Customer Report", "Customer Report"),
        ("Product Report", "Product Report"),
        ("Regional Report", "Regional Report"),
        ("Financial Report", "Financial Report"),
        ("Marketing Report", "Marketing Report"),
        ("Decision Report", "Decision Report"),
        ("Executive Report", "Executive Report"),
    ]

    FORMAT_CHOICES = [
        ("PDF", "PDF"),
        ("Excel", "Excel"),
        ("Both", "Both"),
    ]

    STATUS_CHOICES = [
        ("Generated", "Generated"),
        ("Processing", "Processing"),
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
        null=True,
        blank=True,
    )

    title = models.CharField(
        max_length=255
    )

    report_type = models.CharField(
        max_length=50,
        choices=REPORT_TYPE_CHOICES,
        default="Business Summary",
    )

    output_format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        default="PDF",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Generated",
    )

    description = models.TextField(
        blank=True
    )

    total_recommendations = models.PositiveIntegerField(
        default=0
    )

    critical_recommendations = models.PositiveIntegerField(
        default=0
    )

    high_recommendations = models.PositiveIntegerField(
        default=0
    )

    average_decision_score = models.FloatField(
        default=0
    )

    learning_score = models.FloatField(
        default=0
    )

    feedback_learning_score = models.FloatField(
        default=0
    )

    report_data = models.JSONField(
        default=dict,
        blank=True,
    )

    pdf_file = models.FileField(
        upload_to="reports/pdf/",
        blank=True,
        null=True,
    )

    excel_file = models.FileField(
        upload_to="reports/excel/",
        blank=True,
        null=True,
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
        return self.title