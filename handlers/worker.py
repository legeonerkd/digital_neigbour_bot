"""Фоновый воркер для отправки напоминаний."""

import asyncio
import logging
from datetime import timedelta

from aiogram import Bot

from database.store import ReminderStore
from utils.time_utils import utc_now


async def reminder_worker(bot: Bot, store: ReminderStore) -> None:
    """Фоновая задача для отправки напоминаний.
    
    Args:
        bot: Экземпляр бота
        store: Хранилище данных
    """
    last_processed_minute = ""
    while True:
        now_utc = utc_now()
        current_minute = now_utc.strftime("%Y-%m-%d %H:%M")

        if current_minute != last_processed_minute:
            # Обработка ежедневных напоминаний
            daily = store.list_daily_reminders()
            for reminder in daily:
                user_offset = store.get_user_timezone(reminder.user_id)
                local_now = now_utc + timedelta(minutes=user_offset)
                local_date = local_now.strftime("%Y-%m-%d")
                if (
                    local_now.hour == reminder.hour
                    and local_now.minute == reminder.minute
                    and reminder.last_sent_on != local_date
                ):
                    try:
                        await bot.send_message(reminder.user_id, f"⏰ Напоминание: {reminder.text}")
                        store.mark_daily_sent(reminder.id, local_date)
                    except Exception as e:
                        logging.exception(
                            "Failed to send daily reminder id=%s to user=%s: %s",
                            reminder.id,
                            reminder.user_id,
                            type(e).__name__
                        )

            # Обработка одноразовых напоминаний
            once_due = store.due_once_reminders(now_utc.strftime("%Y-%m-%d %H:%M:%S"))
            for reminder in once_due:
                try:
                    await bot.send_message(reminder.user_id, f"⏰ Одноразовое напоминание: {reminder.text}")
                    store.mark_once_sent(reminder.id)
                except Exception as e:
                    logging.exception(
                        "Failed to send one-time reminder id=%s to user=%s: %s",
                        reminder.id,
                        reminder.user_id,
                        type(e).__name__
                    )

            last_processed_minute = current_minute

        await asyncio.sleep(max(1, 60 - utc_now().second))
