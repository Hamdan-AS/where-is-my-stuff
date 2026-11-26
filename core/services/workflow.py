from django.db import connection

def lock_report_workflow():
    """Serialize matching/reservations across PostgreSQL workers until commit.

    SQLite already serializes writes with IMMEDIATE transactions. One advisory
    lock preserves that behaviour for this small app without deadlock-prone
    ordering between competing match pairs. Reads remain concurrent.
    """
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [3272026001])
