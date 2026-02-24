"""Обработчики команд напоминаний."""

from datetime import datetime, timedelta

from aiogram.filters import CommandObject
from aiogram.types import Message

from database.store import ReminderStore
from models.reminder import Reminder
from utils.validators import validate_reminder_text
from utils.parsers import parse_time, parse_once_datetime, parse_index
from utils.formatters import (
    build_reminders_text,
    build_delete_keyboard,
    format_utc_offset,
    format_once_run_at,
)
from utils.time_utils import next_trigger, next_run_local, utc_now
from config import MAX_REMINDER_TEXT_LENGTH


async def cmd_remind(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /remind - создать ежедневное напоминание."""
    if not command.args:
        await message.answer("Использование: /remind HH:MM текст")
        return

    parts = command.args.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Нужны время и текст. Пример: /remind 19:30 Вынести мусор")
        return

    parsed = parse_time(parts[0])
    if not parsed:
        await message.answer("Некорректное время. Используйте формат HH:MM")
        return

    hour, minute = parsed
    text = parts[1].strip()
    text_error = validate_reminder_text(text)
    if text_error:
        await message.answer(text_error)
        return

    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user_id = message.from_user.id
    store.add_daily_reminder(user_id=user_id, hour=hour, minute=minute, text=text)

    user_offset = store.get_user_timezone(user_id)
    trigger_at = next_trigger(hour, minute, user_offset).strftime("%H:%M")
    await message.answer(
        f"Добавил ежедневное напоминание на {trigger_at} ({format_utc_offset(user_offset)}): {text}"
    )


async def cmd_remind_once(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /remind_once - создать одноразовое напоминание."""
    if not command.args:
        await message.answer(
            "Использование: /remind_once YYYY-MM-DD HH:MM текст"
        )
        return

    parts = command.args.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Нужны дата, время и текст. Пример: /remind_once 2026-02-20 19:30 Встреча"
        )
        return

    run_at_local = parse_once_datetime(parts[0], parts[1])
    if not run_at_local:
        await message.answer("Некорректные дата или время. Формат: YYYY-MM-DD HH:MM")
        return

    text = parts[2].strip()
    text_error = validate_reminder_text(text)
    if text_error:
        await message.answer(text_error)
        return

    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user_id = message.from_user.id
    user_offset = store.get_user_timezone(user_id)
    run_at_utc = run_at_local - timedelta(minutes=user_offset)

    if run_at_utc <= utc_now():
        await message.answer(
            f"Укажите будущее время. Сейчас: {(utc_now() + timedelta(minutes=user_offset)).strftime('%Y-%m-%d %H:%M')}"
        )
        return

    store.add_once_reminder(user_id=user_id, run_at_utc=run_at_utc, text=text)
    await message.answer(
        f"Добавил одноразовое напоминание на {run_at_local.strftime('%Y-%m-%d %H:%M')} ({format_utc_offset(user_offset)}): {text}"
    )


