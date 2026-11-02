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
    get_unique_bubble_sports, get_bubble_sports_by_name,
    add_reminder, delete_reminder, get_user,
    get_user_reminders
)
from ..format import header, card, compose, empty, menu, day_label

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
    "CLEANING": "🧹",
    "MCHS": "🏫",
    "Physical Education": "🏃",
    "PE": "🏃",
    "UCA Security": "👮",
    "SECURITY": "👮",
    "Cricket": "🏏",
    "CRICKET": "🏏",
    "Altai-Naryn Football School": "⚽",
    "ALTAI-NARYN FOOTBALL": "⚽",
    "Volleyball": "🏐",
    "VOLLEYBALL": "🏐",
    "Basketball": "🏀",
    "BASKETBALL": "🏀",
    "Judo Grappling": "🥋",
    "JUDO GRAPPLING": "🥋",
    "JUDO": "🥋",
    "UCA Faculty": "👨‍🏫",
    "Female Football": "⚽♀️",
    "Football": "⚽",
    "FOOTBALL": "⚽",
    "football": "⚽",
    "Tennis": "🎾",
    "TENNIS": "🎾",
    "Badminton": "🏸",
    "BADMINTON": "🏸",
    "MEP & Kitchen": "🍽️",
    "MEP&KITCHEN": "🍽️",
    "Bubble": "🏟️",
}

GYM_LEGEND_LINES = (
    "🟣 Female · 🔵 Male · 🟢 Faculty / OPS · 🔴 Cleaning"
)

BUBBLE_LEGEND_LINES = (
    "🧹 Cleaning · ⚽ Football · 🏐 Volleyball · 🏀 Basketball\n"
    "🥋 Judo · 🏏 Cricket · 🎾 Tennis · 🏃 PE · 👮 Security"
)


def _build_gym_day_parts(day: str, slots, reminder_event_ids: set = None) -> list:
    if reminder_event_ids is None:
        reminder_event_ids = set()
    parts = [day_label(day)]
    for s in slots:
        emoji = SESSION_EMOJI.get(s.session_type, "⚪")
        status = "⏰ Reminder on" if s.event_id in reminder_event_ids else None
        parts.append(
            card(
                f"{s.start_time_str} - {s.end_time_str}",
                f"{emoji} {s.session_type}",
                status=status,
            )
        )
    return parts

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


@router.message(F.text.in_({"📋 Schedules", "🏋️ Sports & Gym & Meal"}))
async def sports_menu(message: Message):
    # "Sports & Gym & Meal" kept so sticky old keyboards still open this menu
    await message.answer(
        menu("📋", "Schedules"),
        reply_markup=get_sports_submenu_kb(),
        parse_mode="HTML",
    )

@router.callback_query(F.data == "sports_menu_back")
async def back_to_sports_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        menu("📋", "Schedules"),
        reply_markup=get_sports_submenu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "sports_library")
async def show_library_hours(callback: CallbackQuery):
    # Hardcoded to match the frontend library hours.
    text = compose(
        header("📚", "Library Hours"),
        "📅 <b>Weekdays</b>",
        card("09:00 - 19:00", "👤 Library Staff"),
        card("19:00 - 22:00", "🧑‍💼 Library Assistants"),
        "📅 <b>Weekends</b>",
        card("09:00 - 15:00", "🔒 Closed"),
        card("15:00 - 22:00", "🧑‍💼 Library Assistants"),
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="« Back", callback_data="sports_menu_back")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

# ──────────────────── Meal Time ────────────────────

@router.callback_query(F.data == "sports_meal")
async def show_meal_times(callback: CallbackQuery):
    reminders = await get_user_reminders(callback.from_user.id)
    active = {r.subject_name for r in reminders if r.reminder_type == "meal"}

    # Breaks are weekday-only, display-only (no reminders).
    text = compose(
        header("🍽", "Meal Times"),
        card(
            "08:00 - 09:30",
            "🥣 Breakfast",
            "Weekends: 08:00 - 10:00",
            status="⏰ Reminder on" if "Breakfast" in active else None,
        ),
        card("10:30 - 11:00", "☕ Break"),
        card(
            "12:00 - 14:00",
            "🍛 Lunch",
            status="⏰ Reminder on" if "Lunch" in active else None,
        ),
        card("15:15 - 16:00", "☕ Break"),
        card(
            "18:00 - 20:00",
            "🍲 Dinner",
            status="⏰ Reminder on" if "Dinner" in active else None,
        ),
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="« Back", callback_data="sports_menu_back")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())


