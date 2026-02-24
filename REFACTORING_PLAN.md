# План завершения рефакторинга Digital Neighbour Bot

## Текущее состояние

### Выполнено ✅
- Создана модульная структура (models, config, database, utils, handlers)
- Созданы базовые handlers: start.py, timezone.py, worker.py
- Исправлены критические проблемы безопасности
- Добавлена конфигурация для Railway

### Не выполнено ❌
- bot.py (61887 строк) содержит весь старый код
- Обработчики не перенесены в модули
- Новые модули не используются

## Этап 1: Создание недостающих handlers

### 1.1 handlers/reminders.py
Извлечь из bot.py:
- `cmd_remind()` - строка 1054
- `cmd_remind_once()` - строка 1090
- `cmd_edit_reminder()` - строка 1135
- `cmd_edit_once_reminder()` - строка 1180
- `cmd_my_reminders()` - строка 1246
- `cmd_next_reminders()` - строка 1264
- `cmd_delete_reminder()` - строка 1335
- `cmd_disable_reminder()` - строка 1373
- `cmd_enable_reminder()` - строка 1405
- `cmd_clear_reminders()` - строка 1437

**Зависимости:**
```python
from aiogram.filters import CommandObject
from aiogram.types import Message

from database.store import ReminderStore
from utils.validators import validate_reminder_text
from utils.parsers import parse_time, parse_once_datetime, parse_index
from utils.formatters import (
    build_reminders_text,
    build_delete_keyboard,
    format_utc_offset,
)
from utils.time_utils import next_trigger, next_run_local, utc_now
from config import MAX_REMINDER_TEXT_LENGTH
```

### 1.2 handlers/services.py
Извлечь из bot.py:
- `cmd_services()` - показать категории
- `cmd_service_category()` - показать сервисы в категории
- `cmd_add_category()` - добавить категорию
- `cmd_add_service()` - добавить сервис
- `cmd_nearby_services()` - ближайшие сервисы (с геолокацией)
- `handle_services_button()` - обработчик кнопки

**Зависимости:**
```python
from aiogram.filters import CommandObject
from aiogram.types import Message, Location

from database.store import ReminderStore
from utils.validators import (
    validate_category_name,
    validate_service_title,
    validate_service_contact,
    validate_service_notes,
)
from utils.formatters import (
    build_service_categories_keyboard,
    format_services,
)
from utils.pharmacy_scraper import fetch_live_duty_pharmacies
from config import DUTY_PHARMACY_CATEGORY
```

### 1.3 handlers/callbacks.py
Извлечь из bot.py все callback обработчики:
- `callback_toggle_reminder()` - включить/выключить напоминание
- `callback_delete_reminder()` - удалить напоминание
- Другие callback обработчики

**Зависимости:**
```python
from aiogram.types import CallbackQuery

from database.store import ReminderStore
from utils.formatters import build_reminders_text, build_delete_keyboard
```

### 1.4 handlers/backup.py
Извлечь из bot.py:
- `cmd_export_reminders()` - экспорт напоминаний
- `cmd_import_reminders()` - импорт напоминаний

**Зависимости:**
```python
import json
from io import BytesIO

from aiogram.types import Message, BufferedInputFile

from database.store import ReminderStore
from config import MAX_IMPORT_REMINDERS
```

