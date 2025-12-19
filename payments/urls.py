from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("initiate/", views.initiate_payment, name="initiate_payment"),
    path("payments/checkout/", views.create_checkout, name="create_checkout"),

    # your existing callback (KEEP IT)
    path("azampay/callback/", views.azampay_callback, name="azampay_callback"),

    # REQUIRED: the one AzamPay is calling
    path("v1/Checkout/Callback", csrf_exempt(views.azampay_callback), name="azampay_callback_v1"),

    path("webhook/", views.webhook_handler, name="webhook_handler"),
]
