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
    def get_prompt_template(doc_type, data):
        """Build professional prompts based on document type."""
        if doc_type.upper() == 'CV':
            return f"""
            You are a senior executive career coach. Refactor the following CV data to be high-impact, professional, and clear.
            
            RULES:
            - Use strong action verbs (e.g., "Spearheaded", "Architected", "Optimized").
            - Remove filler words and passive language.
            - Ensure a consistent tone suitable for international and Tanzanian job markets.
            - Keep the core facts identical but improve the wording.
            - Respond ONLY with valid JSON matching the input structure.
            
            INPUT DATA:
            {json.dumps(data, indent=2)}
            """
        
        # Default prompt for other documents
        return f"""
        You are a professional document consultant. Polish the following {doc_type} to be more professional and clear.
        Maintain all factual details. Respond ONLY with valid JSON.
        
        INPUT DATA:
        {json.dumps(data, indent=2)}
        """

    @classmethod
    def polish_document(cls, user, doc_type, data):
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

        prompt = cls.get_prompt_template(doc_type, data)
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
