from django.urls import path
from .views import GenerateAIValuesAPIView, RisalaAPIView

urlpatterns = [
    path("risala/ai/generate/", GenerateAIValuesAPIView.as_view(), name="ai-generate"),
    path("risala/", RisalaAPIView.as_view(), name="risala-user"),  # GET, POST, PUT for current user
]
