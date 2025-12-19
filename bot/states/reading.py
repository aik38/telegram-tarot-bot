from aiogram.fsm.state import State, StatesGroup


class ReadingStates(StatesGroup):
    choosing_spread = State()
    waiting_question = State()
