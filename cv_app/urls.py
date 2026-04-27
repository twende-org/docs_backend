from django.urls import path
from .views import UserCVDetailsView, CVAIView, FactoryProfileImportView

urlpatterns = [
    path('cv/download/<str:cv_type>/', UserCVDetailsView.as_view(), name='user-cv-download'),
    path('cv/ai-cv/', UserCVDetailsView.as_view(), name='user-cv-download'),
    path("cv/cv-ai/",CVAIView.as_view(),name="ai-cv"),
    path('cv/factory-profile/', FactoryProfileImportView.as_view(), name='factory-profile-import'),

]
