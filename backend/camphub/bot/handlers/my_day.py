from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime

from ..crud import get_user, get_lessons_for_day, get_user_reminders, needs_freshman_prefs
from ..format import header, card, compose, empty, section, profile_meta
from ..keyboards.inline import get_freshman_group_kb

router = Router()


@router.message(F.text == "📅 My Day")
async def my_day_summary(message: Message):
    today_name = datetime.now().strftime("%A")
    today_date_str = datetime.now().strftime("%d.%m")

    user = await get_user(message.from_user.id)
    if not user or not user.academic_level:
        await message.answer("Please set your academic level first (/start)")
        return

    if needs_freshman_prefs(user):
        await message.answer(
            header(
                "👥",
                "Choose your Freshman schedule",
                "Group (CS A / CS B) and Track (Direct / Post Prep) are required.",
                "Select your group first:",
            ),
            reply_markup=get_freshman_group_kb(),
            parse_mode="HTML",
        )
        return

    lessons = await get_lessons_for_day(
        user.academic_level,
        today_name,
        major=getattr(user, "major", None),
        cs_group=getattr(user, "cs_group", None),
        cs_track=getattr(user, "cs_track", None),
    )
    reminders = await get_user_reminders(message.from_user.id)

    hdr = header(
        "📅",
        "My Day",
        profile_meta(user),
        f"📅 {today_name}, {today_date_str}",
    )

    parts = [section("📚", "Lessons")]
    if lessons:
        for l in lessons:
            has_rem = any(
                r.reminder_type == "lesson"
                and r.subject_name == l.subject_name
                and r.day == today_name
                and r.event_time_str == l.start_time_str
                for r in reminders
            )
            parts.append(
                card(
                    l.time_str,
                    l.subject_name,
                    status="⏰ Reminder on" if has_rem else None,
                )
            )
    else:
        parts.append(empty("🎉 Free day — no lessons."))

    today_sports = [
        r for r in reminders
        if r.day == today_name and r.reminder_type in ["gym", "bubble"]
    ]
    parts.append(section("🏋️", "Sports & Gym"))
    if today_sports:
        for r in today_sports:
            icon = "🏋️" if r.reminder_type == "gym" else "🏀"
            parts.append(card(r.event_time_str, f"{icon} {r.subject_name}"))
    else:
        parts.append(empty("No sports reminders for today."))

    await message.answer(compose(hdr, *parts), parse_mode="HTML")
