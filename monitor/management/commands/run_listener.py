import os
import asyncio
import hashlib
from html import escape

from django.core.management.base import BaseCommand
from django.utils import timezone
from dotenv import load_dotenv
from telethon import TelegramClient, events
from asgiref.sync import sync_to_async

from monitor.models import MonitoredChat, UserChatSubscription, Keyword, StopWord, MatchedMessage
from notifications.services import send_telegram_message
from users.models import AppUser

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELETHON_SESSION", "telethon_monitor")

COUNTRY_LABELS = {
    "BY": "Беларусь",
    "RU": "Россия",
    "OTHER": "Другая страна",
}

COUNTRY_EMOJIS = {
    "BY": "🇧🇾",
    "RU": "🇷🇺",
    "OTHER": "🌍",
}


def normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def make_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_monitored_chat_sync(chat_id: int):
    return MonitoredChat.objects.filter(
        telegram_chat_id=chat_id,
        is_active=True
    ).first()


def get_subscriptions_sync(monitored_chat_id: int):
    return list(
        UserChatSubscription.objects.select_related("user", "chat").filter(
            chat_id=monitored_chat_id,
            is_active=True,
            user__is_active=True,
        )
    )


def get_keywords_sync(user_id: int):
    return list(
        Keyword.objects.filter(
            user_id=user_id,
            is_active=True
        ).order_by("phrase")
    )


def get_stop_words_sync(user_id: int):
    return list(
        StopWord.objects.filter(
            user_id=user_id,
            is_active=True
        ).order_by("phrase")
    )


def matched_message_exists_sync(user_id: int, message_hash: str):
    return MatchedMessage.objects.filter(
        user_id=user_id,
        message_hash=message_hash
    ).exists()


def create_matched_message_sync(user_id: int, message_hash: str):
    return MatchedMessage.objects.create(
        user_id=user_id,
        message_hash=message_hash,
    )


def user_has_access_sync(user_id: int) -> bool:
    user = AppUser.objects.filter(id=user_id, is_active=True).first()
    if not user:
        return False

    now = timezone.now()

    has_trial = bool(user.trial_expires_at and user.trial_expires_at > now)
    has_subscription = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    return has_trial or has_subscription


class Command(BaseCommand):
    help = "Запуск мониторинга чатов через Telethon"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    async def main(self):
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()

        is_authorized = await client.is_user_authorized()
        if not is_authorized:
            raise RuntimeError(
                "Telethon не авторизован. Сначала выполни: python manage.py telegram_login"
            )

        self.stdout.write(self.style.SUCCESS("Telethon подключен"))
        self.stdout.write(self.style.SUCCESS("Мониторинг запущен, жду новые сообщения..."))

        @client.on(events.NewMessage)
        async def handler(event):
            text = event.raw_text or ""
            chat_id = event.chat_id
            msg_id = event.message.id

            if not text.strip():
                return

            normalized = normalize_text(text)

            if len(normalized) < 4:
                return

            msg_hash = make_hash(normalized)

            monitored_chat = await sync_to_async(get_monitored_chat_sync)(chat_id)

            if not monitored_chat:
                return

            subscriptions = await sync_to_async(get_subscriptions_sync)(monitored_chat.id)

            if not subscriptions:
                return

            for subscription in subscriptions:
                has_access = await sync_to_async(user_has_access_sync)(subscription.user.id)
                if not has_access:
                    continue

                keywords = await sync_to_async(get_keywords_sync)(subscription.user.id)
                stop_words = await sync_to_async(get_stop_words_sync)(subscription.user.id)

                stop_triggered = False
                for stop_word in stop_words:
                    stop_phrase = (stop_word.phrase or "").strip().lower()
                    if stop_phrase and stop_phrase in normalized:
                        stop_triggered = True
                        break

                if stop_triggered:
                    continue

                for keyword in keywords:
                    phrase = (keyword.phrase or "").strip().lower()

                    if phrase and phrase in normalized:
                        already_exists = await sync_to_async(matched_message_exists_sync)(
                            subscription.user.id,
                            msg_hash
                        )

                        if already_exists:
                            continue

                        await sync_to_async(create_matched_message_sync)(
                            subscription.user.id,
                            msg_hash,
                        )

                        if monitored_chat.username:
                            chat_username = monitored_chat.username.strip("@")
                            message_link = f"https://t.me/{chat_username}/{msg_id}"
                        else:
                            message_link = ""

                        country_label = COUNTRY_LABELS.get(monitored_chat.country, monitored_chat.country)
                        country_emoji = COUNTRY_EMOJIS.get(monitored_chat.country, "🌍")

                        short_text = text.strip()
                        if len(short_text) > 700:
                            short_text = short_text[:700] + "..."

                        notify_text = (
                            "<b>🔔 Новое совпадение</b>\n\n"
                            f"💬 <b>Чат:</b> {escape(monitored_chat.title or monitored_chat.input_name or 'Без названия')}\n"
                            f"{country_emoji} <b>Страна:</b> {country_label}\n"
                            f"🔑 <b>Ключевое слово:</b> {escape(keyword.phrase)}\n\n"
                            f"<b>📝 Сообщение:</b>\n"
                            f"{escape(short_text)}"
                        )

                        if message_link:
                            notify_text += f'\n\n<a href="{message_link}">Открыть сообщение</a>'

                        try:
                            await sync_to_async(send_telegram_message)(
                                subscription.user.telegram_id,
                                notify_text
                            )
                        except Exception as e:
                            print("Ошибка отправки уведомления:", e)

                        break

        await client.run_until_disconnected()