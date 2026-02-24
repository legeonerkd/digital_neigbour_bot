"""Хранилище данных в SQLite."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List

from config.settings import DEFAULT_SERVICE_CATEGORIES
from models.reminder import Reminder


class ReminderStore:
    """Класс для работы с базой данных напоминаний и сервисов."""
    
    def __init__(self, db_path: Path) -> None:
        """Инициализация хранилища.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_schema_version(self) -> int:
        """Получить текущую версию схемы БД.
        
        Returns:
            Номер версии схемы (0 если таблица не существует)
        """
        try:
            row = self.conn.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            ).fetchone()
            return int(row[0]) if row else 0
        except sqlite3.OperationalError:
            return 0

    def _set_schema_version(self, version: int) -> None:
        """Установить версию схемы БД.
        
        Args:
            version: Номер версии
        """
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
        )
        self.conn.execute("INSERT OR REPLACE INTO schema_version VALUES (?)", (version,))

    def _init_db(self) -> None:
        """Инициализация структуры базы данных."""
        # Создание основных таблиц
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

        # Применение миграций
        current_version = self._get_schema_version()
        
        # Миграция 1: добавление новых столбцов в reminders (для старых БД)
        if current_version < 1:
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
            self._set_schema_version(1)

        # Создание индексов
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
        
        # Добавление категорий по умолчанию
        for category_name in DEFAULT_SERVICE_CATEGORIES:
            self.conn.execute(
                "INSERT OR IGNORE INTO service_categories(name) VALUES (?)",
                (category_name,),
            )
        self.conn.commit()

    def set_user_timezone(self, user_id: int, utc_offset_minutes: int) -> None:
        """Установить часовой пояс пользователя.
        
        Args:
            user_id: ID пользователя
            utc_offset_minutes: Смещение в минутах от UTC
        """
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
        """Получить часовой пояс пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Смещение в минутах от UTC
        """
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
        """Добавить ежедневное напоминание.
        
        Args:
            user_id: ID пользователя
            hour: Час срабатывания
            minute: Минута срабатывания
            text: Текст напоминания
            enabled: Включено ли напоминание (1 или 0)
            
        Returns:
            ID созданного напоминания
        """
        cursor = self.conn.execute(
            "INSERT INTO reminders(user_id, hour, minute, text, enabled, is_once, run_at, sent_at, last_sent_on) VALUES (?, ?, ?, ?, ?, 0, NULL, NULL, NULL)",
            (user_id, hour, minute, text, enabled),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_once_reminder(
        self, user_id: int, run_at_utc: datetime, text: str, enabled: int = 1
    ) -> int:
        """Добавить одноразовое напоминание.
        
        Args:
            user_id: ID пользователя
            run_at_utc: Время срабатывания в UTC
            text: Текст напоминания
            enabled: Включено ли напоминание (1 или 0)
            
        Returns:
            ID созданного напоминания
        """
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
        """Получить список напоминаний пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список объектов Reminder
        """
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
        """Получить все активные ежедневные напоминания.
        
        Returns:
            Список объектов Reminder
        """
        rows = self.conn.execute(
            """
            SELECT id, user_id, hour, minute, text, enabled, is_once, run_at, sent_at, last_sent_on
            FROM reminders
            WHERE is_once = 0 AND enabled = 1
            """
        ).fetchall()
        return [Reminder(**dict(row)) for row in rows]

    def due_once_reminders(self, now_utc_sql: str) -> List[Reminder]:
        """Получить одноразовые напоминания, которые пора отправить.
        
        Args:
            now_utc_sql: Текущее время в формате SQL
            
        Returns:
            Список объектов Reminder
        """
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
        """Отметить ежедневное напоминание как отправленное.
        
        Args:
            reminder_id: ID напоминания
            local_date: Локальная дата отправки
        """
        self.conn.execute(
            "UPDATE reminders SET last_sent_on = ? WHERE id = ?",
            (local_date, reminder_id),
        )
        self.conn.commit()

    def mark_once_sent(self, reminder_id: int) -> None:
        """Отметить одноразовое напоминание как отправленное.
        
        Args:
            reminder_id: ID напоминания
        """
        self.conn.execute(
            "UPDATE reminders SET sent_at = CURRENT_TIMESTAMP WHERE id = ?",
            (reminder_id,),
        )
        self.conn.commit()

    def delete_reminder(self, user_id: int, reminder_id: int) -> bool:
        """Удалить напоминание.
        
        Args:
            user_id: ID пользователя
            reminder_id: ID напоминания
            
        Returns:
            True если напоминание было удалено
        """
        cursor = self.conn.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ?",
            (reminder_id, user_id),
        )
        self.conn.commit()
        return int(cursor.rowcount) > 0

    def set_reminder_enabled(self, user_id: int, reminder_id: int, enabled: int) -> bool:
        """Включить/выключить напоминание.
        
        Args:
            user_id: ID пользователя
            reminder_id: ID напоминания
            enabled: 1 для включения, 0 для выключения
            
        Returns:
            True если напоминание было обновлено
        """
        cursor = self.conn.execute(
            "UPDATE reminders SET enabled = ? WHERE id = ? AND user_id = ?",
            (enabled, reminder_id, user_id),
        )
        self.conn.commit()
        return int(cursor.rowcount) > 0

    def update_daily_reminder(
        self, user_id: int, reminder_id: int, hour: int, minute: int, text: str
    ) -> bool:
        """Обновить ежедневное напоминание.
        
        Args:
            user_id: ID пользователя
            reminder_id: ID напоминания
            hour: Новый час
            minute: Новая минута
            text: Новый текст
            
        Returns:
            True если напоминание было обновлено
        """
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
        """Обновить одноразовое напоминание.
        
        Args:
            user_id: ID пользователя
            reminder_id: ID напоминания
            run_at_utc: Новое время срабатывания в UTC
            text: Новый текст
            
        Returns:
            True если напоминание было обновлено
        """
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
        """Удалить все напоминания пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество удаленных напоминаний
        """
        cursor = self.conn.execute("DELETE FROM reminders WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return int(cursor.rowcount)

    def list_service_categories(self) -> list[tuple[int, str]]:
        """Получить список категорий сервисов.
        
        Returns:
            Список кортежей (id, название)
        """
        rows = self.conn.execute(
            "SELECT id, name FROM service_categories ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [(int(row["id"]), str(row["name"])) for row in rows]

    def add_service_category(self, name: str) -> bool:
        """Добавить категорию сервисов.
        
        Args:
            name: Название категории
            
        Returns:
            True если категория была добавлена
        """
        cursor = self.conn.execute(
            "INSERT OR IGNORE INTO service_categories(name) VALUES (?)",
            (name,),
        )
        self.conn.commit()
        return int(cursor.rowcount) > 0

    def get_category_name(self, category_id: int) -> str | None:
        """Получить название категории по ID.
        
        Args:
            category_id: ID категории
            
        Returns:
            Название категории или None
        """
        row = self.conn.execute(
            "SELECT name FROM service_categories WHERE id = ?",
            (category_id,),
        ).fetchone()
        if not row:
            return None
        return str(row["name"])

    def get_category_id(self, category_name: str) -> int | None:
        """Получить ID категории по названию.
        
        Args:
            category_name: Название категории
            
        Returns:
            ID категории или None
        """
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
        """Добавить сервис.
        
        Args:
            category_id: ID категории
            title: Название сервиса
            contact: Контакт
            notes: Примечания
            
        Returns:
            ID созданного сервиса
        """
        cursor = self.conn.execute(
            "INSERT INTO services(category_id, title, contact, notes) VALUES (?, ?, ?, ?)",
            (category_id, title, contact, notes),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_services_by_category(
        self, category_id: int
    ) -> list[tuple[int, str, str, str | None]]:
        """Получить список сервисов в категории.
        
        Args:
            category_id: ID категории
            
        Returns:
            Список кортежей (id, название, контакт, примечания)
        """
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
        """Удалить все сервисы в категории.
        
        Args:
            category_id: ID категории
            
        Returns:
            Количество удаленных сервисов
        """
        cursor = self.conn.execute(
            "DELETE FROM services WHERE category_id = ?",
            (category_id,),
        )
        self.conn.commit()
        return int(cursor.rowcount)

    def close(self) -> None:
        """Закрыть соединение с базой данных."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Вход в контекстный менеджер."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера."""
        self.close()
        return False

    @contextmanager
    def transaction(self):
        """Контекстный менеджер для транзакций.
        
        Yields:
            self: Экземпляр хранилища
            
        Example:
            with store.transaction():
                store.add_daily_reminder(...)
                store.add_once_reminder(...)
        """
        try:
            yield self
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
