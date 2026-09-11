from django.conf import settings
from django.db import models


class Dataset(models.Model):

    DATASET_TYPES = [
        ("Sales", "Sales"),
        ("Customers", "Customers"),
        ("Products", "Products"),
        ("Regional", "Regional"),
        ("Marketing", "Marketing"),
        ("Financial", "Financial"),
        ("Returns", "Returns"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="datasets"
    )

    name = models.CharField(
        max_length=255
    )

    dataset_type = models.CharField(
        max_length=30,
        choices=DATASET_TYPES
    )

    file = models.FileField(
        upload_to="datasets/"
    )

    original_filename = models.CharField(
        max_length=255,
        blank=True
    )

    file_size = models.PositiveBigIntegerField(
        default=0
    )

    total_rows = models.PositiveIntegerField(
        default=0
    )

    total_columns = models.PositiveIntegerField(
        default=0
    )

    missing_values = models.PositiveIntegerField(
        default=0
    )

    duplicate_rows = models.PositiveIntegerField(
        default=0
    )

    quality_score = models.FloatField(
        default=0
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.name} - {self.dataset_type}"

# ============================================================
# DATASET VERSION HISTORY
# ============================================================

class DatasetVersion(models.Model):

    VERSION_TYPES = [
        ("Original", "Original"),
        ("Cleaned", "Cleaned"),
        ("Validated", "Validated"),
        ("Transformed", "Transformed"),
        ("Manual", "Manual"),
    ]

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="versions"
    )

    version_number = models.PositiveIntegerField(
        default=1
    )

    version_type = models.CharField(
        max_length=30,
        choices=VERSION_TYPES,
        default="Original"
    )

    file = models.FileField(
        upload_to="dataset_versions/"
    )

    file_name = models.CharField(
        max_length=255
    )

    file_size = models.PositiveBigIntegerField(
        default=0
    )

    total_rows = models.PositiveIntegerField(
        default=0
    )

    total_columns = models.PositiveIntegerField(
        default=0
    )

    missing_values = models.PositiveIntegerField(
        default=0
    )

    duplicate_rows = models.PositiveIntegerField(
        default=0
    )

    quality_score = models.FloatField(
        default=0
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_current = models.BooleanField(
        default=False
    )

    class Meta:

        ordering = [
            "-version_number",
            "-created_at"
        ]

        unique_together = [
            "dataset",
            "version_number"
        ]

    def __str__(self):

        return (
            f"{self.dataset.name} "
            f"- Version {self.version_number}"
        )

class DatasetActivity(models.Model):

    ACTIVITY_TYPES = [
        ("Uploaded", "Uploaded"),
        ("Validated", "Validated"),
        ("Profiled", "Profiled"),
        ("Quality Checked", "Quality Checked"),
        ("Cleaned", "Cleaned"),
        ("Transformed", "Transformed"),
        ("Analytics Ready", "Analytics Ready"),
    ]

    STATUS_CHOICES = [
        ("Success", "Success"),
        ("Warning", "Warning"),
        ("Failed", "Failed"),
    ]

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    activity_type = models.CharField(
        max_length=40,
        choices=ACTIVITY_TYPES
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Success"
    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    details = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.dataset.name} - {self.activity_type}"