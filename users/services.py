from datetime import timedelta
from django.utils import timezone

from .models import AppUser


def get_or_create_app_user(telegram_id: int, username: str = "", first_name: str = "") -> AppUser:
    user, created = AppUser.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "username": username or "",
            "first_name": first_name or "",
            "is_active": True,
        }
    )

    updated = False

    if username and user.username != username:
        user.username = username
        updated = True

    if first_name and user.first_name != first_name:
        user.first_name = first_name
        updated = True

    if not user.is_active:
        user.is_active = True
        updated = True

    if updated:
        user.save()

    return user


def ensure_user_trial(telegram_id: int) -> AppUser:
    user = AppUser.objects.get(telegram_id=telegram_id)
    user.start_trial_if_needed()
    user.refresh_from_db()
    return user


def get_user_access_status(telegram_id: int) -> dict:
    user = AppUser.objects.get(telegram_id=telegram_id)
    now = timezone.now()

    status = {
        "has_access": user.has_access,
        "has_active_trial": user.has_active_trial,
        "has_active_subscription": user.has_active_subscription,
        "trial_expires_at": user.trial_expires_at,
        "subscription_expires_at": user.subscription_expires_at,
        "payment_method": user.payment_method,
        "days_left": 0,
    }

    if user.has_active_subscription:
        delta = user.subscription_expires_at - now
        status["days_left"] = max(delta.days, 0)
    elif user.has_active_trial:
        delta = user.trial_expires_at - now
        status["days_left"] = max(delta.days, 0)

    return status


def require_paid_access(telegram_id: int) -> bool:
    user = AppUser.objects.get(telegram_id=telegram_id)
    return user.has_access


def extend_subscription(telegram_id: int, days: int, payment_method: str = ""):
    user = AppUser.objects.get(telegram_id=telegram_id)
    now = timezone.now()

    base_date = user.subscription_expires_at if user.subscription_expires_at and user.subscription_expires_at > now else now
    user.subscription_expires_at = base_date + timedelta(days=days)

    if payment_method:
        user.payment_method = payment_method

    user.save(update_fields=["subscription_expires_at", "payment_method"])
    return user