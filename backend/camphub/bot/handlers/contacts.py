from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from ..keyboards.inline import get_contacts_submenu_kb
from ..crud import get_contacts_by_category
from ..format import header, info_card, compose, empty, menu

router = Router()


@router.message(F.text == "📞 Contacts")
async def contacts_menu(message: Message):
    await message.answer(
        menu("📞", "Contacts", "On campus or off campus?"),
        reply_markup=get_contacts_submenu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("contacts_"))
async def show_contacts(callback: CallbackQuery):
    cat_id = callback.data.split("_", 1)[1]
    category = "On Campus" if cat_id == "on_campus" else "Off Campus"

    contacts = await get_contacts_by_category(category)
    hdr = header("📞", f"{category} Contacts")

    if not contacts:
        await callback.message.edit_text(
            compose(hdr, empty(f"No {category.lower()} contacts available.")),
            parse_mode="HTML",
        )
        return

    cards = []
    for c in contacts:
        details = []
        if c.details:
            details.append(f"🪪 {c.details}")
        details.append(f"📱 {c.phone}")
        cards.append(info_card(f"👤 {c.name}", "", *details))

    await callback.message.edit_text(compose(hdr, *cards), parse_mode="HTML")
