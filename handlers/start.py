"""Обработчики базовых команд."""

from aiogram.types import Message

from data.content import CONTACTS_TEXT, EMERGENCY_TEXT, FAQ_ITEMS
from keyboards.main_menu import MAIN_MENU


async def cmd_start(message: Message) -> None:
    """Обработчик команды /start."""
    await message.answer(
        "Привет! Я Digital Neighbour.\n\n"
        "Помогу с контактами, сервисами и напоминаниями.\n"
        "Выберите раздел в меню ниже.",
        reply_markup=MAIN_MENU,
    )


async def cmd_help(message: Message) -> None:
    """Обработчик команды /help."""
    await message.answer(
        "Справка по командам\n\n"
        "Общее:\n"
        "• /start\n"
        "• /help\n"
        "• /faq\n"
        "• /contacts\n"
        "• /emergency\n\n"
        "Сервисы:\n"
        "• /services\n"
        "• /service_category <название>\n"
        "• /add_category <название>\n"
        "• /add_service категория | название | контакт | примечание\n"
        "• /nearby_services\n\n"
        "Часовой пояс:\n"
        "• /set_timezone +/-HH:MM\n"
        "• /my_timezone\n\n"
        "Напоминания:\n"
        "• /remind HH:MM текст\n"
        "• /remind_once YYYY-MM-DD HH:MM текст\n"
        "• /edit_reminder N HH:MM текст\n"
        "• /edit_once_reminder N YYYY-MM-DD HH:MM текст\n"
        "• /my_reminders\n"
        "• /next_reminders\n"
        "• /disable_reminder N\n"
        "• /enable_reminder N\n"
        "• /delete_reminder N\n"
        "• /clear_reminders\n\n"
        "Резервная копия:\n"
        "• /export_reminders\n"
        "• /import_reminders (ответом на JSON/файл .json)"
    )


async def cmd_contacts(message: Message) -> None:
    """Обработчик команды /contacts."""
    await message.answer(CONTACTS_TEXT)


async def cmd_emergency(message: Message) -> None:
    """Обработчик команды /emergency."""
    await message.answer(EMERGENCY_TEXT)


async def cmd_faq(message: Message) -> None:
    """Обработчик команды /faq."""
    lines = ["❓ FAQ"]
    for question, answer in FAQ_ITEMS.items():
        lines.append(f"\n• {question}\n  {answer}")
    await message.answer("\n".join(lines))


# Обработчики кнопок главного меню
async def handle_faq_button(message: Message) -> None:
    """Обработчик кнопки FAQ."""
    await cmd_faq(message)


async def handle_contacts_button(message: Message) -> None:
    """Обработчик кнопки Контакты."""
    await cmd_contacts(message)


async def handle_emergency_button(message: Message) -> None:
    """Обработчик кнопки Экстренная помощь."""
    await cmd_emergency(message)
