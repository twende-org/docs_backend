from django.contrib import admin
from .models import Document, DocumentRequest

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'doc_type', 'status', 'created_at')
    list_filter = ('doc_type', 'status')
    search_fields = ('title', 'user__email', 'customer_name')

@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = ('doc_name', 'user', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('doc_name', 'user__email')
    list_editable = ('status',)
