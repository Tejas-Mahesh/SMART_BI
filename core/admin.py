from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):

    # ============================================================
    # LIST DISPLAY
    # ============================================================

    list_display = (
        "name",
        "email",
        "subject",
        "status",
        "created_at",
        "updated_at",
    )

    # ============================================================
    # FILTERS
    # ============================================================

    list_filter = (
        "status",
        "created_at",
        "updated_at",
    )

    # ============================================================
    # SEARCH
    # ============================================================

    search_fields = (
        "name",
        "email",
        "subject",
        "message",
    )

    # ============================================================
    # DEFAULT ORDER
    # ============================================================

    ordering = (
        "-created_at",
    )

    # ============================================================
    # READ-ONLY FIELDS
    # ============================================================

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    # ============================================================
    # FORM LAYOUT
    # ============================================================

    fieldsets = (

        (
            "Contact Information",
            {
                "fields": (
                    "name",
                    "email",
                    "subject",
                )
            },
        ),

        (
            "Message",
            {
                "fields": (
                    "message",
                )
            },
        ),

        (
            "Message Status",
            {
                "fields": (
                    "status",
                )
            },
        ),

        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),

    )