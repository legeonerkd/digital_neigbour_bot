# Руководство по рефакторингу

## Выполнено

✅ Создана структура модулей:
- `models/` - модели данных (Reminder)
- `config/` - настройки и константы
- `database/` - работа с БД (ReminderStore)
- `utils/` - утилиты (validators, parsers, formatters, time_utils, pharmacy_scraper)
- `handlers/` - обработчики команд (start, timezone, worker)

## Осталось сделать

### 1. Создать недостающие handlers

Необходимо создать следующие файлы в папке `handlers/`:

#### `handlers/reminders.py`
Перенести из `bot.py` функции:
- `cmd_remind`
- `cmd_remind_once`
- `cmd_edit_reminder`
- `cmd_edit_once_reminder`
- `cmd_my_reminders`
- `cmd_next_reminders`
- `cmd_delete_reminder`
- `cmd_disable_reminder`
- `cmd_enable_reminder`
- `cmd_clear_reminders`
- `handle_my_reminders_button`
- `handle_next_reminders_button`

#### `handlers/services.py`
Перенести из `bot.py` функции:
- `cmd_services`
- `cmd_service_category`
- `cmd_add_category`
- `cmd_add_service`
- `cmd_nearby_services`
- `handle_services_button`
- `handle_nearby_services_button`

#### `handlers/callbacks.py`
Перенести из `bot.py` функции:
- `callback_delete_reminder`
- `callback_toggle_reminder`
- `callback_service_category`

#### `handlers/backup.py`
Перенести из `bot.py` функции:
- `cmd_export_reminders`
- `cmd_import_reminders`
- `export_payload`
- `import_payload`

### 2. Создать handlers/__init__.py

```python
"""Обработчики команд бота."""

from .backup import cmd_export_reminders, cmd_import_reminders
from .callbacks import (
    callback_delete_reminder,
    callback_service_category,
    callback_toggle_reminder,
)
from .reminders import (
    cmd_clear_reminders,
    cmd_delete_reminder,
    cmd_disable_reminder,
    cmd_edit_once_reminder,
    cmd_edit_reminder,
    cmd_enable_reminder,
    cmd_my_reminders,
    cmd_next_reminders,
    cmd_remind,
    cmd_remind_once,
    handle_my_reminders_button,
    handle_next_reminders_button,
)
from .services import (
    cmd_add_category,
    cmd_add_service,
    cmd_nearby_services,
    cmd_service_category,
    cmd_services,
    handle_nearby_services_button,
    handle_services_button,
)
from .start import (
    cmd_contacts,
    cmd_emergency,
    cmd_faq,
    cmd_help,
    cmd_start,
    handle_contacts_button,
    handle_emergency_button,
    handle_faq_button,
)
from .timezone import cmd_my_timezone, cmd_set_timezone
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
    "callback_delete_reminder",
    "callback_toggle_reminder",
    "callback_service_category",
    # backup
    "cmd_export_reminders",
    "cmd_import_reminders",
    # worker
    "reminder_worker",
]
```

### 3. Обновить bot.py

Заменить старый `bot.py` на новую версию с импортами из модулей.

### 4. Важные замечания

- Все обработчики должны принимать `store: ReminderStore` как параметр
- В `bot.py` нужно создать экземпляр `STORE = ReminderStore(DB_PATH)` и передавать его в обработчики
- Использовать `functools.partial` или middleware для передачи store в обработчики

### 5. Пример структуры нового bot.py

```python
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
from handlers.worker import reminder_worker


async def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не найден. Создайте .env из .env.example")

    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=token)
    dp = Dispatcher()
    store = ReminderStore(DB_PATH)

    # Регистрация обработчиков с передачей store
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_contacts, Command("contacts"))
    dp.message.register(partial(cmd_services, store=store), Command("services"))
    # ... и так далее для всех команд

    # Запуск воркера и polling
    worker = asyncio.create_task(reminder_worker(bot, store))
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        store.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## Преимущества новой структуры

1. **Модульность**: Код разбит на логические модули
2. **Переиспользование**: Утилиты можно использовать в разных частях проекта
3. **Тестируемость**: Каждый модуль можно тестировать отдельно
4. **Читаемость**: Легче найти нужный код
5. **Масштабируемость**: Проще добавлять новые функции
