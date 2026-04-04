import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELETHON_SESSION", "telethon_monitor")


def normalize_chat_input(value: str) -> str:
    value = (value or "").strip()

    if value.startswith("https://t.me/"):
        value = value.replace("https://t.me/", "")
    elif value.startswith("http://t.me/"):
        value = value.replace("http://t.me/", "")

    return value.strip("/")


async def fetch_chat_data_async(chat_input: str):
    chat_input = normalize_chat_input(chat_input)

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    await client.connect()

    is_authorized = await client.is_user_authorized()
    if not is_authorized:
        await client.disconnect()
        raise RuntimeError(
            "Telethon не авторизован. Сначала выполни: python manage.py telegram_login"
        )

    entity = await client.get_entity(chat_input)

    title = getattr(entity, "title", "") or ""
    username = getattr(entity, "username", "") or ""
    entity_id = getattr(entity, "id", None)

    if entity_id is None:
        await client.disconnect()
        raise ValueError("Не удалось получить ID чата")

    full_chat_id = int(f"-100{entity_id}")

    await client.disconnect()

    return {
        "title": title,
        "username": username,
        "telegram_chat_id": full_chat_id,
    }


def fetch_chat_data(chat_input: str):
    return asyncio.run(fetch_chat_data_async(chat_input))