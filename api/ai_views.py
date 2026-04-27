from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .services.hardened_ai_service import AIService

class AIPolishView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        doc_type = request.data.get("type", "CV")
        data = request.data.get("data")

        if not data:
            return Response(
                {"success": False, "error": "No document data provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Call the hardened AI service
        result = AIService.polish_document(request.user, doc_type, data)
        
        if result.get("success"):
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_429_TOO_MANY_REQUESTS if "limit" in result["error"] else status.HTTP_500_INTERNAL_SERVER_ERROR)
