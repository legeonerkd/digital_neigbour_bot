"""Обработчики команд сервисов и геолокации."""

import logging
from urllib import parse as urlparse

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
    service_maps_link,
)
from utils.pharmacy_scraper import fetch_live_duty_pharmacies, extract_rating
from config import DUTY_PHARMACY_CATEGORY


async def cmd_services(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /services - показать категории сервисов."""
    categories = store.list_service_categories()
    if not categories:
        await message.answer("Категории сервисов пока не настроены")
        return

    names = [name for _, name in categories]
    await message.answer(
        "🛠 Категории сервисов\n\n"
        + "\n".join(f"{idx}. {name}" for idx, name in enumerate(names, start=1))
        + "\n\nОткройте категорию кнопкой ниже или командой:\n"
        "/service_category <название>",
        reply_markup=build_service_categories_keyboard(categories),
    )


async def cmd_service_category(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /service_category - показать сервисы в категории."""
    if not command.args:
        await message.answer("Использование: /service_category <название>")
        return

    category_name = command.args.strip()
    category_id = store.get_category_id(category_name)
    if not category_id:
        await message.answer("Категория не найдена. Используйте /services для списка")
        return

    # Специальная обработка для дежурных аптек с live-парсингом
    if category_name.strip().lower() == DUTY_PHARMACY_CATEGORY.lower():
        try:
            live_items = fetch_live_duty_pharmacies()
        except Exception:
            logging.exception("Failed to fetch duty pharmacies")
            live_items = []

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
            await message.answer("\n".join(lines))
            return
        else:
            # Если live-источник недоступен, показываем резервный список
            services = store.list_services_by_category(category_id)
            if services:
                await message.answer(
                    "Live-источник временно недоступен. Показан резервный список из базы.\n\n"
                    + format_services(category_name, services)
                )
                return

    # Обычные категории
    services = store.list_services_by_category(category_id)
    await message.answer(format_services(category_name, services))


async def cmd_add_category(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /add_category - добавить категорию сервисов."""
    if not command.args:
        await message.answer("Использование: /add_category <название>")
        return

    category_name = command.args.strip()
    error = validate_category_name(category_name)
    if error:
        await message.answer(error)
        return

    created = store.add_service_category(category_name)
    if created:
        await message.answer(f"Категория добавлена: {category_name}")
    else:
        await message.answer(f"Категория уже существует: {category_name}")


async def cmd_add_service(message: Message, command: CommandObject, store: ReminderStore) -> None:
    """Обработчик команды /add_service - добавить сервис."""
    if not command.args:
        await message.answer(
            "Использование: /add_service категория | название | контакт | примечание"
        )
        return

    parts = [p.strip() for p in command.args.split("|")]
    if len(parts) < 3:
        await message.answer(
            "Нужно минимум 3 поля: категория | название | контакт\n"
            "Пример: /add_service Электрик | Alex Electric | +357 99 123456 | аварийный выезд"
        )
        return

    category_name = parts[0]
    title = parts[1]
    contact = parts[2]
    notes = parts[3] if len(parts) > 3 else None

    # Валидация всех полей
    category_error = validate_category_name(category_name)
    if category_error:
        await message.answer(category_error)
        return
    title_error = validate_service_title(title)
    if title_error:
        await message.answer(title_error)
        return
    contact_error = validate_service_contact(contact)
    if contact_error:
        await message.answer(contact_error)
        return
    if notes:
        notes_error = validate_service_notes(notes)
        if notes_error:
            await message.answer(notes_error)
            return

    # Получить или создать категорию
    category_id = store.get_category_id(category_name)
    if not category_id:
        store.add_service_category(category_name)
        category_id = store.get_category_id(category_name)
    if not category_id:
        await message.answer("Не удалось создать/найти категорию")
        return

    # Добавить сервис
    store.add_service(category_id=category_id, title=title.strip(), contact=contact.strip(), notes=notes)
    await message.answer(f"Сервис добавлен в категорию '{category_name}': {title}")


async def cmd_nearby_services(message: Message, store: ReminderStore) -> None:
    """Обработчик команды /nearby_services - показать ближайшие сервисы."""
    categories = store.list_service_categories()
    if not categories:
        await message.answer("Категории сервисов пока не настроены")
        return

    # Собрать все сервисы с рейтингами
    collected: list[tuple[float, str, str, str, str | None]] = []
    for _, category_name in categories:
        services = store.list_services_by_category(store.get_category_id(category_name) or 0)
        for _, title, contact, notes in services:
            rating = extract_rating(notes)
            if rating is None:
                rating = 0.0
            collected.append((rating, category_name, title, contact, notes))

    if not collected:
        await message.answer("Сервисы пока не заполнены")
        return

    # Сортировать по рейтингу
    collected.sort(key=lambda x: x[0], reverse=True)
    lines = ["📍 Ближайшие сервисы (Лимассол)"]
    for idx, (rating, category, title, contact, notes) in enumerate(collected[:12], start=1):
        lines.append(f"{idx}. [{category}] {title}")
        if rating > 0:
            lines.append(f"   ⭐ Рейтинг: {rating:.1f}")
        lines.append(f"   📞 Контакт: {contact}")
        lines.append(f"   🗺 Google Maps: {service_maps_link(title, notes)}")
        lines.append("")
    if len(collected) > 12:
        lines.append(f"... и еще {len(collected) - 12}")

    await message.answer("\n".join(lines))


async def handle_location(message: Message, store: ReminderStore) -> None:
    """Обработчик получения геолокации от пользователя."""
    if not message.location:
        return
    
    lat = message.location.latitude
    lon = message.location.longitude
    
    # TODO: Реализовать поиск ближайших сервисов по координатам
    # Пока показываем все сервисы с сортировкой по рейтингу
    await message.answer(
        f"Получена геолокация: {lat:.6f}, {lon:.6f}\n\n"
        "Функция поиска ближайших сервисов по геолокации в разработке.\n"
        "Показываю все доступные сервисы:"
    )
    
    # Показать ближайшие сервисы (пока без учета геолокации)
    await cmd_nearby_services(message, store)


# Обработчики кнопок главного меню
async def handle_services_button(message: Message, store: ReminderStore) -> None:
    """Обработчик кнопки 'Сервисы'."""
    await cmd_services(message, store)


async def handle_nearby_services_button(message: Message, store: ReminderStore) -> None:
    """Обработчик кнопки 'Ближайшие сервисы'."""
    await cmd_nearby_services(message, store)
