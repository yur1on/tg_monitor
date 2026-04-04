import os
import asyncio

from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELETHON_SESSION", "telethon_monitor")


class Command(BaseCommand):
    help = "Показать чаты и каналы, доступные Telethon"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    async def main(self):
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()

        is_authorized = await client.is_user_authorized()
        if not is_authorized:
            raise RuntimeError("Telethon не авторизован")

        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            title = getattr(entity, "title", None) or getattr(entity, "first_name", None) or "Без названия"
            username = getattr(entity, "username", "") or ""
            entity_id = getattr(entity, "id", None)

            if entity_id is not None:
                full_chat_id = f"-100{entity_id}"
            else:
                full_chat_id = "нет"

            self.stdout.write("================================")
            self.stdout.write(f"title: {title}")
            self.stdout.write(f"username: @{username}" if username else "username: нет")
            self.stdout.write(f"id: {entity_id}")
            self.stdout.write(f"chat_id for DB: {full_chat_id}")

        await client.disconnect()