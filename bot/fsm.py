from aiogram.fsm.state import State, StatesGroup


class CalcStates(StatesGroup):
    awaiting_area = State()
    choosing_foundation = State()
    choosing_walls = State()
    choosing_floors = State()
    choosing_roof = State()
    choosing_extras = State()
    showing_result = State()