# ──────────────────── Gym ────────────────────

@router.callback_query(F.data == "sports_gym")
async def gym_menu_options(callback: CallbackQuery):
    await callback.message.edit_text(
        menu("🏋️", "Gym Schedule"),
        reply_markup=get_gym_options_kb(),
        parse_mode="HTML",
    )

@router.callback_query(F.data == "gym_weekly")
async def gym_weekly_schedule(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.gender:
        await callback.answer("Please set your gender first (/start)", show_alert=True)
        return

    all_slots = await get_all_gym_slots(gender=user.gender)
    if not all_slots:
        await callback.message.edit_text(
            compose(header("🏋️", "Gym Schedule"), empty("No gym schedule found for your gender.")),
            parse_mode="HTML",
        )
        return

    reminders = await get_user_reminders(user.telegram_id)
    reminder_event_ids = {r.event_id for r in reminders if r.reminder_type == "gym"}

    grouped = {}
    for s in all_slots:
        grouped.setdefault(s.day_of_week, []).append(s)

    part1_days = DAYS_ORDER[:4]
    part2_days = DAYS_ORDER[4:]

    parts1 = []
    for day in part1_days:
        if day in grouped:
            parts1.extend(_build_gym_day_parts(day, grouped[day], reminder_event_ids))

    msg1 = compose(header("🏋️", "Gym · Weekly", GYM_LEGEND_LINES), *parts1)
    await callback.message.edit_text(msg1, parse_mode="HTML")

    parts2 = []
    for day in part2_days:
        if day in grouped:
            parts2.extend(_build_gym_day_parts(day, grouped[day], reminder_event_ids))
    if parts2:
        await callback.message.answer(compose(header("🏋️", "Gym · Weekly (cont.)"), *parts2), parse_mode="HTML")

@router.callback_query(F.data == "gym_today")
async def gym_today_schedule(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.gender:
        await callback.answer("Please set your gender first (/start)", show_alert=True)
        return

    today = datetime.now().strftime("%A")
    slots = await get_gym_slots_for_day(today, gender=user.gender)
    hdr = header("🏋️", "Gym · Today", f"📅 {today}", GYM_LEGEND_LINES)
    if not slots:
        await callback.message.edit_text(
            compose(hdr, empty(f"No gym slots today for your gender.")),
            parse_mode="HTML",
        )
        return

    reminders = await get_user_reminders(user.telegram_id)
    reminder_event_ids = {r.event_id for r in reminders if r.reminder_type == "gym"}
    parts = _build_gym_day_parts(today, slots, reminder_event_ids)
    # day_label already included; drop duplicate day heading for today view
    await callback.message.edit_text(compose(hdr, *parts[1:]), parse_mode="HTML")

@router.callback_query(F.data == "gym_current_slot")
async def gym_current_slot_info(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.gender:
        await callback.answer("Please set your gender first (/start)", show_alert=True)
        return

    now = datetime.now()
    today = now.strftime("%A")
    current_min = now.hour * 60 + now.minute

    slots = await get_gym_slots_for_day(today, gender=user.gender)
    if not slots:
        await callback.message.edit_text(
            compose(header("🕒", "Current Gym Slot"), empty("No gym schedule configured for your gender today.")),
            reply_markup=get_gym_options_kb(),
            parse_mode="HTML",
        )
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
        tomorrow_slots = await get_gym_slots_for_day(tomorrow, gender=user.gender)
        if tomorrow_slots:
            next_slot = tomorrow_slots[0]

    parts = []
    if current_slot:
        emoji = SESSION_EMOJI.get(current_slot.session_type, "⚪")
        remaining = _time_to_minutes(current_slot.end_time_str) - current_min
        parts.append(
            card(
                f"{current_slot.start_time_str} - {current_slot.end_time_str}",
                f"{emoji} {current_slot.session_type}",
                f"⏳ {_minutes_to_hm_str(remaining)} left",
            )
        )
    else:
        parts.append(empty("💤 Gym is closed — no active session."))

    if next_slot:
        next_emoji = SESSION_EMOJI.get(next_slot.session_type, "⚪")
        start_min = _time_to_minutes(next_slot.start_time_str)
        if next_slot.day_of_week != today:
            time_until = (24 * 60 - current_min) + start_min
            when = "Tomorrow"
        else:
            time_until = start_min - current_min
            when = "Today"
        parts.append(
            card(
                f"{next_slot.start_time_str} - {next_slot.end_time_str}",
                f"➡️ Next · {next_emoji} {next_slot.session_type}",
                f"📅 {when} · starts in {_minutes_to_hm_str(time_until)}",
            )
        )
    else:
        parts.append(empty("No next slot scheduled."))

    builder = InlineKeyboardBuilder()
    builder.button(text="« Back", callback_data="sports_gym")
    await callback.message.edit_text(
        compose(header("🕒", "Current Gym Slot", f"📅 {today}"), *parts),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )

# ──────────────────── Bubble ────────────────────

@router.callback_query(F.data == "sports_bubble")
async def bubble_menu_options(callback: CallbackQuery):
    await callback.message.edit_text(
        menu("🏀", "Sports Bubble"),
        reply_markup=get_bubble_options_kb(),
        parse_mode="HTML",
    )

@router.callback_query(F.data == "bubble_weekly")
async def bubble_weekly_schedule(callback: CallbackQuery):
    all_sports = await get_all_bubble_sports()
    if not all_sports:
        await callback.message.edit_text(
            compose(header("🏟️", "Bubble · Weekly"), empty("No bubble schedule found.")),
            parse_mode="HTML",
        )
        return

    reminders = await get_user_reminders(callback.from_user.id)
    reminder_event_ids = {r.event_id for r in reminders if r.reminder_type == "bubble"}

    grouped = {}
    for s in all_sports:
        grouped.setdefault(s.day_of_week, []).append(s)

    # Weekly bubble can be long — keep compact cards, split if needed
    parts = []
    for day in DAYS_ORDER:
        if day not in grouped:
            continue
        parts.append(day_label(day))
        for s in grouped[day]:
            emoji = BUBBLE_EMOJI.get(s.sport_name, "⚪")
            status = "⏰ Reminder on" if s.event_id in reminder_event_ids else None
            parts.append(card(s.time_str, f"{emoji} {s.sport_name}", status=status))

    text = compose(header("🏟️", "Bubble · Weekly", BUBBLE_LEGEND_LINES), *parts)
    # Telegram hard limit 4096; fall back to plain split if oversized
    if len(text) <= 4000:
        await callback.message.edit_text(text, parse_mode="HTML")
    else:
        mid = len(parts) // 2
        await callback.message.edit_text(
            compose(header("🏟️", "Bubble · Weekly", BUBBLE_LEGEND_LINES), *parts[:mid]),
            parse_mode="HTML",
        )
        await callback.message.answer(
            compose(header("🏟️", "Bubble · Weekly (cont.)"), *parts[mid:]),
            parse_mode="HTML",
        )

@router.callback_query(F.data == "bubble_today")
async def bubble_today_schedule(callback: CallbackQuery):
    today = datetime.now().strftime("%A")
    sports = await get_bubble_sports_for_day(today)
    hdr = header("🏟️", "Bubble · Today", f"📅 {today}")
    if not sports:
        await callback.message.edit_text(
            compose(hdr, empty(f"No bubble sports scheduled for {today}.")),
            parse_mode="HTML",
        )
        return

    reminders = await get_user_reminders(callback.from_user.id)
    reminder_event_ids = {r.event_id for r in reminders if r.reminder_type == "bubble"}

    parts = []
    for s in sports:
        emoji = BUBBLE_EMOJI.get(s.sport_name, "⚪")
        status = "⏰ Reminder on" if s.event_id in reminder_event_ids else None
        parts.append(card(s.time_str, f"{emoji} {s.sport_name}", status=status))

    await callback.message.edit_text(compose(hdr, *parts), parse_mode="HTML")

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

    parts = []
    if current_sport:
        emoji = BUBBLE_EMOJI.get(current_sport.sport_name, "⚪")
        _, end_min = _parse_bubble_time_range(current_sport.time_str)
        remaining = end_min - current_min
        parts.append(
            card(
                current_sport.time_str,
                f"{emoji} {current_sport.sport_name}",
                f"⏳ {_minutes_to_hm_str(remaining)} left",
            )
        )
    else:
        parts.append(empty("💤 Bubble is empty / closed right now."))

    if next_sport:
        start_min, _ = _parse_bubble_time_range(next_sport.time_str)
        if next_sport.day_of_week != today:
            time_until = (24 * 60 - current_min) + start_min
            when = "Tomorrow"
        else:
            time_until = start_min - current_min
            when = "Today"
        emoji = BUBBLE_EMOJI.get(next_sport.sport_name, "⚪")
        parts.append(
            card(
                next_sport.time_str,
                f"➡️ Next · {emoji} {next_sport.sport_name}",
                f"📅 {when} · starts in {_minutes_to_hm_str(time_until)}",
            )
        )
    else:
        parts.append(empty("No next sport scheduled."))

    builder = InlineKeyboardBuilder()
    builder.button(text="« Back", callback_data="sports_bubble")
    await callback.message.edit_text(
        compose(header("🕒", "Current Bubble Slot", f"📅 {today}"), *parts),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )

# ──────────────────── Reminders ────────────────────



@router.callback_query(F.data == "sports_reminder")
async def sports_reminder_type(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="Gym", callback_data="sprem_gym")
    builder.button(text="Bubble Sports", callback_data="sprem_bub")
    builder.button(text="Meal Times", callback_data="sprem_meal")  # <-- Added
    builder.adjust(3)
    await callback.message.edit_text(
        header("⏰", "Sports Reminders", "Select a type:"),
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )



@router.callback_query(F.data.startswith("sprem_"))
async def sports_reminder_day(callback: CallbackQuery):
    rtype = callback.data.split("_")[1]
    if rtype == "gym":
        from ..keyboards.inline import get_gym_reminder_days_kb
        await callback.message.edit_text(f"Select a day group for gym reminder:", reply_markup=get_gym_reminder_days_kb(f"spr_day_{rtype}"))
    elif rtype == "meal":  # <-- Added this block
        builder = InlineKeyboardBuilder()
        builder.button(text="🍳 Breakfast", callback_data="spr_meal_Breakfast")
        builder.button(text="🍽️ Lunch", callback_data="spr_meal_Lunch")
        builder.button(text="🍲 Dinner", callback_data="spr_meal_Dinner")
        builder.button(text="⬅️ Back", callback_data="sports_reminder")
        builder.adjust(1)
        await callback.message.edit_text("Select a meal to set a reminder:", reply_markup=builder.as_markup())
    else:  # <-- Changed 'else:' to handle 'sprem_bub' specifically
        # For bubble, show sports first
        sports = await get_unique_bubble_sports()
        if not sports:
            await callback.message.edit_text("No bubble sports available.")
            return
        
        from urllib.parse import quote
        builder = InlineKeyboardBuilder()
        for sport in sports:
            emoji = BUBBLE_EMOJI.get(sport, "⚪")
            builder.button(text=f"{emoji} {sport}", callback_data=f"spr_sport_{quote(sport)}")
        builder.button(text="📅 All (by day)", callback_data="spr_sport_ALL")
        builder.adjust(1)
        await callback.message.edit_text("Select a sport for bubble reminder:", reply_markup=builder.as_markup())






@router.callback_query(F.data.startswith("spr_sport_") & ~F.data.startswith("spr_sport_all_") & ~F.data.startswith("spr_sport_tog_") & ~F.data.startswith("spr_sport_off_"))
async def sports_reminder_sport_selected(callback: CallbackQuery):
    from urllib.parse import unquote
    # Extract sport name by removing the prefix
    sport = unquote(callback.data[len("spr_sport_"):])
    
    # Debug logging
    print(f"DEBUG: Callback data: {callback.data}")
    print(f"DEBUG: Extracted sport: '{sport}'")
    
    if sport == "ALL":
        # Show the original day-based selection
        await callback.message.edit_text("Select a day for bubble reminder:", reply_markup=get_days_kb("spr_day_bub"))
        return
    
    # Show all instances of this sport
    events = await get_bubble_sports_by_name(sport)
    print(f"DEBUG: Found {len(events)} events for sport '{sport}'")
    if not events:
        await callback.message.edit_text(f"No events found for {sport}.")
        return
    
    # Group by day for better display
    grouped = {}
    for e in events:
        grouped.setdefault(e.day_of_week, []).append(e)
    
    text = f"🏟️ {sport} - All Sessions\n\n"
    for day in DAYS_ORDER:
        if day in grouped:
            text += f"📅 {day}\n"
            for e in grouped[day]:
                emoji = BUBBLE_EMOJI.get(e.sport_name, "⚪")
                text += f"{emoji} {e.time_str}\n"
            text += "\n"
    
    from urllib.parse import quote
    builder = InlineKeyboardBuilder()
    builder.button(text="⏰ Set Reminder for All", callback_data=f"spr_sport_all_{quote(sport)}")
    builder.button(text="⬅️ Back", callback_data="sports_reminder")
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("spr_sport_all_"))
async def sports_reminder_sport_all_toggle(callback: CallbackQuery):
    from urllib.parse import unquote, quote
    sport = unquote(callback.data[len("spr_sport_all_"):])
    await callback.message.edit_text(
        f"Do you want to turn reminder ON for all {sport} sessions?",
        reply_markup=get_reminder_toggle_kb(f"spr_sport_tog_{quote(sport)}"),
    )


@router.callback_query(F.data.startswith("spr_sport_tog_"))
async def process_sport_reminder_toggle(callback: CallbackQuery):
    from urllib.parse import unquote, quote
    # Extract sport name from callback data
    # Format: spr_sport_tog_{url_encoded_sport}_on or spr_sport_tog_{url_encoded_sport}_off
    data_without_prefix = callback.data[len("spr_sport_tog_"):]
    
    print(f"DEBUG: process_sport_reminder_toggle - raw data: {data_without_prefix}")
    
    # Check if this is a turn on or turn off action
    action = "on" if "_on" in callback.data else "off"
    
    # Remove the "_on" or "_off" suffix BEFORE unquoting
    if data_without_prefix.endswith("_on"):
        data_without_prefix = data_without_prefix[:-3]
        print(f"DEBUG: Removed _on suffix, now: {data_without_prefix}")
    elif data_without_prefix.endswith("_off"):
        data_without_prefix = data_without_prefix[:-4]
        print(f"DEBUG: Removed _off suffix, now: {data_without_prefix}")
    
    sport = unquote(data_without_prefix)
    
    print(f"DEBUG: process_sport_reminder_toggle - action: {action}, sport: '{sport}'")
    
    if action == "on":
        await callback.message.edit_text(
            "Select reminder timing:",
            reply_markup=get_reminder_offsets_kb(f"spr_sport_off_{quote(sport)}"),
        )
        return
    
    # Turn off reminders for this sport
    events = await get_bubble_sports_by_name(sport)
    for e in events:
        time_str = e.time_str.split("–")[0].strip()
        await delete_reminder(callback.from_user.id, "bubble", sport, e.day_of_week, time_str)
    
    await callback.message.edit_text(f"Reminder for {sport} turned OFF for all sessions.")


@router.callback_query(F.data.startswith("spr_sport_off_"))
async def save_sport_reminder(callback: CallbackQuery):
    from urllib.parse import unquote
    # Extract sport name and offset from callback data
    # Format: spr_sport_off_{url_encoded_sport}_{offset}
    data_without_prefix = callback.data[len("spr_sport_off_"):]
    # Split by underscore to separate sport name from offset
    # The offset is always a number at the end
    parts = data_without_prefix.rsplit("_", 1)
    sport = unquote(parts[0])
    offset = int(parts[1])
    
    print(f"DEBUG: save_sport_reminder - callback data: {callback.data}")
    print(f"DEBUG: save_sport_reminder - extracted sport: '{sport}', offset: {offset}")
    
    # Set reminders for all instances of this sport
    events = await get_bubble_sports_by_name(sport)
    print(f"DEBUG: Found {len(events)} events for {sport}")
    if not events:
        await callback.message.edit_text(f"Error: No events found for sport '{sport}'")
        return
    
    for e in events:
        time_str = e.time_str.split("–")[0].strip()
        print(f"DEBUG: Adding reminder for {sport} on {e.day_of_week} at {time_str}")
        result = await add_reminder(callback.from_user.id, "bubble", sport, e.day_of_week, time_str, offset)
        print(f"DEBUG: add_reminder returned: {result}")
    
    emoji = BUBBLE_EMOJI.get(sport, "🏟️")
    text = (
        f"✅ <b>Reminder Configured!</b>\n\n"
        f"{emoji} <b>Sport:</b> {sport}\n"
        f"⏰ <b>Timing:</b> {offset} minutes before each session\n\n"
        f"🔔 You will receive a notification before the sessions start!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back to Bubble Options", callback_data="sports_bubble")
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("spr_day_"))
async def sports_reminder_select_event(callback: CallbackQuery):
    parts = callback.data.split("_")
    rtype = parts[2]
    day = parts[3]
    
    if day == "ALL":
        await callback.message.edit_text("Select a day for gym reminder:", reply_markup=get_days_kb(f"spr_day_{rtype}"))
        return

    day_to_query = day
    if day == "MWF":
        day_to_query = "Monday"
    elif day == "TTS":
        day_to_query = "Tuesday"

    if rtype == "gym":
        user = await get_user(callback.from_user.id)
        if not user or not user.gender:
            await callback.answer("Please set your gender first (/start)", show_alert=True)
            return
        events = await get_gym_slots_for_day(day_to_query, gender=user.gender)
        if not events:
            await callback.message.edit_text(f"No gym slots for {day}.")
            return
        builder = InlineKeyboardBuilder()
        for e in events:
            emoji = SESSION_EMOJI.get(e.session_type, "⚪")
            builder.button(text=f"{emoji} {e.start_time_str} – {e.end_time_str} ({e.session_type})", callback_data=f"spr_sel_{rtype}_{day}_{e.id}")
    else:
        events = await get_bubble_sports_for_day(day_to_query)
        if not events:
            await callback.message.edit_text(f"No bubble sports on {day}.")
            return
        builder = InlineKeyboardBuilder()
        for e in events:
            emoji = BUBBLE_EMOJI.get(e.sport_name, "⚪")
            builder.button(text=f"{emoji} {e.time_str} ({e.sport_name})", callback_data=f"spr_sel_{rtype}_{day}_{e.id}")

    builder.adjust(1)
    await callback.message.edit_text("Select an event:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("spr_sel_"))
async def sports_reminder_toggle(callback: CallbackQuery):
    parts = callback.data.split("_")
    rtype = parts[2]
    day = parts[3]
    event_id = parts[4]
    await callback.message.edit_text(
        "Do you want to turn the reminder ON or OFF?",
        reply_markup=get_reminder_toggle_kb(f"spr_tog_{rtype}_{day}_{event_id}"),
    )

@router.callback_query(F.data.startswith("spr_tog_"))
async def process_sports_reminder_toggle(callback: CallbackQuery):
    from asgiref.sync import sync_to_async
    from camphub.models import GymEvent, Event
    parts = callback.data.split("_")
    rtype = parts[2]
    day_group = parts[3]
    event_id = int(parts[4])
    action = parts[5]

    day_map = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"}

    if action == "on":
        await callback.message.edit_text(
            "Select reminder timing:",
            reply_markup=get_reminder_offsets_kb(f"spr_off_{rtype}_{day_group}_{event_id}"),
        )
        return

    days_to_remove = []
    if day_group == "MWF":
        days_to_remove = ["Monday", "Wednesday", "Friday"]
    elif day_group == "TTS":
        days_to_remove = ["Tuesday", "Thursday", "Saturday"]
    else:
        days_to_remove = [day_group]

    if rtype == "gym":
        get_entry = sync_to_async(lambda: GymEvent.objects.select_related('event_id').get(id=event_id))
        entry = await get_entry()
        subject_name = "Gym Session"
        time_str = entry.event_id.start_time.strftime("%H:%M") if entry.event_id and entry.event_id.start_time else "00:00"
    else:
        get_entry = sync_to_async(lambda: Event.objects.get(id=event_id))
        entry = await get_entry()
        subject_name = entry.status.replace("_", " ").title() if entry.status else "Sport"
        time_str = entry.start_time.strftime("%H:%M") if entry.start_time else "00:00"
        if day_group not in ["MWF", "TTS"]:
            days_to_remove = [day_map.get(entry.day, entry.day)]

    for d in days_to_remove:
        await delete_reminder(callback.from_user.id, rtype, subject_name, d, time_str)
    await callback.message.edit_text(f"Reminder for {subject_name} ({day_group}) turned OFF.")

@router.callback_query(F.data.startswith("spr_off_"))
async def save_sports_reminder(callback: CallbackQuery):
    from asgiref.sync import sync_to_async
    from camphub.models import GymEvent, Event
    parts = callback.data.split("_")
    rtype = parts[2]
    day_group = parts[3]
    event_id = int(parts[4])
    offset = int(parts[5])

    day_map = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"}

    days_to_add = []
    if day_group == "MWF":
        days_to_add = ["Monday", "Wednesday", "Friday"]
    elif day_group == "TTS":
        days_to_add = ["Tuesday", "Thursday", "Saturday"]
    else:
        days_to_add = [day_group]

    if rtype == "gym":
        get_entry = sync_to_async(lambda: GymEvent.objects.select_related('event_id').get(id=event_id))
        entry = await get_entry()
        subject_name = "Gym Session"
        time_str = entry.event_id.start_time.strftime("%H:%M") if entry.event_id and entry.event_id.start_time else "00:00"
    else:
        get_entry = sync_to_async(lambda: Event.objects.get(id=event_id))
        entry = await get_entry()
        subject_name = entry.status.replace("_", " ").title() if entry.status else "Sport"
        time_str = entry.start_time.strftime("%H:%M") if entry.start_time else "00:00"
        if day_group not in ["MWF", "TTS"]:
            days_to_add = [day_map.get(entry.day, entry.day)]

    for d in days_to_add:
        await add_reminder(callback.from_user.id, rtype, subject_name, d, time_str, offset)
    
    emoji = "🏋️" if rtype == "gym" else "🏟️"
    text = (
        f"✅ <b>Reminder Configured!</b>\n\n"
        f"{emoji} <b>Event:</b> {subject_name}\n"
        f"📅 <b>Day:</b> {day_group}\n"
        f"⏰ <b>Timing:</b> {offset} minutes before\n\n"
        f"🔔 You will receive a notification before the session starts!"
    )
    
    builder = InlineKeyboardBuilder()
    back_callback = "sports_gym" if rtype == "gym" else "sports_bubble"
    builder.button(text="⬅️ Back", callback_data=back_callback)
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())


# ──────────────────── Meal Time Reminders ────────────────────


@router.callback_query(F.data.in_(["spr_meal_Breakfast", "spr_meal_Lunch", "spr_meal_Dinner"]))
async def meal_reminder_selected(callback: CallbackQuery):
    meal_name = callback.data[len("spr_meal_"):]
    await callback.message.edit_text(
        f"Do you want to turn reminder ON or OFF for {meal_name}?",
        reply_markup=get_reminder_toggle_kb(f"spr_meal_tog_{meal_name}"),

    )




@router.callback_query(F.data.startswith("spr_meal_tog_"))
async def process_meal_reminder_toggle(callback: CallbackQuery):
    from camphub.models import Event, MealTime, Reminder
    from accounts.models import UserAccount
    from asgiref.sync import sync_to_async
    from aiogram.utils.keyboard import InlineKeyboardBuilder  # Ensure this import is available
    
    # Extract meal name and action from callback data
    data_without_prefix = callback.data[len("spr_meal_tog_"):]
    action = "on" if "_on" in callback.data else "off"
    
    if data_without_prefix.endswith("_on"):
        data_without_prefix = data_without_prefix[:-3]
    elif data_without_prefix.endswith("_off"):
        data_without_prefix = data_without_prefix[:-4]
    
    meal_name = data_without_prefix
    
    if action == "on":
        # Build a custom keyboard with ONLY 5, 10, and 15 minute options
        builder = InlineKeyboardBuilder()
        for offset in [5, 10, 15]:
            builder.button(text=f"{offset} mins before", callback_data=f"spr_meal_off_{meal_name}_{offset}")
        builder.adjust(3)  # Arranges the 3 buttons side-by-side in a single row
        
        await callback.message.edit_text(
            "Select reminder timing:",
            reply_markup=builder.as_markup(),
        )
        return
        
    else:
        @sync_to_async
        def delete_meal_reminders():
            u = UserAccount.objects.get(telegram_id=callback.from_user.id)
            meal_events = Event.objects.filter(
                status="MEAL_TIME", mealtime__meal_name=meal_name
            ).distinct()
            deleted = 0
            for e in meal_events:
                deleted += Reminder.objects.filter(user_id=u, event_id=e).delete()[0]
            return deleted

        await delete_meal_reminders()

        emoji_map = {"Breakfast": "🍳", "Lunch": "🍽️", "Dinner": "🍲"}
        emoji = emoji_map.get(meal_name, "🍽️")
        text = (
            f"❌ <b>Reminder OFF!</b>\n\n"
            f"{emoji} <b>Meal:</b> {meal_name}\n"
            f"📅 <b>Days:</b> All 7 days\n\n"
            f"🔔 You will no longer receive notifications for {meal_name}."
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="« Back", callback_data="sports_menu_back")
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())





