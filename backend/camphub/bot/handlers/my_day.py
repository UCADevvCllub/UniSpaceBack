from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime

from ..crud import get_user, get_lessons_for_day, get_tv_bookings, get_user_reminders

router = Router()

@router.message(F.text == "📅 My Day")
async def my_day_summary(message: Message):
    today_name = datetime.now().strftime("%A")
    today_date_str = datetime.now().strftime("%d.%m")

    user = await get_user(message.from_user.id)
    if not user or not user.academic_level:
        await message.answer("Please set your academic level first (/start)")
        return

    lessons = await get_lessons_for_day(user.academic_level, today_name, major=getattr(user, 'major', None))
    reminders = await get_user_reminders(message.from_user.id)
    tv_bookings = await get_tv_bookings(message.from_user.id)

    today_tv_bookings = [b for b in tv_bookings if b.booking_date == today_date_str]

    text = (
        f"📅 **My Day Overview ({today_name}, {today_date_str})**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    text += "📚 **Today's Lessons:**\n"
    if lessons:
        for l in lessons:
            has_rem = any(
                r.reminder_type == "lesson" and
                r.subject_name == l.subject_name and
                r.day == today_name and
                r.event_time_str == l.time_str
                for r in reminders
            )
            rem_suffix = " ⏰" if has_rem else ""
            text += f"   • {l.time_str} - {l.subject_name}{rem_suffix}\n"
    else:
        text += "   • No lessons scheduled for today.\n"
    text += "\n"

    today_sports_reminders = [r for r in reminders if r.day == today_name and r.reminder_type in ["gym", "bubble"]]
    text += "🏋️ **Sports & Gym Reminders:**\n"
    if today_sports_reminders:
        for r in today_sports_reminders:
            icon = "🏋️" if r.reminder_type == "gym" else "🏀"
            text += f"   • {icon} {r.event_time_str} - {r.subject_name}\n"
    else:
        text += "   • No sports sessions scheduled for today.\n"
    text += "\n"

    text += "📺 **Today's TV Lounge Bookings:**\n"
    if today_tv_bookings:
        for b in today_tv_bookings:
            text += f"   • {b.booking_time} - Lounge {b.lounge_name} (Booker: {b.booker_name})\n"
    else:
        text += "   • You booked nothing for today.\n"

    await message.answer(text, parse_mode="Markdown")
