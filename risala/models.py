from django.conf import settings
from django.db import models

EVENT_TYPES = [
    ("harusi", "Harusi"),
    ("msiba", "Msiba"),
    ("uzinduzi", "Uzinduzi"),
    ("mgeni_rasmi", "Mgeni Rasmi"),
]

class Risala(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    event_title = models.CharField(max_length=255, blank=True)
    event_date = models.DateField(null=True, blank=True)
    event_location = models.CharField(max_length=255, blank=True)

    # Step 2
    guest_of_honor = models.CharField(max_length=255, blank=True)
    guest_title = models.CharField(max_length=255, blank=True)
    organization_name = models.CharField(max_length=255, blank=True)
    organization_representative = models.CharField(max_length=255, blank=True)

    # Step 3
    purpose_statement = models.TextField(blank=True)
    background_info = models.TextField(blank=True)
    main_message = models.TextField(blank=True)

    # Step 4 - uzinduzi
    project_name = models.CharField(max_length=255, blank=True)
    project_goal = models.TextField(blank=True)
    project_beneficiaries = models.TextField(blank=True)

    # Step 4 - mgeni rasmi
    program_name = models.CharField(max_length=255, blank=True)
    program_theme = models.CharField(max_length=255, blank=True)

    # Step 4 - harusi example
    bride_name = models.CharField(max_length=255, blank=True)
    groom_name = models.CharField(max_length=255, blank=True)
    wedding_theme = models.CharField(max_length=255, blank=True)

    # Step 4 - msiba example
    deceased_name = models.CharField(max_length=255, blank=True)
    relationship = models.CharField(max_length=255, blank=True)
    tribute_summary = models.TextField(blank=True)

    # Step 5
    requests = models.TextField(blank=True)
    closing_statement = models.TextField(blank=True)
    presenter_name = models.CharField(max_length=255, blank=True)
    presenter_title = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.event_type} - {self.event_title}"
