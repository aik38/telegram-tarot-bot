from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.common import menu_only_kb
from bot.keyboards.main_menu import main_menu_kb
from bot.texts.ja import HELP_TEXT, SUPPORT_TEXT, TERMS_TEXT


async def _send_with_menu(target, text: str) -> None:
    await target.answer(
        text,
        reply_markup=menu_only_kb(),
        parse_mode="Markdown",
    )


async def command_help(message: Message) -> None:
    await _send_with_menu(message, HELP_TEXT)


async def menu_help(query: CallbackQuery) -> None:
    await _send_with_menu(query.message, HELP_TEXT)
    await query.answer()


async def menu_terms(query: CallbackQuery) -> None:
    await _send_with_menu(query.message, TERMS_TEXT)
    await query.answer()


async def menu_support(query: CallbackQuery) -> None:
    await _send_with_menu(query.message, SUPPORT_TEXT)
    await query.answer()


async def back_to_menu(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.answer()
    if query.message:
        await query.message.answer("メニューはこちらからどうぞ。", reply_markup=main_menu_kb())


def create_router() -> Router:
    router = Router()
    router.message.register(command_help, Command("help"))
    router.callback_query.register(menu_help, F.data == "menu:help")
    router.callback_query.register(menu_terms, F.data == "menu:terms")
    router.callback_query.register(menu_support, F.data == "menu:support")
    router.callback_query.register(back_to_menu, F.data == "nav:menu")
    return router


__all__ = ["create_router"]
