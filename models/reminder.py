"""Модели данных для напоминаний."""

from dataclasses import dataclass


@dataclass
class Reminder:
    """Модель напоминания."""
    
    id: int
    user_id: int
    hour: int
    minute: int
    text: str
    enabled: int
    is_once: int
    run_at: str | None
    sent_at: str | None
    last_sent_on: str | None
