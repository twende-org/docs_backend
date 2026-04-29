from django.db import transaction
from .models import UserCredit

class CreditService:
    @staticmethod
    def get_user_role(user):
        return getattr(user, 'role', 'customer')

    @staticmethod
    def has_sufficient_credits(user):
        """
        Check if user/agent has at least 1 credit remaining.
        Agents require credits for all document types.
        Standard users might have free tiers or different rules.
        """
        if user.is_staff:
            return True
            
        credit, _ = UserCredit.objects.get_or_create(user=user)
        
        # Free Trial Bypass
        if credit.is_in_trial:
            return True
            
        role = CreditService.get_user_role(user)
        
        if role == 'agent':
            return credit.downloads_remaining > 0
            
        # Standard customer logic (could be 1 free doc, etc.)
        return credit.downloads_remaining > 0

    @staticmethod
    def deduct_credit(user):
        """Atomically deduct a credit from the user's account."""
        if user.is_staff:
            return True
            
        with transaction.atomic():
            credit = UserCredit.objects.select_for_update().get(user=user)
            
            # Skip deduction if in trial
            if credit.is_in_trial:
                return True
                
            if credit.downloads_remaining <= 0:
                return False
            credit.downloads_remaining -= 1
            credit.save()
            return True

    @staticmethod
    def add_credits(user, amount_paid):
        """Add credits based on payment amount (3 credits per 3000 TZS)."""
        downloads_per_unit = 3
        price_per_unit = 3000
        credits_to_add = int((amount_paid // price_per_unit) * downloads_per_unit)
        
        if credits_to_add <= 0:
            return 0
            
        with transaction.atomic():
            credit, _ = UserCredit.objects.select_for_update().get_or_create(user=user)
            credit.downloads_remaining += credits_to_add
            credit.total_credits += credits_to_add
            credit.save()
            return credits_to_add
