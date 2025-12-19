import os
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Transaction,UserCredit
from django.contrib.auth import get_user_model

# ---------------------------------------------------
# Azampay Configuration
# ---------------------------------------------------
BASE_URL = os.getenv("AZAMPAY_BASE_URL", "https://sandbox.azampay.co.tz")
AUTH_BASE_URL = os.getenv("AZAMPAY_AUTH_BASE_URL", "https://authenticator-sandbox.azampay.co.tz")
CLIENT_ID = os.getenv("AZAMPAY_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZAMPAY_CLIENT_SECRET")

CALLBACK_URL = os.getenv(
    "CALLBACK_URL",
    "https://your-domain/api/payments/v1/Checkout/Callback"
)
WEBHOOK_URL = os.getenv(
    "WEBHOOK_URL",
    "https://your-domain/api/payments/azampay/webhook/"
)

# ---------------------------------------------------
# Helper: Get Sandbox Token
# ---------------------------------------------------
def get_sandbox_token():
    try:
        url = f"{AUTH_BASE_URL}/AppRegistration/GenerateToken"
        payload = {"AppName": "smartDocs", "clientId": CLIENT_ID.strip(), "clientSecret": CLIENT_SECRET.strip()}
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        token = data.get("data", {}).get("accessToken")
        if not token:
            print("TOKEN ERROR: No access token returned.")
        return token
    except Exception as e:
        print("TOKEN ERROR:", str(e))
        return None

# ---------------------------------------------------
# Helper: Send Checkout Request
# ---------------------------------------------------
def send_checkout_request(account_number, amount, external_id, provider, token):
    try:
        url = f"{BASE_URL}/azampay/mno/checkout"
        payload = {
            "accountNumber": account_number,
            "amount": amount,
            "currency": "TZS",
            "externalId": external_id,
            "provider": provider,
            "additionalProperties": {}
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json(), response.status_code
    except Exception as e:
        print("CHECKOUT ERROR:", str(e))
        return {"error": str(e)}, 500

# ---------------------------------------------------
# 1. INITIATE PAYMENT
# ---------------------------------------------------
@csrf_exempt
def initiate_payment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    return JsonResponse({"status": "ok", "message": "Payment initiation started."})

# ---------------------------------------------------
# 2. CREATE CHECKOUT
# ---------------------------------------------------
@csrf_exempt
def create_checkout(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    required = ["accountNumber", "amount", "externalId", "provider"]
    missing = [f for f in required if f not in data]
    if missing:
        return JsonResponse({"status": "error", "message": f"Missing fields: {missing}"}, status=400)

    token = get_sandbox_token()
    if not token:
        return JsonResponse({"status": "error", "message": "Cannot get Azampay token"}, status=500)

    response_data, status_code = send_checkout_request(
        data["accountNumber"], data["amount"], data["externalId"], data["provider"], token
    )

    # Save transaction: always use external_id, save transaction_id if present
    try:
        tx, created = Transaction.objects.update_or_create(
            external_id=data["externalId"],
            defaults={
                "transaction_id": response_data.get("transactionId") or "",
                "account_number": data["accountNumber"],
                "provider": data["provider"],
                "amount": data["amount"],
                "status": "PENDING",
                "raw_checkout": response_data,
            },
        )
        print(f"TRANSACTION {'CREATED' if created else 'UPDATED'}: {tx.id}")
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({
        "success": response_data.get("success", False),
        "transactionId": tx.transaction_id,
        "message": response_data.get("message", "Transaction processed"),
        "data": response_data.get("data", {}),
    }, status=status_code)




def update_user_credits(user, amount):
    downloads_per_3000 = 3
    credits_to_add = (amount // 3000) * downloads_per_3000

    credit, _ = UserCredit.objects.get_or_create(user=user)
    credit.downloads_remaining += credits_to_add
    credit.total_credits += credits_to_add
    credit.save()
# ---------------------------------------------------
# 3. CALLBACK
# ---------------------------------------------------
@csrf_exempt
def azampay_callback(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    external_id = data.get("externalId") or data.get("externalreference")
    transaction_id = data.get("transid") or data.get("transactionId")

    if not (external_id or transaction_id):
        return JsonResponse({"error": "No external or transaction ID in callback"}, status=400)

    try:
        tx = Transaction.objects.filter(transaction_id=transaction_id).first() \
             or Transaction.objects.filter(external_id=external_id).first()

        if tx:
            tx.status = data.get("transactionstatus") or data.get("status") or "success"
            tx.amount = data.get("amount") or tx.amount
            tx.provider = data.get("operator") or data.get("provider") or tx.provider
            tx.account_number = data.get("msisdn") or data.get("accountNumber") or tx.account_number
            tx.raw_callback = data
            tx.save()
            print(f"CALLBACK UPDATED: {tx.id}")
        else:
            tx = Transaction.objects.create(
                external_id=external_id or f"ext-{transaction_id}",
                transaction_id=transaction_id or "",
                status=data.get("transactionstatus") or data.get("status") or "success",
                amount=data.get("amount") or 0,
                provider=data.get("operator") or data.get("provider") or "",
                account_number=data.get("msisdn") or data.get("accountNumber") or "",
                raw_callback=data
            )
            print(f"CALLBACK CREATED: {tx.id}")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "received"})

# ---------------------------------------------------
# 4. WEBHOOK
# ---------------------------------------------------
@csrf_exempt
def webhook_handler(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    external_id = data.get("externalId") or data.get("externalreference")
    transaction_id = data.get("transid") or data.get("transactionId")

    if not (external_id or transaction_id):
        return JsonResponse({"error": "No external or transaction ID in webhook"}, status=400)

    try:
        tx = Transaction.objects.filter(transaction_id=transaction_id).first() \
             or Transaction.objects.filter(external_id=external_id).first()

        if tx:
            tx.status = data.get("status") or "success"
            tx.amount = data.get("amount") or tx.amount
            tx.provider = data.get("channel") or data.get("operator") or tx.provider
            tx.raw_webhook = data
            tx.save()
            print(f"WEBHOOK UPDATED: {tx.id}")
        else:
            tx = Transaction.objects.create(
                external_id=external_id or f"ext-{transaction_id}",
                transaction_id=transaction_id or "",
                status=data.get("status") or "success",
                amount=data.get("amount") or 0,
                provider=data.get("channel") or data.get("operator") or "",
                raw_webhook=data
            )
            print(f"WEBHOOK CREATED: {tx.id}")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "success"})
