"""Обработчики команд часового пояса."""

from aiogram.filters import CommandObject
from aiogram.types import Message

from database.store import ReminderStore
from utils.formatters import format_utc_offset
from utils.parsers import parse_utc_offset


async def cmd_set_timezone(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /set_timezone."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    if not command.args:
        await message.answer("Использование: /set_timezone +03:00")
        return

    offset = parse_utc_offset(command.args.strip())
    if offset is None:
        await message.answer("Некорректный формат. Пример: /set_timezone +03:00")
        return

    store.set_user_timezone(message.from_user.id, offset)
    await message.answer(f"Часовой пояс сохранен: {format_utc_offset(offset)}")


async def cmd_my_timezone(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /my_timezone."""
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    offset = store.get_user_timezone(message.from_user.id)
    await message.answer(f"Ваш часовой пояс: {format_utc_offset(offset)}")
