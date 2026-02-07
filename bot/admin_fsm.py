from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    choosing_section = State()
    choosing_item = State()
    editing_field = State()
    waiting_value = State()
    importing_config = State()
