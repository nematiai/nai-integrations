import json

import apprise
from django.core.management.base import BaseCommand

from apps.notify.schemas import build_apprise_url


class Command(BaseCommand):
    help = "Test notification service with given config"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--service", required=True, help="Service type (e.g., slack)"
        )
        parser.add_argument("--config", required=True, help="JSON config string")
        parser.add_argument("--live", action="store_true", help="Actually send")

    def handle(self, *args, **options) -> None:
        try:
            config = json.loads(options["config"])
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f"Invalid JSON: {e}"))
            return

        url = build_apprise_url(options["service"], config)
        if not url:
            self.stdout.write(
                self.style.ERROR(f"Failed to build URL for {options['service']}")
            )
            return

        if options["live"]:
            apobj = apprise.Apprise()
            apobj.add(url)
            result = apobj.notify(body="Test from NEMI", title="Test Notification")
            style = self.style.SUCCESS if result else self.style.ERROR
            self.stdout.write(style("Sent" if result else "Failed"))
        else:
            self.stdout.write(f"Built URL: {url}")
            self.stdout.write(self.style.SUCCESS("Dry run OK"))
