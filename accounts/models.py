from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    APPROVAL_PENDING = "Pending"
    APPROVAL_APPROVED = "Approved"
    APPROVAL_REJECTED = "Rejected"

    APPROVAL_CHOICES = [
        (APPROVAL_PENDING, "Pending"),
        (APPROVAL_APPROVED, "Approved"),
        (APPROVAL_REJECTED, "Rejected"),
    ]

    USER_TYPE_CHOICES = [
        ("Business User", "Business User"),
        ("Analyst", "Analyst"),
    ]

    email = models.EmailField(unique=True)

    user_type = models.CharField(
        max_length=30,
        choices=USER_TYPE_CHOICES,
        default="Business User"
    )

    company_name = models.CharField(
        max_length=200,
        blank=True
    )

    business_logo = models.ImageField(
        upload_to="business_logos/",
        blank=True,
        null=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default=APPROVAL_PENDING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.username