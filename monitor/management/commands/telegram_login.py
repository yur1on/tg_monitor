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
    help = "Первичная авторизация Telethon"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    async def main(self):
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

        await client.start()

        me = await client.get_me()

        self.stdout.write(self.style.SUCCESS("Успешный вход в Telegram"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Аккаунт: {getattr(me, 'username', '') or getattr(me, 'first_name', '')}"
            )
        )

        await client.disconnect()