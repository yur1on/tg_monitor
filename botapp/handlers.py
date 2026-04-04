from html import escape

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from users.services import get_or_create_app_user
from monitor.services import (
    get_user_keywords,
    add_user_keyword,
    delete_user_keyword_by_id,
    get_user_stop_words,
    add_user_stop_word,
    delete_user_stop_word_by_id,
    get_chats_by_country_with_status,
    toggle_user_chat,
    create_chat_request,
)
from .keyboards import (
    get_main_menu,
    get_general_menu,
    get_keywords_menu,
    get_stop_words_menu,
    get_chats_menu,
    build_country_select_keyboard,
    build_chats_inline_keyboard,
    build_keywords_delete_keyboard,
    build_stop_words_delete_keyboard,
    build_chat_request_country_keyboard,
)
from .states import KeywordStates, StopWordStates, ChatRequestStates, ChatStates

router = Router()


COUNTRY_LABELS = {
    "BY": "Беларусь",
    "RU": "Россия",
}

COUNTRY_EMOJIS = {
    "BY": "🇧🇾",
    "RU": "🇷🇺",
}


async def render_chats_by_country(target, telegram_id: int, country: str):
    chats = await sync_to_async(get_chats_by_country_with_status)(telegram_id, country)

    country_label = COUNTRY_LABELS.get(country, country)
    country_emoji = COUNTRY_EMOJIS.get(country, "🌍")

    if not chats:
        text = (
            f"<b>💬 Выбор чатов</b>\n"
            f"{country_emoji} <b>Страна:</b> {country_label}\n\n"
            f"Пока нет доступных чатов для этой страны."
        )
        if isinstance(target, Message):
            await target.answer(text, parse_mode="HTML")
        else:
            await target.message.edit_text(text, parse_mode="HTML")
        return

    connected_count = sum(1 for chat in chats if chat["is_connected"])
    total_count = len(chats)

    lines = [
        "<b>💬 Выбор чатов</b>",
        f"{country_emoji} <b>Страна:</b> {country_label}",
        "",
        f"<b>Всего чатов:</b> {total_count}",
        f"<b>Подключено:</b> {connected_count}",
        "",
        "<b>Список чатов:</b>",
    ]

    for chat in chats:
        status = "✅" if chat["is_connected"] else "❌"
        lines.append(f"{status} {escape(chat['short_title'])}")

    lines.append("")
    lines.append("<b>👇 Нажмите на кнопку ниже, чтобы подключить или отключить чат</b>")

    text = "\n".join(lines)
    keyboard = build_chats_inline_keyboard(chats)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await target.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()

    tg_user = message.from_user

    await sync_to_async(get_or_create_app_user)(
        telegram_id=tg_user.id,
        username=tg_user.username or "",
        first_name=tg_user.first_name or "",
    )

    text = (
        "<b>Добро пожаловать.</b>\n\n"
        "Этот бот помогает мониторить Telegram-чаты по вашим ключевым словам.\n\n"
        "<b>Что можно делать:</b>\n"
        "• отслеживать сообщения по ключевым словам\n"
        "• исключать мусор через стоп-слова\n"
        "• выбирать чаты по странам\n"
        "• предлагать новые чаты для добавления"
    )

    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

@router.message(F.text == "⚙️ Общее")
async def general_menu_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>⚙️ Раздел «Общее»</b>\n\nВыберите нужный пункт.",
        reply_markup=get_general_menu(),
        parse_mode="HTML",
    )


@router.message(F.text.in_(["⬅️ Назад", "Назад"]))
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>Главное меню</b>",
        reply_markup=get_main_menu(),
        parse_mode="HTML",
    )


# =========================
# КЛЮЧЕВЫЕ СЛОВА
# =========================

