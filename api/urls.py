from django.urls import path
from .views import RegisterView, VerifyEmailView, UserLoginView,LogoutView, UserProfileView,run_create_superuser,run_migrations,UserDetailView,AdminUserListView,GoogleAuthView
from .password_reset import ForgotPasswordView,PasswordResetView
# from .ai_views import AIPolishView
from rest_framework_simplejwt.views import TokenRefreshView
urlpatterns = [
    path("signup/", RegisterView.as_view(), name="signup"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("login/token/", UserLoginView.as_view(), name="login"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<token>/', PasswordResetView.as_view(), name='reset-password'),
    path("create-superuser/", run_create_superuser),
    path("run-migrations/", run_migrations),
    path("user-details/", UserDetailView.as_view(), name="user-details"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-users"),
    path("admin/users/<int:pk>/", AdminUserListView.as_view(), name="admin-user-detail"),
    path("google-auth/", GoogleAuthView.as_view(), name="google-auth"),
    # path("ai/polish/", AIPolishView.as_view(), name="ai_polish"),
]
