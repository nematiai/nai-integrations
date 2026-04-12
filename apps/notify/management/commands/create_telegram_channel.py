from django.core.management.base import BaseCommand

from apps.notify.models import NotificationChannel


class Command(BaseCommand):
    help = "Create a Telegram notification channel"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--bot-token", required=True, help="Telegram bot token")
        parser.add_argument("--chat-id", required=True, help="Telegram chat ID")
        parser.add_argument("--name", default="Telegram Alerts", help="Channel name")

    def handle(self, *args, **options) -> None:
        bot_token = options["bot_token"]
        chat_id = options["chat_id"]
        channel = NotificationChannel(
            name=options["name"],
            service_type="telegram",
            config={"bot_token": bot_token, "chat_id": chat_id},
            is_active=True,
        )
        channel.save()
        self.stdout.write(self.style.SUCCESS(f"Created channel: {channel.name}"))
