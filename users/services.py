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