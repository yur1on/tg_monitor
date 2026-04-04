from django.contrib import admin
from .models import AppUser


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ("id", "telegram_id", "username", "first_name", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("telegram_id", "username", "first_name")