from rest_framework import serializers, exceptions
from .models import Document
from .schemas import get_document_schema
from payments.services import CreditService

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'user', 'doc_type', 'title', 'customer_name', 'customer_phone', 'content', 'status', 'is_polished', 'created_at', 'updated_at']
        read_only_fields = ['user', 'is_polished', 'created_at', 'updated_at']

    def validate_content(self, value):
        doc_type = self.initial_data.get('doc_type')
        if not doc_type:
            raise serializers.ValidationError("doc_type is required to validate content.")

        schema = get_document_schema(doc_type)
        required_fields = schema.get('required', [])
        
        missing = [f for f in required_fields if f not in value or not value[f]]
        
        if missing:
            raise serializers.ValidationError(
                f"Missing required fields for {doc_type}: {', '.join(missing)}"
            )
        
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        is_final = validated_data.get('status') == 'FINAL'
        
        # Enforce credit system on finalization
        if not user.is_staff and is_final:
            is_agent = getattr(user, 'role', 'customer') == 'agent'
            
            if not CreditService.has_sufficient_credits(user):
                msg = "Insufficient credits to finalize this document."
                if is_agent:
                    msg = "Agent credit exhausted. Please top up to issue more documents."
                raise exceptions.PermissionDenied(msg)
            
            CreditService.deduct_credit(user)

        validated_data['user'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user = self.context['request'].user
        was_draft = instance.status == 'DRAFT'
        is_final = validated_data.get('status') == 'FINAL'

        if was_draft and is_final and not user.is_staff:
             if not CreditService.has_sufficient_credits(user):
                raise exceptions.PermissionDenied("Insufficient credits to finalize this document.")
             CreditService.deduct_credit(user)

        return super().update(instance, validated_data)
