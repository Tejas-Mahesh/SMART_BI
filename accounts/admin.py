from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "company_name",
        "user_type",
        "approval_status",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "approval_status",
        "user_type",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "company_name",
        "phone_number",
    )

    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "Business Information",
            {
                "fields": (
                    "company_name",
                    "phone_number",
                    "user_type",
                    "approval_status",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Business Information",
            {
                "fields": (
                    "email",
                    "company_name",
                    "phone_number",
                    "user_type",
                    "approval_status",
                )
            },
        ),
    )