import os
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Transaction, UserCredit
from .services import CreditService, SnippeService
from django.contrib.auth import get_user_model
import hmac
import hashlib
from django.db import transaction
import stripe

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

# ---------------------------------------------------
# SNIPPE INTEGRATION
# ---------------------------------------------------
@csrf_exempt
def snippe_initiate_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)
    
    try:
        data = json.loads(request.body)
        amount = data.get("amount")
        payment_type = data.get("type") # 'mobile', 'card', 'dynamic-qr'
        phone_number = data.get("phone")
        
        if not amount or not payment_type:
            return JsonResponse({"status": "error", "message": "Missing amount or type"}, status=400)

        # Prepare customer data from request or user profile
        user = request.user
        customer_data = {
            "first_name": getattr(user, 'first_name', 'Customer'),
            "last_name": getattr(user, 'last_name', 'User'),
            "email": getattr(user, 'email', data.get("email", "")),
            "address": data.get("address", "N/A"),
            "city": data.get("city", "DSM"),
            "state": data.get("state", "DSM"),
            "postcode": data.get("postcode", "00000"),
            "country": data.get("country", "TZ")
        }
        
        metadata = {
            "user_id": str(user.id) if user.is_authenticated else None,
            "plan_name": data.get("plan_name", "Credits Purchase")
        }

        response = SnippeService.initiate_payment(
            amount=amount,
            payment_type=payment_type,
            customer_data=customer_data,
            phone_number=phone_number,
            metadata=metadata
        )

        if response.get("status") == "success":
            snippe_data = response.get("data", {})
            reference = snippe_data.get("reference")
            
            # Create transaction record using the Snippe reference as external_id
            Transaction.objects.create(
                user=user if user.is_authenticated else None,
                external_id=reference,
                transaction_id=snippe_data.get("id", ""), # if any
                amount=amount,
                status="PENDING",
                provider="SNIPPE",
                raw_checkout=response
            )
            
            return JsonResponse(response)
        else:
            return JsonResponse(response, status=400)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def snippe_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    
    payload = request.body
    signature = request.headers.get("X-Snippe-Signature")
    
    if not SnippeService.verify_webhook(payload, signature):
        return JsonResponse({"error": "Invalid signature"}, status=403)

    try:
        data = json.loads(payload)
        event_type = data.get("event")
        payment_data = data.get("data", {})
        
        # Based on documentation, event is 'payment.completed'
        if event_type == "payment.completed":
            reference = payment_data.get("reference")
            amount_obj = payment_data.get("amount", {})
            amount_value = amount_obj.get("value")
            metadata = payment_data.get("metadata", {})
            user_id = metadata.get("user_id")
            
            with transaction.atomic():
                tx = Transaction.objects.filter(external_id=reference).first()
                if tx and tx.status != "SUCCESS":
                    tx.status = "SUCCESS"
                    tx.raw_webhook = data
                    tx.save()
                    
                    if user_id:
                        user = get_user_model().objects.get(id=user_id)
                        CreditService.add_credits(user, float(amount_value))
                        
            return JsonResponse({"status": "success"})
            
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "ignored"})


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
            
            # Add credits if successful
            if tx.status.upper() == "SUCCESS":
                CreditService.add_credits(tx.user, tx.amount)
                
            print(f"CALLBACK UPDATED: {tx.id}")
        else:
            # Handle unknown transactions or logs
            print(f"CALLBACK RECEIVED FOR UNKNOWN TX: {transaction_id}")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "received"})

# ---------------------------------------------------
# 4. WEBHOOK (SECURE)
# ---------------------------------------------------
def verify_azampay_signature(payload, signature):
    """
    Verify Azampay HMAC signature.
    Requires AZAMPAY_HMAC_SECRET in environment.
    """
    secret = os.getenv("AZAMPAY_HMAC_SECRET")
    if not secret or not signature:
        return False
        
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_sig, signature)

@csrf_exempt
def webhook_handler(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
        
    # Signature Verification
    sig = request.headers.get("X-Signature")
    if not verify_azampay_signature(request.body, sig):
        print(f"AZAMPAY SECURITY ALERT: Invalid signature from {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({"error": "Invalid signature"}, status=403)

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
            # Secure: Only update if not already success
            if tx.status.upper() != "SUCCESS":
                new_status = (data.get("status") or "success").upper()
                tx.status = new_status
                tx.amount = data.get("amount") or tx.amount
                tx.raw_webhook = data
                tx.save()
                
                if new_status == "SUCCESS":
                    CreditService.add_credits(tx.user, tx.amount)
            
            print(f"WEBHOOK UPDATED: {tx.id} - Status: {tx.status}")
        else:
            print(f"WEBHOOK RECEIVED FOR UNKNOWN TX: {transaction_id}")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"status": "success"})


# ---------------------------------------------------
# 5. STRIPE WEBHOOK (SECURE)
# ---------------------------------------------------
@csrf_exempt
def stripe_webhook_handler(request):
    payload = request.body
    sig_header = request.headers.get("STRIPE_SIGNATURE")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not endpoint_secret:
        return JsonResponse({"error": "Stripe webhook secret not configured"}, status=500)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        print(f"STRIPE SECURITY ALERT: Invalid signature")
        return JsonResponse({"error": "Invalid signature"}, status=403)

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        client_reference_id = session.get("client_reference_id")
        amount_total = session.get("amount_total", 0) / 100  # Stripe is in cents
        
        if client_reference_id:
            try:
                # Use a transaction lock to prevent duplicate credits
                with transaction.atomic():
                    user = get_user_model().objects.get(id=client_reference_id)
                    
                    # Check if this Stripe session ID has already been processed
                    if not Transaction.objects.filter(external_id=session.get("id"), status="SUCCESS").exists():
                        CreditService.add_credits(user, amount_total)
                        
                        Transaction.objects.create(
                            user=user,
                            external_id=session.get("id"),
                            transaction_id=session.get("payment_intent", ""),
                            amount=amount_total,
                            status="SUCCESS",
                            provider="STRIPE",
                            raw_webhook=event
                        )
                    else:
                        print(f"STRIPE WEBHOOK: Duplicate session {session.get('id')} ignored.")
            except get_user_model().DoesNotExist:
                print(f"STRIPE WEBHOOK: User {client_reference_id} not found.")
                pass

    return JsonResponse({"status": "success"})
