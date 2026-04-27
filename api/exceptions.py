from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def global_exception_handler(exc, context):
    """
    Standardize error responses across the API.
    Format: { "error": "Main error message", "details": {...} or None, "code": "error_code" }
    """
    # Call REST framework's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "status": "error",
            "message": "An error occurred during the request.",
            "code": exc.__class__.__name__.lower(),
            "details": response.data
        }

        # Improve readability of common error messages
        if isinstance(response.data, dict):
            if "detail" in response.data:
                custom_data["message"] = response.data["detail"]
            elif len(response.data) > 0:
                # If there are field-specific errors, use the first one as the main message
                first_field = list(response.data.keys())[0]
                first_error = response.data[first_field]
                if isinstance(first_error, list):
                    first_error = first_error[0]
                custom_data["message"] = f"Error in {first_field}: {first_error}"

        response.data = custom_data

    return response
