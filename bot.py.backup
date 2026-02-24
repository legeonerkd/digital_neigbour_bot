import asyncio
import json
import logging
import os
import sqlite3
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List
from urllib import request as urlrequest
from urllib import parse as urlparse
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

from data.content import CONTACTS_TEXT, EMERGENCY_TEXT, FAQ_ITEMS
from keyboards.main_menu import MAIN_MENU


@dataclass
class Reminder:
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


class ReminderStore:
    def __init__(self, db_path: Path) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                text TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                is_once INTEGER NOT NULL DEFAULT 0,
                run_at TEXT,
                sent_at TEXT,
                last_sent_on TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                utc_offset_minutes INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                contact TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(category_id) REFERENCES service_categories(id) ON DELETE CASCADE
            )
            """
        )

        columns = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(reminders)").fetchall()
        }
        if "is_once" not in columns:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN is_once INTEGER NOT NULL DEFAULT 0")
        if "enabled" not in columns:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1")
        if "run_at" not in columns:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN run_at TEXT")
        if "sent_at" not in columns:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN sent_at TEXT")
        if "last_sent_on" not in columns:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN last_sent_on TEXT")

        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(hour, minute)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reminders_enabled ON reminders(enabled)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reminders_once_due ON reminders(is_once, run_at, sent_at)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_services_category ON services(category_id)"
        )
        for category_name in DEFAULT_SERVICE_CATEGORIES:
            self.conn.execute(
                "INSERT OR IGNORE INTO service_categories(name) VALUES (?)",
                (category_name,),
            )
        self.conn.commit()

    def set_user_timezone(self, user_id: int, utc_offset_minutes: int) -> None:
        self.conn.execute(
            """
            INSERT INTO user_settings(user_id, utc_offset_minutes)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                utc_offset_minutes = excluded.utc_offset_minutes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, utc_offset_minutes),
        )
        self.conn.commit()

    def get_user_timezone(self, user_id: int) -> int:
        row = self.conn.execute(
            "SELECT utc_offset_minutes FROM user_settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return 0
        return int(row["utc_offset_minutes"])

    def add_daily_reminder(
        self, user_id: int, hour: int, minute: int, text: str, enabled: int = 1
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO reminders(user_id, hour, minute, text, enabled, is_once, run_at, sent_at, last_sent_on) VALUES (?, ?, ?, ?, ?, 0, NULL, NULL, NULL)",
            (user_id, hour, minute, text, enabled),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_once_reminder(
        self, user_id: int, run_at_utc: datetime, text: str, enabled: int = 1
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO reminders(user_id, hour, minute, text, enabled, is_once, run_at, sent_at, last_sent_on) VALUES (?, ?, ?, ?, ?, 1, ?, NULL, NULL)",
            (
                user_id,
                run_at_utc.hour,
                run_at_utc.minute,
                text,
                enabled,
                run_at_utc.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_reminders(self, user_id: int) -> List[Reminder]:
        rows = self.conn.execute(
            """
            SELECT id, user_id, hour, minute, text, enabled, is_once, run_at, sent_at, last_sent_on
            FROM reminders
            WHERE user_id = ? AND (is_once = 0 OR sent_at IS NULL)
            ORDER BY is_once ASC, hour, minute, run_at, id
            """,
            (user_id,),
        ).fetchall()
        return [Reminder(**dict(row)) for row in rows]

    def list_daily_reminders(self) -> List[Reminder]:
        rows = self.conn.execute(
            """
            SELECT id, user_id, hour, minute, text, enabled, is_once, run_at, sent_at, last_sent_on
            FROM reminders
            WHERE is_once = 0 AND enabled = 1
            """
        ).fetchall()
        return [Reminder(**dict(row)) for row in rows]

    def due_once_reminders(self, now_utc_sql: str) -> List[Reminder]:
        rows = self.conn.execute(
            """
            SELECT id, user_id, hour, minute, text, enabled, is_once, run_at, sent_at, last_sent_on
            FROM reminders
            WHERE is_once = 1 AND enabled = 1 AND sent_at IS NULL AND run_at <= ?
            ORDER BY run_at, id
            """,
            (now_utc_sql,),
        ).fetchall()
        return [Reminder(**dict(row)) for row in rows]

    def mark_daily_sent(self, reminder_id: int, local_date: str) -> None:
        self.conn.execute(
            "UPDATE reminders SET last_sent_on = ? WHERE id = ?",
            (local_date, reminder_id),
        )
        self.conn.commit()

    def mark_once_sent(self, reminder_id: int) -> None:
        self.conn.execute(
            "UPDATE reminders SET sent_at = CURRENT_TIMESTAMP WHERE id = ?",
            (reminder_id,),
        )
        self.conn.commit()

    def delete_reminder(self, user_id: int, reminder_id: int) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id),
        )
        self.conn.commit()
        return int(cursor.rowcount) > 0

    def set_reminder_enabled(self, user_id: int, reminder_id: int, enabled: int) -> bool:
        cursor = self.conn.execute(
            "UPDATE reminders SET enabled = ? WHERE id = ? AND user_id = ?",
            (enabled, reminder_id, user_id),
        )
        self.conn.commit()
        return int(cursor.rowcount) > 0

    def update_daily_reminder(
        self, user_id: int, reminder_id: int, hour: int, minute: int, text: str
    ) -> bool:
        cursor = self.conn.execute(
            """
            UPDATE reminders
            SET hour = ?, minute = ?, text = ?, last_sent_on = NULL
            WHERE id = ? AND user_id = ? AND is_once = 0
            """,
            (hour, minute, text, reminder_id, user_id),
        )
        self.conn.commit()
        return int(cursor.rowcount) > 0

    def update_once_reminder(
        self, user_id: int, reminder_id: int, run_at_utc: datetime, text: str
    ) -> bool:
        cursor = self.conn.execute(
            """
            UPDATE reminders
            SET hour = ?, minute = ?, run_at = ?, text = ?, sent_at = NULL
            WHERE id = ? AND user_id = ? AND is_once = 1
            """,
            (
                run_at_utc.hour,
                run_at_utc.minute,
                run_at_utc.strftime("%Y-%m-%d %H:%M:%S"),
                text,
                reminder_id,
                user_id,
            ),
        )
        self.conn.commit()
        return int(cursor.rowcount) > 0

    def clear_user_reminders(self, user_id: int) -> int:
        cursor = self.conn.execute("DELETE FROM reminders WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return int(cursor.rowcount)

    def list_service_categories(self) -> list[tuple[int, str]]:
        rows = self.conn.execute(
            "SELECT id, name FROM service_categories ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [(int(row["id"]), str(row["name"])) for row in rows]

    def add_service_category(self, name: str) -> bool:
        cursor = self.conn.execute(
            "INSERT OR IGNORE INTO service_categories(name) VALUES (?)",
            (name,),
        )
        self.conn.commit()
        return int(cursor.rowcount) > 0

    def get_category_name(self, category_id: int) -> str | None:
        row = self.conn.execute(
            "SELECT name FROM service_categories WHERE id = ?",
            (category_id,),
        ).fetchone()
        if not row:
            return None
        return str(row["name"])

    def get_category_id(self, category_name: str) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM service_categories WHERE name = ? COLLATE NOCASE",
            (category_name,),
        ).fetchone()
        if not row:
            return None
        return int(row["id"])

    def add_service(
        self, category_id: int, title: str, contact: str, notes: str | None
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO services(category_id, title, contact, notes) VALUES (?, ?, ?, ?)",
            (category_id, title, contact, notes),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_services_by_category(
        self, category_id: int
    ) -> list[tuple[int, str, str, str | None]]:
        rows = self.conn.execute(
            """
            SELECT id, title, contact, notes
            FROM services
            WHERE category_id = ?
            ORDER BY id DESC
            """,
            (category_id,),
        ).fetchall()
        return [
            (int(row["id"]), str(row["title"]), str(row["contact"]), row["notes"])
            for row in rows
        ]

    def clear_services_by_category(self, category_id: int) -> int:
        cursor = self.conn.execute(
            "DELETE FROM services WHERE category_id = ?",
            (category_id,),
        )
        self.conn.commit()
        return int(cursor.rowcount)

    def close(self) -> None:
        self.conn.close()


MAX_REMINDER_TEXT_LENGTH = 280
MAX_IMPORT_REMINDERS = 200
MAX_CATEGORY_NAME_LENGTH = 60
MAX_SERVICE_TITLE_LENGTH = 120
MAX_SERVICE_CONTACT_LENGTH = 160
MAX_SERVICE_NOTES_LENGTH = 240
DEFAULT_SERVICE_CATEGORIES = [
    "Дежурная аптека",
    "Электрик",
    "Сантехник",
    "Автосервис",
]
DUTY_PHARMACY_CATEGORY = "Дежурная аптека"
DB_PATH = Path(__file__).resolve().parent / "reminders.db"
STORE = ReminderStore(DB_PATH)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_time(value: str) -> tuple[int, int] | None:
    try:
        hour_str, minute_str = value.split(":", maxsplit=1)
        hour = int(hour_str)
        minute = int(minute_str)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (ValueError, AttributeError):
        return None
    return None


def validate_reminder_text(text: str) -> str | None:
    clean = text.strip()
    if not clean:
        return "Текст напоминания не может быть пустым"
    if len(clean) > MAX_REMINDER_TEXT_LENGTH:
        return f"Текст слишком длинный (максимум {MAX_REMINDER_TEXT_LENGTH} символов)"
    return None


def validate_category_name(name: str) -> str | None:
    clean = name.strip()
    if not clean:
        return "Название категории не может быть пустым"
    if len(clean) > MAX_CATEGORY_NAME_LENGTH:
        return f"Название категории слишком длинное (максимум {MAX_CATEGORY_NAME_LENGTH} символов)"
    return None


def validate_service_title(value: str) -> str | None:
    clean = value.strip()
    if not clean:
        return "Название сервиса не может быть пустым"
    if len(clean) > MAX_SERVICE_TITLE_LENGTH:
        return f"Название сервиса слишком длинное (максимум {MAX_SERVICE_TITLE_LENGTH} символов)"
    return None


def validate_service_contact(value: str) -> str | None:
    clean = value.strip()
    if not clean:
        return "Контакт сервиса не может быть пустым"
    if len(clean) > MAX_SERVICE_CONTACT_LENGTH:
        return f"Контакт слишком длинный (максимум {MAX_SERVICE_CONTACT_LENGTH} символов)"
    return None


def validate_service_notes(value: str) -> str | None:
    clean = value.strip()
    if len(clean) > MAX_SERVICE_NOTES_LENGTH:
        return f"Примечание слишком длинное (максимум {MAX_SERVICE_NOTES_LENGTH} символов)"
    return None


def parse_index(value: str) -> int | None:
    try:
        index = int(value)
        if index > 0:
            return index
    except (ValueError, TypeError):
        return None
    return None


def parse_once_datetime(date_value: str, time_value: str) -> datetime | None:
    try:
        return datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def parse_utc_offset(value: str) -> int | None:
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


def format_utc_offset(offset_minutes: int) -> str:
    sign = "+" if offset_minutes >= 0 else "-"
    abs_value = abs(offset_minutes)
    hours = abs_value // 60
    minutes = abs_value % 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def next_trigger(hour: int, minute: int, offset_minutes: int) -> datetime:
    now_utc = utc_now()
    now_local = now_utc + timedelta(minutes=offset_minutes)
    run_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if run_local <= now_local:
        run_local += timedelta(days=1)
    return run_local


def format_once_run_at(value_utc: str | None, offset_minutes: int) -> str:
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


def parse_utc_datetime(value_utc: str | None) -> datetime | None:
    if not value_utc:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value_utc, fmt)
        except ValueError:
            continue
    return None


def next_run_local(reminder: Reminder, user_offset: int, now_utc: datetime) -> datetime | None:
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


def reminder_line(reminder: Reminder, index: int, user_offset: int) -> str:
    state = "[off] " if reminder.enabled == 0 else ""
    if reminder.is_once:
        when = format_once_run_at(reminder.run_at, user_offset)
        return f"{index}. {state}[one-time] {when} - {reminder.text}"
    return f"{index}. {state}[daily] {reminder.hour:02d}:{reminder.minute:02d} - {reminder.text}"


def build_reminders_text(reminders: List[Reminder], user_offset: int) -> str:
    lines = [f"⏰ Ваши напоминания ({format_utc_offset(user_offset)})"]
    for idx, reminder in enumerate(reminders, start=1):
        lines.append(reminder_line(reminder, idx, user_offset))
        lines.append("")
    return "\n".join(lines)


def build_delete_keyboard(reminders: List[Reminder]) -> InlineKeyboardMarkup:
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
    rows = []
    for category_id, name in categories:
        rows.append(
            [InlineKeyboardButton(text=name, callback_data=f"svccat:{category_id}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_services(category_name: str, services: list[tuple[int, str, str, str | None]]) -> str:
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


def extract_rating(notes: str | None) -> float | None:
    if not notes:
        return None
    m = re.search(r"Google rating:\s*([0-9.]+)", notes)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def service_maps_link(title: str, notes: str | None) -> str:
    address: str | None = None
    if notes:
        parts = [p.strip() for p in notes.split("|")]
        if len(parts) >= 2 and parts[1] and not parts[1].lower().startswith("source:"):
            address = parts[1]
    query = f"{title}, {address}" if address else f"{title}, Limassol, Cyprus"
    return "https://www.google.com/maps/search/?api=1&query=" + urlparse.quote(query)


def fetch_live_duty_pharmacies() -> list[tuple[str, str, str | None]]:
    candidate_urls = [
        "https://cyprus.ondutypharmacy.com/limassol/",
        "https://cyprus.ondutypharmacy.com/limassol/all-pharmacies/",
    ]
    html = ""
    last_error: Exception | None = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    for url in candidate_urls:
        try:
            req = urlrequest.Request(url, headers=headers)
            html = urlrequest.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
            if html:
                break
        except Exception as exc:
            last_error = exc
            continue

    if not html:
        if last_error:
            raise last_error
        raise RuntimeError("Unable to fetch duty pharmacies")

    items = re.findall(
        r'<div class="col-md-6 mb-15 pharmacy-card"><div class="pharmacy-box">(.*?)</div></div>',
        html,
        re.S | re.I,
    )
    result: list[tuple[str, str, str | None]] = []
    for block in items:
        name_match = re.search(r"<a [^>]*>(.*?)</a>", block, re.S | re.I)
        phone_match = re.search(r'href="tel:([^"]+)"', block, re.S | re.I)
        if not name_match or not phone_match:
            continue

        raw_name = re.sub("<.*?>", "", name_match.group(1)).strip()
        raw_phone = "".join(ch for ch in phone_match.group(1) if ch.isdigit())
        if len(raw_phone) < 8:
            continue
        phone = f"+357 {raw_phone[-8:]}"

        block_text = re.sub("<.*?>", " ", block)
        block_text = " ".join(block_text.split())
        address_match = re.search(r"</span>(.*?)<b>", block, re.S | re.I)
        address: str | None = None
        if address_match:
            address = " ".join(re.sub("<.*?>", " ", address_match.group(1)).split())
            if not address:
                address = None
        elif block_text:
            address = block_text

        result.append((raw_name, phone, address))

    return result


def export_payload(user_id: int) -> dict:
    user_offset = STORE.get_user_timezone(user_id)
    reminders = STORE.list_reminders(user_id)
    payload_reminders: list[dict] = []
    for reminder in reminders:
        payload_reminders.append(
            {
                "enabled": int(reminder.enabled),
                "is_once": int(reminder.is_once),
                "hour": int(reminder.hour),
                "minute": int(reminder.minute),
                "text": reminder.text,
                "run_at": reminder.run_at,
            }
        )
    return {
        "version": 1,
        "exported_at_utc": utc_now().strftime("%Y-%m-%d %H:%M:%S"),
        "utc_offset_minutes": user_offset,
        "reminders": payload_reminders,
    }


def import_payload(user_id: int, payload: dict) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "Некорректный JSON: ожидается объект"

    reminders_data = payload.get("reminders")
    if not isinstance(reminders_data, list):
        return False, "Некорректный JSON: поле reminders должно быть массивом"
    if len(reminders_data) > MAX_IMPORT_REMINDERS:
        return False, f"Слишком много напоминаний в импорте (максимум {MAX_IMPORT_REMINDERS})"

    offset = payload.get("utc_offset_minutes", 0)
    if not isinstance(offset, int):
        return False, "Некорректный JSON: utc_offset_minutes должно быть целым числом"
    if offset < -12 * 60 or offset > 14 * 60:
        return False, "Некорректный JSON: utc_offset_minutes вне диапазона UTC-12:00..UTC+14:00"

    parsed_items: list[tuple[int, int, int, int, str, str | None]] = []
    for idx, item in enumerate(reminders_data, start=1):
        if not isinstance(item, dict):
            return False, f"reminders[{idx}] должен быть объектом"

        enabled = int(item.get("enabled", 1))
        if enabled not in (0, 1):
            return False, f"reminders[{idx}].enabled должен быть 0 или 1"

        is_once = int(item.get("is_once", 0))
        if is_once not in (0, 1):
            return False, f"reminders[{idx}].is_once должен быть 0 или 1"

        try:
            hour = int(item.get("hour"))
            minute = int(item.get("minute"))
        except (TypeError, ValueError):
            return False, f"reminders[{idx}] содержит некорректные hour/minute"
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return False, f"reminders[{idx}] содержит некорректные hour/minute"

        text = str(item.get("text", ""))
        text_error = validate_reminder_text(text)
        if text_error:
            return False, f"reminders[{idx}]: {text_error}"

        run_at = item.get("run_at")
        if is_once == 1:
            if not isinstance(run_at, str):
                return False, f"reminders[{idx}].run_at должен быть строкой для one-time напоминания"
            try:
                datetime.strptime(run_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return False, f"reminders[{idx}].run_at должен быть в формате YYYY-MM-DD HH:MM:SS"
        else:
            run_at = None

        parsed_items.append((enabled, is_once, hour, minute, text.strip(), run_at))

    STORE.clear_user_reminders(user_id)
    STORE.set_user_timezone(user_id, offset)
    for enabled, is_once, hour, minute, text, run_at in parsed_items:
        if is_once == 1 and run_at:
            run_at_dt = datetime.strptime(run_at, "%Y-%m-%d %H:%M:%S")
            STORE.add_once_reminder(
                user_id=user_id, run_at_utc=run_at_dt, text=text, enabled=enabled
            )
        else:
            STORE.add_daily_reminder(
                user_id=user_id, hour=hour, minute=minute, text=text, enabled=enabled
            )

    return True, f"Импорт завершен: {len(parsed_items)} напоминаний"


async def reminder_worker(bot: Bot) -> None:
    last_processed_minute = ""
    while True:
        now_utc = utc_now()
        current_minute = now_utc.strftime("%Y-%m-%d %H:%M")

        if current_minute != last_processed_minute:
            daily = STORE.list_daily_reminders()
            for reminder in daily:
                user_offset = STORE.get_user_timezone(reminder.user_id)
                local_now = now_utc + timedelta(minutes=user_offset)
                local_date = local_now.strftime("%Y-%m-%d")
                if (
                    local_now.hour == reminder.hour
                    and local_now.minute == reminder.minute
                    and reminder.last_sent_on != local_date
                ):
                    try:
                        await bot.send_message(reminder.user_id, f"⏰ Напоминание: {reminder.text}")
                        STORE.mark_daily_sent(reminder.id, local_date)
                    except Exception:
                        logging.exception("Failed to send daily reminder to %s", reminder.user_id)

            once_due = STORE.due_once_reminders(now_utc.strftime("%Y-%m-%d %H:%M:%S"))
            for reminder in once_due:
                try:
                    await bot.send_message(reminder.user_id, f"⏰ Одноразовое напоминание: {reminder.text}")
                    STORE.mark_once_sent(reminder.id)
                except Exception:
                    logging.exception("Failed to send one-time reminder to %s", reminder.user_id)

            last_processed_minute = current_minute

        await asyncio.sleep(max(1, 60 - utc_now().second))


async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я Digital Neighbour.\n\n"
        "Помогу с контактами, сервисами и напоминаниями.\n"
        "Выберите раздел в меню ниже.",
        reply_markup=MAIN_MENU,
    )


async def cmd_help(message: Message) -> None:
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
    await message.answer(CONTACTS_TEXT)


async def cmd_services(message: Message) -> None:
    categories = STORE.list_service_categories()
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


async def cmd_service_category(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /service_category <название>")
        return

    category_name = command.args.strip()
    category_id = STORE.get_category_id(category_name)
    if not category_id:
        await message.answer("Категория не найдена. Используйте /services для списка")
        return

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
            services = STORE.list_services_by_category(category_id)
            if services:
                await message.answer(
                    "Live-источник временно недоступен. Показан резервный список из базы.\n\n"
                    + format_services(category_name, services)
                )
                return

    services = STORE.list_services_by_category(category_id)
    await message.answer(format_services(category_name, services))


async def cmd_add_category(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /add_category <название>")
        return

    category_name = command.args.strip()
    error = validate_category_name(category_name)
    if error:
        await message.answer(error)
        return

    created = STORE.add_service_category(category_name)
    if created:
        await message.answer(f"Категория добавлена: {category_name}")
    else:
        await message.answer(f"Категория уже существует: {category_name}")


async def cmd_add_service(message: Message, command: CommandObject) -> None:
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

    category_id = STORE.get_category_id(category_name)
    if not category_id:
        STORE.add_service_category(category_name)
        category_id = STORE.get_category_id(category_name)
    if not category_id:
        await message.answer("Не удалось создать/найти категорию")
        return

    STORE.add_service(category_id=category_id, title=title.strip(), contact=contact.strip(), notes=notes)
    await message.answer(f"Сервис добавлен в категорию '{category_name}': {title}")


async def cmd_emergency(message: Message) -> None:
    await message.answer(EMERGENCY_TEXT)


async def cmd_faq(message: Message) -> None:
    lines = ["❓ FAQ"]
    for question, answer in FAQ_ITEMS.items():
        lines.append(f"\n• {question}\n  {answer}")
    await message.answer("\n".join(lines))


async def cmd_set_timezone(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    if not command.args:
        await message.answer("Использование: /set_timezone +03:00")
        return

    offset = parse_utc_offset(command.args.strip())
    if offset is None:
        await message.answer("Некорректный формат. Пример: /set_timezone +03:00")
        return

    STORE.set_user_timezone(message.from_user.id, offset)
    await message.answer(f"Часовой пояс сохранен: {format_utc_offset(offset)}")


async def cmd_my_timezone(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    offset = STORE.get_user_timezone(message.from_user.id)
    await message.answer(f"Ваш часовой пояс: {format_utc_offset(offset)}")


async def cmd_remind(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /remind HH:MM текст")
        return

    parts = command.args.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Нужны время и текст. Пример: /remind 19:30 Вынести мусор")
        return

    parsed = parse_time(parts[0])
    if not parsed:
        await message.answer("Некорректное время. Используйте формат HH:MM")
        return

    hour, minute = parsed
    text = parts[1].strip()
    text_error = validate_reminder_text(text)
    if text_error:
        await message.answer(text_error)
        return

    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user_id = message.from_user.id
    STORE.add_daily_reminder(user_id=user_id, hour=hour, minute=minute, text=text)

    user_offset = STORE.get_user_timezone(user_id)
    trigger_at = next_trigger(hour, minute, user_offset).strftime("%H:%M")
    await message.answer(
        f"Добавил ежедневное напоминание на {trigger_at} ({format_utc_offset(user_offset)}): {text}"
    )


async def cmd_remind_once(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer(
            "Использование: /remind_once YYYY-MM-DD HH:MM текст"
        )
        return

    parts = command.args.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Нужны дата, время и текст. Пример: /remind_once 2026-02-20 19:30 Встреча"
        )
        return

    run_at_local = parse_once_datetime(parts[0], parts[1])
    if not run_at_local:
        await message.answer("Некорректные дата или время. Формат: YYYY-MM-DD HH:MM")
        return

    text = parts[2].strip()
    text_error = validate_reminder_text(text)
    if text_error:
        await message.answer(text_error)
        return

    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user_id = message.from_user.id
    user_offset = STORE.get_user_timezone(user_id)
    run_at_utc = run_at_local - timedelta(minutes=user_offset)

    if run_at_utc <= utc_now():
        await message.answer(
            f"Укажите будущее время. Сейчас: {(utc_now() + timedelta(minutes=user_offset)).strftime('%Y-%m-%d %H:%M')}"
        )
        return

    STORE.add_once_reminder(user_id=user_id, run_at_utc=run_at_utc, text=text)
    await message.answer(
        f"Добавил одноразовое напоминание на {run_at_local.strftime('%Y-%m-%d %H:%M')} ({format_utc_offset(user_offset)}): {text}"
    )


async def cmd_edit_reminder(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return
    if not command.args:
        await message.answer("Использование: /edit_reminder N HH:MM текст")
        return

    parts = command.args.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Пример: /edit_reminder 2 08:30 Утренняя прогулка")
        return

    index = parse_index(parts[0])
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    parsed = parse_time(parts[1])
    if not parsed:
        await message.answer("Некорректное время. Используйте формат HH:MM")
        return

    text = parts[2].strip()
    text_error = validate_reminder_text(text)
    if text_error:
        await message.answer(text_error)
        return

    user_id = message.from_user.id
    reminders = STORE.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return
    if index > len(reminders):
        await message.answer(f"У вас только {len(reminders)} напоминаний")
        return

    reminder = reminders[index - 1]
    if reminder.is_once:
        await message.answer("Это одноразовое напоминание. Используйте /edit_once_reminder")
        return

    hour, minute = parsed
    updated = STORE.update_daily_reminder(user_id, reminder.id, hour, minute, text)
    if not updated:
        await message.answer("Не удалось обновить напоминание")
        return

    await message.answer(f"Обновил напоминание {index}: {hour:02d}:{minute:02d} - {text}")


async def cmd_edit_once_reminder(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return
    if not command.args:
        await message.answer("Использование: /edit_once_reminder N YYYY-MM-DD HH:MM текст")
        return

    parts = command.args.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Пример: /edit_once_reminder 3 2026-03-01 14:15 Поход в банк")
        return

    index = parse_index(parts[0])
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    run_at_local = parse_once_datetime(parts[1], parts[2])
    if not run_at_local:
        await message.answer("Некорректные дата или время. Формат: YYYY-MM-DD HH:MM")
        return

    text = parts[3].strip()
    text_error = validate_reminder_text(text)
    if text_error:
        await message.answer(text_error)
        return

    user_id = message.from_user.id
    user_offset = STORE.get_user_timezone(user_id)
    run_at_utc = run_at_local - timedelta(minutes=user_offset)
    if run_at_utc <= utc_now():
        await message.answer("Укажите будущее время для одноразового напоминания")
        return

    reminders = STORE.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return
    if index > len(reminders):
        await message.answer(f"У вас только {len(reminders)} напоминаний")
        return

    reminder = reminders[index - 1]
    if not reminder.is_once:
        await message.answer("Это ежедневное напоминание. Используйте /edit_reminder")
        return

    updated = STORE.update_once_reminder(user_id, reminder.id, run_at_utc, text)
    if not updated:
        await message.answer("Не удалось обновить напоминание")
        return

    await message.answer(
        f"Обновил one-time {index}: {run_at_local.strftime('%Y-%m-%d %H:%M')} - {text}"
    )


async def cmd_my_reminders(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user_id = message.from_user.id
    user_offset = STORE.get_user_timezone(user_id)
    user_reminders = STORE.list_reminders(user_id)
    if not user_reminders:
        await message.answer("У вас пока нет напоминаний")
        return

    await message.answer(
        build_reminders_text(user_reminders, user_offset),
        reply_markup=build_delete_keyboard(user_reminders),
    )


async def cmd_next_reminders(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    user_id = message.from_user.id
    user_offset = STORE.get_user_timezone(user_id)
    reminders = STORE.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return

    now_utc = utc_now()
    upcoming: list[tuple[datetime, Reminder]] = []
    for reminder in reminders:
        run_local = next_run_local(reminder, user_offset, now_utc)
        if run_local:
            upcoming.append((run_local, reminder))

    if not upcoming:
        await message.answer("У вас нет активных ближайших напоминаний")
        return

    upcoming.sort(key=lambda x: x[0])
    lines = [f"⏰ Ближайшие напоминания ({format_utc_offset(user_offset)})"]
    for idx, (run_local, reminder) in enumerate(upcoming[:10], start=1):
        kind = "one-time" if reminder.is_once else "daily"
        lines.append(
            f"{idx}. [{kind}] {run_local.strftime('%Y-%m-%d %H:%M')} - {reminder.text}"
        )
        lines.append("")
    if len(upcoming) > 10:
        lines.append(f"... и еще {len(upcoming) - 10}")

    await message.answer("\n".join(lines))


async def cmd_nearby_services(message: Message) -> None:
    categories = STORE.list_service_categories()
    if not categories:
        await message.answer("Категории сервисов пока не настроены")
        return

    collected: list[tuple[float, str, str, str, str | None]] = []
    for _, category_name in categories:
        services = STORE.list_services_by_category(STORE.get_category_id(category_name) or 0)
        for _, title, contact, notes in services:
            rating = extract_rating(notes)
            if rating is None:
                rating = 0.0
            collected.append((rating, category_name, title, contact, notes))

    if not collected:
        await message.answer("Сервисы пока не заполнены")
        return

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


async def cmd_delete_reminder(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    if not command.args:
        await message.answer("Использование: /delete_reminder N. Пример: /delete_reminder 2")
        return

    index = parse_index(command.args.strip())
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    user_id = message.from_user.id
    user_offset = STORE.get_user_timezone(user_id)
    user_reminders = STORE.list_reminders(user_id)
    if not user_reminders:
        await message.answer("У вас пока нет напоминаний")
        return

    if index > len(user_reminders):
        await message.answer(f"У вас только {len(user_reminders)} напоминаний")
        return

    reminder = user_reminders[index - 1]
    deleted = STORE.delete_reminder(user_id=user_id, reminder_id=reminder.id)
    if not deleted:
        await message.answer("Не удалось удалить напоминание. Попробуйте снова")
        return

    if reminder.is_once:
        schedule = format_once_run_at(reminder.run_at, user_offset)
    else:
        schedule = f"{reminder.hour:02d}:{reminder.minute:02d}"
    await message.answer(f"Удалил напоминание {index}: {schedule} - {reminder.text}")


async def cmd_disable_reminder(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    if not command.args:
        await message.answer("Использование: /disable_reminder N. Пример: /disable_reminder 2")
        return

    index = parse_index(command.args.strip())
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    user_id = message.from_user.id
    reminders = STORE.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return
    if index > len(reminders):
        await message.answer(f"У вас только {len(reminders)} напоминаний")
        return

    reminder = reminders[index - 1]
    if reminder.enabled == 0:
        await message.answer(f"Напоминание {index} уже выключено")
        return

    STORE.set_reminder_enabled(user_id=user_id, reminder_id=reminder.id, enabled=0)
    await message.answer(f"Выключил напоминание {index}")


async def cmd_enable_reminder(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    if not command.args:
        await message.answer("Использование: /enable_reminder N. Пример: /enable_reminder 2")
        return

    index = parse_index(command.args.strip())
    if not index:
        await message.answer("Номер должен быть положительным целым числом")
        return

    user_id = message.from_user.id
    reminders = STORE.list_reminders(user_id)
    if not reminders:
        await message.answer("У вас пока нет напоминаний")
        return
    if index > len(reminders):
        await message.answer(f"У вас только {len(reminders)} напоминаний")
        return

    reminder = reminders[index - 1]
    if reminder.enabled == 1:
        await message.answer(f"Напоминание {index} уже включено")
        return

    STORE.set_reminder_enabled(user_id=user_id, reminder_id=reminder.id, enabled=1)
    await message.answer(f"Включил напоминание {index}")


async def cmd_clear_reminders(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    deleted = STORE.clear_user_reminders(message.from_user.id)
    if deleted == 0:
        await message.answer("У вас не было напоминаний")
        return

    await message.answer("Все ваши напоминания удалены")


async def cmd_export_reminders(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    payload = export_payload(message.from_user.id)
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    data = json_text.encode("utf-8")
    filename = f"reminders_backup_{message.from_user.id}_{utc_now().strftime('%Y%m%d_%H%M%S')}.json"
    document = BufferedInputFile(data, filename=filename)

    await message.answer_document(
        document=document,
        caption="Экспорт готов. Для восстановления ответьте на этот файл командой /import_reminders",
    )


async def cmd_import_reminders(message: Message) -> None:
    if not message.from_user:
        await message.answer("Не удалось определить пользователя")
        return

    replied = message.reply_to_message
    if not replied:
        await message.answer("Использование: ответьте командой /import_reminders на JSON-текст или файл .json")
        return

    payload: dict
    if replied.document:
        if not replied.document.file_name or not replied.document.file_name.lower().endswith(".json"):
            await message.answer("Ожидается файл с расширением .json")
            return
        if replied.document.file_size and replied.document.file_size > 512 * 1024:
            await message.answer("Файл слишком большой (максимум 512 KB)")
            return

        buffer = BytesIO()
        try:
            await message.bot.download(replied.document, destination=buffer)
            raw = buffer.getvalue().decode("utf-8")
            payload = json.loads(raw)
        except UnicodeDecodeError:
            await message.answer("Файл должен быть в кодировке UTF-8")
            return
        except json.JSONDecodeError:
            await message.answer("Не удалось разобрать JSON из файла")
            return
        except Exception:
            logging.exception("Failed to import reminders from file")
            await message.answer("Не удалось прочитать файл. Попробуйте снова")
            return
    else:
        source_text = replied.text
        if not source_text:
            await message.answer("В ответе не найден JSON или файл .json")
            return

        start = source_text.find("{")
        end = source_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            await message.answer("В сообщении не найден корректный JSON")
            return

        try:
            payload = json.loads(source_text[start : end + 1])
        except json.JSONDecodeError:
            await message.answer("Не удалось разобрать JSON")
            return

    ok, result = import_payload(message.from_user.id, payload)
    await message.answer(result)
    if ok:
        await cmd_my_reminders(message)


async def callback_delete_reminder(callback: CallbackQuery) -> None:
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
        await callback.answer("Некорректный id", show_alert=True)
        return

    user_id = callback.from_user.id
    deleted = STORE.delete_reminder(user_id=user_id, reminder_id=reminder_id)
    if not deleted:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return

    user_offset = STORE.get_user_timezone(user_id)
    reminders = STORE.list_reminders(user_id)

    if callback.message:
        if reminders:
            await callback.message.edit_text(
                build_reminders_text(reminders, user_offset),
                reply_markup=build_delete_keyboard(reminders),
            )
        else:
            await callback.message.edit_text("У вас пока нет напоминаний")

    await callback.answer("Удалено")


async def callback_toggle_reminder(callback: CallbackQuery) -> None:
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
    updated = STORE.set_reminder_enabled(user_id=user_id, reminder_id=reminder_id, enabled=target)
    if not updated:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return

    user_offset = STORE.get_user_timezone(user_id)
    reminders = STORE.list_reminders(user_id)

    if callback.message:
        if reminders:
            await callback.message.edit_text(
                build_reminders_text(reminders, user_offset),
                reply_markup=build_delete_keyboard(reminders),
            )
        else:
            await callback.message.edit_text("У вас пока нет напоминаний")

    await callback.answer("Обновлено")


async def callback_service_category(callback: CallbackQuery) -> None:
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

    category_name = STORE.get_category_name(category_id)
    if not category_name:
        await callback.answer("Категория не найдена", show_alert=True)
        return

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
                services = STORE.list_services_by_category(category_id)
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

    services = STORE.list_services_by_category(category_id)
    if callback.message:
        await callback.message.answer(format_services(category_name, services))
    await callback.answer()


async def handle_faq_button(message: Message) -> None:
    await cmd_faq(message)


async def handle_contacts_button(message: Message) -> None:
    await cmd_contacts(message)


async def handle_services_button(message: Message) -> None:
    await cmd_services(message)


async def handle_emergency_button(message: Message) -> None:
    await cmd_emergency(message)


async def handle_my_reminders_button(message: Message) -> None:
    await cmd_my_reminders(message)


async def handle_next_reminders_button(message: Message) -> None:
    await cmd_next_reminders(message)


async def handle_nearby_services_button(message: Message) -> None:
    await cmd_nearby_services(message)


async def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не найден. Создайте .env из .env.example")

    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=token)
    dp = Dispatcher()

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_contacts, Command("contacts"))
    dp.message.register(cmd_services, Command("services"))
    dp.message.register(cmd_service_category, Command("service_category"))
    dp.message.register(cmd_add_category, Command("add_category"))
    dp.message.register(cmd_add_service, Command("add_service"))
    dp.message.register(cmd_emergency, Command("emergency"))
    dp.message.register(cmd_faq, Command("faq"))
    dp.message.register(cmd_set_timezone, Command("set_timezone"))
    dp.message.register(cmd_my_timezone, Command("my_timezone"))
    dp.message.register(cmd_remind, Command("remind"))
    dp.message.register(cmd_remind_once, Command("remind_once"))
    dp.message.register(cmd_edit_reminder, Command("edit_reminder"))
    dp.message.register(cmd_edit_once_reminder, Command("edit_once_reminder"))
    dp.message.register(cmd_my_reminders, Command("my_reminders"))
    dp.message.register(cmd_next_reminders, Command("next_reminders"))
    dp.message.register(cmd_nearby_services, Command("nearby_services"))
    dp.message.register(cmd_disable_reminder, Command("disable_reminder"))
    dp.message.register(cmd_enable_reminder, Command("enable_reminder"))
    dp.message.register(cmd_delete_reminder, Command("delete_reminder"))
    dp.message.register(cmd_export_reminders, Command("export_reminders"))
    dp.message.register(cmd_import_reminders, Command("import_reminders"))
    dp.message.register(cmd_clear_reminders, Command("clear_reminders"))

    dp.callback_query.register(callback_delete_reminder, F.data.startswith("delrem:"))
    dp.callback_query.register(callback_toggle_reminder, F.data.startswith("togrem:"))
    dp.callback_query.register(callback_service_category, F.data.startswith("svccat:"))

    dp.message.register(handle_faq_button, F.text.in_(["FAQ", "❓ FAQ"]))
    dp.message.register(handle_contacts_button, F.text.in_(["Полезные контакты", "📞 Полезные контакты"]))
    dp.message.register(handle_services_button, F.text.in_(["Сервисы", "🛠 Сервисы"]))
    dp.message.register(handle_emergency_button, F.text.in_(["Экстренная помощь", "🆘 Экстренная помощь"]))
    dp.message.register(handle_my_reminders_button, F.text.in_(["Мои напоминания", "⏰ Мои напоминания"]))
    dp.message.register(handle_next_reminders_button, F.text.in_(["Ближайшие напоминания", "⏰ Ближайшие напоминания"]))
    dp.message.register(handle_nearby_services_button, F.text.in_(["Ближайшие сервисы", "📍 Ближайшие сервисы"]))
    dp.message.register(handle_next_reminders_button, F.text == "Ближайшие")

    worker = asyncio.create_task(reminder_worker(bot))
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        STORE.close()


if __name__ == "__main__":
    asyncio.run(main())
