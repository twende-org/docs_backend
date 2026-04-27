from django.urls import path
from .ai_views import AIPolishView

urlpatterns = [
    path('polish/', AIPolishView.as_view(), name='ai_polish'),
]
