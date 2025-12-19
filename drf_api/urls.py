from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import JsonResponse

def home(request):
    return JsonResponse({"message": "Welcome to Docs API"})

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    path('', home),
    path('auth/', include('api.urls')),
    path('sms/', include('smsparser.urls')),
    path('api/', include('personal_details.urls')),
    path('api/', include('work_experiences.urls')),
    path('api/', include('career_objective.urls')),
    path('api/', include('skills_app.urls')),
    path('api/', include('education_app.urls')),
    path('api/', include('language_app.urls')),
    path('api/', include('project_app.urls')),
    path('api/', include('certificate_app.urls')),
    path('api/', include('references_app.urls')),
    path('api/', include('achivements_app.urls')),
    path("api/", include("jobs.urls")),
    path("api/", include("letterApp.urls")),
    path('api/', include('payments.urls')),
    path('api/', include('project_report.urls')),
    path('api/', include('cv_app.urls')),
    path("api/", include("risala.urls")),
    
    # Schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve media in development (DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Optional: In production, if Traefik can't serve media, add this fallback
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
