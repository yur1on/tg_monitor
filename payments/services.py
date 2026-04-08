import hashlib
from decimal import Decimal
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from notifications.services import send_telegram_message
from users.services import extend_subscription

from .models import PaymentInvoice, YooMoneyNotificationLog


YOOMONEY_PLANS = {
    "30": {"title": "1 месяц", "amount": Decimal("200.00"), "days": 30},
    "90": {"title": "3 месяца", "amount": Decimal("300.00"), "days": 90},
    "365": {"title": "12 месяцев", "amount": Decimal("1000.00"), "days": 365},
}


def generate_payment_label(user_id: int, plan_key: str) -> str:
    now = timezone.now().strftime("%Y%m%d%H%M%S%f")
    return f"tgm_{user_id}_{plan_key}_{now}"


def create_yoomoney_invoice(user, plan_key: str) -> PaymentInvoice | None:
    plan = YOOMONEY_PLANS.get(plan_key)
    if not plan:
        return None

    label = generate_payment_label(user.id, plan_key)

    return PaymentInvoice.objects.create(
        user=user,
        label=label,
        plan_key=plan_key,
        amount=plan["amount"],
        days=plan["days"],
        payment_method="yoomoney",
        status="pending",
    )


def build_yoomoney_quickpay_url(invoice: PaymentInvoice) -> str:
    params = {
        "receiver": settings.YOOMONEY_WALLET,
        "quickpay-form": "button",
        "paymentType": "AC",
        "sum": str(invoice.amount),
        "label": invoice.label,
        "targets": f"Подписка Tehsfera Bot ({invoice.label})",
        "successURL": settings.YOOMONEY_SUCCESS_URL,
    }
    return f"https://yoomoney.ru/quickpay/confirm?{urlencode(params)}"


def calculate_yoomoney_sha1(data: dict) -> str:
    raw = "&".join([
        data.get("notification_type", ""),
        data.get("operation_id", ""),
        data.get("amount", ""),
        data.get("currency", ""),
        data.get("datetime", ""),
        data.get("sender", ""),
        data.get("codepro", ""),
        settings.YOOMONEY_NOTIFICATION_SECRET,
        data.get("label", ""),
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def validate_yoomoney_notification(data: dict) -> bool:
    received_hash = (data.get("sha1_hash") or "").strip().lower()
    if not received_hash:
        return False

    expected_hash = calculate_yoomoney_sha1(data)
    return expected_hash == received_hash


def amount_matches(invoice: PaymentInvoice, incoming_amount: str) -> bool:
    if not settings.YOOMONEY_REQUIRE_EXACT_AMOUNT:
        return True

    try:
        return Decimal(incoming_amount) == invoice.amount
    except Exception:
        return False


@transaction.atomic
def process_yoomoney_notification(data: dict) -> tuple[bool, str]:
    is_valid = validate_yoomoney_notification(data)

    YooMoneyNotificationLog.objects.create(
        operation_id=data.get("operation_id", "") or "",
        label=data.get("label", "") or "",
        sha1_hash=data.get("sha1_hash", "") or "",
        is_valid=is_valid,
        payload=data,
    )

    if not is_valid:
        return False, "invalid_hash"

    label = (data.get("label") or "").strip()
    if not label:
        return False, "empty_label"

    invoice = PaymentInvoice.objects.select_for_update().filter(label=label).first()
    if not invoice:
        return False, "invoice_not_found"

    if invoice.status == "paid":
        return True, "already_paid"

    if not amount_matches(invoice, data.get("amount", "")):
        return False, "amount_mismatch"

    operation_id = (data.get("operation_id") or "").strip()
    if operation_id and PaymentInvoice.objects.filter(operation_id=operation_id, status="paid").exists():
        return True, "duplicate_operation"

    paid_amount = data.get("amount") or str(invoice.amount)

    invoice.status = "paid"
    invoice.operation_id = operation_id
    invoice.payer = (data.get("sender") or "").strip()
    invoice.paid_amount = Decimal(str(paid_amount))
    invoice.paid_at = timezone.now()
    invoice.save(update_fields=[
        "status",
        "operation_id",
        "payer",
        "paid_amount",
        "paid_at",
        "updated_at",
    ])

    extend_subscription(invoice.user.telegram_id, invoice.days, "yoomoney")

    try:
        send_telegram_message(
            invoice.user.telegram_id,
            (
                "<b>✅ Оплата ЮMoney подтверждена</b>\n\n"
                f"Тариф: <b>{YOOMONEY_PLANS[invoice.plan_key]['title']}</b>\n"
                f"Сумма: <b>{invoice.amount}</b> RUB\n"
                f"Доступ продлён на <b>{invoice.days}</b> дн."
            ),
        )
    except Exception:
        pass

    return True, "paid"