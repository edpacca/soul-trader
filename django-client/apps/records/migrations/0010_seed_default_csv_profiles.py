from django.db import migrations


FIELD_MAPPINGS = {
    "0": "date",
    "1": "item_name",
    "2": "quantity",
    "3": "unit_price",
    "4": "total_price",
    "5": "shipping_cost",
    "6": "post_code",
    "7": "currency",
}


def seed_profiles(apps, schema_editor):
    CSVFormatProfile = apps.get_model("records", "CSVFormatProfile")

    for record_type, label in [("sales", "Sales"), ("purchase", "Purchase")]:
        CSVFormatProfile.objects.get_or_create(
            name=f"Default ({label})",
            defaults={
                "record_type": record_type,
                "delimiter": ",",
                "date_format": "%Y-%m-%d",
                "has_headers": True,
                "is_active": True,
                "field_mappings": FIELD_MAPPINGS,
            },
        )


def remove_profiles(apps, schema_editor):
    CSVFormatProfile = apps.get_model("records", "CSVFormatProfile")
    CSVFormatProfile.objects.filter(
        name__in=["Default (Sales)", "Default (Purchase)"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("records", "0009_reportpreset"),
    ]

    operations = [
        migrations.RunPython(seed_profiles, remove_profiles),
    ]
