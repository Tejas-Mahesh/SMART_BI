from django.db import models


class ContactMessage(models.Model):

    STATUS_CHOICES = [
        ("New", "New"),
        ("Read", "Read"),
        ("Replied", "Replied"),
        ("Archived", "Archived"),
    ]

    name = models.CharField(
        max_length=150
    )

    email = models.EmailField()

    subject = models.CharField(
        max_length=255
    )

    message = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="New"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.name} - {self.subject}"