"""Функции парсинга данных."""

from datetime import datetime


def parse_time(value: str) -> tuple[int, int] | None:
    """Парсинг времени в формате HH:MM.
    
    Args:
        value: Строка времени
        
    Returns:
        Кортеж (час, минута) или None при ошибке
    """
    try:
        hour_str, minute_str = value.split(":", maxsplit=1)
        hour = int(hour_str)
        minute = int(minute_str)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (ValueError, AttributeError):
        return None
    return None


def parse_index(value: str) -> int | None:
    """Парсинг индекса (положительное целое число).
    
    Args:
        value: Строка с числом
        
    Returns:
        Индекс или None при ошибке
    """
    try:
        index = int(value)
        if index > 0:
            return index
    except (ValueError, TypeError):
        return None
    return None


def parse_once_datetime(date_value: str, time_value: str) -> datetime | None:
    """Парсинг даты и времени для одноразового напоминания.
    
    Args:
        date_value: Дата в формате YYYY-MM-DD
        time_value: Время в формате HH:MM
        
    Returns:
        Объект datetime или None при ошибке
    """
    try:
        return datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def parse_utc_offset(value: str) -> int | None:
    """Парсинг UTC offset в формате +/-HH:MM.
    
    Args:
        value: Строка offset
        
    Returns:
        Offset в минутах или None при ошибке
    """
    if not value:
        return None
    clean = value.strip()
    sign = 1
    if clean[0] == "+":
        clean = clean[1:]
    elif clean[0] == "-":
        clean = clean[1:]
        sign = -1

    if ":" not in clean:
        return None

    parts = clean.split(":", maxsplit=1)
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        return None

    if hours > 14 or minutes > 59:
        return None

    total = sign * (hours * 60 + minutes)
    if total < -12 * 60 or total > 14 * 60:
        return None
    return total


def parse_utc_datetime(value_utc: str | None) -> datetime | None:
    """Парсинг UTC datetime из строки.
    
    Args:
        value_utc: Строка с датой и временем
        
    Returns:
        Объект datetime или None при ошибке
    """
    if not value_utc:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value_utc, fmt)
        except ValueError:
            continue
    return None
