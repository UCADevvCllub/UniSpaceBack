from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗓 Lessons"), KeyboardButton(text="🏋️ Sports & Gym & Meal")],
            [KeyboardButton(text="📺 TV Lounges"), KeyboardButton(text="📞 Contacts")],
            [KeyboardButton(text="📅 My Day"), KeyboardButton(text="⚙️ Settings")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

