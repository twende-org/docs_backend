from rest_framework.exceptions import PermissionDenied
from payments.services import CreditService

class CreditEnforcement:
    @staticmethod
    def ensure_agent_can_create(user):
        """
        Ensures that if the user is an agent, they have at least 1 credit.
        Raises PermissionDenied if they are out of credits.
        """
        if getattr(user, 'role', 'customer') == 'agent':
            if not CreditService.has_sufficient_credits(user):
                raise PermissionDenied({
                    "status": "error",
                    "code": "insufficient_credits",
                    "message": "Your agent account has 0 credits. Please top up to continue."
                })
        return True

    @staticmethod
    def handle_finalization(user, old_status, new_status):
        """
        When a document moves from DRAFT to FINAL, deduct 1 credit from the agent.
        """
        if old_status == 'DRAFT' and new_status == 'FINAL':
            if getattr(user, 'role', 'customer') == 'agent':
                if not CreditService.deduct_credit(user):
                    raise PermissionDenied({
                        "status": "error",
                        "code": "insufficient_credits",
                        "message": "Insufficient credits to finalize this document."
                    })
        return True
