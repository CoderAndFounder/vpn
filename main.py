import asyncio
import os
from loguru import logger
from bot import bot_start

os.makedirs('logs', exist_ok=True)
logger.add("logs/bot.log", rotation="1 day", compression="zip", 
           encoding="utf-8", format="{time} | {level} | {message}",
           level="INFO")

if __name__ == '__main__':
    try:
        logger.info("Запуск бота...")
        asyncio.run(bot_start())
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
