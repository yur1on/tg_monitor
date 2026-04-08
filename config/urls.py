from django.contrib import admin
from django.urls import path
import config.admin  # noqa

from payments.views import yoomoney_webhook, invoice_status

urlpatterns = [
    path("admin/", admin.site.urls),
    path("payments/yoomoney/", yoomoney_webhook, name="yoomoney_webhook"),
    path("payments/invoice/<str:label>/", invoice_status, name="invoice_status"),
]