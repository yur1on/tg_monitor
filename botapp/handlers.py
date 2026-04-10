from html import escape

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async

from users.models import AppUser
from users.services import (
    get_or_create_app_user,
    ensure_user_trial,
    get_user_access_status,
    require_paid_access,
    extend_subscription,
)
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
from payments.services import create_yoomoney_invoice, build_yoomoney_quickpay_url
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
    build_subscription_keyboard,
    build_subscription_method_keyboard,
)
from .states import KeywordStates, StopWordStates, ChatRequestStates, ChatStates

router = Router()

COUNTRY_LABELS = {
    "BY": "Беларусь",
    "RU": "Россия",
    "OTHER": "Другая страна",
}

COUNTRY_EMOJIS = {
    "BY": "🇧🇾",
    "RU": "🇷🇺",
    "OTHER": "🌍",
}

PAYMENT_METHOD_LABELS = {
    "stars": "Telegram Stars",
    "yoomoney": "ЮMoney",
    "admin": "Выдано админом",
    "": "не указан",
}

SUBSCRIPTION_PLANS = {
    "30": {"title": "Подписка на 1 месяц", "stars": 100, "days": 30, "rub": 200},
    "90": {"title": "Подписка на 3 месяца", "stars": 250, "days": 90, "rub": 300},
    "365": {"title": "Подписка на 12 месяцев", "stars": 1000, "days": 365, "rub": 1000},
}


async def render_chats_by_country(target, telegram_id: int, country: str):
    chats = await sync_to_async(get_chats_by_country_with_status)(telegram_id, country)

    country_label = COUNTRY_LABELS.get(country, country)
    country_emoji = COUNTRY_EMOJIS.get(country, "🌍")

    if not chats:
        text = (
            f"<b>💬 Выбор чатов</b>\n"
            f"╭──────────────\n"
            f"{country_emoji} <b>Страна:</b> {country_label}\n"
            f"╰──────────────\n\n"
            "Пока нет доступных чатов для этой категории."
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
        "╭──────────────",
        f"{country_emoji} <b>Страна:</b> {country_label}",
        f"📊 <b>Всего чатов:</b> {total_count}",
        f"✅ <b>Подключено:</b> {connected_count}",
        "╰──────────────",
        "",
        "<b>📋 Список чатов</b>",
    ]

    for index, chat in enumerate(chats, start=1):
        status = "✅" if chat["is_connected"] else "❌"
        username = (chat.get("username") or "").strip().lstrip("@")
        title = escape(chat["short_title"])

        lines.append("──────────────")

        if username:
            chat_link = f"https://t.me/{username}"
            lines.append(f'{index}. {status} <a href="{chat_link}">{title}</a>')
        else:
            lines.append(f"{index}. {status} {title}")

    lines.append("──────────────")
    lines.append("")
    lines.append("👇 <b>Нажмите кнопку ниже, чтобы подключить или отключить чат</b>")

    text = "\n".join(lines)
    keyboard = build_chats_inline_keyboard(chats)

    if isinstance(target, Message):
        await target.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await target.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


async def ensure_access_or_paywall(message: Message) -> bool:
    has_access = await sync_to_async(require_paid_access)(message.from_user.id)
    if has_access:
        return True

    await message.answer(
        "<b>Доступ к этой функции закрыт.</b>\n\n"
        "Пробный период закончился. Выберите способ оплаты.",
        reply_markup=build_subscription_method_keyboard(),
        parse_mode="HTML",
    )
    return False


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()

    tg_user = message.from_user

    await sync_to_async(get_or_create_app_user)(
        telegram_id=tg_user.id,
        username=tg_user.username or "",
        first_name=tg_user.first_name or "",
    )

    await sync_to_async(ensure_user_trial)(tg_user.id)
    status = await sync_to_async(get_user_access_status)(tg_user.id)

    text = (
        "Этот бот собирает в одном месте только нужные вам сообщения из Telegram-чатов по ключевым словам.\n\n"
        "Вам не нужно вручную мониторить десятки чатов — бот сам отслеживает новые сообщения и присылает только подходящие совпадения.\n\n"
        "Это удобно, если:\n"
        "• вы продавец и следите, кто ищет товар или запчасти\n"
        "• вы покупатель и хотите быстро видеть, кто что продаёт\n\n"
        "<b>Что можно делать:</b>\n"
        "• отслеживать сообщения по ключевым словам\n"
        "• исключать мусор через стоп-слова\n"
        "• выбирать чаты по странам\n"
        "• предлагать новые чаты для добавления\n"
    )

    if status["has_active_trial"]:
        text += f"\n<b>🎁 Пробный период активен:</b> осталось {status['days_left']} дн."
    elif status["has_active_subscription"]:
        payment_method = PAYMENT_METHOD_LABELS.get(
            status["payment_method"],
            status["payment_method"] or "не указан"
        )
        text += (
            f"\n<b>⭐ Подписка активна:</b> осталось {status['days_left']} дн.\n"
            f"<b>Способ оплаты:</b> {payment_method}"
        )
    else:
        text += "\n<b>Пробный период завершён.</b> Для продолжения нужна подписка."

    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")


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


