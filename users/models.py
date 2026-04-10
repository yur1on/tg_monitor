from django.db import models
from django.utils import timezone
from datetime import timedelta


class AppUser(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("stars", "Telegram Stars"),
        ("yoomoney", "ЮMoney"),
        ("admin", "Выдано админом"),
        ("", "Не указано"),
    ]

    telegram_id = models.BigIntegerField("Telegram ID", unique=True)
    username = models.CharField("Username", max_length=255, blank=True)
    first_name = models.CharField("Имя", max_length=255, blank=True)

    trial_started_at = models.DateTimeField("Начало пробного периода", null=True, blank=True)
    trial_expires_at = models.DateTimeField("Конец пробного периода", null=True, blank=True)
    is_trial_used = models.BooleanField("Пробный период использован", default=False)

    subscription_expires_at = models.DateTimeField("Подписка активна до", null=True, blank=True)
    payment_method = models.CharField(
        "Способ оплаты",
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        default="",
    )

    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-created_at"]

    def __str__(self):
        return self.username or self.first_name or str(self.telegram_id)

    @property
    def has_active_trial(self) -> bool:
        return bool(self.trial_expires_at and self.trial_expires_at > timezone.now())

    @property
    def has_active_subscription(self) -> bool:
        return bool(self.subscription_expires_at and self.subscription_expires_at > timezone.now())

    @property
    def has_access(self) -> bool:
        return self.has_active_trial or self.has_active_subscription

    def start_trial_if_needed(self):
        if self.is_trial_used:
            return False

        now = timezone.now()
        self.trial_started_at = now
        self.trial_expires_at = now + timedelta(days=30)
        self.is_trial_used = True
        self.save(update_fields=["trial_started_at", "trial_expires_at", "is_trial_used"])
        return True