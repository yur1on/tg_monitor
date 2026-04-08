from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from .models import PaymentInvoice
from .services import process_yoomoney_notification, build_yoomoney_quickpay_url


@csrf_exempt
def yoomoney_webhook(request):
    if request.method == "GET":
        return HttpResponse("YooMoney webhook endpoint", status=200)

    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    data = request.POST.dict()
    ok, reason = process_yoomoney_notification(data)

    if ok:
        return HttpResponse("OK", status=200)

    if reason in {"invalid_hash", "amount_mismatch", "invoice_not_found", "empty_label"}:
        return HttpResponse(reason, status=400)

    return HttpResponse("OK", status=200)


@require_GET
def invoice_status(request, label: str):
    invoice = get_object_or_404(PaymentInvoice, label=label)
    return JsonResponse(
        {
            "label": invoice.label,
            "status": invoice.status,
            "plan_key": invoice.plan_key,
            "amount": str(invoice.amount),
            "payment_url": build_yoomoney_quickpay_url(invoice),
        }
    )