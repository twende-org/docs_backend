# api/services/ai_service.py
import os
import json
import time
import hashlib
import re
import requests
from django.conf import settings
from api.models import AIUsage, AICache

class AIService:
    """
    Centralized AI Service Layer for GENDOCS.
    Focuses on reliability, cost-optimization, and scalability.
    """
    
    # Model preferences in order of cascading fallback
    MODELS = [
        "google/gemini-2.0-flash-lite-preview-02-05:free",
        "meta-llama/llama-3.3-70b-instruct",
        "mistralai/mistral-7b-instruct",
    ]

    @staticmethod
    def _generate_hash(data):
        """Create a stable hash for the input data to check cache."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    @classmethod
    def polish_document(cls, user, doc_type, data, language='en'):
        """
        Public method to polish document content with:
        - Usage tracking
        - Intelligent Caching
        - Multi-model cascading
        - Resilient fallback
        """
        # 1. Check Usage Limits
        if user:
            usage = AIUsage.get_usage(user)
            if usage.request_count >= 50: # Increased limit for premium feel
                return {"success": False, "error": "Daily AI limit reached.", "data": data}
        else:
            # If no user, bypass limits or use a global limit (for internal/background tasks)
            # For GENDOCS background enhancement, we allow it.
            pass

        # 2. Check Cache (Cost Optimization)
        data_hash = cls._generate_hash(data)
        cached = AICache.get_cached(data_hash)
        if cached:
            return {"success": True, "data": cached.polished_content, "cached": True}

        # 3. Build Prompt
        prompt = cls._build_prompt(doc_type, data, language)
        api_key = os.getenv("OPENROUTER_API_KEY") or getattr(settings, 'OPENROUTER_API_KEY', None)

        if not api_key:
            return {"success": False, "error": "AI Config Missing", "data": data}

        # 4. Multi-Model Cascading Execution
        polished_result = None
        for model in cls.MODELS:
            polished_result = cls._call_openrouter(prompt, api_key, model)
            if polished_result:
                break 
        
        # 5. Process Result
        if polished_result:
            try:
                cleaned_json = cls._extract_json(polished_result)
                if cleaned_json:
                    if user:
                        # Increment usage
                        usage.increment()
                    # Store in cache
                    AICache.objects.create(
                        hash=data_hash,
                        doc_type=doc_type,
                        original_content=data,
                        polished_content=cleaned_json
                    )
                    return {"success": True, "data": cleaned_json}
            except Exception:
                pass

        # 6. Ultimate Failsafe: Return original content
        return {"success": False, "error": "AI failed to process. Returning original.", "data": data}

    @staticmethod
    def _build_prompt(doc_type, data, language='en'):
        """High-impact prompt engineering for document polishing."""
        lang_name = "Swahili" if language.startswith('sw') else "English"
        
        if doc_type.upper() == 'CV':
            role = "senior executive career coach"
            grade = "high-impact, professional career language with strong action verbs"
        elif doc_type.upper() in ['AFFIDAVIT', 'CONTRACT']:
            role = "legal drafting expert"
            grade = "highly formal, official legal terminology suitable for government or court use"
        elif doc_type.upper() in ['INVOICE', 'PROFORMA', 'QUOTATION']:
            role = "business financial consultant"
            grade = "concise, trustworthy business language that is professional and clear"
        elif doc_type.upper() == 'LETTER':
            role = "professional correspondence specialist"
            grade = "respectful, formal business standard tone"
        else:
            role = "professional document consultant"
            grade = "professional and clear standard language"

        return f"""
        You are a {role}. Your task is to polish the following {doc_type} data for maximum impact.
        The output MUST BE in {lang_name}. Do NOT translate to another language.
        
        OBJECTIVES:
        - Use {grade}.
        - Enhance grammar, spelling, and structural flow.
        - Maintain 100% of the original meaning and factual details.
        
        RESTRICTIONS:
        - Respond ONLY with the polished JSON object.
        - DO NOT include any conversational text, explanations, or quotes.
        - Maintain the EXACT same JSON keys as the input.
        
        INPUT DATA ({doc_type}):
        {json.dumps(data, indent=2)}
        """

    @staticmethod
    def _call_openrouter(prompt, api_key, model, retries=2):
        """Raw API call logic with retries and timeout handling."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://gendocs.co.tz",
            "X-Title": "GENDOCS AI Engine",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a professional JSON document polisher. NO chatter, only JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2, # Low temperature for consistency
            "max_tokens": 2000,
            "response_format": { "type": "json_object" }
        }

        for attempt in range(retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=25)
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                elif response.status_code == 429: # Rate limit
                    time.sleep(2 ** attempt)
                else:
                    return None
            except Exception:
                time.sleep(1)
        return None

    @staticmethod
    def _extract_json(text):
        """Fallback JSON extraction from markdown or direct response."""
        try:
            return json.loads(text.strip())
        except:
            match = re.search(r'(\{[\s\S]*\})', text)
            if match:
                try: return json.loads(match.group(1))
                except: pass
        return None


# --- LEGACY WRAPPERS & SERIALIZER HELPERS ---
AI_AVAILABLE = True # Always True if we have the service logic

def merge_dicts(original: dict, cleaned: dict) -> dict:
    """Safely merge two dictionaries."""
    if not isinstance(cleaned, dict): return original
    merged = original.copy()
    merged.update(cleaned)
    return merged

def make_ai_call(prompt: str, model: str = None) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY") or getattr(settings, 'OPENROUTER_API_KEY', None)
    if not api_key: return "config_missing"
    return AIService._call_openrouter(prompt, api_key, model or AIService.MODELS[0])

def extract_json_from_text(text: str) -> dict:
    return AIService._extract_json(text)

def clean_user_data_with_ai(serializer_data: dict) -> dict:
    """Wrapper using the new consolidated service."""
    result = AIService.polish_document(None, "UserData", serializer_data)
    if result.get('success'):
        return result['data']
    return serializer_data

def enhance_cv_data(cv_data: dict) -> dict:
    """Enhanced wrapper for CV data polishing."""
    result = AIService.polish_document(None, "FullCV", cv_data)
    return result.get('data', cv_data) if result.get('success') else cv_data
