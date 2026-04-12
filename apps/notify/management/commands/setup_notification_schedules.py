"""Setup notification scheduled tasks in Celery Beat."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Setup notification scheduled tasks in Celery Beat"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--clear", action="store_true", help="Clear existing first")

    def handle(self, *args, **options) -> None:
        try:
            from django_celery_beat.models import CrontabSchedule, PeriodicTask
        except ImportError:
            self.stderr.write(
                self.style.ERROR(
                    "django-celery-beat not installed. Run: pip install django-celery-beat"
                )
            )
            return

        # Cleanup old names
        PeriodicTask.objects.filter(name__startswith="notifications.").delete()
        if options["clear"]:
            deleted, _ = PeriodicTask.objects.filter(
                name__startswith="Notifications"
            ).delete()
            self.stdout.write(f"Cleared {deleted} existing schedules")

        schedules = [
            {
                "name": "Notifications - Channel Health Check",
                "task": "notifications.channel_health_check",
                "crontab": {"hour": "*/6", "minute": 0},
            },
            {
                "name": "Notifications - Cleanup Old Logs",
                "task": "notifications.cleanup_old_logs",
                "crontab": {"hour": 3, "minute": 10},
            },
            {
                "name": "Notifications - Retry Failed",
                "task": "notifications.retry_failed_notifications",
                "crontab": {"minute": 30},
            },
        ]

        for cfg in schedules:
            cron_kw = {
                "minute": cfg["crontab"].get("minute", "*"),
                "hour": cfg["crontab"].get("hour", "*"),
                "day_of_week": cfg["crontab"].get("day_of_week", "*"),
                "day_of_month": cfg["crontab"].get("day_of_month", "*"),
                "month_of_year": cfg["crontab"].get("month_of_year", "*"),
            }
            crontab = CrontabSchedule.objects.filter(**cron_kw).first()
            if crontab is None:
                crontab = CrontabSchedule.objects.create(**cron_kw)

            _, created = PeriodicTask.objects.update_or_create(
                name=cfg["name"],
                defaults={"task": cfg["task"], "crontab": crontab, "enabled": True},
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status}: {cfg['name']}")

        self.stdout.write(self.style.SUCCESS("Done."))
