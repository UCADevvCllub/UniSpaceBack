from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from ..keyboards.inline import get_lessons_submenu_kb, get_days_kb, get_reminder_toggle_kb, get_reminder_offsets_kb
from ..crud import (
    get_user, get_lessons_for_day, get_weekly_lessons, add_reminder,
    delete_reminder, get_user_reminders, add_all_lessons_reminders,
    delete_all_lessons_reminders, needs_freshman_prefs,
)
from ..format import header, card, compose, empty, menu, profile_meta, day_label
from ..keyboards.inline import get_freshman_group_kb

router = Router()


def _lesson_kwargs(user):
    return dict(
        major=getattr(user, "major", None),
        cs_group=getattr(user, "cs_group", None),
        cs_track=getattr(user, "cs_track", None),
    )


async def _require_freshman_prefs(callback, user) -> bool:
    """If Freshman CS prefs missing, prompt and return True (caller should stop)."""
    if not needs_freshman_prefs(user):
        return False
    await callback.message.edit_text(
        header(
            "👥",
            "Choose your Freshman schedule",
            "Group (CS A / CS B) and Track (Direct / Post Prep) are required.",
            "Select your group first:",
        ),
        reply_markup=get_freshman_group_kb(),
        parse_mode="HTML",
    )
    await callback.answer()
    return True


def _lesson_reminder_status(lesson, reminders):
    r = next(
        (
            rem for rem in reminders
            if rem.reminder_type == "lesson"
            and rem.subject_name == lesson.subject_name
            and rem.day == lesson.day_of_week
            and rem.event_time_str == lesson.start_time_str
        ),
        None,
    )
    return f"⏰ {r.reminder_offset} min before" if r else None


def _lesson_cards(lessons, reminders) -> list:
    return [
        card(l.time_str, l.subject_name, status=_lesson_reminder_status(l, reminders))
        for l in lessons
    ]


@router.message(F.text == "🗓 Lessons")
async def lessons_menu(message: Message):
    await message.answer(
        menu("📚", "Lessons"),
        reply_markup=get_lessons_submenu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "lessons_today")
async def show_today_lessons(callback: CallbackQuery):
    today = datetime.now().strftime("%A")
    user = await get_user(callback.from_user.id)
    if not user or not user.academic_level:
        await callback.answer("Please set your academic level first (/start)", show_alert=True)
        return
    if await _require_freshman_prefs(callback, user):
        return

    lessons = await get_lessons_for_day(
        user.academic_level, today, **_lesson_kwargs(user)
    )
    reminders = await get_user_reminders(callback.from_user.id)

    hdr = header("📚", "Today's Lessons", profile_meta(user), f"📅 {today}")
    if not lessons:
        text = compose(hdr, empty("🎉 Free day — no lessons scheduled."))
    else:
        text = compose(hdr, *_lesson_cards(lessons, reminders))

    await callback.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "lessons_weekly")
