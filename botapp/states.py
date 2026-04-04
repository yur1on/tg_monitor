from aiogram.fsm.state import State, StatesGroup


class KeywordStates(StatesGroup):
    waiting_for_new_keyword = State()


class StopWordStates(StatesGroup):
    waiting_for_new_stop_word = State()


class ChatRequestStates(StatesGroup):
    waiting_for_country = State()
    waiting_for_chat_request = State()


class ChatStates(StatesGroup):
    choosing_country = State()