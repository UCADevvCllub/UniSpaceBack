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
    "MCHS": "🏫",
    "Physical Education": "🏃",
    "UCA Security": "👮",
    "Cricket": "🏏",
    "Altai-Naryn Football School": "⚽",
    "Volleyball": "🏐",
    "Basketball": "�️",
    "Judo Grappling": "🥋",
    "UCA Faculty": "👨‍🏫",
    "Female Football": "⚽♀️",
    "Football": "⚽",
    "Tennis": "🎾",
    "MEP & Kitchen": "🍽️",
    "Bubble": "🏟️",
}

GYM_LEGEND = (
    "🏋️ UCA Gym Schedule\n\n"
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

def _build_gym_day_text(day: str, slots, reminder_event_ids: set = None) -> str:
    if reminder_event_ids is None:
        reminder_event_ids = set()
    text = f"\n📅 {day}\n"
    for s in slots:
        emoji = SESSION_EMOJI.get(s.session_type, "⚪")
        reminder_icon = " 🔔" if s.event_id in reminder_event_ids else ""
        text += f"{emoji} {s.start_time_str} – {s.end_time_str} → {s.session_type}{reminder_icon}\n"
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


@router.message(F.text == "🏋️ Sports & Gym & Meal")
async def sports_menu(message: Message):
    await message.answer("🏋️ Sports & Gym & Meal Menu:", reply_markup=get_sports_submenu_kb())

@router.callback_query(F.data == "sports_menu_back")
async def back_to_sports_menu(callback: CallbackQuery):
    await callback.message.edit_text("🏋️ Sports & Gym & Meal Menu:", reply_markup=get_sports_submenu_kb())

# ──────────────────── Meal Time ────────────────────

@router.callback_query(F.data == "sports_meal")
async def show_meal_times(callback: CallbackQuery):
    # Fetch active reminders for the user
    reminders = await get_user_reminders(callback.from_user.id)
    
    # Extract unique meal names that have active reminders
    active_meal_reminders = {r.subject_name for r in reminders if r.reminder_type == "meal"}
    
    # Append the bell icon if the reminder is active
    breakfast_bell = " 🔔" if "Breakfast" in active_meal_reminders else ""
    lunch_bell = " 🔔" if "Lunch" in active_meal_reminders else ""
    dinner_bell = " 🔔" if "Dinner" in active_meal_reminders else ""
    
    text = (
        "🍽 <b>Meal Times</b>\n\n"
        f"🥣 <b>Breakfast:</b>  8:00 AM – 9:30 AM{breakfast_bell}\n"
        "    <i>(Weekends: 8:00 AM – 10:00 AM)</i>\n\n"
        f"🍛 <b>Lunch:</b>  12:00 PM – 2:00 PM{lunch_bell}\n\n"
        f"🍲 <b>Dinner:</b>  6:00 PM – 8:00 PM{dinner_bell}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back", callback_data="sports_menu_back")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())





# ──────────────────── Gym ────────────────────

@router.callback_query(F.data == "sports_gym")
async def gym_menu_options(callback: CallbackQuery):
    await callback.message.edit_text("🏋️ Gym Schedule Options:", reply_markup=get_gym_options_kb())

