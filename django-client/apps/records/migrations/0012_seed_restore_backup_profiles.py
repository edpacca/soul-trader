from django.db import migrations


RESTORE_FIELD_MAPPINGS = {
    "0": "uuid",
    "1": "date",
    "2": "item_name",
    "3": "quantity",
    "4": "unit_price",
    "5": "total_price",
    "6": "shipping_cost",
    "7": "post_code",
    "8": "currency",
    "9": "source",
}


def seed_restore_profiles(apps, schema_editor):
    CSVFormatProfile = apps.get_model("records", "CSVFormatProfile")

    for record_type, label in [("sales", "Sales"), ("purchase", "Purchase")]:
        CSVFormatProfile.objects.get_or_create(
            name=f"Restore from Backup ({label})",
            defaults={
                "record_type": record_type,
                "delimiter": ",",
                "date_format": "%Y-%m-%d",
                "has_headers": True,
                "is_active": True,
                "field_mappings": RESTORE_FIELD_MAPPINGS,
            },
        )


def remove_restore_profiles(apps, schema_editor):
    CSVFormatProfile = apps.get_model("records", "CSVFormatProfile")
    CSVFormatProfile.objects.filter(
        name__in=["Restore from Backup (Sales)", "Restore from Backup (Purchase)"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0011_databaseexporttool_purchaserecord_uuid_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_restore_profiles, remove_restore_profiles),
    ]
