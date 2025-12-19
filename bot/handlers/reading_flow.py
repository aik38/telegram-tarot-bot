from typing import Callable, Optional

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ContentType, Message

from bot.keyboards.common import nav_kb
from bot.keyboards.main_menu import main_menu_kb, spread_select_kb
from bot.states.reading import ReadingStates
from bot.texts.ja import (
    QUESTION_PROMPT_TEXT,
    RETRY_READING_TEXT,
    SPREAD_SELECT_TEXT,
)
from bot.utils.validators import validate_question_text
from core.tarot import ONE_CARD, THREE_CARD_SITUATION
from core.tarot.spreads import Spread

_execute_tarot_request: Optional[Callable[..., object]] = None
_get_start_text: Optional[Callable[[], str]] = None
_persistent_menu_kb: Optional[Callable[[], object]] = None


def setup_dependencies(
    *,
    execute_tarot_request: Callable[..., object],
    get_start_text: Callable[[], str],
    persistent_menu_kb: Callable[[], object],
) -> None:
    global _execute_tarot_request, _get_start_text, _persistent_menu_kb
    _execute_tarot_request = execute_tarot_request
    _get_start_text = get_start_text
    _persistent_menu_kb = persistent_menu_kb


def _resolve_spread(spread_id: str | None) -> Spread:
    if spread_id == THREE_CARD_SITUATION.id:
        return THREE_CARD_SITUATION
    return ONE_CARD


async def _send_main_menu(message: Message) -> None:
    text = _get_start_text() if _get_start_text else "メニューに戻りました。"
    legacy_kb = _persistent_menu_kb() if _persistent_menu_kb else None
    await message.answer(text, reply_markup=legacy_kb)
    await message.answer("操作を選んでください👇", reply_markup=main_menu_kb())


async def start_reading(query: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReadingStates.choosing_spread)
    await query.answer()
    if query.message:
        await query.message.answer(SPREAD_SELECT_TEXT, reply_markup=spread_select_kb())


async def choose_spread(query: CallbackQuery, state: FSMContext) -> None:
    data = query.data or ""
    await query.answer()
    if data == "spread:one":
        await state.set_state(ReadingStates.waiting_question)
        await state.update_data(spread_id=ONE_CARD.id)
        if query.message:
            await query.message.answer(QUESTION_PROMPT_TEXT, reply_markup=nav_kb())
        return

    if data == "spread:three":
        await state.set_state(ReadingStates.waiting_question)
        await state.update_data(spread_id=THREE_CARD_SITUATION.id)
        if query.message:
            await query.message.answer(QUESTION_PROMPT_TEXT, reply_markup=nav_kb())
        return


async def navigate_back(query: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    await query.answer()
    if current_state == ReadingStates.waiting_question.state:
        await state.set_state(ReadingStates.choosing_spread)
        if query.message:
            await query.message.answer(SPREAD_SELECT_TEXT, reply_markup=spread_select_kb())


async def navigate_restart(query: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReadingStates.choosing_spread)
    await query.answer()
    if query.message:
        await query.message.answer(SPREAD_SELECT_TEXT, reply_markup=spread_select_kb())


async def help_during_question(message: Message, state: FSMContext) -> None:
    await state.set_state(ReadingStates.choosing_spread)
    await message.answer(SPREAD_SELECT_TEXT, reply_markup=spread_select_kb())


async def remind_spread_choice(message: Message) -> None:
    await message.answer(SPREAD_SELECT_TEXT, reply_markup=spread_select_kb())


async def receive_question(message: Message, state: FSMContext) -> None:
    is_text = message.content_type == ContentType.TEXT
    ok, error_message = validate_question_text(message.text if is_text else None, is_text=is_text)
    if not ok:
        await message.answer(error_message, reply_markup=nav_kb())
        return

    data = await state.get_data()
    spread_id = data.get("spread_id")
    spread = _resolve_spread(spread_id)

    if _execute_tarot_request is None:
        await message.answer(RETRY_READING_TEXT, reply_markup=main_menu_kb())
        await state.clear()
        return

    try:
        await _execute_tarot_request(
            message,
            user_query=message.text.strip(),
            spread=spread,
        )
    except Exception:
        await message.answer(RETRY_READING_TEXT, reply_markup=nav_kb())
    finally:
        await state.clear()
        await _send_main_menu(message)


def create_router() -> Router:
    router = Router()
    router.callback_query.register(start_reading, F.data == "menu:read")
    router.callback_query.register(choose_spread, F.data.startswith("spread:"))
    router.callback_query.register(navigate_back, F.data == "nav:back")
    router.callback_query.register(navigate_restart, F.data == "nav:restart")
    router.message.register(
        help_during_question, Command("help"), StateFilter(ReadingStates.waiting_question)
    )
    router.message.register(remind_spread_choice, StateFilter(ReadingStates.choosing_spread))
    router.message.register(receive_question, StateFilter(ReadingStates.waiting_question))
    return router


__all__ = ["create_router", "setup_dependencies"]
