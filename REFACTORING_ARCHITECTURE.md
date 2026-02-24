# Архитектура рефакторинга Digital Neighbour Bot

## Обзор

Рефакторинг монолитного [`bot.py`](../digital_neighbour_bot/bot.py) (61887 строк) в модульную структуру с разделением ответственности.

## Текущая структура проекта

```
digital_neighbour_bot/
├── config/
│   ├── __init__.py          ✅ Экспорт настроек
│   └── settings.py          ✅ Константы и настройки
├── data/
│   ├── __init__.py          ✅ Пустой
│   └── content.py           ✅ Статический контент (FAQ, контакты)
├── database/
│   ├── __init__.py          ✅ Экспорт ReminderStore
│   └── store.py             ✅ Класс работы с БД
├── handlers/
│   ├── start.py             ✅ Базовые команды (start, help, contacts, emergency, faq)
│   ├── timezone.py          ✅ Команды часового пояса
│   ├── worker.py            ✅ Фоновый воркер напоминаний
│   ├── reminders.py         ❌ СОЗДАТЬ
│   ├── services.py          ❌ СОЗДАТЬ
│   ├── callbacks.py         ❌ СОЗДАТЬ
│   ├── backup.py            ❌ СОЗДАТЬ
│   └── __init__.py          ❌ СОЗДАТЬ
├── keyboards/
│   ├── __init__.py          ✅ Пустой
│   └── main_menu.py         ✅ Главное меню
├── models/
│   ├── __init__.py          ✅ Экспорт Reminder
│   └── reminder.py          ✅ Dataclass Reminder
├── utils/
│   ├── __init__.py          ✅ Экспорт утилит
│   ├── formatters.py        ✅ Форматирование данных
│   ├── parsers.py           ✅ Парсинг входных данных
│   ├── pharmacy_scraper.py  ✅ Парсинг дежурных аптек
│   ├── time_utils.py        ✅ Работа со временем
│   └── validators.py        ✅ Валидация данных
├── bot.py                   ❌ ОБНОВИТЬ (монолит 61887 строк)
├── bot.py.backup            ✅ Резервная копия (удалить после рефакторинга)
└── reminders.db             ✅ База данных SQLite
```

## План создания handlers

### 1. handlers/reminders.py

**Обработчики команд напоминаний (10 функций):**

| Функция | Строка в bot.py.backup | Описание |
|---------|------------------------|----------|
| `cmd_remind()` | 1054 | Создать ежедневное напоминание |
| `cmd_remind_once()` | 1090 | Создать одноразовое напоминание |
| `cmd_edit_reminder()` | 1135 | Редактировать ежедневное напоминание |
| `cmd_edit_once_reminder()` | 1180 | Редактировать одноразовое напоминание |
| `cmd_my_reminders()` | 1246 | Показать все напоминания |
| `cmd_next_reminders()` | 1264 | Показать ближайшие напоминания |
| `cmd_delete_reminder()` | 1335 | Удалить напоминание |
| `cmd_disable_reminder()` | 1373 | Отключить напоминание |
| `cmd_enable_reminder()` | 1405 | Включить напоминание |
| `cmd_clear_reminders()` | 1437 | Очистить все напоминания |

**Обработчики кнопок (2 функции):**
- `handle_my_reminders_button()` - кнопка "Мои напоминания"
- `handle_next_reminders_button()` - кнопка "Ближайшие напоминания"

**Зависимости:**
```python
from datetime import timedelta
from aiogram.filters import CommandObject
from aiogram.types import Message

from database.store import ReminderStore
from utils.validators import validate_reminder_text
from utils.parsers import parse_time, parse_once_datetime, parse_index
from utils.formatters import (
    build_reminders_text,
    build_delete_keyboard,
    format_utc_offset,
    format_once_run_at,
)
from utils.time_utils import next_trigger, utc_now
from config import MAX_REMINDER_TEXT_LENGTH
```

### 2. handlers/services.py

**Обработчики команд сервисов (5 функций):**

| Функция | Строка в bot.py.backup | Описание |
|---------|------------------------|----------|
| `cmd_services()` | 887 | Показать категории сервисов |
| `cmd_service_category()` | ~920 | Показать сервисы в категории |
| `cmd_add_category()` | ~950 | Добавить категорию |
| `cmd_add_service()` | ~980 | Добавить сервис |
| `cmd_nearby_services()` | ~1010 | Запросить геолокацию |

**Обработчики кнопок и геолокации (3 функции):**
- `handle_services_button()` - кнопка "Сервисы"
- `handle_nearby_services_button()` - кнопка "Ближайшие сервисы"
- `handle_location()` - обработка геолокации

