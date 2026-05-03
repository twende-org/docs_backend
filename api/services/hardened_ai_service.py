import os
import json
import time
import requests
from django.conf import settings
from django.utils import timezone
from api.models import AIUsage

class AIService:
    """
    Hardened AI Service Layer for GENDOCS.
    Handles prompts, OpenRouter API calls, retries, and usage limits.
    """
    
    @staticmethod
    def get_prompt_template(doc_type, data, language='en'):
        """Build professional prompts based on document type and language."""
        lang_name = "Swahili" if language.startswith('sw') else "English"
        
        if doc_type.upper() == 'CV':
            role = "senior executive career coach"
            objectives = [
                "Use strong action verbs (e.g., 'Spearheaded', 'Architected', 'Optimized').",
                "Remove filler words and passive language.",
                "Ensure a consistent tone suitable for international and Tanzanian job markets."
            ]
        elif doc_type.upper() in ['AFFIDAVIT', 'CONTRACT']:
            role = "legal drafting expert"
            objectives = [
                "Use highly formal, 'official' legal language suitable for court or government use.",
                "Ensure maximum precision and clarity in every clause.",
                f"Use standard {lang_name} legal terminology (e.g., 'Jamhuri ya Muungano' for TZ official docs)."
            ]
        elif doc_type.upper() in ['INVOICE', 'PROFORMA', 'QUOTATION']:
            role = "business financial consultant"
            objectives = [
                "Ensure terms are concise, professional, and build trust.",
                "Verify that descriptions are clear and easy for clients to understand.",
                "Maintain a high level of business professionalism."
            ]
        elif doc_type.upper() == 'LETTER':
            role = "professional correspondence specialist"
            objectives = [
                "Use a respectful, formal, and standard business tone.",
                "Ensure the subject and body flow logically and professionally.",
                "Maintain standard letter etiquette."
            ]
        else:
            role = "professional document consultant"
            objectives = [
                "Polish the text to be more professional and clear.",
                "Maintain all factual details and core meaning."
            ]

        rules_text = "\n            ".join([f"- {obj}" for obj in objectives])

        return f"""
        You are a {role}. Polish the following {doc_type} to be more professional and clear.
        
        RULES:
        {rules_text}
        - The output MUST BE in {lang_name}. Do NOT translate to another language.
        - Maintain all factual details.
        - Respond ONLY with valid JSON matching the input structure.
        
        INPUT DATA:
        {json.dumps(data, indent=2)}

        RESPONSE FORMAT:
        You must respond with a JSON object.
        If polishing a single paragraph/string, return: {{"polished_content": "Your polished string here"}}
        """

    @classmethod
    def polish_document(cls, user, doc_type, data, language='en'):
        """
        Public method to polish a document with usage tracking and retries.
        """
        # 1. Check Usage Limits (20 requests per day)
        if user:
            usage = AIUsage.get_usage(user)
            if usage.request_count >= 20:
                return {"success": False, "error": "Daily AI limit reached. Please try again tomorrow.", "data": data}
        else:
            # Internal or background enhancement: bypass limit
            pass

        prompt = cls.get_prompt_template(doc_type, data, language)
        api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not api_key:
            return {"success": False, "error": "AI Service misconfigured (Missing API Key).", "data": data}

        # 2. Call AI with Retries
        polished_content = cls._call_openrouter(prompt, api_key)
        
        if polished_content:
            try:
                # Attempt to parse JSON response
                cleaned_json = cls._extract_json(polished_content)
                if cleaned_json:
                    if user:
                        # 3. Track Usage
                        usage.increment()
                    
                    # If it's a direct string-to-string polish, it might be in 'polished_content' or the object itself
                    if isinstance(cleaned_json, dict) and "polished_content" in cleaned_json:
                        return {"success": True, "polished_content": cleaned_json["polished_content"]}
                    
                    return {"success": True, "polished_content": cleaned_json}
            except Exception:
                pass

        # 4. Failsafe: Return original data on error
        return {"success": False, "error": "AI failed to process. Returning original content.", "data": data}

    @staticmethod
    def _call_openrouter(prompt, api_key, retries=3):
        """Internal method to handle the raw API call to OpenRouter."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://gendocs.co.tz", 
            "X-Title": "GENDOCS Production",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": os.getenv("AI_MODEL_PREMIUM", "openai/gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": "You are a professional document specialist. You only respond in JSON format."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3 # Lower temperature for consistency in polishing
        }

        for attempt in range(retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                elif response.status_code == 429:
                    time.sleep(2 ** attempt) # Exponential backoff
                else:
                    print(f"OpenRouter Error: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Connection Error (Attempt {attempt+1}): {e}")
                time.sleep(1)
        
        return None

    @staticmethod
    def _extract_json(text):
        """Helper to extract JSON from AI response block."""
        try:
            # Try direct parse
            return json.loads(text.strip())
        except:
            # Try to find { ... }
            import re
            match = re.search(r'(\{[\s\S]*\})', text)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
        return None
