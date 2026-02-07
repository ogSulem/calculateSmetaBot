import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.settings import Settings
from bot.db import init_db
from bot.handlers.client import router as client_router
from bot.handlers.admin import router as admin_router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()

    await init_db(settings.db_path)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(client_router)
    dp.include_router(admin_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
