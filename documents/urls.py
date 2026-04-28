from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, DocumentRequestViewSet

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'requests', DocumentRequestViewSet, basename='doc-request')

urlpatterns = [
    path('', include(router.urls)),
]