async def show_weekly_lessons(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.academic_level:
        await callback.answer("Please set your academic level first", show_alert=True)
        return
    if await _require_freshman_prefs(callback, user):
        return

    lessons = await get_weekly_lessons(
        user.academic_level, **_lesson_kwargs(user)
    )
    reminders = await get_user_reminders(callback.from_user.id)

    hdr = header("📅", "Weekly Schedule", profile_meta(user))
    if not lessons:
        await callback.message.edit_text(
            compose(hdr, empty("No weekly lessons found.")),
            parse_mode="HTML",
        )
        return

    grouped = {}
    for l in lessons:
        grouped.setdefault(l.day_of_week, []).append(l)

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    parts = []
    for day in days_order:
        if day not in grouped:
            continue
        parts.append(day_label(day))
        parts.extend(_lesson_cards(grouped[day], reminders))

    await callback.message.edit_text(compose(hdr, *parts), parse_mode="HTML")


@router.callback_query(F.data == "lessons_reminder")
async def select_reminder_day(callback: CallbackQuery):
    await callback.message.edit_text(
        header("⏰", "Lesson Reminders", "Select a day:"),
        reply_markup=get_days_kb("lr_day", include_all=True),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("lr_day_"))
async def select_reminder_lesson(callback: CallbackQuery):
    day = callback.data.split("_")[2]
    user = await get_user(callback.from_user.id)
    if not user or not user.academic_level:
        return
    if await _require_freshman_prefs(callback, user):
        return

    if day == "All":
        await callback.message.edit_text(
            header("⏰", "All Lessons", "Turn reminders ON or OFF for the whole week:"),
            reply_markup=get_reminder_toggle_kb("lr_tog_All"),
            parse_mode="HTML",
        )
        return

    lessons = await get_lessons_for_day(
        user.academic_level, day, **_lesson_kwargs(user)
    )

    if not lessons:
        await callback.message.edit_text(
            compose(header("⏰", day), empty(f"No lessons on {day}.")),
            parse_mode="HTML",
        )
        return

    builder = InlineKeyboardBuilder()
    for l in lessons:
        builder.button(text=f"{l.subject_name} ({l.time_str})", callback_data=f"lr_sel_{l.id}")
    builder.button(text="« Back", callback_data="lessons_reminder")
    builder.adjust(1)

    await callback.message.edit_text(
        header("⏰", f"Reminders · {day}", "Select a lesson:"),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("lr_sel_"))
async def lesson_reminder_toggle(callback: CallbackQuery):
    lesson_id = int(callback.data.split("_")[2])
    await callback.message.edit_text(
        header("⏰", "Reminder", "Turn this reminder ON or OFF:"),
        reply_markup=get_reminder_toggle_kb(f"lr_tog_{lesson_id}"),
        parse_mode="HTML",
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
            await delete_all_lessons_reminders(
                callback.from_user.id, user.academic_level, **_lesson_kwargs(user)
            )
            await callback.message.edit_text(
                header("⏰", "Reminders Off", "All weekly lesson reminders turned off."),
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                header("⏰", "All Lessons", "Select reminder timing:"),
                reply_markup=get_reminder_offsets_kb("lr_off_All"),
                parse_mode="HTML",
            )
        return

    lesson_id = int(lesson_id_str)
    get_entry = sync_to_async(
        lambda: ClassEvent.objects.select_related("subject_id", "cohort_id", "event_id").get(id=lesson_id)
    )
    try:
        entry = await get_entry()
    except ClassEvent.DoesNotExist:
        await callback.answer("Lesson not found.")
        return

    subject_name = entry.subject_id.name.title() if entry.subject_id else "Unknown"
    day_map = {
        "MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday",
        "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday",
    }
    day = day_map.get(entry.event_id.day, entry.event_id.day) if entry.event_id else "Monday"
    time_str = (
        entry.event_id.start_time.strftime("%H:%M")
        if entry.event_id and entry.event_id.start_time
        else "09:00"
    )

    event_pk = entry.event_id.id if entry.event_id else None

    if action == "off":
        await delete_reminder(
            callback.from_user.id, "lesson", subject_name, day, time_str, event_id=event_pk
        )
        await callback.message.edit_text(
            header("⏰", "Reminder Off", f"{subject_name} — reminder turned off."),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            header("⏰", subject_name, "Select reminder timing:"),
            reply_markup=get_reminder_offsets_kb(f"lr_off_{lesson_id}"),
            parse_mode="HTML",
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
        if await _require_freshman_prefs(callback, user):
            return
        count = await add_all_lessons_reminders(
            callback.from_user.id, user.academic_level, offset, **_lesson_kwargs(user)
        )
        await callback.message.edit_text(
            header(
                "⏰",
                "Reminders Set",
                f"{count} weekly lesson(s) — {offset} min before.",
            ),
            parse_mode="HTML",
        )
        return

    lesson_id = int(lesson_id_str)
    get_entry = sync_to_async(
        lambda: ClassEvent.objects.select_related("subject_id", "event_id").get(id=lesson_id)
    )
    try:
        entry = await get_entry()
    except ClassEvent.DoesNotExist:
        return

    subject_name = entry.subject_id.name.title() if entry.subject_id else "Unknown"
    day_map = {
        "MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday",
        "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday",
    }
    day = day_map.get(entry.event_id.day, entry.event_id.day) if entry.event_id else "Monday"
    time_str = (
        entry.event_id.start_time.strftime("%H:%M")
        if entry.event_id and entry.event_id.start_time
        else "09:00"
    )
    event_pk = entry.event_id.id if entry.event_id else None

    saved = await add_reminder(
        callback.from_user.id, "lesson", subject_name, day, time_str, offset, event_id=event_pk
    )
    if not saved:
        await callback.message.edit_text(
            header("⏰", "Reminder Failed", f"Could not find the event for {subject_name}."),
            parse_mode="HTML",
        )
        return
    await callback.message.edit_text(
        header("⏰", "Reminder Set", f"{subject_name} — {offset} min before."),
        parse_mode="HTML",
    )
