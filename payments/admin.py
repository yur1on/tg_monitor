from django.contrib import admin

from .models import PaymentInvoice, YooMoneyNotificationLog


@admin.register(PaymentInvoice)
class PaymentInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "label",
        "user",
        "plan_key",
        "amount",
        "status",
        "operation_id",
        "paid_amount",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "plan_key", "payment_method")
    search_fields = ("label", "operation_id", "user__telegram_id", "user__username")
    readonly_fields = ("created_at", "updated_at")


@admin.register(YooMoneyNotificationLog)
class YooMoneyNotificationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "operation_id", "label", "is_valid", "created_at")
    list_filter = ("is_valid",)
    search_fields = ("operation_id", "label", "sha1_hash")
    readonly_fields = ("payload", "created_at")