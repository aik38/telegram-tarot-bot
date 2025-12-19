from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def nav_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="↩️ 戻る", callback_data="nav:back"),
                InlineKeyboardButton(text="🔄 やり直す", callback_data="nav:restart"),
            ],
            [InlineKeyboardButton(text="🏠 メニュー", callback_data="nav:menu")],
        ]
    )


def menu_only_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 メニューへ戻る", callback_data="nav:menu")]]
    )
