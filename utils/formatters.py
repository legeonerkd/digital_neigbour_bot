"""Функции форматирования данных для отображения."""

from datetime import datetime, timedelta
from typing import List
from urllib import parse as urlparse

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.reminder import Reminder


def format_utc_offset(offset_minutes: int) -> str:
    """Форматировать UTC offset в строку.
    
    Args:
        offset_minutes: Смещение в минутах
        
    Returns:
        Строка вида UTC+03:00
    """
    sign = "+" if offset_minutes >= 0 else "-"
    abs_value = abs(offset_minutes)
    hours = abs_value // 60
    minutes = abs_value % 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def format_once_run_at(value_utc: str | None, offset_minutes: int) -> str:
    """Форматировать время запуска одноразового напоминания.
    
    Args:
        value_utc: Время в UTC
        offset_minutes: Смещение часового пояса
        
    Returns:
        Отформатированная строка времени
    """
    if not value_utc:
        return "неизвестно"
    parsed: datetime | None = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            parsed = datetime.strptime(value_utc, fmt)
            break
        except ValueError:
            continue
    if not parsed:
        return value_utc
    local_dt = parsed + timedelta(minutes=offset_minutes)
    return local_dt.strftime("%Y-%m-%d %H:%M")


def reminder_line(reminder: Reminder, index: int, user_offset: int) -> str:
    """Форматировать строку напоминания для списка.
    
    Args:
        reminder: Объект напоминания
        index: Номер в списке
        user_offset: Смещение часового пояса пользователя
        
    Returns:
        Отформатированная строка
    """
    state = "[off] " if reminder.enabled == 0 else ""
    if reminder.is_once:
        when = format_once_run_at(reminder.run_at, user_offset)
        return f"{index}. {state}[one-time] {when} - {reminder.text}"
    return f"{index}. {state}[daily] {reminder.hour:02d}:{reminder.minute:02d} - {reminder.text}"


def build_reminders_text(reminders: List[Reminder], user_offset: int) -> str:
    """Построить текст списка напоминаний.
    
    Args:
        reminders: Список напоминаний
        user_offset: Смещение часового пояса пользователя
        
    Returns:
        Отформатированный текст
    """
    lines = [f"⏰ Ваши напоминания ({format_utc_offset(user_offset)})"]
    for idx, reminder in enumerate(reminders, start=1):
        lines.append(reminder_line(reminder, idx, user_offset))
        lines.append("")
    return "\n".join(lines)


def build_delete_keyboard(reminders: List[Reminder]) -> InlineKeyboardMarkup:
    """Построить клавиатуру для управления напоминаниями.
    
    Args:
        reminders: Список напоминаний
        
    Returns:
        Inline клавиатура
    """
    rows = []
    for idx, reminder in enumerate(reminders, start=1):
        toggle_text = f"Выключить {idx}" if reminder.enabled else f"Включить {idx}"
        toggle_target = 0 if reminder.enabled else 1
        rows.append(
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=f"togrem:{reminder.id}:{toggle_target}",
                ),
                InlineKeyboardButton(
                    text=f"Удалить {idx}",
                    callback_data=f"delrem:{reminder.id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_service_categories_keyboard(categories: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Построить клавиатуру категорий сервисов.
    
    Args:
        categories: Список кортежей (id, название)
        
    Returns:
        Inline клавиатура
    """
    rows = []
    for category_id, name in categories:
        rows.append(
            [InlineKeyboardButton(text=name, callback_data=f"category:{category_id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_services(category_name: str, services: list[tuple[int, str, str, str | None]]) -> str:
    """Форматировать список сервисов для отображения.
    
    Args:
        category_name: Название категории
        services: Список сервисов (id, название, контакт, примечания)
        
    Returns:
        Отформатированный текст
    """
    def extract_address(notes: str | None) -> str | None:
        if not notes:
            return None
        parts = [p.strip() for p in notes.split("|")]
        # Expected format: Google rating: X.X | <address> | Source: Google Maps
        if len(parts) >= 2 and parts[1] and not parts[1].lower().startswith("source:"):
            return parts[1]
        return None

    def maps_link(title: str, address: str | None) -> str:
        query = f"{title}, {address}" if address else f"{title}, Limassol, Cyprus"
        return "https://www.google.com/maps/search/?api=1&query=" + urlparse.quote(query)

    lines = [f"🛠 Категория: {category_name}"]
    if not services:
        lines.append("Пока пусто. Добавьте запись через /add_service")
        lines.append("Формат: /add_service категория | название | контакт | примечание")
        return "\n".join(lines)

    for idx, (_, title, contact, notes) in enumerate(services, start=1):
        address = extract_address(notes)
        lines.append(f"{idx}. {title}")
        lines.append(f"   📞 Контакт: {contact}")
        lines.append(f"   🗺 Google Maps: {maps_link(title, address)}")
        if notes:
            lines.append(f"   ℹ {notes}")
        lines.append("")
    return "\n".join(lines)


def service_maps_link(title: str, notes: str | None) -> str:
    """Создать ссылку на Google Maps для сервиса.
    
    Args:
        title: Название сервиса
        notes: Примечания (могут содержать адрес)
        
    Returns:
        URL для Google Maps
    """
    address: str | None = None
    if notes:
        parts = [p.strip() for p in notes.split("|")]
        if len(parts) >= 2 and parts[1] and not parts[1].lower().startswith("source:"):
            address = parts[1]
    query = f"{title}, {address}" if address else f"{title}, Limassol, Cyprus"
    return "https://www.google.com/maps/search/?api=1&query=" + urlparse.quote(query)
