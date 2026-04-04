import os
import asyncio

from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from botapp.handlers import router

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


class Command(BaseCommand):
    help = "Запуск Telegram-бота"

    def handle(self, *args, **options):
        asyncio.run(self.main())

    async def main(self):
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()

        dp.include_router(router)

        self.stdout.write(self.style.SUCCESS("Telegram-бот запущен"))
        await dp.start_polling(bot)