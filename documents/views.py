import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Document
from .serializers import DocumentSerializer
from api.services.ai_service import make_ai_call, extract_json_from_text

from .services import CreditEnforcement

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Document.objects.filter(user=self.request.user)
        return Document.objects.none()

    def perform_create(self, serializer):
        # Validate that if the user is an agent, they have at least 1 credit
        CreditEnforcement.ensure_agent_can_create(self.request.user)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        new_status = self.request.data.get('status')
        
        # Trigger credit deduction for Agents when moving from DRAFT to FINAL
        CreditEnforcement.handle_finalization(self.request.user, instance.status, new_status)
        
        serializer.save()

    @action(detail=False, methods=['post'], url_path='validate')
    def validate_document(self, request):
        # Enforce agent credit check via service
        CreditEnforcement.ensure_agent_can_create(request.user)

        return Response({
            "status": "valid",
            "message": "Credit check passed and document type is valid."
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def polish(self, request, pk=None):
        """
        Use high-performance AI to improve the language and tone.
        """
        document = self.get_object()
        from api.services.ai_service import AIService
        
        result = AIService.polish_document(request.user, document.doc_type, document.content)
        
        if result.get('success'):
            document.content = result['data']
            document.is_polished = True
            document.save()
            return Response(DocumentSerializer(document).data)
        
        return Response({
            "error": result.get('error', "AI polishing failed."),
            "data": document.content # Fallback
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Generate and download a high-quality PDF.
        """
        from .utils import generate_unified_pdf
        from django.http import HttpResponse
        
        document = self.get_object()
        try:
            pdf_buffer = generate_unified_pdf(document)
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{document.doc_type}_{document.id}.pdf"'
            return response
        except Exception as e:
            return Response({"error": f"Failed to generate PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
