from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🧩 Мои ключевые слова"),
                KeyboardButton(text="💬 Мои чаты"),
            ],
            [
                KeyboardButton(text="⚙️ Общее"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел",
    )


def get_general_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛑 Стоп-слова")],
            [KeyboardButton(text="💳 Подписка")],
            [KeyboardButton(text="ℹ️ Информация")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Раздел «Общее»",
    )


def get_keywords_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить слово")],
            [KeyboardButton(text="🗑 Удалить слово")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Управление ключевыми словами",
    )


def get_stop_words_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить стоп-слово")],
            [KeyboardButton(text="🗑 Удалить стоп-слово")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Управление стоп-словами",
    )


def get_chats_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📂 Выбрать чат")],
            [KeyboardButton(text="➕ Предложить новый чат")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Управление чатами",
    )


def build_country_select_keyboard(prefix: str = "chat_country") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇧🇾 Беларусь", callback_data=f"{prefix}:BY"),
        InlineKeyboardButton(text="🇷🇺 Россия", callback_data=f"{prefix}:RU"),
    )
    return builder.as_markup()


def build_chats_inline_keyboard(chats: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for chat in chats:
        status_icon = "🟢" if chat["is_connected"] else "⚪️"
        action_text = "Отключить" if chat["is_connected"] else "Подключить"
        text = f"{status_icon} {action_text}: {chat['short_title']}"
        callback_data = f"chat_toggle:{chat['id']}"
        builder.row(
            InlineKeyboardButton(text=text, callback_data=callback_data)
        )

    return builder.as_markup()


def build_keywords_delete_keyboard(keywords: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for keyword in keywords:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {keyword.phrase}",
                callback_data=f"keyword_delete:{keyword.id}"
            )
        )

    return builder.as_markup()


def build_stop_words_delete_keyboard(stop_words: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for stop_word in stop_words:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {stop_word.phrase}",
                callback_data=f"stopword_delete:{stop_word.id}"
            )
        )

    return builder.as_markup()


def build_chat_request_country_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇧🇾 Беларусь", callback_data="request_country:BY"),
        InlineKeyboardButton(text="🇷🇺 Россия", callback_data="request_country:RU"),
    )
    return builder.as_markup()