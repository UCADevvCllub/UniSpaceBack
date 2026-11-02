import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from ..crud import get_all_reminders
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def check_reminders(bot: Bot):
    now = datetime.now()
    current_day = now.strftime("%A")
    current_date = now.strftime("%d.%m")

    logger.info(f"Checking reminders at {now.strftime('%H:%M')} on {current_day} ({current_date})")

    reminders = await get_all_reminders()

    if not reminders:
        logger.info("No reminders found in database.")
        return

    logger.info(f"Found {len(reminders)} total reminder(s) in database.")

    for r in reminders:
        # TV Lounges is disabled ("coming soon") — never send TV reminders.
        if r.reminder_type == "tv":
            continue

        # Weekday-based reminders (lessons, gym, bubble, meals)
        if r.reminder_type in ["lesson", "gym", "bubble", "meal"]:
            if r.day != current_day:
                continue
        elif r.reminder_type == "unknown":
            continue

        try:
            if not r.event_time_str:
                continue
            event_time = datetime.strptime(r.event_time_str, "%H:%M").time()
            event_datetime = datetime.combine(now.date(), event_time)
            trigger_time = event_datetime - timedelta(minutes=r.reminder_offset)

            logger.info(
                f"  Reminder [{r.reminder_type}] '{r.subject_name}' on {r.day}: "
                f"event at {r.event_time_str}, trigger at {trigger_time.strftime('%H:%M')}, "
                f"now is {now.strftime('%H:%M')}"
            )

            if trigger_time.hour == now.hour and trigger_time.minute == now.minute:
                if r.reminder_type == "lesson":
                    msg = (
                        f"📚 <b>Lesson Reminder!</b>\n\n"
                        f"📖 <b>{r.subject_name}</b> starts in <b>{r.reminder_offset} minutes</b>!\n"
                        f"⏰ Class time: {r.event_time_str}\n\n"
                        f"Get ready! 🎒"
                    )
                elif r.reminder_type == "gym":
                    msg = (
                        f"🏋️ <b>Gym Reminder!</b>\n\n"
                        f"💪 <b>{r.subject_name}</b> session starts in <b>{r.reminder_offset} minutes</b>!\n"
                        f"⏰ Session time: {r.event_time_str}\n\n"
                        f"Time to work out! 🔥"
                    )
                elif r.reminder_type == "bubble":
                    msg = (
                        f"🏀 <b>Sports Bubble Reminder!</b>\n\n"
                        f"⚽ <b>{r.subject_name}</b> starts in <b>{r.reminder_offset} minutes</b>!\n"
                        f"⏰ Session time: {r.event_time_str}\n\n"
                        f"Get your gear ready! 🏃"
                    )
                elif r.reminder_type == "meal":
                    msg = (
                        f"🍽 <b>Meal Reminder!</b>\n\n"
                        f"🥣 <b>{r.subject_name}</b> starts in <b>{r.reminder_offset} minutes</b>!\n"
                        f"⏰ Time: {r.event_time_str}\n\n"
                        f"Don't miss it! 😋"
                    )
                else:
                    continue

                if not r.telegram_user_id:
                    logger.warning(f"  Reminder {r.id} has no telegram_user_id — skip")
                    continue

                logger.info(f"  >>> SENDING reminder to user {r.telegram_user_id}: {r.subject_name}")
                await bot.send_message(r.telegram_user_id, msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error processing reminder {r.id}: {e}")

def setup_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_reminders, 'cron', minute='*', args=[bot])
    scheduler.start()
    return scheduler
