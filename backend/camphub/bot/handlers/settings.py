from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..keyboards.inline import get_academic_level_kb, get_major_kb
from ..keyboards.reply import get_main_menu
from ..crud import get_user, update_user_level, update_user_gender, update_user_major

router = Router()

class SettingsState(StatesGroup):
    waiting_for_gender = State()


@router.message(F.text == "⚙️ Settings")
async def settings_menu(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Please register first by sending /start")
        return

    gender = getattr(user, 'gender', None) or "Not set"
    level = getattr(user, 'academic_level', None) or "Not set"
    raw_major = getattr(user, 'major', None) or "Not set"

    # Display gender in readable format
    gender_display = gender.capitalize() if gender and gender != "Not set" else "Not set"
    
    # Display major in readable format
    if raw_major == "CS":
        major_display = "Computer Science (CS)"
    elif raw_major == "CM":
        major_display = "Communications & Media (CM)"
    else:
        major_display = "Not set"

    builder = InlineKeyboardBuilder()
    builder.button(text="🎓 Change Academic Level", callback_data="settings_level")
    builder.button(text="📚 Change Major", callback_data="settings_major")
    builder.button(text="👤 Change Gender", callback_data="settings_gender")
    builder.adjust(1)

    await message.answer(
        f"⚙️ <b>Settings</b>\n\n"
        f"👤 <b>Gender:</b> {gender_display}\n"
        f"🎓 <b>Academic Level:</b> {level}\n"
        f"📚 <b>Major:</b> {major_display}\n\n"
        f"What would you like to change?",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "settings_level")
async def change_level(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎓 Select your new academic level:",
        reply_markup=get_academic_level_kb()
    )


@router.callback_query(F.data == "settings_major")
async def change_major(callback: CallbackQuery):
    await callback.message.edit_text(
        "📚 Select your new major:",
        reply_markup=get_major_kb(prefix="settings_set_major_")
    )


@router.callback_query(F.data.startswith("settings_set_major_"))
async def save_major(callback: CallbackQuery):
    major = callback.data.split("_")[3]  # "CS" or "CM"
    major_name = "Computer Science (CS)" if major == "CS" else "Communications & Media (CM)"

    await update_user_major(callback.from_user.id, major)

    await callback.message.edit_text(
        f"✅ Major updated to: <b>{major_name}</b>",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Settings saved! Use the menu below to continue.",
        reply_markup=get_main_menu()
    )


@router.callback_query(F.data == "settings_gender")
async def change_gender(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_gender)

    builder = InlineKeyboardBuilder()
    builder.button(text="Male", callback_data="settings_set_gender_Male")
    builder.button(text="Female", callback_data="settings_set_gender_Female")
    builder.adjust(2)

    await callback.message.edit_text(
        "👤 Select your gender:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("settings_set_gender_"))
async def save_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[3]  # "Male" or "Female"

    await update_user_gender(callback.from_user.id, gender)
    await state.clear()

    await callback.message.edit_text(
        f"✅ Gender updated to: <b>{gender}</b>",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Settings saved! Use the menu below to continue.",
        reply_markup=get_main_menu()
    )
