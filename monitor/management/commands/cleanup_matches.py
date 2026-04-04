from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from monitor.models import MatchedMessage


class Command(BaseCommand):
    help = "Удаление старых технических совпадений"

    def handle(self, *args, **options):
        threshold = timezone.now() - timedelta(days=3)
        deleted_count, _ = MatchedMessage.objects.filter(created_at__lt=threshold).delete()
        self.stdout.write(self.style.SUCCESS(f"Удалено записей: {deleted_count}"))