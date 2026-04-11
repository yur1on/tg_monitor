from django.core.management.base import BaseCommand

from monitor.services import cleanup_old_matched_messages


class Command(BaseCommand):
    help = "Удаление старых технических совпадений"

    def handle(self, *args, **options):
        deleted_count = cleanup_old_matched_messages(retention_days=3)
        self.stdout.write(self.style.SUCCESS(f"Удалено записей: {deleted_count}"))
