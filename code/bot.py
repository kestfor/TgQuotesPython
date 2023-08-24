import asyncio
from aiogram import Bot, Dispatcher
import callbacks
import handlers
from config_reader import config


async def main():
    token = config.bot_token.get_secret_value()
    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_routers(callbacks.router, handlers.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
