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
            [KeyboardButton(text="⭐ Подписка")],
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
    )


def get_stop_words_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить стоп-слово")],
            [KeyboardButton(text="🗑 Удалить стоп-слово")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
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
    builder.row(
        InlineKeyboardButton(text="🌍 Другая страна", callback_data=f"{prefix}:OTHER"),
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
    builder.row(
        InlineKeyboardButton(text="🌍 Другая страна", callback_data="request_country:OTHER"),
    )
    return builder.as_markup()


def build_subscription_method_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐ Оплата Stars", callback_data="payment_method:stars"),
    )
    builder.row(
        InlineKeyboardButton(text="💳 Оплата ЮMoney", callback_data="payment_method:yoomoney"),
    )
    return builder.as_markup()


def build_subscription_keyboard(payment_method: str = "stars") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 месяц — 200 RUB", callback_data=f"buy_sub:{payment_method}:30"),
    )
    builder.row(
        InlineKeyboardButton(text="3 месяца — 300 RUB", callback_data=f"buy_sub:{payment_method}:90"),
    )
    builder.row(
        InlineKeyboardButton(text="12 месяцев — 1000 RUB", callback_data=f"buy_sub:{payment_method}:365"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к способам оплаты", callback_data="payment_back"),
    )
    return builder.as_markup()