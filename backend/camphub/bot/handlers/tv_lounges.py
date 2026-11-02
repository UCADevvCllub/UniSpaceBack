from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..format import header, empty, compose

router = Router()

# TV Lounges is temporarily disabled. The main-menu button stays visible,
# but every entry point (including stale inline keyboards and in-progress
# booking flows persisted in FSM storage) just shows this message.
COMING_SOON_TEXT = compose(
    header("📺", "TV Lounges"),
    empty("🚧 Coming soon — this feature is not available yet. Stay tuned!"),
)


class BookTVState(StatesGroup):
    # Kept so FSM states persisted from the old booking flow are still
    # recognised (and cleared) instead of leaving users stuck in them.
    waiting_for_lounge_selection = State()
    waiting_for_booker_name = State()
    waiting_for_booking_date = State()
    waiting_for_booking_time = State()


@router.message(F.text == "📺 TV Lounges")
async def tv_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(COMING_SOON_TEXT, parse_mode="HTML")


@router.message(BookTVState.waiting_for_lounge_selection)
@router.message(BookTVState.waiting_for_booker_name)
@router.message(BookTVState.waiting_for_booking_date)
@router.message(BookTVState.waiting_for_booking_time)
async def tv_booking_flow_disabled(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(COMING_SOON_TEXT, parse_mode="HTML")


@router.callback_query(F.data.startswith("tv_"))
async def tv_coming_soon_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(COMING_SOON_TEXT, parse_mode="HTML")
    except Exception:
        # Message may already show this text or no longer be editable.
        pass
    await callback.answer("🚧 TV Lounges — coming soon!")
