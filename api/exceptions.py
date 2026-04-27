from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def global_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # If an unexpected error occurs (500), return a clean JSON
    if response is None:
        logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
        return Response({
            "error": "Internal Server Error",
            "message": "The Factory is currently experiencing a technical glitch. Please try again shortly.",
            "detail": str(exc) if hasattr(exc, 'message') else "No additional details."
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Standardize the format for validation errors (400)
    if response.status_code == 400:
        response.data = {
            "error": "Validation Failed",
            "message": "Please check your inputs and try again.",
            "fields": response.data
        }
    
    # Standardize credit/permission errors (403)
    elif response.status_code == 403:
        response.data = {
            "error": "Access Denied",
            "message": response.data.get('detail', "You do not have permission or sufficient credits for this action.")
        }

    return response
