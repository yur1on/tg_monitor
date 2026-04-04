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
    help = "Показать Telegram-аккаунт Telethon"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    async def main(self):
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()

        is_authorized = await client.is_user_authorized()
        if not is_authorized:
            raise RuntimeError("Telethon не авторизован")

        me = await client.get_me()

        self.stdout.write(self.style.SUCCESS("Telethon аккаунт:"))
        self.stdout.write(f"id: {me.id}")
        self.stdout.write(f"username: @{me.username}" if me.username else "username: нет")
        self.stdout.write(f"name: {(me.first_name or '')} {(me.last_name or '')}".strip())

        await client.disconnect()