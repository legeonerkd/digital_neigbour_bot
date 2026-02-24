"""Обработчики команд бота."""

from .start import (
    cmd_start,
    cmd_help,
    cmd_contacts,
    cmd_emergency,
    cmd_faq,
    handle_faq_button,
    handle_contacts_button,
    handle_emergency_button,
)
from .timezone import cmd_set_timezone, cmd_my_timezone
from .reminders import (
    cmd_remind,
    cmd_remind_once,
    cmd_edit_reminder,
    cmd_edit_once_reminder,
    cmd_my_reminders,
    cmd_next_reminders,
    cmd_delete_reminder,
    cmd_disable_reminder,
    cmd_enable_reminder,
    cmd_clear_reminders,
    handle_my_reminders_button,
    handle_next_reminders_button,
)
from .services import (
    cmd_services,
    cmd_service_category,
    cmd_add_category,
    cmd_add_service,
    cmd_nearby_services,
    handle_services_button,
    handle_nearby_services_button,
    handle_location,
)
from .callbacks import (
    callback_toggle_reminder,
    callback_delete_reminder,
    callback_service_category,
)
from .backup import cmd_export_reminders, cmd_import_reminders
from .worker import reminder_worker

__all__ = [
    # start
    "cmd_start",
    "cmd_help",
    "cmd_contacts",
    "cmd_emergency",
    "cmd_faq",
    "handle_faq_button",
    "handle_contacts_button",
    "handle_emergency_button",
    # timezone
    "cmd_set_timezone",
    "cmd_my_timezone",
    # reminders
    "cmd_remind",
    "cmd_remind_once",
    "cmd_edit_reminder",
    "cmd_edit_once_reminder",
    "cmd_my_reminders",
    "cmd_next_reminders",
    "cmd_delete_reminder",
    "cmd_disable_reminder",
    "cmd_enable_reminder",
    "cmd_clear_reminders",
    "handle_my_reminders_button",
    "handle_next_reminders_button",
    # services
    "cmd_services",
    "cmd_service_category",
    "cmd_add_category",
    "cmd_add_service",
    "cmd_nearby_services",
    "handle_services_button",
    "handle_nearby_services_button",
    "handle_location",
    # callbacks
    "callback_toggle_reminder",
    "callback_delete_reminder",
    "callback_service_category",
    # backup
    "cmd_export_reminders",
    "cmd_import_reminders",
    # worker
    "reminder_worker",
]
