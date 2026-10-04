"""Offline, verified import into an empty PostgreSQL application database."""
import copy
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections, transaction


class Command(BaseCommand):
    help = "Back up SQLite, import into an empty PostgreSQL DB, and verify every imported record. Stop app writers first."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path)

    def handle(self, *args, **options):
        if connections["default"].vendor != "postgresql":
            raise CommandError("The target must be PostgreSQL. Set DATABASE_URL first.")
        source = options["source"].resolve()
        if not source.is_file():
            raise CommandError("SQLite source file does not exist.")
        # Generated permission/content-type IDs differ between engines. Natural
        # keys preserve user/group permissions without copying these tables.
        excluded = ["contenttypes", "auth.permission", "sessions.session", "admin.logentry"]
        models = [model for model in apps.get_models() if model._meta.managed
                  and model._meta.app_label not in ("contenttypes", "sessions", "admin")
                  and model._meta.label_lower != "auth.permission"]
        if any(model.objects.exists() for model in models):
            raise CommandError("Target contains application records; refusing to overwrite or merge.")
        directory = settings.BASE_DIR / ".local-data" / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        directory.mkdir(parents=True)
        snapshot = directory / "source.sqlite3"
        with sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True) as original:
            with sqlite3.connect(snapshot) as backup:
                original.backup(backup)
        config = copy.deepcopy(connections["default"].settings_dict)
        config.update(ENGINE="django.db.backends.sqlite3", NAME=str(snapshot), USER="", PASSWORD="", HOST="", PORT="", OPTIONS={}, CONN_MAX_AGE=0)
        connections.databases["legacy"] = config
        export_options = dict(exclude=excluded, natural_foreign=True, natural_primary=True, verbosity=0)
        fixture = directory / "records.json"
        try:
            call_command("dumpdata", database="legacy", output=str(fixture), **export_options)
            expected = json.loads(fixture.read_text(encoding="utf-8"))
            # All-or-nothing import; loaddata resets PostgreSQL sequences.
            with transaction.atomic():
                call_command("loaddata", str(fixture), verbosity=0)
                actual = io.StringIO()
                call_command("dumpdata", stdout=actual, **export_options)
                def ordered(records):
                    return sorted(records, key=lambda record: (record["model"], json.dumps(record.get("pk")), json.dumps(record["fields"], sort_keys=True)))
                if ordered(json.loads(actual.getvalue())) != ordered(expected):
                    raise CommandError("Record verification failed; PostgreSQL import was rolled back.")
            self.stdout.write(self.style.SUCCESS(f"Imported and verified {len(expected)} records. SQLite backup and private fixture: {directory}"))
            self.stdout.write("Sessions and admin logs were not imported. Existing media paths are unchanged.")
        finally:
            connections["legacy"].close()
