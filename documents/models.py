from django.db import models
from django.conf import settings

class Document(models.Model):
    DOCUMENT_TYPES = [
        ('CV', 'Curriculum Vitae'),
        ('INVOICE', 'Business Invoice'),
        ('LETTER', 'General/Official Letter'),
        ('QUOTATION', 'Quotation'),
        ('PROFORMA', 'Proforma Invoice'),
        ('AFFIDAVIT', 'Affidavit'),
        ('CONTRACT', 'Personal Contract'),
        ('EVENT_PROGRAM', 'Event Program'),
        ('OTHER', 'Other Document'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=255)
    customer_name = models.CharField(max_length=255, blank=True, null=True, help_text="For agents creating docs for others")
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    content = models.JSONField(help_text="Flexible JSON storage for all document fields")
    status = models.CharField(max_length=20, default='DRAFT', choices=[('DRAFT', 'Draft'), ('FINAL', 'Final')])
    is_polished = models.BooleanField(default=False, help_text="Checked if AI has optimized the content")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.get_doc_type_display()}: {self.title} ({self.user.username})"
