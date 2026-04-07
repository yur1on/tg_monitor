from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def yoomoney_webhook(request):
    if request.method == "GET":
        return HttpResponse("YooMoney webhook endpoint", status=200)

    if request.method == "POST":
        print("YooMoney POST received")
        print("POST data:", request.POST.dict())
        return HttpResponse("OK", status=200)

    return HttpResponse("Method not allowed", status=405)