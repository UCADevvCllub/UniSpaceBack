from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..keyboards.inline import (
    get_academic_level_kb, get_major_kb,
    get_freshman_group_kb, get_freshman_track_kb,
)
from ..keyboards.reply import get_main_menu
from ..crud import (
    get_user, update_user_level, update_user_gender, update_user_major,
    update_user_freshman_prefs, is_freshman_cs, needs_freshman_prefs,
    CS_GROUP_LABELS, CS_TRACK_LABELS,
)
from ..format import header, info_card, compose, major_label

router = Router()


class SettingsState(StatesGroup):
    waiting_for_gender = State()


@router.message(F.text == "⚙️ Settings")
async def settings_menu(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Please register first by sending /start")
        return

    gender = getattr(user, "gender", None) or "Not set"
    level = getattr(user, "academic_level", None) or "Not set"
    raw_major = getattr(user, "major", None)

    gender_display = gender.capitalize() if gender and gender != "Not set" else "Not set"
    major_display = major_label(raw_major) if raw_major else "Not set"

    cards = [
        info_card("👤 Gender", gender_display),
        info_card("🎓 Academic Level", level),
        info_card("📚 Major", major_display),
    ]

    builder = InlineKeyboardBuilder()
    builder.button(text="🎓 Change Academic Level", callback_data="settings_level")
    builder.button(text="📚 Change Major", callback_data="settings_major")
    builder.button(text="👤 Change Gender", callback_data="settings_gender")

    if is_freshman_cs(level, raw_major):
        group_label = CS_GROUP_LABELS.get(getattr(user, "cs_group", None), "Not set")
        track_label = CS_TRACK_LABELS.get(getattr(user, "cs_track", None), "Not set")
        cards.append(info_card("👥 Group", group_label))
        cards.append(info_card("🛤 Track", track_label))
        builder.button(text="👥 Change Group", callback_data="settings_group")
        builder.button(text="🛤 Change Track", callback_data="settings_track")

    builder.adjust(1)

    await message.answer(
        compose(header("⚙️", "Settings", "Your profile"), *cards),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "settings_level")
async def change_level(callback: CallbackQuery):
    await callback.message.edit_text(
        header("🎓", "Academic Level", "Select your new level:"),
        reply_markup=get_academic_level_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "settings_major")
async def change_major(callback: CallbackQuery):
    await callback.message.edit_text(
        header("📚", "Major", "Select your new major:"),
        reply_markup=get_major_kb(prefix="settings_set_major_"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("settings_set_major_"))
async def save_major(callback: CallbackQuery, state: FSMContext):
    major = callback.data.split("_")[3]  # "CS" or "CM"
    major_name = major_label(major)

    await update_user_major(callback.from_user.id, major)
    check = await get_user(callback.from_user.id)

    await callback.message.edit_text(
        header("✅", "Major Updated", major_name),
        parse_mode="HTML",
    )

    if needs_freshman_prefs(check):
        await callback.message.answer(
            header("👥", "Freshman Group", "Select your group (CS A or CS B):"),
            reply_markup=get_freshman_group_kb(prefix="settings_fgroup_"),
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            "Settings saved. Use the menu below to continue.",
            reply_markup=get_main_menu(),
        )


@router.callback_query(F.data == "settings_group")
async def change_group(callback: CallbackQuery):
    await callback.message.edit_text(
        header("👥", "Freshman Group", "Select your group:"),
        reply_markup=get_freshman_group_kb(prefix="settings_fgroup_"),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "settings_track")
async def change_track(callback: CallbackQuery):
    await callback.message.edit_text(
        header("🛤", "Freshman Track", "Select your track:"),
        reply_markup=get_freshman_track_kb(prefix="settings_ftrack_"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("settings_fgroup_"))
async def save_group(callback: CallbackQuery):
    group = callback.data[len("settings_fgroup_"):]
    if group not in CS_GROUP_LABELS:
        await callback.answer("Invalid group")
        return

    await update_user_freshman_prefs(callback.from_user.id, cs_group=group)
    check = await get_user(callback.from_user.id)

    if needs_freshman_prefs(check):
        await callback.message.edit_text(
            header(
                "🛤",
                "Freshman Track",
                f"Group: {CS_GROUP_LABELS[group]}",
                "Now select your track:",
            ),
            reply_markup=get_freshman_track_kb(prefix="settings_ftrack_"),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            header("✅", "Group Updated", CS_GROUP_LABELS[group]),
            parse_mode="HTML",
        )
        await callback.message.answer(
            "Settings saved. Use the menu below to continue.",
            reply_markup=get_main_menu(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("settings_ftrack_"))
async def save_track(callback: CallbackQuery):
    track = callback.data[len("settings_ftrack_"):]
    if track not in CS_TRACK_LABELS:
        await callback.answer("Invalid track")
        return

    await update_user_freshman_prefs(callback.from_user.id, cs_track=track)
    await callback.message.edit_text(
        header("✅", "Track Updated", CS_TRACK_LABELS[track]),
        parse_mode="HTML",
    )
    await callback.message.answer(
        "Settings saved. Use the menu below to continue.",
        reply_markup=get_main_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "settings_gender")
async def change_gender(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_gender)

    builder = InlineKeyboardBuilder()
    builder.button(text="Male", callback_data="settings_set_gender_Male")
    builder.button(text="Female", callback_data="settings_set_gender_Female")
    builder.adjust(2)

    await callback.message.edit_text(
        header("👤", "Gender", "Select your gender:"),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("settings_set_gender_"))
async def save_gender(callback: CallbackQuery, state: FSMContext):
    gender = callback.data.split("_")[3]  # "Male" or "Female"

    await update_user_gender(callback.from_user.id, gender)
    await state.clear()

    await callback.message.edit_text(
        header("✅", "Gender Updated", gender),
        parse_mode="HTML",
    )
    await callback.message.answer(
        "Settings saved. Use the menu below to continue.",
        reply_markup=get_main_menu(),
    )
