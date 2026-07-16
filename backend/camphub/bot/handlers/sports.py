from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from ..keyboards.inline import (
    get_sports_submenu_kb, get_days_kb, get_reminder_toggle_kb,
    get_reminder_offsets_kb, get_gym_options_kb, get_bubble_options_kb
)
from ..crud import (
    get_gym_slots_for_day, get_bubble_sports_for_day,
    get_all_gym_slots, get_all_bubble_sports,
    add_reminder, delete_reminder,
)

router = Router()

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SESSION_EMOJI = {
    "Female": "🟣",
    "Male": "🔵",
    "Faculty / Ops": "🟢",
    "Faculty": "🟢",
    "Cleaning": "🔴",
}

BUBBLE_EMOJI = {
    "Cleaning & Disinfection": "🧹",
    "Mchs": "🏫",
    "Physical Education": "🏃",
    "Uca Security": "👮",
    "Cricket": "🏏",
    "Altai-Naryn Football School": "⚽",
    "Volleyball": "🏐",
    "Basketball": "🏀",
    "Judo Grappling": "🥋",
    "Uca Faculty": "👨‍🏫",
    "Female Football": "⚽♀️",
    "Football": "⚽",
    "Tennis": "🎾",
    "Mep & Kitchen": "🍽️",
    "Bubble": "🏟️",
}

GYM_LEGEND = (
    "🏋️ UCA Gym Weekly Schedule\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🟣 = Female Session\n"
    "🔵 = Male Session\n"
    "🟢 = Faculty / OPS\n"
    "🔴 = Cleaning Time\n"
    "━━━━━━━━━━━━━━━━━━\n"
)

BUBBLE_LEGEND = (
    "🏟️ Sports Bubble Weekly Schedule\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "🧹 Cleaning & Disinfection\n"
    "⚽ Football\n"
    "🏐 Volleyball\n"
    "🏀 Basketball\n"
    "🥋 Judo Grappling\n"
    "🏏 Cricket\n"
    "🎾 Tennis\n"
    "🏃 Physical Education\n"
    "👮 UCA Security\n"
    "👨‍🏫 UCA Faculty\n"
    "━━━━━━━━━━━━━━━━━━\n"
)

def _build_gym_day_text(day: str, slots) -> str:
    text = f"\n📅 {day}\n"
    for s in slots:
        emoji = SESSION_EMOJI.get(s.session_type, "⚪")
        text += f"{emoji} {s.start_time_str} – {s.end_time_str} → {s.session_type}\n"
    text += "\n━━━━━━━━━━━━━━━━━━\n"
    return text

def _time_to_minutes(time_str: str) -> int:
    if time_str == "00:00":
        return 24 * 60
    try:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m
    except ValueError:
        return 0