@router.callback_query(F.data == "gym_weekly")
async def gym_weekly_schedule(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.gender:
        await callback.answer("Please set your gender first (/start)", show_alert=True)
        return

    all_slots = await get_all_gym_slots(gender=user.gender)
    if not all_slots:
        await callback.message.edit_text("No gym schedule found for your gender.")
        return

    reminders = await get_user_reminders(user.telegram_id)
    reminder_event_ids = {r.event_id for r in reminders if r.reminder_type == "gym"}

    grouped = {}
    for s in all_slots:
        grouped.setdefault(s.day_of_week, []).append(s)

    part1_days = DAYS_ORDER[:4]
    part2_days = DAYS_ORDER[4:]

    msg1 = GYM_LEGEND
    for day in part1_days:
        if day in grouped:
            msg1 += _build_gym_day_text(day, grouped[day], reminder_event_ids)

    msg2 = ""
    for day in part2_days:
        if day in grouped:
            msg2 += _build_gym_day_text(day, grouped[day], reminder_event_ids)

    await callback.message.edit_text(msg1)
    if msg2:
        await callback.message.answer(msg2)

@router.callback_query(F.data == "gym_today")
async def gym_today_schedule(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.gender:
        await callback.answer("Please set your gender first (/start)", show_alert=True)
        return

    today = datetime.now().strftime("%A")
    slots = await get_gym_slots_for_day(today, gender=user.gender)
    if not slots:
        await callback.message.edit_text(f"No gym slots found for today ({today}) for your gender.")
        return

    reminders = await get_user_reminders(user.telegram_id)
    reminder_event_ids = {r.event_id for r in reminders if r.reminder_type == "gym"}

    text = f"🏋️ Today's Gym Schedule:\n" + _build_gym_day_text(today, slots, reminder_event_ids)
    await callback.message.edit_text(text)

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
        await callback.message.edit_text("No gym schedule configured for your gender today.", reply_markup=get_gym_options_kb())
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
    print(f"DEBUG: bubble_weekly callback received")
    all_sports = await get_all_bubble_sports()
    print(f"DEBUG: Found {len(all_sports)} bubble sports")
    if not all_sports:
        await callback.message.edit_text("No bubble schedule found.")
        return

    # Get user reminders for bubble sports
    reminders = await get_user_reminders(callback.from_user.id)
    # Create a set of event IDs that have reminders (like gym does)
    reminder_event_ids = {r.event_id for r in reminders if r.reminder_type == "bubble"}
    
    # Debug logging
    print(f"DEBUG: User {callback.from_user.id} bubble reminder event IDs: {reminder_event_ids}")

    grouped = {}
    for s in all_sports:
        grouped.setdefault(s.day_of_week, []).append(s)

    text = BUBBLE_LEGEND
    for day in DAYS_ORDER:
        if day in grouped:
            text += f"\n📅 {day}\n"
            for s in grouped[day]:
                emoji = BUBBLE_EMOJI.get(s.sport_name, "⚪")
                reminder_icon = " 🔔" if s.event_id in reminder_event_ids else ""
                print(f"DEBUG: Checking {s.sport_name}, event_id {s.event_id} -> {reminder_icon}")
                text += f"{emoji} {s.time_str} → {s.sport_name}{reminder_icon}\n"
            text += "\n━━━━━━━━━━━━━━━━━━\n"

    await callback.message.edit_text(text)

@router.callback_query(F.data == "bubble_today")
async def bubble_today_schedule(callback: CallbackQuery):
    today = datetime.now().strftime("%A")
    sports = await get_bubble_sports_for_day(today)
    if not sports:
        await callback.message.edit_text(f"No bubble sports scheduled for today ({today}).")
        return

    # Get user reminders for bubble sports
    reminders = await get_user_reminders(callback.from_user.id)
    # Create a set of event IDs that have reminders (like gym does)
    reminder_event_ids = {r.event_id for r in reminders if r.reminder_type == "bubble"}

    text = f"🏟️ Today's Sports Bubble Schedule:\n\n📅 {today}\n"
    for s in sports:
        emoji = BUBBLE_EMOJI.get(s.sport_name, "⚪")
        reminder_icon = " 🔔" if s.event_id in reminder_event_ids else ""
        text += f"{emoji} {s.time_str} → {s.sport_name}{reminder_icon}\n"
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
    builder.button(text="Meal Times", callback_data="sprem_meal")  # <-- Added
    builder.adjust(3)
    await callback.message.edit_text("Select type:", reply_markup=builder.as_markup())



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
        # Turn off reminders (remains the same)
        @sync_to_async
        def delete_meal_reminders():
            u = UserAccount.objects.get(telegram_id=callback.from_user.id)
            meal_events = Event.objects.filter(status="MEAL_TIME").prefetch_related('mealtime_set')
            for e in meal_events:
                me = e.mealtime_set.first()
                if me and me.meal_name == meal_name:
                    Reminder.objects.filter(user_id=u, event_id=e).delete()
        
        await delete_meal_reminders()
        
        emoji_map = {"Breakfast": "🍳", "Lunch": "🍽️", "Dinner": "🍲"}
        emoji = emoji_map.get(meal_name, "🍽️")
        text = (
            f"❌ <b>Reminder OFF!</b>\n\n"
            f"{emoji} <b>Meal:</b> {meal_name}\n"
            f"📅 <b>Days:</b> Permanent (All 7 days)\n\n"
            f"🔔 You will no longer receive notifications for {meal_name}."
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Back to Sports Menu", callback_data="sports_menu_back")
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())





@router.callback_query(F.data.startswith("spr_meal_off_"))
async def save_meal_reminder(callback: CallbackQuery):
    from camphub.models import Event, MealTime, Reminder
    from accounts.models import UserAccount
    from asgiref.sync import sync_to_async
    
    # Callback data format: spr_meal_off_{meal_name}_{offset}
    data_without_prefix = callback.data[len("spr_meal_off_"):]
    
    # Split by the last underscore to separate meal name and offset
    parts = data_without_prefix.rsplit("_", 1)
    meal_name = parts[0]
    offset = int(parts[1])
    
    @sync_to_async
    def set_meal_reminders():
        u = UserAccount.objects.get(telegram_id=callback.from_user.id)
        meal_events = Event.objects.filter(status="MEAL_TIME").prefetch_related('mealtime_set')
        count = 0
        for e in meal_events:
            me = e.mealtime_set.first()
            if me and me.meal_name == meal_name:
                time_str = e.start_time.strftime("%H:%M")
                # Delete any pre-existing reminder for safety
                Reminder.objects.filter(user_id=u, event_id=e).delete()
                # Save a permanent reminder linked directly to this Event
                Reminder.objects.create(
                    user_id=u,
                    event_time_str=time_str,
                    reminder_offset=offset,
                    event_id=e
                )
                count += 1
        return count
    
    await set_meal_reminders()
    
    emoji_map = {"Breakfast": "🍳", "Lunch": "🍽️", "Dinner": "🍲"}
    emoji = emoji_map.get(meal_name, "🍽️")
    text = (
        f"✅ <b>Reminder ON!</b>\n\n"
        f"{emoji} <b>Meal:</b> {meal_name}\n"
        f"⏰ <b>Timing:</b> {offset} minutes before each meal\n"
        f"📅 <b>Days:</b> Permanent (All 7 days)\n\n"
        f"🔔 You will receive a notification before every {meal_name}!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back to Sports Menu", callback_data="sports_menu_back")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())






