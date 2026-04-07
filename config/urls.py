from django.contrib import admin
from django.urls import path
import config.admin  # noqa
from payments.views import yoomoney_webhook

urlpatterns = [
    path("admin/", admin.site.urls),
    path("payments/yoomoney/", yoomoney_webhook, name="yoomoney_webhook"),
]