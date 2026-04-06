from django.db import models
from users.models import AppUser


class MonitoredChat(models.Model):
    COUNTRY_CHOICES = [
        ("BY", "Беларусь"),
        ("RU", "Россия"),
        ("OTHER", "Другая страна"),
    ]

    input_name = models.CharField("Что ввели", max_length=255, blank=True)
    title = models.CharField("Название", max_length=255, blank=True)
    telegram_chat_id = models.BigIntegerField("Telegram Chat ID", unique=True, null=True, blank=True)
    username = models.CharField("Username/ссылка", max_length=255, blank=True)
    country = models.CharField("Страна", max_length=10, choices=COUNTRY_CHOICES)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Чат для мониторинга"
        verbose_name_plural = "Чаты для мониторинга"
        ordering = ["country", "title", "id"]

    def __str__(self):
        return self.title or self.input_name or str(self.id)


class Keyword(models.Model):
    user = models.ForeignKey(
        AppUser,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="keywords"
    )
    phrase = models.CharField("Ключевое слово", max_length=255)
    is_active = models.BooleanField("Активно", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Ключевое слово"
        verbose_name_plural = "Ключевые слова"
        ordering = ["phrase"]

    def __str__(self):
        return self.phrase


class StopWord(models.Model):
    user = models.ForeignKey(
        AppUser,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="stop_words"
    )
    phrase = models.CharField("Стоп-слово", max_length=255)
    is_active = models.BooleanField("Активно", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Стоп-слово"
        verbose_name_plural = "Стоп-слова"
        ordering = ["phrase"]

    def __str__(self):
        return self.phrase


class UserChatSubscription(models.Model):
    user = models.ForeignKey(AppUser, verbose_name="Пользователь", on_delete=models.CASCADE)
    chat = models.ForeignKey(MonitoredChat, verbose_name="Чат", on_delete=models.CASCADE)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Подписка на чат"
        verbose_name_plural = "Подписки на чаты"
        unique_together = ("user", "chat")

    def __str__(self):
        return f"{self.user} → {self.chat}"


class MatchedMessage(models.Model):
    user = models.ForeignKey(AppUser, verbose_name="Пользователь", on_delete=models.CASCADE)
    message_hash = models.CharField("Хэш", max_length=64, db_index=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Техническое совпадение"
        verbose_name_plural = "Технические совпадения"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} | {self.message_hash}"


class ChatRequest(models.Model):
    COUNTRY_CHOICES = [
        ("BY", "Беларусь"),
        ("RU", "Россия"),
        ("OTHER", "Другая страна"),
    ]

    user = models.ForeignKey(AppUser, verbose_name="Пользователь", on_delete=models.CASCADE)
    country = models.CharField("Страна", max_length=10, choices=COUNTRY_CHOICES)
    chat_input = models.CharField("Имя чата или ссылка", max_length=255)
    comment = models.CharField("Комментарий", max_length=255, blank=True)
    is_processed = models.BooleanField("Обработана", default=False)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на добавление чата"
        verbose_name_plural = "Заявки на добавление чатов"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.chat_input} ({self.get_country_display()})"