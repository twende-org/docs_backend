import os
import django
from dotenv import load_dotenv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drf_api.settings')
django.setup()

from api.services.ai_service import make_ai_call

print("Testing AI call...")
result = make_ai_call("Hello, say 'AI is working' if you can hear me.", tier="premium")
if result:
    print(f"SUCCESS: {result}")
else:
    print("FAILURE: AI call returned None")
