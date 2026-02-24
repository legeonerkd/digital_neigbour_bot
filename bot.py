"""Digital Neighbour Bot - главный файл."""

import asyncio
import logging
import os
from functools import partial

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from dotenv import load_dotenv

from config import DB_PATH
from database import ReminderStore
from handlers import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")


def register_handlers(dp: Dispatcher, store: ReminderStore) -> None:
    """Регистрация всех обработчиков команд и событий.
    
    Args:
        dp: Диспетчер aiogram
        store: Хранилище данных
    """
    
    # ========== Команды start ==========
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_contacts, Command("contacts"))
    dp.message.register(cmd_emergency, Command("emergency"))
    dp.message.register(cmd_faq, Command("faq"))
    
    # ========== Команды timezone ==========
    dp.message.register(
        partial(cmd_set_timezone, store=store),
        Command("set_timezone")
    )
    dp.message.register(
        partial(cmd_my_timezone, store=store),
        Command("my_timezone")
    )
    
    # ========== Команды reminders ==========
    dp.message.register(
        partial(cmd_remind, store=store),
        Command("remind")
    )
    dp.message.register(
        partial(cmd_remind_once, store=store),
        Command("remind_once")
    )
    dp.message.register(
        partial(cmd_edit_reminder, store=store),
        Command("edit_reminder")
    )
    dp.message.register(
        partial(cmd_edit_once_reminder, store=store),
        Command("edit_once_reminder")
    )
    dp.message.register(
        partial(cmd_my_reminders, store=store),
        Command("my_reminders")
    )
    dp.message.register(
        partial(cmd_next_reminders, store=store),
        Command("next_reminders")
    )
    dp.message.register(
        partial(cmd_delete_reminder, store=store),
        Command("delete_reminder")
    )
    dp.message.register(
        partial(cmd_disable_reminder, store=store),
        Command("disable_reminder")
    )
    dp.message.register(
        partial(cmd_enable_reminder, store=store),
        Command("enable_reminder")
    )
    dp.message.register(
        partial(cmd_clear_reminders, store=store),
        Command("clear_reminders")
    )
    
    # ========== Команды services ==========
    dp.message.register(
        partial(cmd_services, store=store),
        Command("services")
    )
    dp.message.register(
        partial(cmd_service_category, store=store),
        Command("service_category")
    )
    dp.message.register(
        partial(cmd_add_category, store=store),
        Command("add_category")
    )
    dp.message.register(
        partial(cmd_add_service, store=store),
        Command("add_service")
    )
    dp.message.register(
        partial(cmd_nearby_services, store=store),
        Command("nearby_services")
    )
    
    # ========== Команды backup ==========
    dp.message.register(
        partial(cmd_export_reminders, store=store),
        Command("export_reminders")
    )
    dp.message.register(
        partial(cmd_import_reminders, store=store),
        Command("import_reminders")
    )
    
    # ========== Обработчики кнопок главного меню ==========
    dp.message.register(
        handle_faq_button,
        F.text.in_(["FAQ", "❓ FAQ"])
    )
    dp.message.register(
        handle_contacts_button,
        F.text.in_(["Полезные контакты", "📞 Полезные контакты"])
    )
    dp.message.register(
        handle_emergency_button,
        F.text.in_(["Экстренная помощь", "🆘 Экстренная помощь"])
    )
    dp.message.register(
        partial(handle_my_reminders_button, store=store),
        F.text.in_(["Мои напоминания", "⏰ Мои напоминания"])
    )
    dp.message.register(
        partial(handle_next_reminders_button, store=store),
        F.text.in_(["Ближайшие напоминания", "⏰ Ближайшие напоминания"])
    )
    dp.message.register(
        partial(handle_services_button, store=store),
        F.text.in_(["Сервисы", "🛠 Сервисы"])
    )
    dp.message.register(
        partial(handle_nearby_services_button, store=store),
        F.text.in_(["Ближайшие сервисы", "📍 Ближайшие сервисы"])
    )
    
    # ========== Обработчик геолокации ==========
    dp.message.register(
        partial(handle_location, store=store),
        F.location
    )
    
    # ========== Callback обработчики ==========
    dp.callback_query.register(
        partial(callback_toggle_reminder, store=store),
        F.data.startswith("toggle_")
    )
    dp.callback_query.register(
        partial(callback_delete_reminder, store=store),
        F.data.startswith("delete_")
    )
    dp.callback_query.register(
        partial(callback_service_category, store=store),
        F.data.startswith("category:")
    )


async def main() -> None:
    """Главная функция запуска бота."""
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Инициализация хранилища
    store = ReminderStore(DB_PATH)
    
    try:
        # Регистрация обработчиков
        register_handlers(dp, store)
        
        # Запуск воркера напоминаний
        worker = asyncio.create_task(reminder_worker(bot, store))
        
        try:
            logging.info("Бот запущен")
            await dp.start_polling(bot)
        finally:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
            logging.info("Бот остановлен")
    finally:
        # Закрытие соединения с БД
        store.close()


if __name__ == "__main__":
    asyncio.run(main())