@router.message(F.text.in_(["🧩 Мои ключевые слова", "Мои ключевые слова"]))
async def keywords_handler(message: Message, state: FSMContext):
    await state.clear()

    keywords = await sync_to_async(get_user_keywords)(message.from_user.id)

    if keywords:
        text = "<b>🧩 Ваши ключевые слова:</b>\n\n" + "\n".join(
            f"• {escape(keyword.phrase)}" for keyword in keywords
        )
    else:
        text = "У вас пока нет ключевых слов."

    await message.answer(text, reply_markup=get_keywords_menu(), parse_mode="HTML")


@router.message(F.text.in_(["➕ Добавить слово", "Добавить слово"]))
async def add_keyword_start(message: Message, state: FSMContext):
    await state.set_state(KeywordStates.waiting_for_new_keyword)
    await message.answer(
        "<b>Введите новое ключевое слово или фразу.</b>\n\n"
        "Примеры:\n"
        "• ищу дисплей\n"
        "• куплю плату\n"
        "• iphone 11",
        parse_mode="HTML",
    )


@router.message(KeywordStates.waiting_for_new_keyword)
async def add_keyword_finish(message: Message, state: FSMContext):
    phrase = (message.text or "").strip()

    if len(phrase) < 2:
        await message.answer("Слишком короткое слово. Введите нормальное ключевое слово.")
        return

    keyword, created = await sync_to_async(add_user_keyword)(
        message.from_user.id,
        phrase
    )

    await state.clear()

    if not keyword:
        await message.answer("Не удалось добавить слово.", reply_markup=get_keywords_menu())
        return

    if created:
        await message.answer(
            f"Ключевое слово добавлено: <b>{escape(phrase)}</b>",
            reply_markup=get_keywords_menu(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"Такое слово уже есть: <b>{escape(phrase)}</b>",
            reply_markup=get_keywords_menu(),
            parse_mode="HTML",
        )


@router.message(F.text.in_(["🗑 Удалить слово", "Удалить слово"]))
async def delete_keyword_start(message: Message, state: FSMContext):
    await state.clear()

    keywords = await sync_to_async(get_user_keywords)(message.from_user.id)

    if not keywords:
        await message.answer("У вас нет слов для удаления.", reply_markup=get_keywords_menu())
        return

    await message.answer(
        "<b>Нажмите на ключевое слово, которое хотите удалить:</b>",
        reply_markup=build_keywords_delete_keyboard(keywords),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("keyword_delete:"))
async def keyword_delete_callback(callback: CallbackQuery):
    raw_keyword_id = callback.data.split(":")[1]

    if not raw_keyword_id.isdigit():
        await callback.answer("Некорректный ID", show_alert=True)
        return

    keyword_id = int(raw_keyword_id)

    success, keyword = await sync_to_async(delete_user_keyword_by_id)(
        callback.from_user.id,
        keyword_id
    )

    if not success:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    await callback.answer(f"Удалено: {keyword.phrase}")

    keywords = await sync_to_async(get_user_keywords)(callback.from_user.id)

    if not keywords:
        await callback.message.edit_text("У вас больше нет ключевых слов.")
    else:
        await callback.message.edit_text(
            "<b>Нажмите на ключевое слово, которое хотите удалить:</b>",
            reply_markup=build_keywords_delete_keyboard(keywords),
            parse_mode="HTML",
        )


# =========================
# СТОП-СЛОВА
# =========================

@router.message(F.text.in_(["🛑 Стоп-слова", "Стоп-слова"]))
async def stop_words_handler(message: Message, state: FSMContext):
    await state.clear()

    stop_words = await sync_to_async(get_user_stop_words)(message.from_user.id)

    if stop_words:
        text = "<b>🛑 Ваши стоп-слова:</b>\n\n" + "\n".join(
            f"• {escape(stop_word.phrase)}" for stop_word in stop_words
        )
    else:
        text = "У вас пока нет стоп-слов."

    await message.answer(text, reply_markup=get_stop_words_menu(), parse_mode="HTML")


@router.message(F.text.in_(["➕ Добавить стоп-слово", "Добавить стоп-слово"]))
async def add_stop_word_start(message: Message, state: FSMContext):
    await state.set_state(StopWordStates.waiting_for_new_stop_word)
    await message.answer(
        "<b>Введите стоп-слово или фразу.</b>\n\n"
        "Примеры:\n"
        "• продам\n"
        "• в наличии\n"
        "• акция",
        parse_mode="HTML",
    )


@router.message(StopWordStates.waiting_for_new_stop_word)
async def add_stop_word_finish(message: Message, state: FSMContext):
    phrase = (message.text or "").strip()

    if len(phrase) < 2:
        await message.answer("Слишком короткое стоп-слово. Введите нормальное значение.")
        return

    stop_word, created = await sync_to_async(add_user_stop_word)(
        message.from_user.id,
        phrase
    )

    await state.clear()

    if not stop_word:
        await message.answer("Не удалось добавить стоп-слово.", reply_markup=get_stop_words_menu())
        return

    if created:
        await message.answer(
            f"Стоп-слово добавлено: <b>{escape(phrase)}</b>",
            reply_markup=get_stop_words_menu(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"Такое стоп-слово уже есть: <b>{escape(phrase)}</b>",
            reply_markup=get_stop_words_menu(),
            parse_mode="HTML",
        )


@router.message(F.text.in_(["🗑 Удалить стоп-слово", "Удалить стоп-слово"]))
async def delete_stop_word_start(message: Message, state: FSMContext):
    await state.clear()

    stop_words = await sync_to_async(get_user_stop_words)(message.from_user.id)

    if not stop_words:
        await message.answer("У вас нет стоп-слов для удаления.", reply_markup=get_stop_words_menu())
        return

    await message.answer(
        "<b>Нажмите на стоп-слово, которое хотите удалить:</b>",
        reply_markup=build_stop_words_delete_keyboard(stop_words),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("stopword_delete:"))
async def stop_word_delete_callback(callback: CallbackQuery):
    raw_stop_word_id = callback.data.split(":")[1]

    if not raw_stop_word_id.isdigit():
        await callback.answer("Некорректный ID", show_alert=True)
        return

    stop_word_id = int(raw_stop_word_id)

    success, stop_word = await sync_to_async(delete_user_stop_word_by_id)(
        callback.from_user.id,
        stop_word_id
    )

    if not success:
        await callback.answer("Стоп-слово не найдено", show_alert=True)
        return

    await callback.answer(f"Удалено: {stop_word.phrase}")

    stop_words = await sync_to_async(get_user_stop_words)(callback.from_user.id)

    if not stop_words:
        await callback.message.edit_text("У вас больше нет стоп-слов.")
    else:
        await callback.message.edit_text(
            "<b>Нажмите на стоп-слово, которое хотите удалить:</b>",
            reply_markup=build_stop_words_delete_keyboard(stop_words),
            parse_mode="HTML",
        )


# =========================
# ЧАТЫ
# =========================

@router.message(F.text.in_(["💬 Мои чаты", "Мои чаты"]))
async def chats_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>💬 Раздел «Мои чаты»</b>\n\n"
        "Здесь вы можете:\n"
        "• открыть список чатов по стране\n"
        "• предложить новый чат для добавления",
        reply_markup=get_chats_menu(),
        parse_mode="HTML",
    )


@router.message(F.text.in_(["📂 Выбрать чат", "Выбрать чат"]))
async def choose_chat_country_handler(message: Message, state: FSMContext):
    await state.set_state(ChatStates.choosing_country)
    await message.answer(
        "<b>Выберите страну:</b>",
        reply_markup=build_country_select_keyboard("chat_country"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("chat_country:"))
async def chat_country_callback(callback: CallbackQuery, state: FSMContext):
    country = callback.data.split(":")[1]
    await state.clear()

    await callback.answer(f"Открываю чаты: {COUNTRY_LABELS.get(country, country)}")
    await render_chats_by_country(callback, callback.from_user.id, country)


@router.callback_query(F.data.startswith("chat_toggle:"))
async def chat_toggle_callback(callback: CallbackQuery, state: FSMContext):
    raw_chat_id = callback.data.split(":")[1]

    if not raw_chat_id.isdigit():
        await callback.answer("Некорректный ID", show_alert=True)
        return

    chat_id = int(raw_chat_id)

    try:
        success, result, chat = await sync_to_async(toggle_user_chat)(
            callback.from_user.id,
            chat_id
        )
    except Exception:
        await callback.answer("Не удалось изменить статус", show_alert=True)
        return

    if result == "connected":
        await callback.answer(f'Чат "{chat.title}" подключен')
    else:
        await callback.answer(f'Чат "{chat.title}" отключен')

    await render_chats_by_country(callback, callback.from_user.id, chat.country)


# =========================
# ЗАЯВКИ НА ЧАТЫ
# =========================

@router.message(F.text.in_(["➕ Предложить новый чат", "Предложить новый чат"]))
async def request_chat_start(message: Message, state: FSMContext):
    await state.set_state(ChatRequestStates.waiting_for_country)
    await message.answer(
        "<b>Для какой страны вы хотите предложить чат?</b>",
        reply_markup=build_chat_request_country_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("request_country:"))
async def request_country_callback(callback: CallbackQuery, state: FSMContext):
    country = callback.data.split(":")[1]
    await state.update_data(request_country=country)
    await state.set_state(ChatRequestStates.waiting_for_chat_request)

    await callback.answer(f"Выбрана страна: {COUNTRY_LABELS.get(country, country)}")
    await callback.message.edit_text(
        f"<b>Страна выбрана:</b> {COUNTRY_LABELS.get(country, country)}\n\n"
        f"Теперь отправьте username чата или ссылку.\n\n"
        f"Примеры:\n"
        f"@zapchastygsm\n"
        f"https://t.me/zapchastygsm",
        parse_mode="HTML",
    )


@router.message(ChatRequestStates.waiting_for_chat_request)
async def request_chat_finish(message: Message, state: FSMContext):
    chat_input = (message.text or "").strip()

    if len(chat_input) < 3:
        await message.answer("Слишком короткое значение. Отправьте username или ссылку.")
        return

    data = await state.get_data()
    country = data.get("request_country")

    if not country:
        await state.clear()
        await message.answer("Сначала выберите страну заявки.", reply_markup=get_main_menu())
        return

    request_obj = await sync_to_async(create_chat_request)(
        message.from_user.id,
        country,
        chat_input,
        "",
    )

    await state.clear()

    if not request_obj:
        await message.answer("Не удалось сохранить заявку.", reply_markup=get_main_menu())
        return

    await message.answer(
        "<b>Заявка на добавление чата отправлена.</b>\n\n"
        "Я увижу её в админке, вступлю в чат и добавлю в общий список.",
        reply_markup=get_main_menu(),
        parse_mode="HTML",
    )


# =========================
# ОБЩЕЕ
# =========================

@router.message(F.text.in_(["💳 Подписка", "Подписка"]))
async def subscription_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Раздел подписки пока не подключен.",
        reply_markup=get_general_menu(),
    )


@router.message(F.text.in_(["ℹ️ Информация", "Информация"]))
async def info_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>ℹ️ О боте</b>\n\n"
        "Этот бот мониторит выбранные Telegram-чаты и присылает уведомления, "
        "если в сообщениях встречаются ваши ключевые слова.\n\n"
        "<b>Как работает поиск:</b>\n"
        "• вы добавляете ключевые слова\n"
        "• выбираете нужные чаты\n"
        "• бот анализирует новые сообщения\n"
        "• если найдено совпадение — приходит уведомление\n\n"
        "<b>Что делает бот дополнительно:</b>\n"
        "• игнорирует сообщения со стоп-словами\n"
        "• игнорирует дубли\n"
        "• если одинаковое сообщение повторяется в других чатах, бот не присылает его повторно\n\n"
        "<b>Это помогает:</b>\n"
        "• не получать лишний спам\n"
        "• быстрее видеть реальные новые запросы\n"
        "• удобнее мониторить много чатов сразу",
        reply_markup=get_general_menu(),
        parse_mode="HTML",
    )