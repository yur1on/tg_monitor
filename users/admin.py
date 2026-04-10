from datetime import timedelta

from django.contrib import admin
from django.utils import timezone

from .models import AppUser


@admin.action(description="Продлить подписку на 30 дней")
def extend_subscription_30(modeladmin, request, queryset):
    now = timezone.now()
    updated = 0

    for user in queryset:
        base_date = user.subscription_expires_at if user.subscription_expires_at and user.subscription_expires_at > now else now
        user.subscription_expires_at = base_date + timedelta(days=30)
        user.payment_method = "admin"
        user.save(update_fields=["subscription_expires_at", "payment_method"])
        updated += 1

    modeladmin.message_user(request, f"Продлено подписок на 30 дней: {updated}")


@admin.action(description="Продлить подписку на 90 дней")
def extend_subscription_90(modeladmin, request, queryset):
    now = timezone.now()
    updated = 0

    for user in queryset:
        base_date = user.subscription_expires_at if user.subscription_expires_at and user.subscription_expires_at > now else now
        user.subscription_expires_at = base_date + timedelta(days=90)
        user.payment_method = "admin"
        user.save(update_fields=["subscription_expires_at", "payment_method"])
        updated += 1

    modeladmin.message_user(request, f"Продлено подписок на 90 дней: {updated}")


@admin.action(description="Продлить подписку на 365 дней")
def extend_subscription_365(modeladmin, request, queryset):
    now = timezone.now()
    updated = 0

    for user in queryset:
        base_date = user.subscription_expires_at if user.subscription_expires_at and user.subscription_expires_at > now else now
        user.subscription_expires_at = base_date + timedelta(days=365)
        user.payment_method = "admin"
        user.save(update_fields=["subscription_expires_at", "payment_method"])
        updated += 1

    modeladmin.message_user(request, f"Продлено подписок на 365 дней: {updated}")


@admin.action(description="Отключить подписку")
def remove_subscription(modeladmin, request, queryset):
    updated = 0

    for user in queryset:
        user.subscription_expires_at = None
        user.payment_method = ""
        user.save(update_fields=["subscription_expires_at", "payment_method"])
        updated += 1

    modeladmin.message_user(request, f"Подписок отключено: {updated}")


@admin.action(description="Запустить пробный период на 30 дней")
def start_trial_30_days(modeladmin, request, queryset):
    now = timezone.now()
    updated = 0

    for user in queryset:
        user.trial_started_at = now
        user.trial_expires_at = now + timedelta(days=30)
        user.is_trial_used = True
        user.save(update_fields=["trial_started_at", "trial_expires_at", "is_trial_used"])
        updated += 1

    modeladmin.message_user(request, f"Пробный период выдан: {updated}")


@admin.action(description="Сбросить пробный период")
def reset_trial(modeladmin, request, queryset):
    updated = 0

    for user in queryset:
        user.is_trial_used = False
        user.trial_started_at = None
        user.trial_expires_at = None
        user.save(update_fields=["is_trial_used", "trial_started_at", "trial_expires_at"])
        updated += 1

    modeladmin.message_user(request, f"Пробный период сброшен у: {updated}")


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "telegram_id",
        "username",
        "first_name",
        "access_status",
        "payment_method_display",
        "is_trial_used",
        "trial_expires_at",
        "subscription_expires_at",
        "is_active",
        "created_at",
    )
    search_fields = ("telegram_id", "username", "first_name")
    list_filter = (
        "is_trial_used",
        "is_active",
        "payment_method",
    )
    readonly_fields = (
        "created_at",
        "access_status_display",
    )
    actions = [
        extend_subscription_30,
        extend_subscription_90,
        extend_subscription_365,
        remove_subscription,
        start_trial_30_days,
        reset_trial,
    ]

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "telegram_id",
                    "username",
                    "first_name",
                    "is_active",
                    "created_at",
                )
            },
        ),
        (
            "Пробный период",
            {
                "fields": (
                    "is_trial_used",
                    "trial_started_at",
                    "trial_expires_at",
                )
            },
        ),
        (
            "Подписка",
            {
                "fields": (
                    "subscription_expires_at",
                    "payment_method",
                    "access_status_display",
                )
            },
        ),
    )

    def access_status(self, obj):
        now = timezone.now()

        if obj.subscription_expires_at and obj.subscription_expires_at > now:
            return "Подписка активна"

        if obj.trial_expires_at and obj.trial_expires_at > now:
            return "Пробный период"

        return "Нет доступа"

    access_status.short_description = "Статус доступа"

    def payment_method_display(self, obj):
        return obj.get_payment_method_display() if obj.payment_method else "—"

    payment_method_display.short_description = "Способ оплаты"

    def access_status_display(self, obj):
        now = timezone.now()

        if obj.subscription_expires_at and obj.subscription_expires_at > now:
            days_left = max((obj.subscription_expires_at - now).days, 0)
            return f"Подписка активна, осталось {days_left} дн."

        if obj.trial_expires_at and obj.trial_expires_at > now:
            days_left = max((obj.trial_expires_at - now).days, 0)
            return f"Пробный период активен, осталось {days_left} дн."

        return "Доступ не активен"

    access_status_display.short_description = "Текущий статус"