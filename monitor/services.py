from users.models import AppUser
from .models import Keyword, StopWord, MonitoredChat, UserChatSubscription, ChatRequest


MAX_USER_KEYWORDS = 10
MAX_USER_CHATS = 10


def normalize_phrase(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def shorten_text(text: str, max_length: int = 28) -> str:
    text = (text or "").strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


# =========================
# КЛЮЧЕВЫЕ СЛОВА
# =========================

def get_user_keywords(telegram_id: int):
    return list(
        Keyword.objects.filter(
            user__telegram_id=telegram_id,
            is_active=True
        ).order_by("phrase")
    )


def add_user_keyword(telegram_id: int, phrase: str):
    user = AppUser.objects.get(telegram_id=telegram_id)

    phrase = normalize_phrase(phrase)
    if not phrase:
        return None, False

    existing_keyword = Keyword.objects.filter(
        user=user,
        phrase=phrase,
    ).first()

    if existing_keyword:
        if not existing_keyword.is_active:
            existing_keyword.is_active = True
            existing_keyword.save(update_fields=["is_active"])
        return existing_keyword, False

    active_keywords_count = Keyword.objects.filter(
        user=user,
        is_active=True,
    ).count()

    if active_keywords_count >= MAX_USER_KEYWORDS:
        raise ValueError(f"Можно добавить не более {MAX_USER_KEYWORDS} ключевых фраз.")

    keyword = Keyword.objects.create(
        user=user,
        phrase=phrase,
        is_active=True,
    )
    return keyword, True


def delete_user_keyword_by_id(telegram_id: int, keyword_id: int):
    keyword = Keyword.objects.filter(
        id=keyword_id,
        user__telegram_id=telegram_id,
        is_active=True
    ).first()

    if not keyword:
        return False, None

    keyword.is_active = False
    keyword.save(update_fields=["is_active"])
    return True, keyword


# =========================
# СТОП-СЛОВА
# =========================

def get_user_stop_words(telegram_id: int):
    return list(
        StopWord.objects.filter(
            user__telegram_id=telegram_id,
            is_active=True
        ).order_by("phrase")
    )


def add_user_stop_word(telegram_id: int, phrase: str):
    user = AppUser.objects.get(telegram_id=telegram_id)

    phrase = normalize_phrase(phrase)
    if not phrase:
        return None, False

    stop_word, created = StopWord.objects.get_or_create(
        user=user,
        phrase=phrase,
        defaults={"is_active": True}
    )

    if not created and not stop_word.is_active:
        stop_word.is_active = True
        stop_word.save(update_fields=["is_active"])

    return stop_word, created


def delete_user_stop_word_by_id(telegram_id: int, stop_word_id: int):
    stop_word = StopWord.objects.filter(
        id=stop_word_id,
        user__telegram_id=telegram_id,
        is_active=True
    ).first()

    if not stop_word:
        return False, None

    stop_word.is_active = False
    stop_word.save(update_fields=["is_active"])
    return True, stop_word


# =========================
# ЧАТЫ
# =========================

def get_chats_by_country_with_status(telegram_id: int, country: str):
    chats = list(
        MonitoredChat.objects.filter(
            is_active=True,
            country=country
        ).order_by("title")
    )

    user_chat_ids = set(
        UserChatSubscription.objects.filter(
            user__telegram_id=telegram_id,
            is_active=True
        ).values_list("chat_id", flat=True)
    )

    result = []
    for chat in chats:
        title = chat.title or chat.input_name or f"Чат #{chat.id}"
        result.append({
            "id": chat.id,
            "title": title,
            "short_title": shorten_text(title, 30),
            "username": chat.username,
            "country": chat.country,
            "is_connected": chat.id in user_chat_ids,
        })
    return result


def toggle_user_chat(telegram_id: int, chat_id: int):
    user = AppUser.objects.get(telegram_id=telegram_id)
    chat = MonitoredChat.objects.get(id=chat_id, is_active=True)

    subscription, created = UserChatSubscription.objects.get_or_create(
        user=user,
        chat=chat,
        defaults={"is_active": True}
    )

    if created:
        active_chats_count = UserChatSubscription.objects.filter(
            user=user,
            is_active=True,
        ).count()

        if active_chats_count > MAX_USER_CHATS:
            subscription.delete()
            raise ValueError(f"Можно подключить не более {MAX_USER_CHATS} чатов.")

        return True, "connected", chat

    if subscription.is_active:
        subscription.is_active = False
        subscription.save(update_fields=["is_active"])
        return True, "disconnected", chat

    active_chats_count = UserChatSubscription.objects.filter(
        user=user,
        is_active=True,
    ).count()

    if active_chats_count >= MAX_USER_CHATS:
        raise ValueError(f"Можно подключить не более {MAX_USER_CHATS} чатов.")

    subscription.is_active = True
    subscription.save(update_fields=["is_active"])
    return True, "connected", chat


# =========================
# ЗАЯВКИ НА ЧАТЫ
# =========================

def create_chat_request(telegram_id: int, country: str, chat_input: str, comment: str = ""):
    user = AppUser.objects.get(telegram_id=telegram_id)

    chat_input = (chat_input or "").strip()
    comment = (comment or "").strip()

    if not chat_input:
        return None

    return ChatRequest.objects.create(
        user=user,
        country=country,
        chat_input=chat_input,
        comment=comment,
    )