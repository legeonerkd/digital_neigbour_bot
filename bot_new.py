"""Digital Neighbour Bot - главный файл (рефакторинг)."""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from config import DB_PATH
from database import ReminderStore
from handlers.worker import reminder_worker

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")


async def main() -> None:
    """Главная функция запуска бота."""
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Инициализация хранилища
    with ReminderStore(DB_PATH) as store:
        # TODO: Регистрация обработчиков
        # Пока используем старый bot.py
        
        # Запуск воркера напоминаний
        worker = asyncio.create_task(reminder_worker(bot, store))
        
        try:
            await dp.start_polling(bot)
        finally:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    asyncio.run(main())
