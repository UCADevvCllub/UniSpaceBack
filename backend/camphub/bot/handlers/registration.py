from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ..keyboards.inline import get_academic_level_kb, get_major_kb
from ..keyboards.reply import get_main_menu
from ..crud import get_user, create_user, update_user_level, update_user_major

router = Router()

class RegistrationState(StatesGroup):
    waiting_for_gender = State()
    waiting_for_level = State()
    waiting_for_major = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if user:
        await message.answer(
            f"Welcome back, {message.from_user.first_name or 'Student'}! 🌟\n"
            f"Here is your MAIN MENU. Use the buttons below to navigate.",
            reply_markup=get_main_menu()
        )
    else:
        # Start combined registration flow
        await state.set_state(RegistrationState.waiting_for_gender)
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Male"), KeyboardButton(text="Female")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            "🌟 <b>Welcome to the UCA Campus Assistant!</b> 🎓\n\n"
            "I'm here to help you navigate campus life seamlessly.\n"
            "To personalize your experience, please select your gender first: 👇",
            reply_markup=kb,
            parse_mode="HTML"
        )

@router.message(RegistrationState.waiting_for_gender)
async def process_gender(message: Message, state: FSMContext):
    gender_text = message.text.strip()
    if gender_text not in ["Male", "Female"]:
        await message.answer("Please use the buttons provided to select your gender (Male/Female).")
        return
        
    await state.update_data(gender=gender_text)
    await state.set_state(RegistrationState.waiting_for_level)
    
    # Hide the reply keyboard
    await message.answer(
        "Gender recorded! ✅",
        reply_markup=ReplyKeyboardRemove()
    )
    # Ask for Academic Level
    await message.answer(
        "Now, please select your current academic level below: 👇",
        reply_markup=get_academic_level_kb()
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
            parse_mode="HTML"
        )
    else:
        # Existing user updating their level
        await update_user_level(callback.from_user.id, level)
        await callback.message.edit_text(f"🎓 Academic level updated to: {level}")
        await callback.message.answer(
            "Here is your MAIN MENU. Use the buttons below to navigate.",
            reply_markup=get_main_menu()
        )
    await callback.answer()

@router.callback_query(F.data.startswith("major_"))
async def process_major_selection(callback: CallbackQuery, state: FSMContext):
    major = callback.data.split("_")[1]  # "CS" or "CM"
    current_state = await state.get_state()
    
    major_name = "Computer Science (CS)" if major == "CS" else "Communications and Media (CM)"
    
    if current_state == RegistrationState.waiting_for_major.state:
        data = await state.get_data()
        gender = data.get("gender", "Male")
        level = data.get("level", "Freshman")
        
        await create_user(
            telegram_id=callback.from_user.id,
            name=callback.from_user.full_name or "Student",
            gender=gender,
            cohort_name=level,
            major=major
        )
        await state.clear()
        
        await callback.message.edit_text(
            f"✅ <b>Registration complete!</b>\n\n"
            f"👤 <b>Gender:</b> {gender}\n"
            f"🎓 <b>Academic Level:</b> {level}\n"
            f"📚 <b>Major:</b> {major_name}",
            parse_mode="HTML"
        )
        await callback.message.answer(
            "Here is your MAIN MENU. Use the buttons below to navigate.",
            reply_markup=get_main_menu()
        )
    else:
        await update_user_major(callback.from_user.id, major)
        await callback.message.edit_text(f"📚 Major updated to: <b>{major_name}</b>", parse_mode="HTML")
        await callback.message.answer(
            "Here is your MAIN MENU. Use the buttons below to navigate.",
            reply_markup=get_main_menu()
        )
    await callback.answer()
