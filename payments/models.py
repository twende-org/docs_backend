from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
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
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.downloads_remaining} downloads left"
    
    @property
    def is_in_trial(self):
        """Check if the user is currently in their free trial period."""
        if self.trial_ends_at:
            return timezone.now() < self.trial_ends_at
        return False
    

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_credit(sender, instance, created, **kwargs):
    if created:
        # Default trial period: 20 days
        trial_end = timezone.now() + timezone.timedelta(days=20)
        UserCredit.objects.create(user=instance, trial_ends_at=trial_end)