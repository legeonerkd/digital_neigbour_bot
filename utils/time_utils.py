"""Утилиты для работы со временем."""

from datetime import datetime, timedelta, timezone

from models.reminder import Reminder
from utils.parsers import parse_utc_datetime


def utc_now() -> datetime:
    """Получить текущее время в UTC без timezone info.
    
    Returns:
        Текущее время UTC
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def next_trigger(hour: int, minute: int, offset_minutes: int) -> datetime:
    """Вычислить следующее время срабатывания ежедневного напоминания.
    
    Args:
        hour: Час срабатывания
        minute: Минута срабатывания
        offset_minutes: Смещение часового пояса пользователя в минутах
        
    Returns:
        Локальное время следующего срабатывания
    """
    now_utc = utc_now()
    now_local = now_utc + timedelta(minutes=offset_minutes)
    run_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_local <= now_local:
        run_local += timedelta(days=1)
    return run_local


def next_run_local(reminder: Reminder, user_offset: int, now_utc: datetime) -> datetime | None:
    """Вычислить следующее время срабатывания напоминания.
    
    Args:
        reminder: Объект напоминания
        user_offset: Смещение часового пояса пользователя в минутах
        now_utc: Текущее время UTC
        
    Returns:
        Локальное время следующего срабатывания или None если напоминание выключено/просрочено
    """
    if reminder.enabled == 0:
        return None

    if reminder.is_once:
        run_at_utc = parse_utc_datetime(reminder.run_at)
        if not run_at_utc or run_at_utc <= now_utc:
            return None
        return run_at_utc + timedelta(minutes=user_offset)

    now_local = now_utc + timedelta(minutes=user_offset)
    run_local = now_local.replace(
        hour=reminder.hour, minute=reminder.minute, second=0, microsecond=0
    )
    if run_local <= now_local:
        run_local += timedelta(days=1)
    return run_local
