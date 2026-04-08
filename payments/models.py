from django.db import models

from users.models import AppUser


class PaymentInvoice(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает оплаты"),
        ("paid", "Оплачен"),
        ("expired", "Истёк"),
        ("cancelled", "Отменён"),
    ]

    PLAN_CHOICES = [
        ("30", "1 месяц"),
        ("90", "3 месяца"),
        ("365", "12 месяцев"),
    ]

    user = models.ForeignKey(
        AppUser,
        on_delete=models.CASCADE,
        related_name="payment_invoices",
        verbose_name="Пользователь",
    )
    label = models.CharField("Метка платежа", max_length=64, unique=True, db_index=True)
    plan_key = models.CharField("Код тарифа", max_length=10, choices=PLAN_CHOICES)
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    days = models.PositiveIntegerField("Дней доступа")
    payment_method = models.CharField("Метод оплаты", max_length=20, default="yoomoney")
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default="pending")

    operation_id = models.CharField("ID операции ЮMoney", max_length=100, blank=True, default="")
    payer = models.CharField("Плательщик", max_length=64, blank=True, default="")
    paid_amount = models.DecimalField("Оплаченная сумма", max_digits=10, decimal_places=2, null=True, blank=True)
    paid_at = models.DateTimeField("Дата оплаты", null=True, blank=True)

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Счёт на оплату"
        verbose_name_plural = "Счета на оплату"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} | {self.user_id} | {self.amount}"


class YooMoneyNotificationLog(models.Model):
    operation_id = models.CharField("ID операции", max_length=100, blank=True, default="", db_index=True)
    label = models.CharField("Метка", max_length=64, blank=True, default="", db_index=True)
    sha1_hash = models.CharField("SHA1", max_length=64, blank=True, default="")
    is_valid = models.BooleanField("Валидно", default=False)
    payload = models.JSONField("Payload", default=dict, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Лог уведомления ЮMoney"
        verbose_name_plural = "Логи уведомлений ЮMoney"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.operation_id or '-'} | {self.label or '-'}"