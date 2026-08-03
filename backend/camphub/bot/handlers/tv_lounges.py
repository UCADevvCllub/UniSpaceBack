from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
from datetime import datetime

from ..keyboards.inline import get_tv_submenu_kb, get_tv_lounges_kb
from ..crud import (
    get_tv_bookings, get_tv_booking_by_id, add_tv_booking, update_tv_booking, 
    delete_tv_booking, add_reminder, delete_reminder
)

router = Router()

class BookTVState(StatesGroup):
    waiting_for_lounge_selection = State()
    waiting_for_booker_name = State()
    waiting_for_booking_date = State()
    waiting_for_booking_time = State()

@router.message(F.text == "📺 TV Lounges")
async def tv_menu(message: Message):
    await message.answer("📺 TV Lounges Menu:", reply_markup=get_tv_submenu_kb())

@router.callback_query(F.data == "tv_menu_back")
async def tv_menu_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("📺 TV Lounges Menu:", reply_markup=get_tv_submenu_kb())

# ──────────────────── My Bookings ────────────────────

@router.callback_query(F.data == "tv_my_bookings")
async def my_tv_bookings(callback: CallbackQuery):
    bookings = await get_tv_bookings(callback.from_user.id)
        
    if not bookings:
        await callback.message.edit_text("You have no TV Lounge bookings.")
        return
        
    text = "📺 Your TV Lounge Bookings:\n\n"
    for b in bookings:
        text += (
            f"▪️ {b.lounge_name}\n"
            f"   👤 Booker: {b.booker_name}\n"
            f"   📅 Booking Date: {b.booking_date}\n"
            f"   🕐 Time: {b.booking_time}\n\n"
        )
        
    await callback.message.edit_text(text)

# ──────────────────── Booking Flow ────────────────────

@router.callback_query(F.data == "tv_book")
async def start_tv_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "📝 Book TV Lounge\n\nPlease select a TV Lounge to book:",
        reply_markup=get_tv_lounges_kb()
    )
    await state.set_state(BookTVState.waiting_for_lounge_selection)

@router.callback_query(BookTVState.waiting_for_lounge_selection, F.data.startswith("tv_lounge_"))
async def process_lounge_selection(callback: CallbackQuery, state: FSMContext):
    lounge = callback.data.split("_")[2]
    await state.update_data(lounge_name=lounge)
    await callback.message.edit_text("👤 Booker Name\n\nPlease enter the booker's name:")
    await state.set_state(BookTVState.waiting_for_booker_name)

@router.message(BookTVState.waiting_for_booker_name)
async def process_booker_name(message: Message, state: FSMContext):
    await state.update_data(booker_name=message.text.strip())
    await message.answer(
        "📅 Date\n\n"
        "Please enter the date (Format: DD/MM, e.g. 29/05):"
    )
    await state.set_state(BookTVState.waiting_for_booking_date)

@router.message(BookTVState.waiting_for_booking_date)
async def process_booking_date(message: Message, state: FSMContext):
    date_str = message.text.strip()
    match = re.match(r"^(\d{2})/(\d{2})(?:/(\d{4}))?$", date_str)
    if not match:
        await message.answer("Invalid format. Please enter date in DD/MM format (e.g. 29/05):")
        return
        
    try:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else datetime.now().year
        parsed_date = datetime(year, month, day)
    except ValueError:
        await message.answer("That is not a valid calendar date. Please enter a valid date (DD/MM):")
        return
        
    # Check if date is in the past (comparing date part only)
    now = datetime.now()
    if parsed_date.date() < now.date():
        await message.answer("❌ Past dates are not allowed. Please enter a valid date (DD/MM):")
        return

    await state.update_data(booking_date_obj=parsed_date.strftime("%Y-%m-%d"), booking_date_str=date_str)
    await message.answer(
        "🕐 Time\n\n"
        "Please enter the start time (Format: HH:MM, e.g. 18:00):"
    )
    await state.set_state(BookTVState.waiting_for_booking_time)

