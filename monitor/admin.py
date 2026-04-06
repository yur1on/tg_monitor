from django.contrib import admin, messages
from .models import MonitoredChat, Keyword, StopWord, UserChatSubscription, ChatRequest
from .telegram_utils import fetch_chat_data


@admin.action(description="Заполнить данные чата из Telegram")
def fill_chat_data(modeladmin, request, queryset):
    success_count = 0

    for obj in queryset:
        if not obj.input_name:
            messages.warning(request, f"У записи ID={obj.id} не заполнено поле 'Что ввели'")
            continue

        try:
            data = fetch_chat_data(obj.input_name)
            obj.title = data["title"]
            obj.username = data["username"]
            obj.telegram_chat_id = data["telegram_chat_id"]
            obj.save()
            success_count += 1
        except Exception as e:
            messages.error(request, f"Ошибка для '{obj.input_name}': {e}")

    if success_count:
        messages.success(request, f"Успешно обновлено чатов: {success_count}")


@admin.register(MonitoredChat)
class MonitoredChatAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "country",
        "input_name",
        "telegram_chat_id",
        "username",
        "is_active",
        "created_at",
    )
    list_filter = ("country", "is_active")
    search_fields = ("title", "username", "input_name", "telegram_chat_id")
    actions = [fill_chat_data]


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("id", "phrase", "user", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("phrase", "user__username", "user__telegram_id")


@admin.register(StopWord)
class StopWordAdmin(admin.ModelAdmin):
    list_display = ("id", "phrase", "user", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("phrase", "user__username", "user__telegram_id")


@admin.register(UserChatSubscription)
class UserChatSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "chat", "is_active", "created_at")
    list_filter = ("is_active", "chat__country")
    search_fields = ("user__username", "chat__title")


@admin.register(ChatRequest)
class ChatRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "chat_input", "country", "user", "is_processed", "created_at")
    list_filter = ("country", "is_processed")
    search_fields = ("chat_input", "comment", "user__username", "user__telegram_id")