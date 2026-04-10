import os
import asyncio
import hashlib
import time
from collections import defaultdict
from html import escape

from django.core.management.base import BaseCommand
from django.utils import timezone
from dotenv import load_dotenv
from telethon import TelegramClient, events
from asgiref.sync import sync_to_async

from monitor.models import (
    MonitoredChat,
    UserChatSubscription,
    Keyword,
    StopWord,
    MatchedMessage,
)
from notifications.services import send_telegram_message

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

CACHE_TTL_SECONDS = 30


class SimpleTTLCache:
    def __init__(self, ttl_seconds: int = 30):
        self.ttl_seconds = ttl_seconds
        self._data = {}

    def get(self, key):
        item = self._data.get(key)
        if not item:
            return None

        expires_at, value = item
        if time.monotonic() >= expires_at:
            self._data.pop(key, None)
            return None

        return value

    def set(self, key, value):
        self._data[key] = (time.monotonic() + self.ttl_seconds, value)

    def cleanup(self):
        now = time.monotonic()
        expired_keys = [
            key for key, (expires_at, _) in self._data.items()
            if now >= expires_at
        ]
        for key in expired_keys:
            self._data.pop(key, None)


monitored_chat_cache = SimpleTTLCache(CACHE_TTL_SECONDS)
subscriptions_cache = SimpleTTLCache(CACHE_TTL_SECONDS)
keywords_cache = SimpleTTLCache(CACHE_TTL_SECONDS)
stop_words_cache = SimpleTTLCache(CACHE_TTL_SECONDS)


def normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def make_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_monitored_chat_sync(chat_id: int):
    return MonitoredChat.objects.filter(
        telegram_chat_id=chat_id,
        is_active=True,
    ).first()


def get_active_subscriptions_sync(monitored_chat_id: int):
    return list(
        UserChatSubscription.objects.select_related("user", "chat").filter(
            chat_id=monitored_chat_id,
            is_active=True,
            user__is_active=True,
        )
    )


def get_keywords_map_sync(user_ids: list[int]):
    result = defaultdict(list)

    rows = Keyword.objects.filter(
        user_id__in=user_ids,
        is_active=True,
    ).values("user_id", "phrase").order_by("phrase")

    for row in rows:
        phrase = normalize_text(row["phrase"])
        if phrase:
            result[row["user_id"]].append(phrase)

    return dict(result)


def get_stop_words_map_sync(user_ids: list[int]):
    result = defaultdict(list)

    rows = StopWord.objects.filter(
        user_id__in=user_ids,
        is_active=True,
    ).values("user_id", "phrase").order_by("phrase")

    for row in rows:
        phrase = normalize_text(row["phrase"])
        if phrase:
            result[row["user_id"]].append(phrase)

    return dict(result)


def create_matched_message_if_not_exists_sync(user_id: int, message_hash: str) -> bool:
    _, created = MatchedMessage.objects.get_or_create(
        user_id=user_id,
        message_hash=message_hash,
    )
    return created


def user_has_access_from_obj(user) -> bool:
    now = timezone.now()

    has_trial = bool(user.trial_expires_at and user.trial_expires_at > now)
    has_subscription = bool(user.subscription_expires_at and user.subscription_expires_at > now)

    return has_trial or has_subscription


def build_message_link(username: str, msg_id: int) -> str:
    username = (username or "").strip().strip("@")
    if not username:
        return ""
    return f"https://t.me/{username}/{msg_id}"


def build_notify_text(monitored_chat, keyword_phrase: str, text: str, message_link: str) -> str:
    country_label = COUNTRY_LABELS.get(monitored_chat.country, monitored_chat.country)
    country_emoji = COUNTRY_EMOJIS.get(monitored_chat.country, "🌍")

    short_text = (text or "").strip()
    if len(short_text) > 700:
        short_text = short_text[:700] + "..."

    notify_text = (
        "<b>🔔 Новое совпадение</b>\n\n"
        f"💬 <b>Чат:</b> {escape(monitored_chat.title or monitored_chat.input_name or 'Без названия')}\n"
        f"{country_emoji} <b>Страна:</b> {country_label}\n"
        f"🔑 <b>Ключевая фраза:</b> {escape(keyword_phrase)}\n\n"
        f"<b>📝 Сообщение:</b>\n"
        f"{escape(short_text)}"
    )

    if message_link:
        notify_text += f'\n\n<a href="{message_link}">Открыть сообщение</a>'

    return notify_text


