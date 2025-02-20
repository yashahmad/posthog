import pprint

from django.core.management.base import BaseCommand

from posthog.tasks.usage_report import send_all_org_usage_reports


class Command(BaseCommand):
    help = "Send the usage report for a given day"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", type=bool, help="Print information instead of sending it")
        parser.add_argument("--print-reports", type=bool, help="Print the reports in full")
        parser.add_argument("--date", type=str, help="The date to be ran in format YYYY-MM-DD")
        parser.add_argument("--event-name", type=str, help="Override the event name to be sent - for testing")
        parser.add_argument(
            "--skip-capture-event", type=str, help="Skip the posthog capture events - for retrying to billing service"
        )
        parser.add_argument("--organization-id", type=str, help="Only send the report for this organization ID")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        date = options["date"]
        event_name = options["event_name"]
        skip_capture_event = options["skip_capture_event"]
        organization_id = options["organization_id"]

        results = send_all_org_usage_reports(
            dry_run, date, event_name, skip_capture_event=skip_capture_event, only_organization_id=organization_id
        )

        if options["print_reports"]:
            print("")  # noqa T201
            pprint.pprint(results)  # noqa T203
            print("")  # noqa T201

        if dry_run:
            print("Dry run so not sent.")  # noqa T201
        else:
            print(f"{len(results)} Reports sent!")  # noqa T201
            print("Done!")  # noqa T201
