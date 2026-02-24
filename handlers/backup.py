"""Обработчики экспорта и импорта напоминаний."""

import json
import logging
from datetime import datetime
from io import BytesIO

from aiogram.types import Message, BufferedInputFile

from database.store import ReminderStore
from utils.validators import validate_reminder_text
from utils.time_utils import utc_now
from config import MAX_IMPORT_REMINDERS


def export_payload(user_id: int, store: ReminderStore) -> dict:
    """Создать payload для экспорта напоминаний пользователя.
    
    Args:
        user_id: ID пользователя
        store: Хранилище данных
        
    Returns:
        Словарь с данными для экспорта
    """
    user_offset = store.get_user_timezone(user_id)
    reminders = store.list_reminders(user_id)
    payload_reminders: list[dict] = []
    for reminder in reminders:
        payload_reminders.append(
            {
                "enabled": int(reminder.enabled),
                "is_once": int(reminder.is_once),
                "hour": int(reminder.hour),
                "minute": int(reminder.minute),
                "text": reminder.text,
                "run_at": reminder.run_at,
            }
        )
    return {
        "version": 1,
        "exported_at_utc": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
        "utc_offset_minutes": user_offset,
        "reminders": payload_reminders,
    }


def import_payload(user_id: int, payload: dict, store: ReminderStore) -> tuple[bool, str]:
    """Импортировать напоминания из payload.
    
    Args:
        user_id: ID пользователя
        payload: Данные для импорта
        store: Хранилище данных
        
    Returns:
        Кортеж (успех, сообщение)
    """
    if not isinstance(payload, dict):
        return False, "Некорректный JSON: ожидается объект"

    reminders_data = payload.get("reminders")
    if not isinstance(reminders_data, list):
        return False, "Некорректный JSON: поле reminders должно быть массивом"
    if len(reminders_data) > MAX_IMPORT_REMINDERS:
        return False, f"Слишком много напоминаний в импорте (максимум {MAX_IMPORT_REMINDERS})"

    offset = payload.get("utc_offset_minutes", 0)
    if not isinstance(offset, int):
        return False, "Некорректный JSON: utc_offset_minutes должно быть целым числом"
    if offset < -12 * 60 or offset > 14 * 60:
        return False, "Некорректный JSON: utc_offset_minutes вне диапазона UTC-12:00..UTC+14:00"

    parsed_items: list[tuple[int, int, int, int, str, str | None]] = []
    for idx, item in enumerate(reminders_data, start=1):
        if not isinstance(item, dict):
            return False, f"reminders[{idx}] должен быть объектом"

        enabled = int(item.get("enabled", 1))
        if enabled not in (0, 1):
            return False, f"reminders[{idx}].enabled должен быть 0 или 1"

        is_once = int(item.get("is_once", 0))
        if is_once not in (0, 1):
            return False, f"reminders[{idx}].is_once должен быть 0 или 1"

        try:
            hour = int(item.get("hour"))
            minute = int(item.get("minute"))
        except (TypeError, ValueError):
            return False, f"reminders[{idx}] содержит некорректные hour/minute"
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return False, f"reminders[{idx}] содержит некорректные hour/minute"

        text = str(item.get("text", ""))
        text_error = validate_reminder_text(text)
        if text_error:
            return False, f"reminders[{idx}]: {text_error}"

        run_at = item.get("run_at")
        if is_once == 1:
            if not isinstance(run_at, str):
                return False, f"reminders[{idx}].run_at должен быть строкой для one-time напоминания"
            try:
                datetime.strptime(run_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return False, f"reminders[{idx}].run_at должен быть в формате YYYY-MM-DD HH:MM:SS"
        else:
            run_at = None

        parsed_items.append((enabled, is_once, hour, minute, text.strip(), run_at))

    # Очистить существующие напоминания и импортировать новые
    store.clear_user_reminders(user_id)
    store.set_user_timezone(user_id, offset)
    for enabled, is_once, hour, minute, text, run_at in parsed_items:
        if is_once == 1 and run_at:
            run_at_dt = datetime.strptime(run_at, "%Y-%m-%d %H:%M:%S")
            store.add_once_reminder(
                user_id=user_id, run_at_utc=run_at_dt, text=text, enabled=enabled
            )
        else:
            store.add_daily_reminder(
                user_id=user_id, hour=hour, minute=minute, text=text, enabled=enabled
            )

    return True, f"Импорт завершен: {len(parsed_items)} напоминаний"


async def cmd_export_reminders(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /export_reminders - экспорт напоминаний в JSON."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    payload = export_payload(message.from_user.id, store)
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    data = json_text.encode("utf-8")
    filename = f"reminders_backup_{message.from_user.id}_{utc_now().strftime('%Y%m%d_%H%M%S')}.json"
    document = BufferedInputFile(data, filename=filename)

    await message.answer_document(
        document=document,
        caption="Экспорт готов. Для восстановления ответьте на этот файл командой /import_reminders",
    )


async def cmd_import_reminders(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /import_reminders - импорт напоминаний из JSON."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    replied = message.reply_to_message
    if not replied:
        await message.answer("Использование: ответьте командой /import_reminders на JSON-текст или файл .json")
        return

    payload: dict
    if replied.document:
        # Импорт из файла
        if not replied.document.file_name or not replied.document.file_name.lower().endswith(".json"):
            await message.answer("Ожидается файл с расширением .json")
            return
        if replied.document.file_size and replied.document.file_size > 512 * 1024:
            await message.answer("Файл слишком большой (максимум 512 KB)")
            return

        buffer = BytesIO()
        try:
            await message.bot.download(replied.document, destination=buffer)
            raw = buffer.getvalue().decode("utf-8")
            payload = json.loads(raw)
        except UnicodeDecodeError:
            await message.answer("Файл должен быть в кодировке UTF-8")
            return
        except json.JSONDecodeError:
            await message.answer("Не удалось разобрать JSON из файла")
            return
        except Exception:
            logging.exception("Failed to import reminders from file")
            await message.answer("Не удалось прочитать файл. Попробуйте снова")
            return
    else:
        # Импорт из текста сообщения
        source_text = replied.text
        if not source_text:
            await message.answer("В ответе не найден JSON или файл .json")
            return

        start = source_text.find("{")
        end = source_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            await message.answer("В сообщении не найден корректный JSON")
            return

        try:
            payload = json.loads(source_text[start : end + 1])
        except json.JSONDecodeError:
            await message.answer("Не удалось разобрать JSON")
            return

    # Импортировать данные
    ok, result = import_payload(message.from_user.id, payload, store)
    await message.answer(result)
    
    # Если импорт успешен, показать список напоминаний
    if ok:
        # Импортируем функцию здесь, чтобы избежать циклических импортов
        from .reminders import cmd_my_reminders
        await cmd_my_reminders(message, store)
