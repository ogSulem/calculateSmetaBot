import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.types import Update
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

    # Webhook setup
    railway_url = os.getenv('RAILWAY_STATIC_URL')  # e.g., your-app.railway.app
    if not railway_url:
        logging.error("RAILWAY_STATIC_URL not set")
        return
    
    webhook_url = f"https://{railway_url}/webhook"
    await bot.set_webhook(url=webhook_url, drop_pending_updates=True)

    async def handle_webhook(request):
        try:
            data = await request.json()
            update = Update(**data)
            await dp.feed_update(bot, update)
        except Exception as e:
            logging.error(f"Webhook error: {e}")
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_post('/webhook', handle_webhook)
    app.router.add_get('/health', lambda r: web.Response(text="OK"))

    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Webhook server started on port {port}, URL: {webhook_url}")

    # Keep alive
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await runner.cleanup()
        await bot.delete_webhook()


if __name__ == "__main__":
    asyncio.run(main())
