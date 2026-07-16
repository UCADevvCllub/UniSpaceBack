from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import re

from ..keyboards.inline import get_lessons_submenu_kb, get_days_kb, get_reminder_toggle_kb, get_reminder_offsets_kb, get_edit_lessons_kb
from ..crud import get_user, get_lessons_for_day, get_weekly_lessons, add_reminder, delete_reminder, get_user_reminders, add_lesson, remove_lesson, add_all_lessons_reminders, delete_all_lessons_reminders

router = Router()

@router.message(F.text == "🗓 Lessons")
async def lessons_menu(message: Message):
    await message.answer("🗓 Lessons Menu:", reply_markup=get_lessons_submenu_kb())

@router.callback_query(F.data == "lessons_today")
async def show_today_lessons(callback: CallbackQuery):
    today = datetime.now().strftime("%A")
    user = await get_user(callback.from_user.id)
    if not user or not user.academic_level:
        await callback.answer("Please set your academic level first (/start)", show_alert=True)
        return

    lessons = await get_lessons_for_day(user.academic_level, today)
    reminders = await get_user_reminders(callback.from_user.id)

    if not lessons:
        await callback.message.edit_text(f"No lessons scheduled for today ({today}).")
        return

    text = f"📚 Today's Lessons ({today}):\n\n"
    for l in lessons:
        r = next((rem for rem in reminders if rem.reminder_type == "lesson" and rem.subject_name == l.subject_name and rem.day == l.day_of_week and rem.event_time_str == l.time_str), None)
        rem_text = f"⏰ {r.reminder_offset} min" if r else "⏰ No reminder"
        text += f"   • {l.time_str} - {l.subject_name} ({rem_text})\n"

    await callback.message.edit_text(text)

