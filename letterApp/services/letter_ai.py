import json
import re
from api.services.ai_service import make_ai_call, extract_json_from_text, merge_dicts, AI_AVAILABLE
from django.conf import settings


def generate_clean_letter(data: dict) -> dict:
    """
    Generate a professional letter body using AI (or fallback template),
    supporting both English and Swahili (lang field).
    """

    # Extract fields
    sender_name = data.get("sender", "").strip()
    sender_title = data.get("senderTitle", "").strip()
    sender_address = data.get("senderAddress", "").strip()
    recipient_name = data.get("recipient", "").strip()
    recipient_title = data.get("recipientTitle", "").strip()
    recipient_address = data.get("recipientAddress", "").strip()
    subject = data.get("subject", "").strip()
    content = data.get("content", "").strip()
    closing = data.get("closing", "").strip()
    lang = data.get("lang", "en")
    date = data.get("date", "")

    # Fallback template
    def fallback_letter():
        nonlocal subject, content, closing
        if not subject:
            subject = "Maombi" if lang == "sw" else "Application"
        if not content:
            if lang == "sw":
                content_lines = [
                    f"Halo {recipient_title} {recipient_name},",
                    "Ninaandika kuhusiana na jambo lililotajwa.",
                    "Tafadhali zingatia kama mawasiliano yangu rasmi."
                ]
            else:
                content_lines = [
                    f"Dear {recipient_title} {recipient_name},",
                    "I am writing regarding the above matter.",
                    "Please consider this as my formal communication."
                ]
            content = "\n\n".join(content_lines).strip()
        if not closing:
            closing = f"Kwa dhati, {sender_name}" if lang == "sw" and sender_name else f"Sincerely, {sender_name}" if sender_name else "Sincerely,"

        return {
            "recipient": recipient_name,
            "recipientTitle": recipient_title,
            "recipientAddress": recipient_address,
            "sender": sender_name,
            "senderTitle": sender_title,
            "senderAddress": sender_address,
            "date": date,
            "subject": subject,
            "content": content,
            "closing": closing,
            "senderSignature": data.get("senderSignature", None),
            "lang": lang,
            "alignContact": data.get("alignContact", "start")
        }

    # Get API key from settings
    api_key = getattr(settings, "OPENROUTER_API_KEY", None)
    if not AI_AVAILABLE or not api_key:
        return fallback_letter()

    # AI prompt
    prompt = f"""
    You are a professional letter writer. Using the user input below, generate a polished, professional letter in JSON format.
    Requirements:
    - Include all Letter fields: subject, recipientAddress, content, closing, sender, date, etc.
    - Use provided information: recipientTitle, recipientName, senderName, senderTitle, purpose, context.
    - Do NOT include closing phrases or sender name inside content.
    - Clean content: remove placeholders like [Your Name], [senderName], etc.
    - Write in Kiswahili if lang='sw', otherwise English.
    - Return ONLY valid JSON corresponding to the Letter interface.

    User Input:
    {json.dumps(data, indent=2)}
    """

    try:
        # Call AI with the API key and 'premium' tier for high-quality letters
        response_text = make_ai_call(prompt, api_key=api_key, tier="premium")
        if not response_text:
            return fallback_letter()

        cleaned_data = extract_json_from_text(response_text) or {}

        # Ensure closing exists
        if not cleaned_data.get("closing"):
            cleaned_data["closing"] = f"Kwa dhati, {sender_name}" if lang == "sw" else f"Sincerely, {sender_name}" if sender_name else "Sincerely,"

        # Clean AI content
        if "content" in cleaned_data and cleaned_data["content"]:
            c = cleaned_data["content"]
            if lang == "sw":
                c = re.sub(r"\b(Kwa dhati|Wako mwaminifu|Wako kwa heshima),?\b", "", c, flags=re.IGNORECASE)
            else:
                c = re.sub(r"\b(Sincerely|Yours faithfully|Yours sincerely|Best regards),?\b", "", c, flags=re.IGNORECASE)
            if sender_name:
                c = re.sub(re.escape(sender_name), "", c, flags=re.IGNORECASE)
            c = re.sub(r"\[[^\]]+\]", "", c)
            c = re.sub(r"\s{2,}", " ", c)
            c = re.sub(r",\s*,", ",", c)
            cleaned_data["content"] = c.strip()

        # Merge AI output with original fields
        final_letter = merge_dicts({
            "recipient": recipient_name,
            "recipientTitle": recipient_title,
            "recipientAddress": recipient_address,
            "sender": sender_name,
            "senderTitle": sender_title,
            "senderAddress": sender_address,
            "date": date,
            "subject": subject,
            "content": content,
            "closing": closing,
            "senderSignature": data.get("senderSignature", None),
            "lang": lang,
            "alignContact": data.get("alignContact", "start")
        }, cleaned_data)

        return final_letter

    except Exception as e:
        print(f"Letter AI error: {e}")
        return fallback_letter()
