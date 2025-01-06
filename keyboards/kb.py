from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.utils import load_config

del_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="confirm_del"),
         InlineKeyboardButton(text="Нет", callback_data="cancel_del")]
    ]
)

async def inline_choice_shop():
    config_list = load_config()
    keyboard = InlineKeyboardBuilder()
    for shop in config_list:
        keyboard.add(InlineKeyboardButton(text=shop["name_shop"], callback_data=f"{shop["name_shop"].lower()}"))
    return keyboard.adjust(2).as_markup()
