"""Обработчики callback-запросов от inline-кнопок."""

import logging
from urllib import parse as urlparse

from aiogram.types import CallbackQuery

from database.store import ReminderStore
from utils.formatters import build_reminders_text, build_delete_keyboard, format_services
from utils.pharmacy_scraper import fetch_live_duty_pharmacies
from config import DUTY_PHARMACY_CATEGORY


async def callback_toggle_reminder(callback: CallbackQuery, store: ReminderStore) -> None:
    """Обработчик callback для включения/выключения напоминания.
    
    Формат callback.data: "toggle:reminder_id:target_state"
    где target_state: 0 (выключить) или 1 (включить)
    """
    if not callback.from_user or not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":", maxsplit=2)
    if len(parts) != 3:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    try:
        reminder_id = int(parts[1])
        target = int(parts[2])
    except ValueError:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    if target not in (0, 1):
        await callback.answer("Некорректное состояние", show_alert=True)
        return

    user_id = callback.from_user.id
    updated = store.set_reminder_enabled(user_id=user_id, reminder_id=reminder_id, enabled=target)
    if not updated:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return

    user_offset = store.get_user_timezone(user_id)
    reminders = store.list_reminders(user_id)

    if callback.message:
        if reminders:
            await callback.message.edit_text(
                build_reminders_text(reminders, user_offset),
                reply_markup=build_delete_keyboard(reminders),
            )
        else:
            await callback.message.edit_text("У вас пока нет напоминаний")

    await callback.answer("Обновлено")


async def callback_delete_reminder(callback: CallbackQuery, store: ReminderStore) -> None:
    """Обработчик callback для удаления напоминания.
    
    Формат callback.data: "delete:reminder_id"
    """
    if not callback.from_user or not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":", maxsplit=1)
    if len(parts) != 2:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    try:
        reminder_id = int(parts[1])
    except ValueError:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    user_id = callback.from_user.id
    deleted = store.delete_reminder(user_id=user_id, reminder_id=reminder_id)
    if not deleted:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return

    user_offset = store.get_user_timezone(user_id)
    reminders = store.list_reminders(user_id)

    if callback.message:
        if reminders:
            await callback.message.edit_text(
                build_reminders_text(reminders, user_offset),
                reply_markup=build_delete_keyboard(reminders),
            )
        else:
            await callback.message.edit_text("У вас пока нет напоминаний")

    await callback.answer("Удалено")


async def callback_service_category(callback: CallbackQuery, store: ReminderStore) -> None:
    """Обработчик callback для показа сервисов в категории.
    
    Формат callback.data: "category:category_id"
    """
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split(":", maxsplit=1)
    if len(parts) != 2:
        await callback.answer("Некорректный запрос", show_alert=True)
        return

    try:
        category_id = int(parts[1])
    except ValueError:
        await callback.answer("Некорректная категория", show_alert=True)
        return

    category_name = store.get_category_name(category_id)
    if not category_name:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    # Специальная обработка для дежурных аптек с live-парсингом
    if category_name.strip().lower() == DUTY_PHARMACY_CATEGORY.lower():
        try:
            live_items = fetch_live_duty_pharmacies()
        except Exception:
            logging.exception("Failed to fetch duty pharmacies")
            live_items = []

        if callback.message:
            if live_items:
                lines = [f"🧪 {DUTY_PHARMACY_CATEGORY} (актуально на сейчас)"]
                for idx, (name, phone, address) in enumerate(live_items, start=1):
                    query = f"{name}, {address}" if address else f"{name}, Limassol, Cyprus"
                    maps_url = "https://www.google.com/maps/search/?api=1&query=" + urlparse.quote(query)
                    lines.append(f"{idx}. {name}")
                    lines.append(f"   📞 Контакт: {phone}")
                    if address:
                        lines.append(f"   📍 Адрес: {address}")
                    lines.append(f"   🗺 Google Maps: {maps_url}")
                    lines.append("")
                lines.append("Источник: cyprus.ondutypharmacy.com")
                await callback.message.answer("\n".join(lines))
            else:
                # Если live-источник недоступен, показываем резервный список
                services = store.list_services_by_category(category_id)
                if services:
                    await callback.message.answer(
                        "Live-источник временно недоступен. Показан резервный список из базы.\n\n"
                        + format_services(category_name, services)
                    )
                else:
                    await callback.message.answer(
                        "Не удалось получить live-список дежурных аптек, и резервный список пуст."
                    )
        await callback.answer()
        return

    # Обычные категории
    services = store.list_services_by_category(category_id)
    if callback.message:
        await callback.message.answer(format_services(category_name, services))
    await callback.answer()
