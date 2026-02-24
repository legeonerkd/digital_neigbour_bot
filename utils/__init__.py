"""Утилиты проекта."""

from .formatters import (
    build_delete_keyboard,
    build_reminders_text,
    build_service_categories_keyboard,
    format_once_run_at,
    format_services,
    format_utc_offset,
    reminder_line,
    service_maps_link,
)
from .parsers import (
    parse_index,
    parse_once_datetime,
    parse_time,
    parse_utc_datetime,
    parse_utc_offset,
)
from .pharmacy_scraper import extract_rating, fetch_live_duty_pharmacies
from .time_utils import next_run_local, next_trigger, utc_now
from .validators import (
    validate_category_name,
    validate_reminder_text,
    validate_service_contact,
    validate_service_notes,
    validate_service_title,
)

__all__ = [
    # formatters
    "build_delete_keyboard",
    "build_reminders_text",
    "build_service_categories_keyboard",
    "format_once_run_at",
    "format_services",
    "format_utc_offset",
    "reminder_line",
    "service_maps_link",
    # parsers
    "parse_index",
    "parse_once_datetime",
    "parse_time",
    "parse_utc_datetime",
    "parse_utc_offset",
    # pharmacy_scraper
    "extract_rating",
    "fetch_live_duty_pharmacies",
    # time_utils
    "next_run_local",
    "next_trigger",
    "utc_now",
    # validators
    "validate_category_name",
    "validate_reminder_text",
    "validate_service_contact",
    "validate_service_notes",
    "validate_service_title",
]
