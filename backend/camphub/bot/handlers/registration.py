from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ..keyboards.inline import (
    get_academic_level_kb, get_major_kb,
    get_freshman_group_kb, get_freshman_track_kb,
)
from ..keyboards.reply import get_main_menu
from ..crud import (
    get_user, create_user, update_user_level, update_user_major,
    update_user_freshman_prefs, is_freshman_cs, needs_freshman_prefs,
    CS_GROUP_LABELS, CS_TRACK_LABELS,
)
from ..format import header

router = Router()


class RegistrationState(StatesGroup):
    waiting_for_gender = State()
    waiting_for_level = State()
    waiting_for_major = State()
    waiting_for_group = State()
    waiting_for_track = State()


async def _finish_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    gender = data.get("gender", "Male")
    level = data.get("level", "Freshman")
    major = data.get("major", "CS")
    cs_group = data.get("cs_group")
    cs_track = data.get("cs_track")

    await create_user(
        telegram_id=callback.from_user.id,
        name=callback.from_user.full_name or "Student",
        gender=gender,
        cohort_name=level,
        major=major,
        cs_group=cs_group,
        cs_track=cs_track,
    )
    await state.clear()

    major_name = "Computer Science (CS)" if major == "CS" else "Communications and Media (CM)"
    lines = [
        f"👤 <b>Gender:</b> {gender}",
        f"🎓 <b>Academic Level:</b> {level}",
        f"📚 <b>Major:</b> {major_name}",
    ]
    if cs_group and cs_track:
        lines.append(f"👥 <b>Group:</b> {CS_GROUP_LABELS.get(cs_group, cs_group)}")
        lines.append(f"🛤 <b>Track:</b> {CS_TRACK_LABELS.get(cs_track, cs_track)}")

    await callback.message.edit_text(
        "✅ <b>Registration complete!</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )
    await callback.message.answer(
        "Here is your MAIN MENU. Use the buttons below to navigate.",
        reply_markup=get_main_menu(),
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if user:
        name = message.from_user.first_name or "Student"
        await message.answer(
            header("🌟", f"Welcome back, {name}!", "Use the menu below to navigate."),
            reply_markup=get_main_menu(),
            parse_mode="HTML",
        )
        if needs_freshman_prefs(user):
            await state.set_state(RegistrationState.waiting_for_group)
            await message.answer(
                header("👥", "Freshman Group", "Select your group (CS A or CS B):"),
                reply_markup=get_freshman_group_kb(),
                parse_mode="HTML",
            )
    else:
        await state.set_state(RegistrationState.waiting_for_gender)
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Male"), KeyboardButton(text="Female")]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await message.answer(
            header(
                "🌟",
                "UCA Campus Assistant",
                "I'll help you navigate campus life.",
                "First, select your gender:",
            ),
            reply_markup=kb,
            parse_mode="HTML",
        )


@router.message(RegistrationState.waiting_for_gender)
async def process_gender(message: Message, state: FSMContext):
    gender_text = message.text.strip()
    if gender_text not in ["Male", "Female"]:
        await message.answer("Please use the buttons provided to select your gender (Male/Female).")
        return

    await state.update_data(gender=gender_text)
    await state.set_state(RegistrationState.waiting_for_level)

    await message.answer("Gender recorded! ✅", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "Now, please select your current academic level below: 👇",
        reply_markup=get_academic_level_kb(),
    )


@router.callback_query(F.data.startswith("level_"))
async def process_level_selection(callback: CallbackQuery, state: FSMContext):
    level = callback.data.split("_")[1]
    current_state = await state.get_state()

    if current_state == RegistrationState.waiting_for_level.state:
        await state.update_data(level=level)
        await state.set_state(RegistrationState.waiting_for_major)
        await callback.message.edit_text(
            f"Academic level set to: <b>{level}</b> ✅\n\n"
            "Finally, please select your major below: 👇",
            reply_markup=get_major_kb(),
            parse_mode="HTML",
        )
    else:
        await update_user_level(callback.from_user.id, level)
        check = await get_user(callback.from_user.id)
        if not check or getattr(check, "academic_level", None) != level:
            await callback.message.edit_text(
                "❌ Sorry, your academic level could not be saved. "
                "Please make sure your major is set (Settings → Change Major), then try again."
            )
            await callback.answer()
            return

        await callback.message.edit_text(f"🎓 Academic level updated to: {level}")
        if is_freshman_cs(level, getattr(check, "major", None)) and needs_freshman_prefs(check):
            await state.set_state(RegistrationState.waiting_for_group)
            await callback.message.answer(
                header("👥", "Freshman Group", "Select your group (CS A or CS B):"),
                reply_markup=get_freshman_group_kb(),
                parse_mode="HTML",
            )
        else:
            await callback.message.answer(
                "Here is your MAIN MENU. Use the buttons below to navigate.",
                reply_markup=get_main_menu(),
            )
    await callback.answer()


@router.callback_query(F.data.startswith("major_"))
async def process_major_selection(callback: CallbackQuery, state: FSMContext):
    # Ignore settings_set_major_ which also starts with major_ if we're not careful —
    # settings uses prefix settings_set_major_, so split carefully.
    if callback.data.startswith("settings_"):
        return

    major = callback.data.split("_")[1]  # "CS" or "CM"
    current_state = await state.get_state()
    major_name = "Computer Science (CS)" if major == "CS" else "Communications and Media (CM)"

    if current_state == RegistrationState.waiting_for_major.state:
        await state.update_data(major=major)
        data = await state.get_data()
        level = data.get("level", "Freshman")

        if is_freshman_cs(level, major):
            await state.set_state(RegistrationState.waiting_for_group)
            await callback.message.edit_text(
                header("👥", "Freshman Group", "Select your group:"),
                reply_markup=get_freshman_group_kb(),
                parse_mode="HTML",
            )
        else:
            await _finish_registration(callback, state)
    else:
        await update_user_major(callback.from_user.id, major)
        check = await get_user(callback.from_user.id)
        await callback.message.edit_text(
            f"📚 Major updated to: <b>{major_name}</b>", parse_mode="HTML"
        )
        if needs_freshman_prefs(check):
            await state.set_state(RegistrationState.waiting_for_group)
            await callback.message.answer(
                header("👥", "Freshman Group", "Select your group (CS A or CS B):"),
                reply_markup=get_freshman_group_kb(),
                parse_mode="HTML",
            )
        else:
            await callback.message.answer(
                "Here is your MAIN MENU. Use the buttons below to navigate.",
                reply_markup=get_main_menu(),
            )
    await callback.answer()


@router.callback_query(F.data.startswith("fgroup_"))
async def process_group_selection(callback: CallbackQuery, state: FSMContext):
    group = callback.data[len("fgroup_"):]  # CS_A or CS_B
    if group not in CS_GROUP_LABELS:
        await callback.answer("Invalid group")
        return

    current_state = await state.get_state()
    await state.update_data(cs_group=group)

    # Existing user updating prefs (not mid-registration create)
    user = await get_user(callback.from_user.id)
    if user and current_state != RegistrationState.waiting_for_group.state:
        # Settings-style update handled in settings handler; still allow continue to track
        pass

    if current_state == RegistrationState.waiting_for_group.state:
        await state.set_state(RegistrationState.waiting_for_track)
        await callback.message.edit_text(
            header(
                "🛤",
                "Freshman Track",
                f"Group: {CS_GROUP_LABELS[group]}",
                "Now select your track:",
            ),
            reply_markup=get_freshman_track_kb(),
            parse_mode="HTML",
        )
    else:
        # Fallback: treat as prefs update then ask track
        await update_user_freshman_prefs(callback.from_user.id, cs_group=group)
        await state.set_state(RegistrationState.waiting_for_track)
        await callback.message.edit_text(
            header(
                "🛤",
                "Freshman Track",
                f"Group: {CS_GROUP_LABELS[group]}",
                "Now select your track:",
            ),
            reply_markup=get_freshman_track_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("ftrack_"))
async def process_track_selection(callback: CallbackQuery, state: FSMContext):
    track = callback.data[len("ftrack_"):]  # CS_DIRECT or POST_PREP
    if track not in CS_TRACK_LABELS:
        await callback.answer("Invalid track")
        return

    current_state = await state.get_state()
    await state.update_data(cs_track=track)
    data = await state.get_data()
    group = data.get("cs_group")

    user = await get_user(callback.from_user.id)
    if user is None and current_state == RegistrationState.waiting_for_track.state:
        await _finish_registration(callback, state)
    else:
        # Existing user — save prefs
        await update_user_freshman_prefs(
            callback.from_user.id, cs_group=group, cs_track=track
        )
        await state.clear()
        await callback.message.edit_text(
            header(
                "✅",
                "Freshman schedule set",
                f"Group: {CS_GROUP_LABELS.get(group, group)}",
                f"Track: {CS_TRACK_LABELS.get(track, track)}",
            ),
            parse_mode="HTML",
        )
        await callback.message.answer(
            "Here is your MAIN MENU. Use the buttons below to navigate.",
            reply_markup=get_main_menu(),
        )
    await callback.answer()