**Зависимости:**
```python
from aiogram.filters import CommandObject
from aiogram.types import Message, Location, ReplyKeyboardMarkup, KeyboardButton

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

### 3. handlers/callbacks.py

**Callback обработчики (2 функции):**

| Функция | Строка в bot.py.backup | Описание |
|---------|------------------------|----------|
| `callback_toggle_reminder()` | 1562 | Включить/выключить напоминание |
| `callback_delete_reminder()` | ~1600 | Удалить напоминание |

**Зависимости:**
```python
from aiogram.types import CallbackQuery

from database.store import ReminderStore
from utils.formatters import build_reminders_text, build_delete_keyboard
```

### 4. handlers/backup.py

**Обработчики экспорт/импорт (2 функции):**

| Функция | Строка в bot.py.backup | Описание |
|---------|------------------------|----------|
| `cmd_export_reminders()` | 1450 | Экспорт напоминаний в JSON |
| `cmd_import_reminders()` | ~1490 | Импорт напоминаний из JSON |

**Зависимости:**
```python
import json
from io import BytesIO

from aiogram.types import Message, BufferedInputFile

from database.store import ReminderStore
from config import MAX_IMPORT_REMINDERS
```

### 5. handlers/__init__.py

**Экспорт всех обработчиков:**

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
    handle_location,
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
    "handle_location",
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

## Обновление bot.py

**Новая структура bot.py (~150 строк):**

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
    
    # Команды reminders (10 команд)
    dp.message.register(
        partial(cmd_remind, store=store),
        Command("remind")
    )
    # ... остальные команды напоминаний
    
    # Команды services (5 команд)
    dp.message.register(
        partial(cmd_services, store=store),
        Command("services")
    )
    # ... остальные команды сервисов
    
    # Команды backup (2 команды)
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
    # ... остальные кнопки
    
    # Обработчик геолокации
    dp.message.register(
        partial(handle_location, store=store),
        F.location
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

## Ключевые изменения

### 1. Разделение ответственности

- **handlers/start.py** - базовые команды и информация
- **handlers/timezone.py** - управление часовыми поясами
- **handlers/reminders.py** - управление напоминаниями (основная функциональность)
- **handlers/services.py** - управление сервисами и геолокация
- **handlers/callbacks.py** - обработка inline-кнопок
- **handlers/backup.py** - экспорт/импорт данных
- **handlers/worker.py** - фоновая отправка напоминаний

### 2. Использование functools.partial

Вместо глобальной переменной `STORE` используем `partial()` для передачи `store` в обработчики:

```python
dp.message.register(
    partial(cmd_remind, store=store),
    Command("remind")
)
```

### 3. Контекстный менеджер для БД

```python
with ReminderStore(DB_PATH) as store:
    # Работа с БД
```

### 4. Централизованная регистрация обработчиков

Функция `register_handlers()` регистрирует все обработчики в одном месте.

## Порядок реализации

1. ✅ Создать [`handlers/reminders.py`](../digital_neighbour_bot/handlers/reminders.py)
2. ✅ Создать [`handlers/services.py`](../digital_neighbour_bot/handlers/services.py)
3. ✅ Создать [`handlers/callbacks.py`](../digital_neighbour_bot/handlers/callbacks.py)
4. ✅ Создать [`handlers/backup.py`](../digital_neighbour_bot/handlers/backup.py)
5. ✅ Создать [`handlers/__init__.py`](../digital_neighbour_bot/handlers/__init__.py)
6. ✅ Обновить [`bot.py`](../digital_neighbour_bot/bot.py)
7. ✅ Протестировать локально
8. ✅ Удалить [`bot.py.backup`](../digital_neighbour_bot/bot.py.backup)
9. ✅ Деплой на Railway

## Тестирование

### Локальное тестирование

```bash
cd ../digital_neighbour_bot
python bot.py
```

### Проверка команд

- `/start` - главное меню
- `/help` - справка
- `/remind 19:30 Тест` - создать напоминание
- `/my_reminders` - список напоминаний
- `/services` - категории сервисов
- `/export_reminders` - экспорт
- Кнопки главного меню
- Callback-кнопки в напоминаниях

### Проверка воркера

- Создать напоминание на текущее время + 1 минута
- Дождаться отправки
- Проверить логи

## Деплой на Railway

После успешного тестирования:

```bash
git add .
git commit -m "Завершен рефакторинг: модульная структура handlers"
git push origin main
```

Railway автоматически задеплоит изменения.

## Метрики успеха

- ✅ bot.py сокращен с 61887 до ~150 строк
- ✅ Код разделен на 7 модулей handlers
- ✅ Все команды работают
- ✅ Воркер напоминаний работает
- ✅ Callback-кнопки работают
- ✅ Экспорт/импорт работает
- ✅ Бот успешно деплоится на Railway