@router.message(F.text.in_(["🧩 Мои ключевые слова", "Мои ключевые слова"]))
async def keywords_handler(message: Message, state: FSMContext):
    await state.clear()

    if not await ensure_access_or_paywall(message):
        return

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
    if not await ensure_access_or_paywall(message):
        return

    await state.set_state(KeywordStates.waiting_for_new_keyword)
    await message.answer(
        "<b>Введите слово или фразу для отслеживания.</b>\n\n"
        "Если бот увидит это слово в новых сообщениях выбранных чатов, он пришлёт вам уведомление.\n\n"
        "<b>Примеры:</b>\n"
        "• куплю\n"
        "• ищу дисплей\n"
        "• iphone 17\n"
        "• нужен донор\n"
        "• ищу плату",
        parse_mode="HTML",
    )
@router.message(KeywordStates.waiting_for_new_keyword)
async def add_keyword_finish(message: Message, state: FSMContext):
    if not await ensure_access_or_paywall(message):
        await state.clear()
        return

    phrase = (message.text or "").strip()

    if len(phrase) < 2:
        await message.answer("Слишком короткое слово. Введите нормальное ключевое слово.")
        return

    try:
        keyword, created = await sync_to_async(add_user_keyword)(message.from_user.id, phrase)
    except Exception as e:
        print("Ошибка add_user_keyword:", repr(e))
        await state.clear()
        await message.answer(
            f"Ошибка сохранения: {escape(str(e)[:200])}",
            reply_markup=get_keywords_menu(),
            parse_mode="HTML",
        )
        return

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


@router.message(F.text.in_(["👁 Посмотреть / 🗑 удалить слово", "🗑 Удалить слово", "Удалить слово"]))
async def delete_keyword_start(message: Message, state: FSMContext):
    if not await ensure_access_or_paywall(message):
        return

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


@router.message(F.text.in_(["🛑 Стоп-слова", "Стоп-слова"]))
async def stop_words_handler(message: Message, state: FSMContext):
    await state.clear()

    if not await ensure_access_or_paywall(message):
        return

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
    if not await ensure_access_or_paywall(message):
        return

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
    if not await ensure_access_or_paywall(message):
        await state.clear()
        return

    phrase = (message.text or "").strip()

    if len(phrase) < 2:
        await message.answer("Слишком короткое стоп-слово. Введите нормальное значение.")
        return

    try:
        stop_word, created = await sync_to_async(add_user_stop_word)(message.from_user.id, phrase)
    except Exception as e:
        print("Ошибка add_user_stop_word:", repr(e))
        await state.clear()
        await message.answer(
            f"Ошибка сохранения: {escape(str(e)[:200])}",
            reply_markup=get_stop_words_menu(),
            parse_mode="HTML",
        )
        return

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


@router.message(F.text.in_(["👁 Посмотреть / 🗑 удалить стоп-слово", "🗑 Удалить стоп-слово", "Удалить стоп-слово"]))
async def delete_stop_word_start(message: Message, state: FSMContext):
    if not await ensure_access_or_paywall(message):
        return

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


@router.message(F.text.in_(["💬 Мои чаты", "Мои чаты"]))
async def chats_handler(message: Message, state: FSMContext):
    await state.clear()

    if not await ensure_access_or_paywall(message):
        return

    await message.answer(
        "<b>💬 Раздел «Мои чаты»</b>\n\n"
        "📂 <b>Выбрать чат</b> — открыть список доступных чатов и подключить нужные\n"
        "➕ <b>Предложить новый чат</b> — если нужного чата нет в списке\n\n"
        "👇 Выберите действие ниже",
        reply_markup=get_chats_menu(),
        parse_mode="HTML",
    )

