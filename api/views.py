from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserTB
from .serializers import UserTBSerializer, LoginSerializer, UserProfileSerializer,UserDetailSerializer
import jwt
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .serializers import UserDetailSerializer
from .services.ai_service import clean_user_data_with_ai, enhance_cv_data
from django.contrib.auth.models import User
from google.oauth2 import id_token
from google.auth.transport import requests
import logging
from api.models import UserTB

logger = logging.getLogger(__name__)
import subprocess
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

# User = settings.AUTH_USER_MODEL
def ensure_user_enhanced_data(user):
    if not user.enhanced_data:
        try:
            serializer = UserDetailSerializer(user)
            enhanced = serializer.data.get("enhanced_data", {})
            user.enhanced_data = enhanced
            user.save(update_fields=['enhanced_data'])
        except Exception as e:
            logger.error(f"Failed to generate enhanced_data for user {user.email}: {e}")
            user.enhanced_data = {}
            user.save(update_fields=['enhanced_data'])
    return user.enhanced_data or {}


class RegisterView(APIView):
    permission_classes = [AllowAny]
    """
    API for user registration.
    """
    @extend_schema(
        request=UserTBSerializer,
        responses={200: None},
        summary="Register a new user",
        description="Takes email and password to create a new user.",
    )

   

    def post(self, request):
     serializer = UserTBSerializer(data=request.data)
     if serializer.is_valid():
        user = serializer.save()

        # Create your own JWT token with user_id payload and expiration
        payload = {
            "user_id": str(user.id),
            "exp": datetime.utcnow() + timedelta(hours=24),  # token expiry (e.g. 24 hours)
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        verification_url = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token}"

        # Send Premium HTML Verification Email
        subject = "Welcome to GenDocs - Please Verify Your Account"
        context = {
            'user': user,
            'verification_link': verification_url,
        }
        
        try:
            html_content = render_to_string('api/emails/verification_email.html', context)
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")

        if settings.DEBUG:
            user.is_active = True
            user.save()
            
            # Also generate tokens for immediate login
            refresh = RefreshToken.for_user(user)
            return Response({
                "message": f"Registration successful for {user.email}. User auto-activated (DEBUG=True).",
                "verification_required": False,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserTBSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        user.is_active = False 
        user.save()

        return Response({
            "message": f"Registration successful for {user.email}. Please check your email inbox to verify your account.",
            "verification_required": True
        }, status=status.HTTP_201_CREATED)

     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from rest_framework.permissions import AllowAny

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        token = request.GET.get("token")

        if not token:
            return Response({"error": "Token missing"}, status=400)

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")

            if not user_id:
                return Response({"error": "Invalid token"}, status=400)

            # activate user
            user = UserTB.objects.get(pk=user_id)
            user.is_active = True
            user.save()

            return Response({"message": "Email verified successfully"}, status=200)

        except jwt.ExpiredSignatureError:
            return Response({"error": "Token has expired"}, status=400)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=400)
        except UserTB.DoesNotExist:
            return Response({"error": "User does not exist"}, status=400)
        
class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            refresh = RefreshToken.for_user(user)

            # Use helper to populate enhanced_data
            enhanced_data = ensure_user_enhanced_data(user)

            user_data = UserDetailSerializer(user, context={'enhanced_data': enhanced_data}).data

            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "email": user.email,
                "user": user_data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)







