from django.contrib import admin
from .models import Risala

@admin.register(Risala)
class RisalaAdmin(admin.ModelAdmin):
    # Fields to display in the list view
    list_display = (
        "event_type",
        "event_title",
        "event_date",
        "event_location",
        "guest_of_honor",
        "created_at",
    )

    # Enable filtering by these fields
    list_filter = ("event_type", "event_date", "created_at")

    # Enable search by these fields
    search_fields = ("event_title", "guest_of_honor", "organization_name", "bride_name", "groom_name")

    # Ordering
    ordering = ("-created_at",)

    # Optional: fields grouping in form
    fieldsets = (
        ("Step 1: Tukio", {
            "fields": ("event_type", "event_title", "event_date", "event_location")
        }),
        ("Step 2: Mgeni Rasmi / Taasisi", {
            "fields": ("guest_of_honor", "guest_title", "organization_name", "organization_representative")
        }),
        ("Step 3: Maudhui ya Risala", {
            "fields": ("purpose_statement", "background_info", "main_message")
        }),
        ("Step 4: Maelezo ya Tukio Maalum", {
            "fields": ("bride_name", "groom_name", "wedding_theme", "deceased_name", "relationship", "tribute_summary")
        }),
        ("Step 5: Mwisho", {
            "fields": ("requests", "closing_statement", "presenter_name", "presenter_title")
        }),
    )