@router.callback_query(F.data.startswith("spr_meal_off_"))
async def save_meal_reminder(callback: CallbackQuery):
    from camphub.models import Event, MealTime, Reminder
    from accounts.models import UserAccount
    from asgiref.sync import sync_to_async
    from datetime import time as dt_time

    # Callback data format: spr_meal_off_{meal_name}_{offset}
    data_without_prefix = callback.data[len("spr_meal_off_"):]
    parts = data_without_prefix.rsplit("_", 1)
    meal_name = parts[0]
    offset = int(parts[1])

    # Must match the Meal Times screen (weekday starts).
    MEAL_TIMES = {
        "Breakfast": (dt_time(8, 0), dt_time(9, 30)),
        "Lunch": (dt_time(12, 0), dt_time(14, 0)),
        "Dinner": (dt_time(18, 0), dt_time(20, 0)),
    }
    DAY_CODES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    if meal_name not in MEAL_TIMES:
        await callback.answer("Unknown meal", show_alert=True)
        return

    start_t, end_t = MEAL_TIMES[meal_name]

    @sync_to_async
    def set_meal_reminders():
        u = UserAccount.objects.get(telegram_id=callback.from_user.id)
        count = 0
        for day_code in DAY_CODES:
            # Ensure a MEAL_TIME event exists for this day (DB had none before).
            event = Event.objects.filter(
                status="MEAL_TIME", day=day_code, start_time=start_t
            ).first()
            if not event:
                event = Event.objects.create(
                    status="MEAL_TIME",
                    day=day_code,
                    start_time=start_t,
                    end_time=end_t,
                )
            mt = MealTime.objects.filter(event_id=event, meal_name=meal_name).first()
            if not mt:
                # Re-link or create MealTime for this event
                existing = MealTime.objects.filter(event_id=event).first()
                if existing:
                    existing.meal_name = meal_name
                    existing.save()
                else:
                    MealTime.objects.create(meal_name=meal_name, event_id=event)

            time_str = start_t.strftime("%H:%M")
            Reminder.objects.filter(user_id=u, event_id=event).delete()
            Reminder.objects.create(
                user_id=u,
                event_time_str=time_str,
                reminder_offset=offset,
                event_id=event,
            )
            count += 1
        return count

    count = await set_meal_reminders()

    emoji_map = {"Breakfast": "🍳", "Lunch": "🍽️", "Dinner": "🍲"}
    emoji = emoji_map.get(meal_name, "🍽️")
    text = (
        f"✅ <b>Reminder ON!</b>\n\n"
        f"{emoji} <b>Meal:</b> {meal_name}\n"
        f"⏰ <b>Timing:</b> {offset} minutes before each meal\n"
        f"📅 <b>Days:</b> All 7 days ({count} reminders)\n\n"
        f"🔔 You will receive a notification before every {meal_name}!"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="« Back", callback_data="sports_menu_back")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())






