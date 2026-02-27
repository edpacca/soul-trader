import csv
import io
import os
import subprocess

from django.conf import settings

from apps.records.models import PurchaseRecord, SalesRecord

CSV_COLUMNS = [
    "uuid",
    "date",
    "item_name",
    "quantity",
    "unit_price",
    "total_price",
    "shipping_cost",
    "post_code",
    "currency",
    "source",
]


def export_records_as_csv(record_type: str) -> str:
    """Export SalesRecord and/or PurchaseRecord rows as a CSV string.

    Args:
        record_type: One of "sales", "purchase", or "all".

    Returns:
        CSV content as a string with headers matching the canonical column order.
    """
    querysets = []
    if record_type in ("sales"):
        querysets.append(SalesRecord.objects.all())
    if record_type in ("purchase"):
        querysets.append(PurchaseRecord.objects.all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)

    for qs in querysets:
        for record in qs.order_by("date"):
            writer.writerow([
                str(record.uuid),
                record.date.strftime("%Y-%m-%d"),
                record.item_name,
                record.quantity,
                str(record.unit_price),
                str(record.total_price),
                str(record.shipping_cost),
                record.post_code,
                record.currency,
                record.source.name if record.source else "",
            ])

    return output.getvalue()


def export_db_dump() -> bytes:
    """Run pg_dump against the default database and return the raw output.

    Raises:
        RuntimeError: If the database engine is not PostgreSQL or pg_dump fails.
    """
    db = settings.DATABASES["default"]
    engine = db.get("ENGINE", "")

    if "postgresql" not in engine:
        raise RuntimeError(
            "Database export is only supported for PostgreSQL. "
            f"Current engine: {engine}"
        )

    env = os.environ.copy()
    env["PGPASSWORD"] = db.get("PASSWORD", "")

    cmd = [
        "pg_dump",
        "-h", db.get("HOST", "localhost"),
        "-p", str(db.get("PORT", "5432")),
        "-U", db.get("USER", "postgres"),
        db.get("NAME", "django_client"),
    ]

    result = subprocess.run(cmd, capture_output=True, env=env)

    if result.returncode != 0:
        raise RuntimeError(
            f"pg_dump failed (exit code {result.returncode}): "
            f"{result.stderr.decode('utf-8', errors='replace')}"
        )

    return result.stdout