@router.callback_query(F.data == "lessons_weekly")
async def show_weekly_lessons(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.academic_level:
        await callback.answer("Please set your academic level first", show_alert=True)
        return

    lessons = await get_weekly_lessons(user.academic_level)
    reminders = await get_user_reminders(callback.from_user.id)

    if not lessons:
        await callback.message.edit_text("No weekly lessons found.")
        return

    grouped = {}
    for l in lessons:
        grouped.setdefault(l.day_of_week, []).append(l)

    text = "📅 Your Weekly Schedule:\n\n"
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for day in days_order:
        if day in grouped:
            text += f"📌 {day}:\n"
            for l in grouped[day]:
                r = next((rem for rem in reminders if rem.reminder_type == "lesson" and rem.subject_name == l.subject_name and rem.day == l.day_of_week and rem.event_time_str == l.time_str), None)
                rem_text = f"⏰ {r.reminder_offset} min" if r else "⏰ No reminder"
                text += f"   • {l.time_str} - {l.subject_name} ({rem_text})\n"
            text += "\n"

    await callback.message.edit_text(text)

@router.callback_query(F.data == "lessons_reminder")
async def select_reminder_day(callback: CallbackQuery):
    await callback.message.edit_text("Select a day:", reply_markup=get_days_kb("lr_day", include_all=True))

@router.callback_query(F.data.startswith("lr_day_"))
async def select_reminder_lesson(callback: CallbackQuery):
    day = callback.data.split("_")[2]
    user = await get_user(callback.from_user.id)
    if not user or not user.academic_level:
        return

    if day == "All":
        await callback.message.edit_text(
            "Do you want to turn reminders ON or OFF for all weekly lessons?",
            reply_markup=get_reminder_toggle_kb("lr_tog_All")
        )
        return

    lessons = await get_lessons_for_day(user.academic_level, day)

    if not lessons:
        await callback.message.edit_text(f"No lessons on {day}.")
        return

    builder = InlineKeyboardBuilder()
    for l in lessons:
        builder.button(text=f"{l.subject_name} ({l.time_str})", callback_data=f"lr_sel_{l.id}")
    builder.button(text="Back", callback_data="lessons_reminder")
    builder.adjust(1)

    await callback.message.edit_text(f"Select a lesson on {day}:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("lr_sel_"))
async def lesson_reminder_toggle(callback: CallbackQuery):
    lesson_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        "Do you want to turn the reminder ON or OFF?",
        reply_markup=get_reminder_toggle_kb(f"lr_tog_{lesson_id}")
    )

@router.callback_query(F.data.startswith("lr_tog_"))
async def process_reminder_toggle(callback: CallbackQuery):
    from asgiref.sync import sync_to_async
    from camphub.models import ClassEvent
    parts = callback.data.split("_")
    lesson_id_str = parts[2]
    action = parts[3]

    if lesson_id_str == "All":
        user = await get_user(callback.from_user.id)
        if not user or not user.academic_level:
            await callback.answer("Please set your academic level first.")
            return

        if action == "off":
            await delete_all_lessons_reminders(callback.from_user.id, user.academic_level)
            await callback.message.edit_text("Reminders for all weekly lessons turned OFF.")
        else:
            await callback.message.edit_text(
                "Select reminder timing for all lessons:",
                reply_markup=get_reminder_offsets_kb("lr_off_All")
            )
        return

    lesson_id = int(lesson_id_str)
    get_entry = sync_to_async(lambda: ClassEvent.objects.select_related('subject_id', 'cohort_id', 'event_id').get(id=lesson_id))
    try:
        entry = await get_entry()
    except ClassEvent.DoesNotExist:
        await callback.answer("Lesson not found.")
        return

    subject_name = entry.subject_id.name.title() if entry.subject_id else "Unknown"
    day_map = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"}
    day = day_map.get(entry.event_id.day, entry.event_id.day) if entry.event_id else "Monday"
    time_str = entry.event_id.start_time.strftime("%H:%M") if entry.event_id and entry.event_id.start_time else "09:00"

    if action == "off":
        await delete_reminder(callback.from_user.id, "lesson", subject_name, day, time_str)
        await callback.message.edit_text(f"Reminder for {subject_name} turned OFF.")
    else:
        await callback.message.edit_text(
            "Select reminder timing:",
            reply_markup=get_reminder_offsets_kb(f"lr_off_{lesson_id}")
        )

@router.callback_query(F.data.startswith("lr_off_"))
async def save_lesson_reminder(callback: CallbackQuery):
    from asgiref.sync import sync_to_async
    from camphub.models import ClassEvent
    parts = callback.data.split("_")
    lesson_id_str = parts[2]
    offset = int(parts[3])

    if lesson_id_str == "All":
        user = await get_user(callback.from_user.id)
        if not user or not user.academic_level:
            return
        await add_all_lessons_reminders(callback.from_user.id, user.academic_level, offset)
        await callback.message.edit_text(f"Reminders set for all weekly lessons {offset} minutes before start.")
        return

    lesson_id = int(lesson_id_str)
    get_entry = sync_to_async(lambda: ClassEvent.objects.select_related('subject_id', 'event_id').get(id=lesson_id))
    try:
        entry = await get_entry()
    except ClassEvent.DoesNotExist:
        return

    subject_name = entry.subject_id.name.title() if entry.subject_id else "Unknown"
    day_map = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"}
    day = day_map.get(entry.event_id.day, entry.event_id.day) if entry.event_id else "Monday"
    time_str = entry.event_id.start_time.strftime("%H:%M") if entry.event_id and entry.event_id.start_time else "09:00"


    await add_reminder(callback.from_user.id, "lesson", subject_name, day, time_str, offset)
    await callback.message.edit_text(f"Reminder set for {subject_name} {offset} minutes before start.")

class AddLessonStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_day = State()
    waiting_for_time = State()

@router.callback_query(F.data == "lessons_edit")
async def edit_lessons_menu(callback: CallbackQuery):
    await callback.message.edit_text("Edit Lessons:", reply_markup=get_edit_lessons_kb())

@router.callback_query(F.data == "lessons_menu_back")
async def back_to_lessons_menu(callback: CallbackQuery):
    await callback.message.edit_text("🗓 Lessons Menu:", reply_markup=get_lessons_submenu_kb())

@router.callback_query(F.data == "edit_lesson_add")
async def start_add_lesson(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddLessonStates.waiting_for_name)
    await callback.message.edit_text("📝 Add New Lesson\n\nPlease enter the course name:\n\nExample: Calculus 2")

@router.message(AddLessonStates.waiting_for_name)
async def process_lesson_name(message: Message, state: FSMContext):
    await state.update_data(course_name=message.text)
    await state.set_state(AddLessonStates.waiting_for_day)
    await message.answer(f"📚 Course: {message.text}\n\n📅 Select the day:", reply_markup=get_days_kb("add_lesson_day"))

@router.callback_query(AddLessonStates.waiting_for_day, F.data.startswith("add_lesson_day_"))
async def process_lesson_day(callback: CallbackQuery, state: FSMContext):
    day = callback.data.split("_")[3]
    await state.update_data(day=day)
    data = await state.get_data()
    course_name = data.get("course_name")
    await state.set_state(AddLessonStates.waiting_for_time)
    await callback.message.edit_text(f"📚 Course: {course_name}\n📅 Day: {day}\n\n🕐 Enter the time:\n\nFormat: ##:##\nExample: 09:30 or 14:00")

@router.message(AddLessonStates.waiting_for_time)
async def process_lesson_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
        await message.answer("Invalid format. Please enter time in HH:MM format (e.g. 09:30 or 14:00):")
        return

    data = await state.get_data()
    course_name = data.get("course_name")
    day = data.get("day")

    user = await get_user(message.from_user.id)
    if not user or not user.academic_level:
        await message.answer("You must set your academic level first.")
        await state.clear()
        return

    await add_lesson(user.academic_level, day, time_str, course_name)
    await state.clear()
    await message.answer(f"✅ Lesson Added:\n\n📚 Course: {course_name}\n📅 Day: {day}\n🕐 Time: {time_str}")

@router.callback_query(F.data == "edit_lesson_remove")
async def start_remove_lesson(callback: CallbackQuery):
    await callback.message.edit_text("Select a day to remove a lesson from:", reply_markup=get_days_kb("rm_lesson_day"))

@router.callback_query(F.data.startswith("rm_lesson_day_"))
async def process_remove_lesson_day(callback: CallbackQuery):
    day = callback.data.split("_")[3]
    user = await get_user(callback.from_user.id)
    if not user or not user.academic_level:
        return
    lessons = await get_lessons_for_day(user.academic_level, day)

    if not lessons:
        await callback.message.edit_text(f"No lessons found on {day}.")
        return

    builder = InlineKeyboardBuilder()
    for l in lessons:
        builder.button(text=f"❌ {l.subject_name} ({l.time_str})", callback_data=f"rm_lesson_sel_{l.id}")
    builder.button(text="Back", callback_data="lessons_edit")
    builder.adjust(1)

    await callback.message.edit_text(f"Select a lesson to remove on {day}:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("rm_lesson_sel_"))
async def process_remove_lesson_selection(callback: CallbackQuery):
    lesson_id = int(callback.data.split("_")[3])
    await remove_lesson(lesson_id)
    await callback.message.edit_text("✅ Lesson Removed.")
