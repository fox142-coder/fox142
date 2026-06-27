import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import config
from handlers import router
from payments import payments_router

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    """Меню команд рядом с полем ввода (кнопка «Меню» в Telegram)."""
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Запустить бота"),
        BotCommand(command="buy", description="🛒 Купить VPN"),
        BotCommand(command="subs", description="🔑 Мои подписки"),
        BotCommand(command="help", description="❓ Помощь"),
    ])


def build_bot() -> Bot:
    if not config.bot_token:
        raise RuntimeError(
            "BOT_TOKEN не задан. Создай файл .env (см. .env.example) "
            "и вставь токен от @BotFather."
        )
    return Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


# ---------- Режим 1: long polling (домен не нужен) ----------

async def run_polling():
    bot = build_bot()
    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(payments_router)

    await set_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Бот запущен в режиме polling. Открой его в Telegram и напиши /start")
    await dp.start_polling(bot)


# ---------- Режим 2: webhook (нужен свой домен + SSL) ----------

def run_webhook():
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = build_bot()
    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(payments_router)

    async def on_startup(app: web.Application):
        await set_commands(bot)
        await bot.set_webhook(
            url=config.webhook_url,
            secret_token=config.webhook_secret,
            drop_pending_updates=True,
        )
        logger.info("Webhook установлен: %s", config.webhook_url)

    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config.webhook_secret,
    ).register(app, path=config.webhook_path)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)

    web.run_app(app, host=config.webapp_host, port=config.webapp_port)


def main():
    if config.use_webhook:
        run_webhook()
    else:
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
