from users.models import AppUser
from .models import Keyword, StopWord, MonitoredChat, UserChatSubscription, ChatRequest


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

    keyword, created = Keyword.objects.get_or_create(
        user=user,
        phrase=phrase,
        defaults={"is_active": True}
    )

    if not created and not keyword.is_active:
        keyword.is_active = True
        keyword.save()

    return keyword, created


def delete_user_keyword_by_id(telegram_id: int, keyword_id: int):
    keyword = Keyword.objects.filter(
        id=keyword_id,
        user__telegram_id=telegram_id,
        is_active=True
    ).first()

    if not keyword:
        return False, None

    keyword.is_active = False
    keyword.save()
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
        stop_word.save()

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
    stop_word.save()
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
        result.append({
            "id": chat.id,
            "title": chat.title,
            "short_title": shorten_text(chat.title, 30),
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
        return True, "connected", chat

    subscription.is_active = not subscription.is_active
    subscription.save()

    return True, "connected" if subscription.is_active else "disconnected", chat


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