@router.message(F.text.in_(["📂 Выбрать чат", "Выбрать чат"]))
async def choose_chat_country_handler(message: Message, state: FSMContext):
    if not await ensure_access_or_paywall(message):
        return

    await state.set_state(ChatStates.choosing_country)
    await message.answer(
        "<b>🌍 Сначала выберите страну:</b>\n\n"
        "После этого я покажу доступные чаты для мониторинга.",
        reply_markup=build_country_select_keyboard("chat_country"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("chat_country:"))
async def chat_country_callback(callback: CallbackQuery, state: FSMContext):
    country = callback.data.split(":")[1]
    await state.clear()

    await callback.answer(f"Открываю: {COUNTRY_LABELS.get(country, country)}")
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
    except Exception as e:
        print("Ошибка toggle_user_chat:", repr(e))
        await callback.answer(f"Ошибка: {str(e)[:150]}", show_alert=True)
        return

    if result == "connected":
        await callback.answer(f'Чат "{chat.title}" подключен')
    else:
        await callback.answer(f'Чат "{chat.title}" отключен')

    await render_chats_by_country(callback, callback.from_user.id, chat.country)


@router.message(F.text.in_(["➕ Предложить новый чат", "Предложить новый чат"]))
async def request_chat_start(message: Message, state: FSMContext):
    if not await ensure_access_or_paywall(message):
        return

    await state.set_state(ChatRequestStates.waiting_for_country)
    await message.answer(
        "<b>Для какой страны или категории вы хотите предложить чат?</b>",
        reply_markup=build_chat_request_country_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("request_country:"))
async def request_country_callback(callback: CallbackQuery, state: FSMContext):
    country = callback.data.split(":")[1]
    await state.update_data(request_country=country)
    await state.set_state(ChatRequestStates.waiting_for_chat_request)

    await callback.answer(f"Выбрано: {COUNTRY_LABELS.get(country, country)}")
    await callback.message.edit_text(
        f"<b>Выбрано:</b> {COUNTRY_LABELS.get(country, country)}\n\n"
        "Теперь отправьте username чата или ссылку.\n\n"
        "Примеры:\n"
        "@mobirazbor_chat\n"
        "https://t.me/mobirazbor_chat",
        parse_mode="HTML",
        reply_markup=None,
    )


@router.message(ChatRequestStates.waiting_for_chat_request)
async def request_chat_finish(message: Message, state: FSMContext):
    if not await ensure_access_or_paywall(message):
        await state.clear()
        return

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
        ""
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


@router.message(F.text.in_(["⭐ Подписка", "Подписка"]))
async def subscription_handler(message: Message, state: FSMContext):
    await state.clear()

    status = await sync_to_async(get_user_access_status)(message.from_user.id)

    if status["has_active_subscription"]:
        payment_method = PAYMENT_METHOD_LABELS.get(
            status["payment_method"],
            status["payment_method"] or "не указан"
        )
        text = (
            "<b>⭐ Подписка</b>\n\n"
            "Подписка активна.\n"
            f"Осталось дней: <b>{status['days_left']}</b>\n"
            f"Способ оплаты: <b>{payment_method}</b>\n\n"
            "Выберите способ оплаты для продления:"
        )
    elif status["has_active_trial"]:
        text = (
            "<b>🎁 Пробный период</b>\n\n"
            "Пробный период активен.\n"
            f"Осталось дней: <b>{status['days_left']}</b>\n\n"
            "Выберите удобный способ оплаты:"
        )
    else:
        text = (
            "<b>⭐ Подписка</b>\n\n"
            "Пробный период завершён.\n\n"
            "Выберите способ оплаты:"
        )

    await message.answer(
        text,
        reply_markup=build_subscription_method_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "payment_method:stars")
async def payment_method_stars_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>⭐ Оплата через Telegram Stars</b>\n\n"
        "Выберите тариф в звёздах:",
        reply_markup=build_subscription_keyboard("stars"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "payment_method:yoomoney")
async def payment_method_yoomoney_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>💳 Оплата через ЮMoney</b>\n\n"
        "Выберите тариф в российских рублях:",
        reply_markup=build_subscription_keyboard("yoomoney"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "payment_back")
async def payment_back_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>Выберите способ оплаты:</b>",
        reply_markup=build_subscription_method_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_sub:"))
async def buy_subscription_callback(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")

    if len(parts) == 2:
        payment_method = "stars"
        plan_key = parts[1]
    else:
        payment_method = parts[1]
        plan_key = parts[2]

    plan = SUBSCRIPTION_PLANS.get(plan_key)

    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    if payment_method == "stars":
        prices = [LabeledPrice(label=plan["title"], amount=plan["stars"])]

        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=plan["title"],
            description=f"Доступ к боту на {plan['days']} дней",
            payload=f"sub_{plan_key}",
            currency="XTR",
            prices=prices,
            provider_token="",
        )

        await callback.answer("Счёт отправлен")
        return

    if payment_method == "yoomoney":
        try:
            user = await sync_to_async(AppUser.objects.get)(telegram_id=callback.from_user.id)
            invoice = await sync_to_async(create_yoomoney_invoice)(user, plan_key)

            if not invoice:
                await callback.answer("Не удалось создать счёт", show_alert=True)
                return

            pay_url = await sync_to_async(build_yoomoney_quickpay_url)(invoice)

            await callback.message.edit_text(
                "<b>💳 Счёт ЮMoney создан</b>\n\n"
                f"Тариф: <b>{escape(plan['title'])}</b>\n"
                f"Сумма: <b>{plan['rub']} ₽</b>\n\n"
                "1. Нажмите на ссылку ниже\n"
                "2. Оплатите картой или через кошелёк ЮMoney\n"
                "3. После подтверждения подписка активируется автоматически\n\n"
                f'<a href="{pay_url}">👉 Оплатить через ЮMoney</a>',
                reply_markup=build_subscription_method_keyboard(),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            await callback.answer("Ссылка на оплату готова")
            return
        except Exception as e:
            print("Ошибка создания инвойса ЮMoney:", repr(e))
            await callback.answer("Ошибка создания счёта", show_alert=True)
            return

    await callback.answer("Неизвестный способ оплаты", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("sub_"):
        return

    plan_key = payload.replace("sub_", "")
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        return

    await sync_to_async(extend_subscription)(message.from_user.id, plan["days"], "stars")

    await message.answer(
        f"<b>Оплата прошла успешно.</b>\n\n"
        f"Подписка активирована: <b>{escape(plan['title'])}</b>",
        reply_markup=get_general_menu(),
        parse_mode="HTML",
    )


@router.message(F.text.in_(["ℹ️ Информация", "Информация"]))
async def info_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "<b>ℹ️ О боте</b>\n\n"
        "Этот бот собирает в одном месте только нужные вам сообщения из Telegram-чатов по ключевым словам.\n\n"
        "Вам не нужно вручную мониторить десятки чатов — бот сам отслеживает новые сообщения и присылает только подходящие совпадения.\n\n"
        "Это удобно, если:\n"
        "• вы продавец и ищете, кто ищет товар или запчасти\n"
        "• вы покупатель и хотите быстро видеть, кто что продаёт\n\n"
        "<b>Как это работает:</b>\n"
        "• вы добавляете ключевые слова\n"
        "• подключаете нужные чаты\n"
        "• бот фильтрует сообщения и присылает совпадения\n\n"
        "<b>Дополнительно:</b>\n"
        "• можно добавлять стоп-слова\n\n"
        "<b>🎁 Пробный период:</b>\n"
        "• после первого запуска /start даётся 30 дней бесплатно\n\n"
        "<b>⭐ Telegram Stars:</b>\n"
        "• 1 месяц — 100 Stars\n"
        "• 3 месяца — 250 Stars\n"
        "• 12 месяцев — 1000 Stars\n\n"
        "<b>💳 ЮMoney:</b>\n"
        "• 1 месяц — 200 ₽\n"
        "• 3 месяца — 300 ₽\n"
        "• 12 месяцев — 1000 ₽\n\n"
        "<b>После оплаты:</b>\n"
        "• подписка активируется автоматически\n",
        reply_markup=get_general_menu(),
        parse_mode="HTML",
    )