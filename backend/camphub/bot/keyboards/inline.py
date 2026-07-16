from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_academic_level_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Freshman", callback_data="level_Freshman")
    builder.button(text="Sophomore", callback_data="level_Sophomore")
    builder.button(text="Junior", callback_data="level_Junior")
    builder.button(text="Senior", callback_data="level_Senior")
    builder.adjust(2)
    return builder.as_markup()

def get_lessons_submenu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Today's Lessons", callback_data="lessons_today")
    builder.button(text="Weekly Schedule", callback_data="lessons_weekly")
    builder.button(text="Set Reminder", callback_data="lessons_reminder")
    builder.button(text="Edit", callback_data="lessons_edit")
    builder.adjust(1)
    return builder.as_markup()

def get_edit_lessons_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Add Lesson", callback_data="edit_lesson_add")
    builder.button(text="Remove Lesson", callback_data="edit_lesson_remove")
    builder.button(text="Back", callback_data="lessons_menu_back")
    builder.adjust(1)
    return builder.as_markup()

def get_sports_submenu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏋️ Gym", callback_data="sports_gym")
    builder.button(text="🏀 Bubble", callback_data="sports_bubble")
    builder.button(text="⏰ Set Reminder", callback_data="sports_reminder")
    builder.adjust(1)
    return builder.as_markup()

def get_gym_options_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗓 Weekly Schedule", callback_data="gym_weekly")
    builder.button(text="📅 Today's Schedule", callback_data="gym_today")
    builder.button(text="🕒 Current Time Slot", callback_data="gym_current_slot")
    builder.button(text="Back", callback_data="sports_menu_back")
    builder.adjust(1)
    return builder.as_markup()

def get_bubble_options_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗓 Weekly Schedule", callback_data="bubble_weekly")
    builder.button(text="📅 Today's Schedule", callback_data="bubble_today")
    builder.button(text="🕒 Current Time Slot", callback_data="bubble_current_slot")
    builder.button(text="Back", callback_data="sports_menu_back")
    builder.adjust(1)
    return builder.as_markup()

def get_tv_submenu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Book Lounge", callback_data="tv_book")
    builder.button(text="✏️ Edit/Delete Booking", callback_data="tv_edit")
    builder.button(text="📺 My Bookings", callback_data="tv_my_bookings")
    builder.adjust(1)
    return builder.as_markup()

def get_tv_lounges_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Lounge A1", callback_data="tv_lounge_A1")
    builder.button(text="Lounge A2", callback_data="tv_lounge_A2")
    builder.button(text="Lounge B1", callback_data="tv_lounge_B1")
    builder.button(text="Lounge B2", callback_data="tv_lounge_B2")
    builder.button(text="Back", callback_data="tv_menu_back")
    builder.adjust(2)
    return builder.as_markup()

def get_contacts_submenu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="On Campus", callback_data="contacts_on_campus")
    builder.button(text="Off Campus", callback_data="contacts_off_campus")
    builder.adjust(2)
    return builder.as_markup()

def get_days_kb(prefix: str, include_all: bool = False) -> InlineKeyboardMarkup:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    builder = InlineKeyboardBuilder()
    for day in days:
        builder.button(text=day, callback_data=f"{prefix}_{day}")
    if include_all:
        builder.button(text="All 📅", callback_data=f"{prefix}_All")
    builder.adjust(2)
    return builder.as_markup()

def get_reminder_toggle_kb(callback_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Turn ON Reminder", callback_data=f"{callback_prefix}_on")
    builder.button(text="Turn OFF Reminder", callback_data=f"{callback_prefix}_off")
    builder.adjust(1)
    return builder.as_markup()

def get_reminder_offsets_kb(callback_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    offsets = [5, 10, 15, 30, 60]
    for offset in offsets:
        text = f"{offset} mins before" if offset < 60 else "1 hour before"
        builder.button(text=text, callback_data=f"{callback_prefix}_{offset}")
    builder.adjust(2)
    return builder.as_markup()
