from django.db import transaction
from .models import UserCredit
import os
import requests
import uuid

class CreditService:
    @staticmethod
    def get_user_role(user):
        return getattr(user, 'role', 'customer')

    @staticmethod
    def has_sufficient_credits(user):
        """
        Temporarily allowing free downloads for all users.
        Payment functionality remains ready but is not enforced.
        """
        return True

    @staticmethod
    def deduct_credit(user):
        """
        Temporarily bypassing credit deduction.
        """
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

class SnippeService:
    BASE_URL = "https://api.snippe.sh/v1"
    
    @staticmethod
    def get_headers():
        api_key = os.getenv("SNIPPE_API_KEY")
        # Keys must be 30 characters or fewer
        idempotency_key = str(uuid.uuid4()).replace("-", "")[:30]
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key
        }

    @classmethod
    def initiate_payment(cls, amount, payment_type, customer_data, phone_number=None, metadata=None):
        """
        Initiate a payment with Snippe based on 2026-01-25 documentation.
        """
        url = f"{cls.BASE_URL}/payments"
        
        # Base details
        details = {
            "amount": int(amount),
            "currency": "TZS"
        }
        
        # Add card specific URLs
        if payment_type == "card":
            frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
            details["redirect_url"] = f"{frontend_url}/dashboard?payment=success"
            details["cancel_url"] = f"{frontend_url}/pricing?payment=cancelled"

        payload = {
            "payment_type": payment_type,
            "details": details,
            "customer": {
                "firstname": customer_data.get("first_name", "Customer"),
                "lastname": customer_data.get("last_name", "User"),
                "email": customer_data.get("email", "")
            },
            "webhook_url": os.getenv("SNIPPE_WEBHOOK_URL"),
            "metadata": metadata or {}
        }

        # Mobile needs phone_number at top level (based on docs)
        if phone_number:
            payload["phone_number"] = phone_number

        # Card requires more customer fields
        if payment_type == "card":
            payload["customer"].update({
                "address": customer_data.get("address", "N/A"),
                "city": customer_data.get("city", "DSM"),
                "state": customer_data.get("state", "DSM"),
                "postcode": customer_data.get("postcode", "00000"),
                "country": customer_data.get("country", "TZ")
            })

        try:
            response = requests.post(url, json=payload, headers=cls.get_headers(), timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"SNIPPE ERROR: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    return e.response.json()
                except:
                    pass
            return {"status": "error", "message": str(e)}

    @staticmethod
    def verify_webhook(payload, signature):
        """
        Verify Snippe webhook signature.
        """
        secret = os.getenv("SNIPPE_WEBHOOK_SECRET")
        if not secret or not signature:
            return False
            
        import hmac
        import hashlib
        
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, signature)