def _minutes_to_hm_str(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h > 0:
        return f"{h}h {m}m" if m > 0 else f"{h}h"
    return f"{m}m"

def _get_tomorrow_day(today: str) -> str:
    idx = DAYS_ORDER.index(today)
    return DAYS_ORDER[(idx + 1) % 7]

def _parse_bubble_time_range(time_range_str: str) -> tuple:
    normalized = time_range_str.replace("–", "-").replace("—", "-")
    parts = normalized.split("-")
    if len(parts) != 2:
        return 0, 0
    return _time_to_minutes(parts[0].strip()), _time_to_minutes(parts[1].strip())


@router.message(F.text == "🏋️ Sports & Gym")
async def sports_menu(message: Message):
    await message.answer("🏋️ Sports & Gym Menu:", reply_markup=get_sports_submenu_kb())

@router.callback_query(F.data == "sports_menu_back")
async def back_to_sports_menu(callback: CallbackQuery):
    await callback.message.edit_text("🏋️ Sports & Gym Menu:", reply_markup=get_sports_submenu_kb())

# ──────────────────── Gym ────────────────────

@router.callback_query(F.data == "sports_gym")
async def gym_menu_options(callback: CallbackQuery):
    await callback.message.edit_text("🏋️ Gym Schedule Options:", reply_markup=get_gym_options_kb())

@router.callback_query(F.data == "gym_weekly")
async def gym_weekly_schedule(callback: CallbackQuery):
    all_slots = await get_all_gym_slots()
    if not all_slots:
        await callback.message.edit_text("No gym schedule found.")
        return

    grouped = {}
    for s in all_slots:
        grouped.setdefault(s.day_of_week, []).append(s)

    part1_days = DAYS_ORDER[:4]
    part2_days = DAYS_ORDER[4:]

    msg1 = GYM_LEGEND
    for day in part1_days:
        if day in grouped:
            msg1 += _build_gym_day_text(day, grouped[day])

    msg2 = ""
    for day in part2_days:
        if day in grouped:
            msg2 += _build_gym_day_text(day, grouped[day])

    await callback.message.edit_text(msg1)
    if msg2:
        await callback.message.answer(msg2)

@router.callback_query(F.data == "gym_today")
async def gym_today_schedule(callback: CallbackQuery):
    today = datetime.now().strftime("%A")
    slots = await get_gym_slots_for_day(today)
    if not slots:
        await callback.message.edit_text(f"No gym slots found for today ({today}).")
        return
    text = f"🏋️ Today's Gym Schedule:\n" + _build_gym_day_text(today, slots)
    await callback.message.edit_text(text)

@router.callback_query(F.data == "gym_current_slot")
async def gym_current_slot_info(callback: CallbackQuery):
    now = datetime.now()
    today = now.strftime("%A")
    current_min = now.hour * 60 + now.minute

    slots = await get_gym_slots_for_day(today)
    if not slots:
        await callback.message.edit_text("No gym schedule configured.", reply_markup=get_gym_options_kb())
        return

    current_slot = None
    next_slot = None

    for i, slot in enumerate(slots):
        start_min = _time_to_minutes(slot.start_time_str)
        end_min = _time_to_minutes(slot.end_time_str)
        if start_min <= current_min < end_min:
            current_slot = slot
            if i + 1 < len(slots):
                next_slot = slots[i + 1]
            break

    if not current_slot:
        for slot in slots:
            if _time_to_minutes(slot.start_time_str) > current_min:
                next_slot = slot
                break

    if not next_slot:
        tomorrow = _get_tomorrow_day(today)
        tomorrow_slots = await get_gym_slots_for_day(tomorrow)
        if tomorrow_slots:
            next_slot = tomorrow_slots[0]

    if current_slot:
        emoji = SESSION_EMOJI.get(current_slot.session_type, "⚪")
        end_min = _time_to_minutes(current_slot.end_time_str)
        remaining = end_min - current_min
        text = (
            f"🕒 <b>Current Gym Time Slot:</b>\n\n"
            f"{emoji} <b>Active Slot:</b> {current_slot.session_type}\n"
            f"⏰ <b>Hours:</b> {current_slot.start_time_str} – {current_slot.end_time_str}\n"
            f"⏳ <b>Time Remaining:</b> {_minutes_to_hm_str(remaining)}\n\n"
        )
    else:
        text = "🕒 <b>Current Gym Time Slot:</b>\n\n💤 <b>Active Slot:</b> Gym is currently CLOSED / No active session.\n\n"

    if next_slot:
        next_emoji = SESSION_EMOJI.get(next_slot.session_type, "⚪")
        start_min = _time_to_minutes(next_slot.start_time_str)
        if next_slot.day_of_week != today:
            time_until = (24 * 60 - current_min) + start_min
            text += f"➡️ <b>Next Slot:</b> {next_slot.session_type} (Tomorrow)\n⏰ <b>Hours:</b> {next_slot.start_time_str} – {next_slot.end_time_str}\n⏳ <b>Starts in:</b> {_minutes_to_hm_str(time_until)}\n"
        else:
            time_until = start_min - current_min
            text += f"➡️ <b>Next Slot:</b> {next_slot.session_type}\n⏰ <b>Hours:</b> {next_slot.start_time_str} – {next_slot.end_time_str}\n⏳ <b>Starts in:</b> {_minutes_to_hm_str(time_until)}\n"
    else:
        text += "➡️ <b>Next Slot:</b> None scheduled."

    builder = InlineKeyboardBuilder()
    builder.button(text="Back", callback_data="sports_gym")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

# ──────────────────── Bubble ────────────────────

@router.callback_query(F.data == "sports_bubble")
async def bubble_menu_options(callback: CallbackQuery):
    await callback.message.edit_text("🏀 Sports Bubble Options:", reply_markup=get_bubble_options_kb())

@router.callback_query(F.data == "bubble_weekly")
async def bubble_weekly_schedule(callback: CallbackQuery):
    all_sports = await get_all_bubble_sports()
    if not all_sports:
        await callback.message.edit_text("No bubble schedule found.")
        return

    grouped = {}
    for s in all_sports:
        grouped.setdefault(s.day_of_week, []).append(s)

    text = BUBBLE_LEGEND
    for day in DAYS_ORDER:
        if day in grouped:
            text += f"\n📅 {day}\n"
            for s in grouped[day]:
                emoji = BUBBLE_EMOJI.get(s.sport_name, "⚪")
                text += f"{emoji} {s.time_str} → {s.sport_name}\n"
            text += "\n━━━━━━━━━━━━━━━━━━\n"

    await callback.message.edit_text(text)

@router.callback_query(F.data == "bubble_today")
async def bubble_today_schedule(callback: CallbackQuery):
    today = datetime.now().strftime("%A")
    sports = await get_bubble_sports_for_day(today)
    if not sports:
        await callback.message.edit_text(f"No bubble sports scheduled for today ({today}).")
        return

    text = f"🏟️ Today's Sports Bubble Schedule:\n\n📅 {today}\n"
    for s in sports:
        emoji = BUBBLE_EMOJI.get(s.sport_name, "⚪")
        text += f"{emoji} {s.time_str} → {s.sport_name}\n"
    text += "\n━━━━━━━━━━━━━━━━━━\n"
    await callback.message.edit_text(text)

@router.callback_query(F.data == "bubble_current_slot")
async def bubble_current_slot_info(callback: CallbackQuery):
    now = datetime.now()
    today = now.strftime("%A")
    current_min = now.hour * 60 + now.minute

    sports = list(await get_bubble_sports_for_day(today))
    sports.sort(key=lambda s: _parse_bubble_time_range(s.time_str)[0])

    current_sport = None
    next_sport = None

    for i, sport in enumerate(sports):
        start_min, end_min = _parse_bubble_time_range(sport.time_str)
        if start_min <= current_min < end_min:
            current_sport = sport
            if i + 1 < len(sports):
                next_sport = sports[i + 1]
            break

    if not current_sport:
        for sport in sports:
            start_min, _ = _parse_bubble_time_range(sport.time_str)
            if start_min > current_min:
                next_sport = sport
                break

    if not next_sport:
        tomorrow = _get_tomorrow_day(today)
        tomorrow_sports = list(await get_bubble_sports_for_day(tomorrow))
        tomorrow_sports.sort(key=lambda s: _parse_bubble_time_range(s.time_str)[0])
        if tomorrow_sports:
            next_sport = tomorrow_sports[0]

    if current_sport:
        emoji = BUBBLE_EMOJI.get(current_sport.sport_name, "⚪")
        start_min, end_min = _parse_bubble_time_range(current_sport.time_str)
        remaining = end_min - current_min
        text = (
            f"🕒 <b>Current Bubble Time Slot:</b>\n\n"
            f"{emoji} <b>Active Sport:</b> {current_sport.sport_name}\n"
            f"⏰ <b>Hours:</b> {current_sport.time_str}\n"
            f"⏳ <b>Time Remaining:</b> {_minutes_to_hm_str(remaining)}\n\n"
        )
    else:
        text = "🕒 <b>Current Bubble Time Slot:</b>\n\n💤 <b>Active Sport:</b> Bubble is currently empty / CLOSED.\n\n"

    if next_sport:
        start_min, _ = _parse_bubble_time_range(next_sport.time_str)
        if next_sport.day_of_week != today:
            time_until = (24 * 60 - current_min) + start_min
            text += f"➡️ <b>Next Sport:</b> {next_sport.sport_name} (Tomorrow)\n⏰ <b>Hours:</b> {next_sport.time_str}\n⏳ <b>Starts in:</b> {_minutes_to_hm_str(time_until)}\n"
        else:
            time_until = start_min - current_min
            text += f"➡️ <b>Next Sport:</b> {next_sport.sport_name}\n⏰ <b>Hours:</b> {next_sport.time_str}\n⏳ <b>Starts in:</b> {_minutes_to_hm_str(time_until)}\n"
    else:
        text += "➡️ <b>Next Sport:</b> None scheduled."

    builder = InlineKeyboardBuilder()
    builder.button(text="Back", callback_data="sports_bubble")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

# ──────────────────── Reminders ────────────────────

@router.callback_query(F.data == "sports_reminder")
async def sports_reminder_type(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="Gym", callback_data="sprem_gym")
    builder.button(text="Bubble Sports", callback_data="sprem_bub")
    builder.adjust(2)
    await callback.message.edit_text("Select type:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("sprem_"))
async def sports_reminder_day(callback: CallbackQuery):
    rtype = callback.data.split("_")[1]
    await callback.message.edit_text(f"Select a day for {rtype} reminder:", reply_markup=get_days_kb(f"spr_day_{rtype}"))

@router.callback_query(F.data.startswith("spr_day_"))
async def sports_reminder_select_event(callback: CallbackQuery):
    parts = callback.data.split("_")
    rtype = parts[2]
    day = parts[3]

    if rtype == "gym":
        events = await get_gym_slots_for_day(day)
        if not events:
            await callback.message.edit_text(f"No gym slots on {day}.")
            return
        builder = InlineKeyboardBuilder()
        for e in events:
            emoji = SESSION_EMOJI.get(e.session_type, "⚪")
            builder.button(text=f"{emoji} {e.start_time_str} – {e.end_time_str} ({e.session_type})", callback_data=f"spr_sel_{rtype}_{e.id}")
    else:
        events = await get_bubble_sports_for_day(day)
        if not events:
            await callback.message.edit_text(f"No bubble sports on {day}.")
            return
        builder = InlineKeyboardBuilder()
        for e in events:
            emoji = BUBBLE_EMOJI.get(e.sport_name, "⚪")
            builder.button(text=f"{emoji} {e.time_str} ({e.sport_name})", callback_data=f"spr_sel_{rtype}_{e.id}")

    builder.adjust(1)
    await callback.message.edit_text("Select an event:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("spr_sel_"))
async def sports_reminder_toggle(callback: CallbackQuery):
    parts = callback.data.split("_")
    rtype = parts[2]
    event_id = parts[3]
    await callback.message.edit_text(
        "Do you want to turn the reminder ON or OFF?",
        reply_markup=get_reminder_toggle_kb(f"spr_tog_{rtype}_{event_id}"),
    )

@router.callback_query(F.data.startswith("spr_tog_"))
async def process_sports_reminder_toggle(callback: CallbackQuery):
    from asgiref.sync import sync_to_async
    from camphub.models import GymEvent, Event
    parts = callback.data.split("_")
    rtype = parts[2]
    event_id = int(parts[3])
    action = parts[4]

    day_map = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"}

    if rtype == "gym":
        get_entry = sync_to_async(lambda: GymEvent.objects.select_related('event_id').get(id=event_id))
        entry = await get_entry()
        subject_name = "Gym Session"
        time_str = entry.event_id.start_time.strftime("%H:%M") if entry.event_id and entry.event_id.start_time else "00:00"
        day = day_map.get(entry.event_id.day, entry.event_id.day) if entry.event_id else "Monday"
    else:
        get_entry = sync_to_async(lambda: Event.objects.get(id=event_id))
        entry = await get_entry()
        subject_name = entry.status.replace("_", " ").title() if entry.status else "Sport"
        time_str = entry.start_time.strftime("%H:%M") if entry.start_time else "00:00"
        day = day_map.get(entry.day, entry.day)

    if action == "off":
        await delete_reminder(callback.from_user.id, rtype, subject_name, day, time_str)
        await callback.message.edit_text(f"Reminder for {subject_name} turned OFF.")
    else:
        await callback.message.edit_text(
            "Select reminder timing:",
            reply_markup=get_reminder_offsets_kb(f"spr_off_{rtype}_{event_id}"),
        )

@router.callback_query(F.data.startswith("spr_off_"))
async def save_sports_reminder(callback: CallbackQuery):
    from asgiref.sync import sync_to_async
    from camphub.models import GymEvent, Event
    parts = callback.data.split("_")
    rtype = parts[2]
    event_id = int(parts[3])
    offset = int(parts[4])

    day_map = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"}

    if rtype == "gym":
        get_entry = sync_to_async(lambda: GymEvent.objects.select_related('event_id').get(id=event_id))
        entry = await get_entry()
        subject_name = "Gym Session"
        time_str = entry.event_id.start_time.strftime("%H:%M") if entry.event_id and entry.event_id.start_time else "00:00"
        day = day_map.get(entry.event_id.day, entry.event_id.day) if entry.event_id else "Monday"
    else:
        get_entry = sync_to_async(lambda: Event.objects.get(id=event_id))
        entry = await get_entry()
        subject_name = entry.status.replace("_", " ").title() if entry.status else "Sport"
        time_str = entry.start_time.strftime("%H:%M") if entry.start_time else "00:00"
        day = day_map.get(entry.day, entry.day)

    await add_reminder(callback.from_user.id, rtype, subject_name, day, time_str, offset)
    await callback.message.edit_text(f"Reminder set for {subject_name} {offset} minutes before.")