### 1.5 handlers/__init__.py
Создать файл с экспортом всех обработчиков:
```python
"""Обработчики команд бота."""

from .start import (
    cmd_start,
    cmd_help,
    cmd_contacts,
    cmd_emergency,
    cmd_faq,
    handle_faq_button,
    handle_contacts_button,
    handle_emergency_button,
)
from .timezone import cmd_set_timezone, cmd_my_timezone
from .reminders import (
    cmd_remind,
    cmd_remind_once,
    cmd_edit_reminder,
    cmd_edit_once_reminder,
    cmd_my_reminders,
    cmd_next_reminders,
    cmd_delete_reminder,
    cmd_disable_reminder,
    cmd_enable_reminder,
    cmd_clear_reminders,
    handle_my_reminders_button,
    handle_next_reminders_button,
)
from .services import (
    cmd_services,
    cmd_service_category,
    cmd_add_category,
    cmd_add_service,
    cmd_nearby_services,
    handle_services_button,
    handle_nearby_services_button,
)
from .callbacks import (
    callback_toggle_reminder,
    callback_delete_reminder,
)
from .backup import cmd_export_reminders, cmd_import_reminders
from .worker import reminder_worker

__all__ = [
    # start
    "cmd_start",
    "cmd_help",
    "cmd_contacts",
    "cmd_emergency",
    "cmd_faq",
    "handle_faq_button",
    "handle_contacts_button",
    "handle_emergency_button",
    # timezone
    "cmd_set_timezone",
    "cmd_my_timezone",
    # reminders
    "cmd_remind",
    "cmd_remind_once",
    "cmd_edit_reminder",
    "cmd_edit_once_reminder",
    "cmd_my_reminders",
    "cmd_next_reminders",
    "cmd_delete_reminder",
    "cmd_disable_reminder",
    "cmd_enable_reminder",
    "cmd_clear_reminders",
    "handle_my_reminders_button",
    "handle_next_reminders_button",
    # services
    "cmd_services",
    "cmd_service_category",
    "cmd_add_category",
    "cmd_add_service",
    "cmd_nearby_services",
    "handle_services_button",
    "handle_nearby_services_button",
    # callbacks
    "callback_toggle_reminder",
    "callback_delete_reminder",
    # backup
    "cmd_export_reminders",
    "cmd_import_reminders",
    # worker
    "reminder_worker",
]
```

## Этап 2: Обновление bot.py

Заменить весь bot.py на новую версию:

```python
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
    """Регистрация всех обработчиков."""
    
    # Создаем partial функции с store
    # Команды start
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_contacts, Command("contacts"))
    dp.message.register(cmd_emergency, Command("emergency"))
    dp.message.register(cmd_faq, Command("faq"))
    
    # Команды timezone
    dp.message.register(
        partial(cmd_set_timezone, store=store),
        Command("set_timezone")
    )
    dp.message.register(
        partial(cmd_my_timezone, store=store),
        Command("my_timezone")
    )
    
    # Команды reminders
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
    
    # Команды services
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
    
    # Команды backup
    dp.message.register(
        partial(cmd_export_reminders, store=store),
        Command("export_reminders")
    )
    dp.message.register(
        partial(cmd_import_reminders, store=store),
        Command("import_reminders")
    )
    
    # Обработчики кнопок
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
    
    # Callback обработчики
    dp.callback_query.register(
        partial(callback_toggle_reminder, store=store),
        F.data.startswith("toggle_")
    )
    dp.callback_query.register(
        partial(callback_delete_reminder, store=store),
        F.data.startswith("delete_")
    )


async def main() -> None:
    """Главная функция запуска бота."""
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Инициализация хранилища
    with ReminderStore(DB_PATH) as store:
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


if __name__ == "__main__":
    asyncio.run(main())
```

## Этап 3: Добавление геолокации

В handlers/services.py добавить обработку геолокации:

```python
async def cmd_nearby_services(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /nearby_services."""
    await message.answer(
        "Отправьте вашу геолокацию, чтобы найти ближайшие сервисы",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

async def handle_location(message: Message, store: ReminderStore) -> None:
    """Обработчик получения геолокации."""
    if not message.location:
        return
    
    lat = message.location.latitude
    lon = message.location.longitude
    
    # TODO: Реализовать поиск ближайших сервисов по координатам
    # Пока показываем все сервисы
    await message.answer(
        f"Получена геолокация: {lat}, {lon}\n\n"
        "Функция поиска ближайших сервисов в разработке."
    )
```

## Этап 4: Тестирование

1. Запустить бота локально
2. Проверить все команды
3. Проверить все кнопки
4. Проверить callback-кнопки
5. Проверить воркер напоминаний
6. Проверить экспорт/импорт

## Этап 5: Деплой

1. Закоммитить изменения
2. Запушить в репозиторий
3. Railway автоматически задеплоит
4. Проверить работу на Railway

## Примечания

- Текущий bot.py сохранен как bot.py.backup
- Можно выполнять рефакторинг поэтапно
- После каждого этапа тестировать
- Использовать git для отката при необходимости
