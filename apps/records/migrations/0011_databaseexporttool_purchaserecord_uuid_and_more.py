import uuid

from django.db import migrations, models


def backfill_uuids(apps, schema_editor):
    """Assign a unique UUID to every existing row that has uuid=NULL."""
    for model_name in ("SalesRecord", "PurchaseRecord"):
        Model = apps.get_model("records", model_name)
        for obj in Model.objects.filter(uuid__isnull=True):
            obj.uuid = uuid.uuid4()
            obj.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0010_seed_default_csv_profiles"),
    ]

    operations = [
        # 0) Create the unmanaged proxy model (auto-detected)
        migrations.CreateModel(
            name="DatabaseExportTool",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "verbose_name": "Database Export",
                "verbose_name_plural": "Database Exports",
                "managed": False,
            },
        ),
        # 1) Add uuid column as nullable (no unique constraint yet)
        migrations.AddField(
            model_name="purchaserecord",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.AddField(
            model_name="salesrecord",
            name="uuid",
            field=models.UUIDField(null=True, editable=False),
        ),
        # 2) Backfill UUIDs for all existing rows
        migrations.RunPython(backfill_uuids, migrations.RunPython.noop),
        # 3) Now make the column non-null, unique, and indexed
        migrations.AlterField(
            model_name="purchaserecord",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
        migrations.AlterField(
            model_name="salesrecord",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
