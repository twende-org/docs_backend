from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from api.serializers import UserDetailSerializer
from .serializers import AIGenerateSerializer
from django.conf import settings
import requests
import json
from rest_framework import status, permissions
from api.models import UserTB
from cv_app.services.cv_tradition_generator.core import generate_cv as generate_cv_basic
from cv_app.services.cv_intermideate_generator.cv_generator import generate_cv as generate_cv_intermediate
from cv_app.services.cv_advanced_generator.cv_generator import generate_cv_safe as generate_cv_advanced
from cv_app.services.cv_minimal_generator.minimalist_cv_generator import generate_minimalist_cv as generate_cv_minimalist
from cv_app.services.cv_creative_generator.creative_cv_generator import generate_creative_cv as generate_cv_creative
from cv_app.services.cv_modern_genrator.modern_cv_generator import generate_modern_sidebar_cv as generate_cv_modern
import logging
logger = logging.getLogger(__name__)  
import io,os
from payments.models import UserCredit
from django.http import FileResponse
from api.services.ai_service import make_ai_call, extract_json_from_text

class UserCVDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get_user_cv_data(self, user: UserTB) -> dict:
        """Convert authenticated user object into detailed CV JSON."""
        serializer = UserDetailSerializer(user)
        data = serializer.data

        def title_case(s: str):
            return " ".join([w.capitalize() for w in s.split()]) if s else ""

        # ----- BASIC PERSONAL DETAILS -----
        personal = data.get("personal_details", {}) or {}

