"""Настройки и константы приложения."""

from pathlib import Path

# Лимиты
MAX_REMINDER_TEXT_LENGTH = 280
MAX_IMPORT_REMINDERS = 200
MAX_CATEGORY_NAME_LENGTH = 60
MAX_SERVICE_TITLE_LENGTH = 120
MAX_SERVICE_CONTACT_LENGTH = 160
MAX_SERVICE_NOTES_LENGTH = 240

# Категории сервисов по умолчанию
DEFAULT_SERVICE_CATEGORIES = [
    "Дежурная аптека",
    "Электрик",
    "Сантехник",
    "Автосервис",
]

# Специальная категория для live-парсинга
DUTY_PHARMACY_CATEGORY = "Дежурная аптека"

# Путь к базе данных
DB_PATH = Path(__file__).resolve().parent.parent / "reminders.db"