async def get_monitored_chat_cached(chat_id: int):
    cached = monitored_chat_cache.get(chat_id)
    if cached is not None:
        return cached

    monitored_chat = await sync_to_async(get_monitored_chat_sync)(chat_id)
    monitored_chat_cache.set(chat_id, monitored_chat)
    return monitored_chat


async def get_subscriptions_cached(monitored_chat_id: int):
    cached = subscriptions_cache.get(monitored_chat_id)
    if cached is not None:
        return cached

    subscriptions = await sync_to_async(get_active_subscriptions_sync)(monitored_chat_id)
    subscriptions_cache.set(monitored_chat_id, subscriptions)
    return subscriptions


def make_user_ids_cache_key(user_ids: list[int]) -> tuple[int, ...]:
    return tuple(sorted(user_ids))


async def get_keywords_map_cached(user_ids: list[int]):
    key = make_user_ids_cache_key(user_ids)

    cached = keywords_cache.get(key)
    if cached is not None:
        return cached

    keywords_map = await sync_to_async(get_keywords_map_sync)(user_ids)
    keywords_cache.set(key, keywords_map)
    return keywords_map


async def get_stop_words_map_cached(user_ids: list[int]):
    key = make_user_ids_cache_key(user_ids)

    cached = stop_words_cache.get(key)
    if cached is not None:
        return cached

    stop_words_map = await sync_to_async(get_stop_words_map_sync)(user_ids)
    stop_words_cache.set(key, stop_words_map)
    return stop_words_map


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

        processed_events = 0

        @client.on(events.NewMessage)
        async def handler(event):
            nonlocal processed_events

            text = event.raw_text or ""
            chat_id = event.chat_id
            msg_id = event.message.id

            if not text.strip():
                return

            normalized = normalize_text(text)
            if len(normalized) < 4:
                return

            msg_hash = make_hash(normalized)

            monitored_chat = await get_monitored_chat_cached(chat_id)
            if not monitored_chat:
                return

            subscriptions = await get_subscriptions_cached(monitored_chat.id)
            if not subscriptions:
                return

            user_ids = [subscription.user_id for subscription in subscriptions]

            keywords_map, stop_words_map = await asyncio.gather(
                get_keywords_map_cached(user_ids),
                get_stop_words_map_cached(user_ids),
            )

            message_link = build_message_link(monitored_chat.username, msg_id)

            for subscription in subscriptions:
                user = subscription.user

                if not user_has_access_from_obj(user):
                    continue

                keywords = keywords_map.get(user.id, [])
                if not keywords:
                    continue

                stop_words = stop_words_map.get(user.id, [])
                if stop_words and any(stop_word in normalized for stop_word in stop_words):
                    continue

                matched_keyword = next((phrase for phrase in keywords if phrase in normalized), None)
                if not matched_keyword:
                    continue

                created = await sync_to_async(create_matched_message_if_not_exists_sync)(
                    user.id,
                    msg_hash,
                )
                if not created:
                    continue

                notify_text = build_notify_text(
                    monitored_chat=monitored_chat,
                    keyword_phrase=matched_keyword,
                    text=text,
                    message_link=message_link,
                )

                try:
                    await sync_to_async(send_telegram_message)(
                        user.telegram_id,
                        notify_text,
                    )
                except Exception as e:
                    print(f"Ошибка отправки уведомления user_id={user.id}: {e}")

            processed_events += 1
            if processed_events % 100 == 0:
                monitored_chat_cache.cleanup()
                subscriptions_cache.cleanup()
                keywords_cache.cleanup()
                stop_words_cache.cleanup()

        await client.run_until_disconnected()