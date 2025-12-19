import os
import requests
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import AIStepRequestSerializer, RisalaSerializer
from .models import Risala
from rest_framework.permissions import IsAuthenticated

# -------------------------------------------------------
# FIELD MAP FOR EVENT-BASED CONTENT (AI STEPS)
# -------------------------------------------------------
FIELD_MAP = {
    1: ["event_type", "event_title", "event_date", "event_location"],
    2: ["guest_of_honor", "guest_title", "organization_name", "organization_representative"],
    3: ["purpose_statement", "background_info", "main_message"],
    4: {
        "harusi": ["bride_name", "groom_name", "wedding_theme"],
        "msiba": ["deceased_name", "relationship", "tribute_summary"],
        "uzinduzi": ["project_name", "project_goal", "project_beneficiaries"],
        "mgeni_rasmi": ["program_name", "program_theme"],
    },
    5: ["requests", "closing_statement", "presenter_name", "presenter_title"]
}

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# -------------------------------------------------------
# AI STEP-WISE GENERATION
# -------------------------------------------------------
class GenerateAIValuesAPIView(APIView):
    def post(self, request):
        serializer = AIStepRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        step = serializer.validated_data["step"]
        event_type = serializer.validated_data.get("event_type")
        instruction = serializer.validated_data.get("instruction", "")

        # Resolve correct fields
        fields = FIELD_MAP.get(step, [])
        if step == 4 and event_type:
            fields = FIELD_MAP[4].get(event_type, [])

        if not fields:
            return Response(
                {"error": "No fields found for this step/event_type"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build prompt
        field_labels = ", ".join(fields)
        prompt = (
            f"Andika maandishi kwa Kiswahili fasaha kwa ajili ya sehemu zifuatazo: "
            f"{field_labels}. {instruction}\n\n"
            "⚠ Muhimu:\n"
            "- Usitumie mabano kama [hivi].\n"
            "- Usiunde majina au taarifa mpya.\n"
            "- Andika mistari tofauti kwa kila field."
        )

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }

        # Call API safely
        try:
            response = requests.post(OPENROUTER_URL, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            return Response({"error": f"AI request failed: {str(e)}"}, status=500)

        # Extract text
        text_output = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not text_output:
            return Response({"error": "AI returned empty response"}, status=500)

        # Map lines → fields
        lines = [l.strip() for l in text_output.split("\n") if l.strip()]
        ai_output = {}
        for i, field in enumerate(fields):
            ai_output[field] = lines[i] if i < len(lines) else ""

        return Response({"data": ai_output}, status=200)


# -------------------------------------------------------
# RISALA VIEW WITH CLEANING + FULL RISALA FLOW
# -------------------------------------------------------

class RisalaAPIView(APIView):
    """
    Retrieve, create, or update Risala for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch the risala for the logged-in user
        risala = Risala.objects.filter(user=request.user).order_by('-created_at').first()
        if not risala:
            # If none exist, create a new one
            risala = Risala.objects.create(user=request.user)

        serializer = RisalaSerializer(risala)
        raw_data = serializer.data
        event_type = raw_data.get("event_type")

        # Relevant fields
        relevant_fields = (
            FIELD_MAP[1]
            + FIELD_MAP[2]
            + FIELD_MAP[3]
            + FIELD_MAP[5]
            + FIELD_MAP[4].get(event_type, [])
        )

        # Validate text for cleaning
        def is_valid_text(value):
            if not value or value.strip() == "":
                return False
            if len(value) < 3:
                return False
            if any(x in value for x in ["@@@", "###", "??", "///"]):
                return False
            if value.isalpha() and len({c for c in value}) < 4:
                return False
            return True

        # Clean fields
        cleaned_fields = {
            key: val for key, val in raw_data.items()
            if key in relevant_fields and is_valid_text(val)
        }

        formatted_input = "\n".join([f"{k}: {v}" for k, v in cleaned_fields.items()])

        # Tone based on event type
        tone = {
            "harusi": "ya sherehe, furaha na heshima",
            "msiba": "ya faraja, upole, utulivu na heshima",
            "uzinduzi": "ya matumaini, kuhamasisha na uwazi wa kitaalamu",
            "mgeni_rasmi": "ya heshima, ukaribisho na weledi"
        }.get(event_type, "ya heshima na mpangilio mzuri")

        # Build AI prompt
        prompt = (
            "Tumia taarifa zifuatazo kutengeneza RISALA KAMILI YA MUHUTUBIAJI.\n\n"
            "⚠ MUHIMU SANA:\n"
            "- Usiongeze taarifa mpya wala majina mapya.\n"
            "- Usitumie placeholders kama [jina].\n"
            "- Safisha maneno yasiyoeleweka.\n"
            "- Tumia tu taarifa safi zilizopo.\n"
            "- Andika RISALA NDEFU, kamili na yenye mtiririko.\n"
            "- Mpangilio: utangulizi, salamu, shukrani, madhumuni, ujumbe mkuu, hitimisho.\n"
            f"- Sauti iwe {tone}.\n\n"
            "Hizi ndizo taarifa zilizopo:\n"
            f"{formatted_input}\n\n"
            "Sasa andika RISALA KAMILI, NDEFU, YENYE UFAFANUZI NA MWENENDO WA HOTUBA."
        )

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.45,
            "max_tokens": 1500
        }

        # Call AI
        try:
            response = requests.post(OPENROUTER_URL, json=data, headers=headers, timeout=40)
            response.raise_for_status()
            risala_text = response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return Response({"error": f"AI request failed: {str(e)}"}, status=500)

        return Response({
            "raw_data": raw_data,
            "cleaned_fields": cleaned_fields,
            "event_type": event_type,
            "generated_risala": risala_text
        })

    # Create new risala
    def post(self, request):
        serializer = RisalaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)

    # Update existing risala
    def put(self, request):
        risala = Risala.objects.filter(user=request.user).first()
        if not risala:
            return Response({"error": "No Risala found for this user."}, status=404)
        serializer = RisalaSerializer(risala, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