@router.message(BookTVState.waiting_for_booking_time)
async def process_booking_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
        await message.answer("Invalid format. Please enter time in HH:MM format (e.g. 18:00):")
        return
        
    data = await state.get_data()
    lounge_name = data.get("lounge_name")
    booker_name = data.get("booker_name")
    date_obj_str = data.get("booking_date_obj")
    date_str = data.get("booking_date_str")
    
    # Combined date & time validation
    now = datetime.now()
    try:
        booking_dt = datetime.combine(
            datetime.strptime(date_obj_str, "%Y-%m-%d").date(),
            datetime.strptime(time_str, "%H:%M").time()
        )
    except Exception:
        await message.answer("An error occurred during verification. Please re-enter the date (DD/MM):")
        await state.set_state(BookTVState.waiting_for_booking_date)
        return
        
    if booking_dt < now:
        await message.answer(
            "❌ Past Date / Time Not Allowed!\n\n"
            f"The date & time you entered ({date_str} at {time_str}) is in the past.\n"
            "Please enter a valid future time (HH:MM) or restart date (DD/MM):"
        )
        return

    booking_id = data.get("edit_booking_id")
    
    if booking_id:
        # Edit existing
        booking = await get_tv_booking_by_id(booking_id)
        if booking:
            # Delete old reminder if exists
            await delete_reminder(
                message.from_user.id, "tv", 
                booking.lounge_name, booking.booking_date, booking.booking_time
            )
            
            # Update booking
            await update_tv_booking(booking_id, lounge_name, booker_name, date_str, time_str)
            
            # Add new automatic reminder 15 minutes before
            await add_reminder(message.from_user.id, "tv", lounge_name, date_str, time_str, 15)
            await message.answer(
                f"✅ Booking Updated Successfully!\n\n"
                f"🏛️ Lounge: Lounge {lounge_name}\n"
                f"👤 Booker: {booker_name}\n"
                f"📅 Date: {date_str}\n"
                f"🕐 Time: {time_str}\n\n"
                f"🔔 A reminder has been set for 15 minutes before."
            )
        else:
            await message.answer("Error: Booking could not be found.")
    else:
        # Create new booking
        await add_tv_booking(message.from_user.id, lounge_name, booker_name, date_str, time_str)
        
        # Add automatic reminder 15 minutes before
        await add_reminder(message.from_user.id, "tv", lounge_name, date_str, time_str, 15)
        
        await message.answer(
            f"✅ Booking Confirmed!\n\n"
            f"🏛️ Lounge: Lounge {lounge_name}\n"
            f"👤 Booker: {booker_name}\n"
            f"📅 Date: {date_str}\n"
            f"🕐 Time: {time_str}\n\n"
            f"🔔 A reminder has been set for 15 minutes before."
        )
            
    await state.clear()

# ──────────────────── Edit Booking Flow ────────────────────

@router.callback_query(F.data == "tv_edit")
async def start_tv_edit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    bookings = await get_tv_bookings(callback.from_user.id)
        
    if not bookings:
        await callback.message.edit_text("You have no TV Lounge bookings to edit.")
        return
        
    builder = InlineKeyboardBuilder()
    for b in bookings:
        builder.button(
            text=f"✏️ {b.lounge_name} - {b.booking_date} ({b.booking_time})",
            callback_data=f"tv_edit_sel_{b.id}"
        )
    builder.button(text="Back", callback_data="tv_menu_back")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "✏️ Edit Booking\n\nPlease select which booking you want to edit:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("tv_edit_sel_"))
async def process_tv_edit_selection(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.split("_")[3])
    booking = await get_tv_booking_by_id(booking_id)
        
    if not booking:
        await callback.message.edit_text("Booking not found.", reply_markup=get_tv_submenu_kb())
        return
        
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit Details", callback_data=f"tv_action_edit_{booking_id}")
    builder.button(text="❌ Delete Booking", callback_data=f"tv_action_delete_{booking_id}")
    builder.button(text="Back", callback_data="tv_edit")
    builder.adjust(1)
    
    text = (
        f"📋 Manage Booking:\n\n"
        f"🏛️ Lounge: Lounge {booking.lounge_name}\n"
        f"👤 Booker: {booking.booker_name}\n"
        f"📅 Date: {booking.booking_date}\n"
        f"🕐 Time: {booking.booking_time}\n\n"
        f"What would you like to do?"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("tv_action_edit_"))
async def process_tv_edit_details(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.split("_")[3])
    await state.update_data(edit_booking_id=booking_id)
    
    await callback.message.edit_text(
        "✏️ Editing Booking\n\nPlease select the new TV Lounge:",
        reply_markup=get_tv_lounges_kb()
    )
    await state.set_state(BookTVState.waiting_for_lounge_selection)

@router.callback_query(F.data.startswith("tv_action_delete_"))
async def process_tv_delete(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[3])
    booking = await get_tv_booking_by_id(booking_id)
        
    if booking:
        # Delete associated reminder
        await delete_reminder(
            callback.from_user.id, "tv", 
            booking.lounge_name, booking.booking_date, booking.booking_time
        )
        # Delete booking
        await delete_tv_booking(booking_id)
        await callback.message.edit_text(
            "✅ Booking Deleted Successfully!",
            reply_markup=get_tv_submenu_kb()
        )
    else:
        await callback.message.edit_text(
            "❌ Error: Booking could not be found.",
            reply_markup=get_tv_submenu_kb()
        )

