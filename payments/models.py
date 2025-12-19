from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class Transaction(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)  # Added
    account_number = models.CharField(max_length=20, blank=True, null=True)
    provider = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=50, default="PENDING")  
    raw_checkout = models.JSONField(blank=True, null=True)  # Added
    raw_callback = models.JSONField(blank=True, null=True)
    raw_webhook = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.external_id} - {self.status}"

class UserCredit(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="credit"
    )
    downloads_remaining = models.IntegerField(default=0)  # e.g., 3 per 3000 TZS
    total_credits = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.downloads_remaining} downloads left"
    

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_credit(sender, instance, created, **kwargs):
    if created:
        UserCredit.objects.create(user=instance)