class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            logger.warning("Logout request missing refresh token")
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("Refresh token blacklisted successfully")
            return Response({"detail": "Logout successful."}, status=status.HTTP_200_OK)

        except TokenError:
            # Token is already blacklisted or invalid
            logger.warning("Attempt to blacklist an invalid or already blacklisted token")
            return Response({"detail": "Invalid or already blacklisted token."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Unexpected error blacklisting token: {str(e)}", exc_info=True)
            return Response({"detail": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
        
class UserProfileView(APIView):
    """
    API for retrieving and updating user profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def run_create_superuser(request):
    User = get_user_model()
    email = "admin@gmail.com"
    password = "admin12345"

    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(
            email=email,
            password=password,
            first_name="Super",
            last_name="Admin",
            middle_name="System",
            phone_number="1234567890",
            role="seller",  # or any role you support
            is_active=True,
        )
        return JsonResponse({"message": "✅ Superuser created successfully."})
    else:
        return JsonResponse({"message": "⚠️ Superuser already exists."})
    


@api_view(['POST'])
@permission_classes([IsAdminUser])
@csrf_exempt
def run_migrations(request):
    try:
        result = subprocess.run(["python", "manage.py", "migrate"], check=True, capture_output=True, text=True)
        return JsonResponse({"message": "✅ Migrations applied", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return JsonResponse({"error": "❌ Migration failed", "details": e.stderr}, status=500)
    




class UserDetailView(APIView):
    """
    API for retrieving and updating user details with AI enhancement.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        responses=UserDetailSerializer,
        summary="Retrieve user details",
        description="Get the details of the authenticated user."
    )
    def get(self, request):
        try:
            user = request.user

            # Always ensure enhanced_data is a dict
            enhanced_data = user.enhanced_data or {}

            # If no enhanced_data yet, generate it
            if not enhanced_data:
                serializer = UserDetailSerializer(user)
                original_data = dict(serializer.data)

                cleaned_data = clean_user_data_with_ai(original_data)
                enhanced_data = enhance_cv_data(cleaned_data)

                user.enhanced_data = enhanced_data
                user.save(update_fields=['enhanced_data'])
                user.refresh_from_db()

            serializer = UserDetailSerializer(user, context={'enhanced_data': enhanced_data})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            serializer = UserDetailSerializer(request.user)
            return Response({
                'data': serializer.data,
                'error': f'AI processing failed: {str(e)}'
            }, status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        responses=UserDetailSerializer,
        summary="Re-enhance user details",
        description="Re-run AI enhancement if user data was updated (e.g., new skills, education, etc.)"
    )
    def put(self, request):
        try:
            user = request.user
            serializer = UserDetailSerializer(user)
            original_data = dict(serializer.data)

            cleaned_data = clean_user_data_with_ai(original_data)
            enhanced_data = enhance_cv_data(cleaned_data)

            user.enhanced_data = enhanced_data
            user.save(update_fields=['enhanced_data'])
            user.refresh_from_db()

            return Response({
                "message": "AI-enhanced data updated successfully.",
                "enhanced_data": enhanced_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": f"Failed to update enhanced data: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        
class AdminUserListView(APIView):
    """
    API to fetch all users for admin dashboard.
    Only accessible by staff/superusers.
    """
    # permission_classes = [IsAdminUser] 

    @extend_schema(
        responses=UserDetailSerializer(many=True),
        summary="Retrieve all users",
        description="Get the full list of all users in the system. Admin only."
    )
    def get(self, request):
        users = UserTB.objects.all()  # Fetch all users
        serializer = UserDetailSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk=None):
        try:
            user = UserTB.objects.get(pk=pk)
            user.is_active = not user.is_active
            user.save()
            return Response({
                "message": f"User {user.email} status toggled.",
                "is_active": user.is_active
            }, status=status.HTTP_200_OK)
        except UserTB.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk=None):
        try:
            user = UserTB.objects.get(pk=pk)
            email = user.email
            user.delete()
            return Response({"message": f"User {email} deleted successfully."}, status=status.HTTP_200_OK)
        except UserTB.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"message": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Step 1: Verify Google token
            try:
                idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)
                logger.info(f"Google token verified: {idinfo}")
            except ValueError as ve:
                logger.error(f"Google token verification failed: {ve}")
                return Response({"message": "Invalid Google token"}, status=status.HTTP_400_BAD_REQUEST)

            email = idinfo.get("email")
            first_name = idinfo.get("given_name") or ""
            last_name = idinfo.get("family_name") or ""

            if not email:
                return Response({"message": "Email not found in Google token"}, status=status.HTTP_400_BAD_REQUEST)

            # Step 2: Get or create user
            try:
                user = UserTB.objects.get(email=email)
                created = False
            except UserTB.DoesNotExist:
                user = UserTB.objects.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                created = True

            # Step 3: Ensure enhanced_data
            enhanced_data = ensure_user_enhanced_data(user)
            logger.info(f"Enhanced data generated for user {email}")

            # Step 4: Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)

            # Step 5: Serialize user
            user_data = UserDetailSerializer(user, context={'enhanced_data': enhanced_data}).data

            return Response({
                "refresh": str(refresh),
                "access": access,
                "email": user.email,
                "user": user_data,
                "is_new_user": created
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Google auth failed: {str(e)}")
            return Response(
                {"message": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# class AIServiceFormFiller:
#     """
#     Service to interact with AI for form filling and data cleaning.
#     """
    
#     @staticmethod
#     def extract_relevant_data(ai_response: str) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
#         """
#         Extract relevant JSON data from AI response.
#         Handles cases where AI may return extra text.
#         """
#         import json
#         import re

#         # Use regex to find JSON objects/arrays in the response
#         json_pattern = r'(\{.*\}|\[.*\])'
#         matches = re.findall(json_pattern, ai_response, re.DOTALL)

#         results = []
#         for match in matches:
#             try:
#                 data = json.loads(match)
#                 results.append(data)
#             except json.JSONDecodeError:
#                 continue

   
   
class PublicStatsView(APIView):
    """
    Publicly accessible statistics for the landing page social proof.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from documents.models import Document, DocumentRequest
        
        return Response({
            "users": UserTB.objects.count(),
            "documents": Document.objects.count(),
            "agents": UserTB.objects.filter(role='seller').count(),
            "requests": DocumentRequest.objects.count()
        }, status=status.HTTP_200_OK)
