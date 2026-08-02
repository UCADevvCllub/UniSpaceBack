import asyncio
import os
import logging
from django.core.management.base import BaseCommand
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage
from redis.asyncio import Redis

# Import all routers from the bot package
from camphub.bot.handlers.registration import router as registration_router
from camphub.bot.handlers.lessons import router as lessons_router
from camphub.bot.handlers.sports import router as sports_router
from camphub.bot.handlers.tv_lounges import router as tv_router
from camphub.bot.handlers.contacts import router as contacts_router
from camphub.bot.handlers.my_day import router as my_day_router
from camphub.bot.handlers.admin import router as admin_router
from camphub.bot.handlers.settings import router as settings_router
from camphub.bot.scheduler.reminders import setup_scheduler

load_dotenv()

class Command(BaseCommand):
    help = "Starts the combined Telegram bot"

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        asyncio.run(self.main())

    async def main(self):
        # Configure storage backend (Redis with Memory fallback)
        REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            redis_connection = Redis.from_url(REDIS_URL)
            await redis_connection.ping()
            storage = RedisStorage(redis=redis_connection)
            logging.info("Redis storage connected successfully.")
        except Exception as e:
            logging.warning(f"Could not connect to Redis: {e}. Falling back to MemoryStorage.")
            storage = MemoryStorage()

        TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        bot = Bot(token=TOKEN)
        dp = Dispatcher(storage=storage)

        # Include all handler routers
        dp.include_router(registration_router)
        dp.include_router(lessons_router)
        dp.include_router(sports_router)
        dp.include_router(tv_router)
        dp.include_router(contacts_router)
        dp.include_router(my_day_router)
        dp.include_router(admin_router)
        dp.include_router(settings_router)

        # Setup and start background scheduler
        scheduler = setup_scheduler(bot)

        self.stdout.write(self.style.SUCCESS("Combined Telegram bot is running..."))
        
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()
