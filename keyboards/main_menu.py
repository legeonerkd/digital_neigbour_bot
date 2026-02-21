from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❓ FAQ"), KeyboardButton(text="📞 Полезные контакты")],
        [KeyboardButton(text="🆘 Экстренная помощь"), KeyboardButton(text="🛠 Сервисы")],
        [KeyboardButton(text="⏰ Мои напоминания"), KeyboardButton(text="📍 Ближайшие сервисы")],
    ],
    resize_keyboard=True,
)
