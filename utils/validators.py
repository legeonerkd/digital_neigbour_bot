"""Функции валидации данных."""

from config.settings import (
    MAX_CATEGORY_NAME_LENGTH,
    MAX_REMINDER_TEXT_LENGTH,
    MAX_SERVICE_CONTACT_LENGTH,
    MAX_SERVICE_NOTES_LENGTH,
    MAX_SERVICE_TITLE_LENGTH,
)


def validate_reminder_text(text: str) -> str | None:
    """Валидация текста напоминания.
    
    Args:
        text: Текст напоминания
        
    Returns:
        Сообщение об ошибке или None если валидация прошла успешно
    """
    clean = text.strip()
    if not clean:
        return "Текст напоминания не может быть пустым"
    if len(clean) > MAX_REMINDER_TEXT_LENGTH:
        return f"Текст слишком длинный (максимум {MAX_REMINDER_TEXT_LENGTH} символов)"
    return None


def validate_category_name(name: str) -> str | None:
    """Валидация названия категории.
    
    Args:
        name: Название категории
        
    Returns:
        Сообщение об ошибке или None если валидация прошла успешно
    """
    clean = name.strip()
    if not clean:
        return "Название категории не может быть пустым"
    if len(clean) > MAX_CATEGORY_NAME_LENGTH:
        return f"Название категории слишком длинное (максимум {MAX_CATEGORY_NAME_LENGTH} символов)"
    return None


def validate_service_title(value: str) -> str | None:
    """Валидация названия сервиса.
    
    Args:
        value: Название сервиса
        
    Returns:
        Сообщение об ошибке или None если валидация прошла успешно
    """
    clean = value.strip()
    if not clean:
        return "Название сервиса не может быть пустым"
    if len(clean) > MAX_SERVICE_TITLE_LENGTH:
        return f"Название сервиса слишком длинное (максимум {MAX_SERVICE_TITLE_LENGTH} символов)"
    return None


def validate_service_contact(value: str) -> str | None:
    """Валидация контакта сервиса.
    
    Args:
        value: Контакт сервиса
        
    Returns:
        Сообщение об ошибке или None если валидация прошла успешно
    """
    clean = value.strip()
    if not clean:
        return "Контакт сервиса не может быть пустым"
    if len(clean) > MAX_SERVICE_CONTACT_LENGTH:
        return f"Контакт слишком длинный (максимум {MAX_SERVICE_CONTACT_LENGTH} символов)"
    return None


def validate_service_notes(value: str) -> str | None:
    """Валидация примечания сервиса.
    
    Args:
        value: Примечание сервиса
        
    Returns:
        Сообщение об ошибке или None если валидация прошла успешно
    """
    clean = value.strip()
    if len(clean) > MAX_SERVICE_NOTES_LENGTH:
        return f"Примечание слишком длинное (максимум {MAX_SERVICE_NOTES_LENGTH} символов)"
    return None