# Build full_name from personal_details
        full_name = title_case(" ".join(filter(None, [
            personal.get("first_name", ""),
            personal.get("middle_name", ""),
            personal.get("last_name", "")
        ])))

        # Fallback to top-level fields if personal_details is missing
        if not full_name.strip():
            full_name = title_case(" ".join(filter(None, [
                data.get("first_name", ""),
                data.get("middle_name", ""),
                data.get("last_name", "")
            ])))


        # Format phone
        phone = personal.get("phone", "")
        if phone and not phone.startswith("+"):
            phone = f"+{phone}"

        # Career Objective
        career_objective_list = data.get("career_objectives", [])
        career_objective = career_objective_list[0].get("career_objective", "") if career_objective_list else ""

        # ----- EDUCATIONS -----
        educations = [
            {
                "degree": e.get("degree", ""),
                "institution": title_case(e.get("institution", "")),
                "start_date": e.get("start_date", ""),
                "end_date": e.get("end_date", ""),
                "grade": e.get("grade", ""),
                "location": e.get("location", "")
            }
            for e in data.get("educations", [])
        ]

        # ----- CERTIFICATES -----
        profile = data.get("profile", {}) or {}
        certificates = [
            {
                "name": c.get("name", ""),
                "issuer": c.get("issuer", ""),
                "date": c.get("date", "")
            }
            for c in profile.get("certificates", [])
        ]

        # ----- WORK EXPERIENCES -----
        work_experiences = []
        for we in data.get("work_experiences", []):
            responsibilities = [
                r.get("value", "") if isinstance(r, dict) else str(r)
                for r in we.get("responsibilities", [])
            ]
            work_experiences.append({
                "company": title_case(we.get("company", "")),
                "location": we.get("location", ""),
                "job_title": title_case(we.get("job_title", "")),
                "start_date": we.get("start_date", ""),
                "end_date": we.get("end_date", ""),
                "responsibilities": [r.rstrip(".") + "." for r in responsibilities if r]
            })

        # ----- PROJECTS -----
        projects = []
        for p in data.get("projects", []):
            techs = [
                t.get("value", "") if isinstance(t, dict) else str(t)
                for t in p.get("technologies", [])
            ]
            projects.append({
                "title": title_case(p.get("title", "")),
                "description": p.get("description", ""),
                "link": p.get("link", ""),
                "technologies": [t for t in techs if t]
            })

        # ----- SKILLS -----
        skill_set = data.get("skill_sets", [{}])[0] if data.get("skill_sets") else {}
        technical_skills = [t.get("value") for t in skill_set.get("technical_skills", []) if t.get("value")]
        soft_skills = [s.get("value") for s in skill_set.get("soft_skills", []) if s.get("value")]

        # ----- ACHIEVEMENTS -----
        achievements = [
            (a.get("value") if isinstance(a, dict) else str(a)).rstrip(".") + "."
            for a in (data.get("achievement_profile", {}) or {}).get("achievements", [])
        ]

        # ----- LANGUAGES -----
        languages = [
            {"language": l.get("language", ""), "proficiency": l.get("proficiency", "")}
            for l in data.get("languages", [])
        ]

        # ----- REFERENCES -----
        references = [
            {
                "name": r.get("name", ""),
                "position": r.get("position", ""),
                "email": r.get("email", ""),
                "phone": r.get("phone", "")
            }
            for r in data.get("references", [])
        ]

        # ✅ FINAL STRUCTURE
        return {
            "id": data.get("id"),
            "full_name": full_name,
            "first_name": title_case(personal.get("first_name", "")),
            "middle_name": title_case(personal.get("middle_name", "")),
            "last_name": title_case(personal.get("last_name", "")),
            "email": data.get("email", ""),
            "phone": phone,
            "address": personal.get("address", ""),
            "website": personal.get("website", ""),
            "linkedin": personal.get("linkedin", ""),
            "profile_image": personal.get("profile_image") , # path relative to MEDIA_ROOT
            "github": personal.get("github", ""),
            "nationality": personal.get("nationality", ""),
            "date_of_birth": personal.get("date_of_birth", ""),
            "profile_summary": personal.get("profile_summary", ""),
            "career_objective": career_objective,
            "educations": educations,
            "certificates": certificates,
            "work_experiences": work_experiences,
            "projects": projects,
            "technical_skills": technical_skills,
            "soft_skills": soft_skills,
            "achievements": achievements,
            "languages": languages,
            "references": references
        }

    def get(self, request, cv_type="basic"):
        """Return JSON or stream PDF CV, only if user has downloads available."""
        try:
            user = request.user

            # Check download credits
            credit, _ = UserCredit.objects.get_or_create(user=user)
            if credit.downloads_remaining <= 0:
                return Response(
                    {"detail": "You have no download credits. Please purchase more to download CVs."},
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )

            user_data = self.get_user_cv_data(user)

            # --- JSON response ---
            if request.query_params.get("format") == "json":
                return Response(user_data, status=status.HTTP_200_OK)

            # --- Generate PDF into temp file ---
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=True)
            target_type = cv_type.lower()

            # CV generation logic
            if target_type == "basic":
                generate_cv_basic(user_data, temp_file)
            elif target_type == "intermediate":
                generate_cv_intermediate(user_data, output_path=temp_file)
            elif target_type == "advanced":
                generate_cv_advanced(user_data, output_path=temp_file)
            elif target_type == "modern":
                generate_cv_modern(user_data, output_path=temp_file)
            elif target_type == "minimalist":
                generate_cv_minimalist(user_data, output_path=temp_file)
            elif target_type == "creative":
                generate_cv_creative(user_data, output_path=temp_file)
            else:
                return Response(
                    {"detail": f"Invalid CV type '{cv_type}'. Options: basic, intermediate, advanced, modern, minimalist, creative."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Reset file pointer
            temp_file.seek(0)

            # Deduct 1 download credit
            credit.downloads_remaining -= 1
            credit.save()

            # Return the file
            return FileResponse(
                temp_file,
                as_attachment=True,
                filename=f"{user.first_name}_{user.last_name}_{cv_type.capitalize()}_CV.pdf",
                content_type='application/pdf'
            )

        except Exception as e:
            logger.exception(f"Error generating {cv_type} CV for user {user.id}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

SECTION_FORMATS = {
    "personal_information": {
    "array_field": "personal_information",
        "template": {
            "first_name": "",
            "middle_name": "",
            "last_name": "",
            "phone": "",
            "address": "",
            "linkedin": "",
            "github": "",
            "website": "",
            "date_of_birth": "",
            "nationality": "",
            "profile_summary": ""
        }
    },

    "work_experience": {
        "array_field": "experiences",
        "template": {
            "job_title": "",
            "company": "",
            "location": "",
            "start_date": "",
            "end_date": "",
            "responsibilities": [{"value": ""}],
        }
    },
    "education": {
        "array_field": "educations",
        "template": {
            "degree": "",
            "institution": "",
            "location": "",
            "start_date": "",
            "end_date": "",
            "grade": ""
        }
    },
    "skills": {
        "array_field": "skills",
        "template": {
            "technicalSkills": [{"value": ""}],
            "softSkills": [{"value": ""}]
        }
    },
    "languages": {
        "array_field": "languages",
        "template": {
            "language": "",
            "proficiency": ""
        }
    },
    "certifications": {
        "array_field": "certificates",
        "template": {
            "name": "",
            "issuer": "",
            "date": ""
        }
    },
    "projects": {
        "array_field": "projects",
        "template": {
            "title": "",
            "description": "",
            "link": "",
            "technologies": [{"value": ""}]
        }
    },
    "achievements": {
        "array_field": "achievements",
        "template": {"value": ""}
    },
    "references": {
        "array_field": "references",
        "template": {
            "name": "",
            "position": "",
            "email": "",
            "phone": ""
        }
    },
    # Add more sections as needed
}
class CVAIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logger.info("CVAIView POST called with data: %s", request.data)

        serializer = AIGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        section = serializer.validated_data.get("section")
        user_data = serializer.validated_data.get("userData", {})
        ai_input_text = user_data.get("instruction_text") or user_data.get("prompt")

        if not ai_input_text:
            error_msg = "instruction_text or prompt is required in userData"
            logger.error(error_msg)
            return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)

        # Determine AI output format based on section
        section_format = SECTION_FORMATS.get(section, {"array_field": "items", "template": {}})

        prompt = f"""
        You are an expert CV data extractor.
        Extract all relevant information for the CV section '{section}' from the text below.
        Return a valid JSON object only.
        If multiple items exist, put them inside the array '{section_format['array_field']}'.
        Use this template for each item: {json.dumps(section_format['template'])}
        If any field is missing, set it to an empty string "".

        Text        \"\"\"{ai_input_text}\"\"\"
        """
        try:
            # Use centralized AI service with 'premium' tier for CV generation
            response_text = make_ai_call(prompt, tier="premium")
            if not response_text:
                return Response({"error": "AI returned empty response"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Use centralized robust JSON extraction
            ai_json = extract_json_from_text(response_text)
            if not ai_json:
                return Response({"error": "Failed to parse AI response as JSON", "raw": response_text},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Ensure array structure as per original logic
            array_field = section_format['array_field']
            template = section_format['template']

            if array_field not in ai_json or not isinstance(ai_json[array_field], list):
                if isinstance(ai_json, dict):
                    ai_json = {array_field: [ai_json]}
                else:
                    return Response({"error": "AI response format invalid"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Fill missing template keys
            for item in ai_json[array_field]:
                if isinstance(template, dict):
                    for k, v in template.items():
                        if k not in item:
                            item[k] = v

            return Response(ai_json, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("AI generation failed.")
            return Response({"error": "AI generation failed", "detail": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FactoryProfileImportView(APIView):
    """
    Returns the user's current legacy profile data formatted exactly 
    for the frontend 'Document Factory' CV Editor.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cv_details_view = UserCVDetailsView()
        # Use existing extraction logic
        raw_data = cv_details_view.get_user_cv_data(user)

        # Transform to Factory structure (camelCase and specific nesting)
        factory_data = {
            "personalInfo": {
                "fullName": raw_data.get("full_name", ""),
                "jobTitle": raw_data.get("career_objective", "")[:100], # Fallback title
                "email": raw_data.get("email", ""),
                "phone": raw_data.get("phone", ""),
                "address": raw_data.get("address", ""),
            },
            "summary": raw_data.get("profile_summary", ""),
            "experience": [
                {
                    "id": str(i),
                    "title": exp.get("job_title", ""),
                    "company": exp.get("company", ""),
                    "duration": f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}",
                    "description": "\n".join(exp.get("responsibilities", []))
                }
                for i, exp in enumerate(raw_data.get("work_experiences", []))
            ],
            "education": [
                {
                    "id": str(i),
                    "degree": edu.get("degree", ""),
                    "school": edu.get("institution", ""),
                    "year": f"{edu.get('start_date', '')} - {edu.get('end_date', '')}"
                }
                for i, edu in enumerate(raw_data.get("educations", []))
            ],
            "skills": raw_data.get("technical_skills", []) + raw_data.get("soft_skills", [])
        }

        return Response(factory_data, status=status.HTTP_200_OK)