async def cmd_edit_reminder(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /edit_reminder - редактировать ежедневное напоминание."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return
    if not command.args:
        await message.answer("Использование: /edit_reminder N HH:MM текст")
        return

    parts = command.args.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Пример: /edit_reminder 2 08:30 Утренняя прогулка")
        return

    index = parse_index(parts[0])
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    parsed = parse_time(parts[1])
    if not parsed:
        await message.answer("Некорректное время. Используйте формат HH:MM")
        return

    text = parts[2].strip()
    text_error = validate_reminder_text(text)
    if text_error:
        await message.answer(text_error)
        return

    user_id = message.from_user.id
    reminders = store.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return
    if index > len(reminders):
        await message.answer(f"У вас только {len(reminders)} напоминаний")
        return

    reminder = reminders[index - 1]
    if reminder.is_once:
        await message.answer("Это одноразовое напоминание. Используйте /edit_once_reminder")
        return

    hour, minute = parsed
    updated = store.update_daily_reminder(user_id, reminder.id, hour, minute, text)
    if not updated:
        await message.answer("Не удалось обновить напоминание")
        return

    await message.answer(f"Обновил напоминание {index}: {hour:02d}:{minute:02d} - {text}")


async def cmd_edit_once_reminder(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /edit_once_reminder - редактировать одноразовое напоминание."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return
    if not command.args:
        await message.answer("Использование: /edit_once_reminder N YYYY-MM-DD HH:MM текст")
        return

    parts = command.args.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Пример: /edit_once_reminder 3 2026-03-01 14:15 Поход в банк")
        return

    index = parse_index(parts[0])
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    run_at_local = parse_once_datetime(parts[1], parts[2])
    if not run_at_local:
        await message.answer("Некорректные дата или время. Формат: YYYY-MM-DD HH:MM")
        return

    text = parts[3].strip()
    text_error = validate_reminder_text(text)
    if text_error:
        await message.answer(text_error)
        return

    user_id = message.from_user.id
    user_offset = store.get_user_timezone(user_id)
    run_at_utc = run_at_local - timedelta(minutes=user_offset)
    if run_at_utc <= utc_now():
        await message.answer("Укажите будущее время для одноразового напоминания")
        return

    reminders = store.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return
    if index > len(reminders):
        await message.answer(f"У вас только {len(reminders)} напоминаний")
        return

    reminder = reminders[index - 1]
    if not reminder.is_once:
        await message.answer("Это ежедневное напоминание. Используйте /edit_reminder")
        return

    updated = store.update_once_reminder(user_id, reminder.id, run_at_utc, text)
    if not updated:
        await message.answer("Не удалось обновить напоминание")
        return

    await message.answer(
        f"Обновил one-time {index}: {run_at_local.strftime('%Y-%m-%d %H:%M')} - {text}"
    )


async def cmd_my_reminders(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /my_reminders - показать все напоминания."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user_id = message.from_user.id
    user_offset = store.get_user_timezone(user_id)
    user_reminders = store.list_reminders(user_id)
    if not user_reminders:
        await message.answer("У вас пока нет напоминаний")
        return

    await message.answer(
        build_reminders_text(user_reminders, user_offset),
        reply_markup=build_delete_keyboard(user_reminders),
    )


async def cmd_next_reminders(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /next_reminders - показать ближайшие напоминания."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user_id = message.from_user.id
    user_offset = store.get_user_timezone(user_id)
    reminders = store.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return

    now_utc = utc_now()
    upcoming: list[tuple[datetime, Reminder]] = []
    for reminder in reminders:
        run_local = next_run_local(reminder, user_offset, now_utc)
        if run_local:
            upcoming.append((run_local, reminder))

    if not upcoming:
        await message.answer("У вас нет активных ближайших напоминаний")
        return

    upcoming.sort(key=lambda x: x[0])
    lines = [f"⏰ Ближайшие напоминания ({format_utc_offset(user_offset)})"]
    for idx, (run_local, reminder) in enumerate(upcoming[:10], start=1):
        kind = "one-time" if reminder.is_once else "daily"
        lines.append(
            f"{idx}. [{kind}] {run_local.strftime('%Y-%m-%d %H:%M')} - {reminder.text}"
        )
        lines.append("")
    if len(upcoming) > 10:
        lines.append(f"... и еще {len(upcoming) - 10}")

    await message.answer("\n".join(lines))


async def cmd_delete_reminder(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /delete_reminder - удалить напоминание."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    if not command.args:
        await message.answer("Использование: /delete_reminder N. Пример: /delete_reminder 2")
        return

    index = parse_index(command.args.strip())
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    user_id = message.from_user.id
    user_offset = store.get_user_timezone(user_id)
    user_reminders = store.list_reminders(user_id)
    if not user_reminders:
        await message.answer("У вас пока нет напоминаний")
        return

    if index > len(user_reminders):
        await message.answer(f"У вас только {len(user_reminders)} напоминаний")
        return

    reminder = user_reminders[index - 1]
    deleted = store.delete_reminder(user_id=user_id, reminder_id=reminder.id)
    if not deleted:
        await message.answer("Не удалось удалить напоминание. Попробуйте снова")
        return

    if reminder.is_once:
        schedule = format_once_run_at(reminder.run_at, user_offset)
    else:
        schedule = f"{reminder.hour:02d}:{reminder.minute:02d}"
    await message.answer(f"Удалил напоминание {index}: {schedule} - {reminder.text}")


async def cmd_disable_reminder(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /disable_reminder - отключить напоминание."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    if not command.args:
        await message.answer("Использование: /disable_reminder N. Пример: /disable_reminder 2")
        return

    index = parse_index(command.args.strip())
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    user_id = message.from_user.id
    reminders = store.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return
    if index > len(reminders):
        await message.answer(f"У вас только {len(reminders)} напоминаний")
        return

    reminder = reminders[index - 1]
    if reminder.enabled == 0:
        await message.answer(f"Напоминание {index} уже выключено")
        return

    store.set_reminder_enabled(user_id=user_id, reminder_id=reminder.id, enabled=0)
    await message.answer(f"Выключил напоминание {index}")


async def cmd_enable_reminder(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /enable_reminder - включить напоминание."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    if not command.args:
        await message.answer("Использование: /enable_reminder N. Пример: /enable_reminder 2")
        return

    index = parse_index(command.args.strip())
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    user_id = message.from_user.id
    reminders = store.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return
    if index > len(reminders):
        await message.answer(f"У вас только {len(reminders)} напоминаний")
        return

    reminder = reminders[index - 1]
    if reminder.enabled == 1:
        await message.answer(f"Напоминание {index} уже включено")
        return

    store.set_reminder_enabled(user_id=user_id, reminder_id=reminder.id, enabled=1)
    await message.answer(f"Включил напоминание {index}")


async def cmd_clear_reminders(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /clear_reminders - очистить все напоминания."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    deleted = store.clear_user_reminders(message.from_user.id)
    if deleted == 0:
        await message.answer("У вас не было напоминаний")
        return

    await message.answer("Все ваши напоминания удалены")


# Обработчики кнопок главного меню
async def handle_my_reminders_button(message: Message, store: ReminderStore) -> None:
    """Обработчик кнопки 'Мои напоминания'."""
    await cmd_my_reminders(message, store)


async def handle_next_reminders_button(message: Message, store: ReminderStore) -> None:
    """Обработчик кнопки 'Ближайшие напоминания'."""
    await cmd_next_reminders(message, store)
