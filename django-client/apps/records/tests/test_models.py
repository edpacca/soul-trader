from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.records.models import CSVFormatProfile


class TestCSVFormatProfileModel(TestCase):
    def _valid_mappings(self):
        return {
            "0": "date",
            "1": "item_name",
            "2": "quantity",
            "3": "unit_price",
            "4": "total_price",
            "5": "post_code",
        }

    def _build_profile(self, **overrides):
        defaults = {
            "name": "Test Profile",
            "record_type": "sales",
            "delimiter": ",",
            "date_format": "%Y-%m-%d",
            "field_mappings": self._valid_mappings(),
        }
        defaults.update(overrides)
        return CSVFormatProfile(**defaults)

    def test_create_valid_sales_profile(self):
        profile = self._build_profile()
        profile.full_clean()
        profile.save()
        self.assertEqual(CSVFormatProfile.objects.count(), 1)
        self.assertEqual(profile.name, "Test Profile")
        self.assertEqual(profile.record_type, "sales")
        self.assertTrue(profile.is_active)

    def test_create_valid_purchase_profile(self):
        profile = self._build_profile(record_type="purchase")
        profile.full_clean()
        profile.save()
        self.assertEqual(CSVFormatProfile.objects.count(), 1)
        self.assertEqual(profile.record_type, "purchase")

    def test_default_delimiter(self):
        profile = self._build_profile()
        self.assertEqual(profile.delimiter, ",")

    def test_default_is_active(self):
        profile = self._build_profile()
        self.assertTrue(profile.is_active)

    def test_str_representation(self):
        profile = self._build_profile(name="My Sales Format")
        self.assertEqual(str(profile), "My Sales Format (Sales)")

    def test_str_representation_purchase(self):
        profile = self._build_profile(name="Purchase CSV", record_type="purchase")
        self.assertEqual(str(profile), "Purchase CSV (Purchase)")

    def test_clean_rejects_empty_field_mappings(self):
        profile = self._build_profile(field_mappings={})
        with self.assertRaises(ValidationError) as ctx:
            profile.full_clean()
        self.assertIn("field_mappings", ctx.exception.message_dict)

    def test_clean_rejects_non_dict_field_mappings(self):
        profile = self._build_profile(field_mappings=["date", "item_name"])
        with self.assertRaises(ValidationError) as ctx:
            profile.full_clean()
        self.assertIn("field_mappings", ctx.exception.message_dict)

    def test_clean_rejects_invalid_field_names(self):
        mappings = self._valid_mappings()
        mappings["6"] = "nonexistent_field"
        profile = self._build_profile(field_mappings=mappings)
        with self.assertRaises(ValidationError) as ctx:
            profile.full_clean()
        self.assertIn("field_mappings", ctx.exception.message_dict)
        self.assertIn("nonexistent_field", str(ctx.exception.message_dict["field_mappings"]))

    def test_clean_rejects_missing_required_fields(self):
        mappings = {"0": "date", "1": "item_name"}
        profile = self._build_profile(field_mappings=mappings)
        with self.assertRaises(ValidationError) as ctx:
            profile.full_clean()
        self.assertIn("field_mappings", ctx.exception.message_dict)
        self.assertIn("Missing required", str(ctx.exception.message_dict["field_mappings"]))

    def test_clean_accepts_optional_fields_omitted(self):
        mappings = self._valid_mappings()
        profile = self._build_profile(field_mappings=mappings)
        profile.full_clean()

    def test_clean_accepts_all_fields_including_optional(self):
        mappings = self._valid_mappings()
        mappings["6"] = "shipping_cost"
        mappings["7"] = "currency"
        profile = self._build_profile(field_mappings=mappings)
        profile.full_clean()

    def test_clean_validates_against_correct_model_for_sales(self):
        profile = self._build_profile(record_type="sales")
        valid_fields = profile._get_model_fields()
        self.assertIn("date", valid_fields)
        self.assertIn("item_name", valid_fields)
        self.assertIn("total_price", valid_fields)
        self.assertNotIn("id", valid_fields)
        self.assertNotIn("created_at", valid_fields)

    def test_clean_validates_against_correct_model_for_purchase(self):
        profile = self._build_profile(record_type="purchase")
        valid_fields = profile._get_model_fields()
        self.assertIn("date", valid_fields)
        self.assertIn("item_name", valid_fields)
        self.assertNotIn("id", valid_fields)
        self.assertNotIn("created_at", valid_fields)

    def test_created_at_and_updated_at_auto_set(self):
        profile = self._build_profile()
        profile.full_clean()
        profile.save()
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)

    def test_updated_at_changes_on_save(self):
        profile = self._build_profile()
        profile.full_clean()
        profile.save()
        first_updated = profile.updated_at
        profile.name = "Updated Name"
        profile.save()
        profile.refresh_from_db()
        self.assertGreaterEqual(profile.updated_at, first_updated)

    def test_ordering_by_name(self):
        self._build_profile(name="Zebra").save()
        self._build_profile(name="Alpha").save()
        profiles = list(CSVFormatProfile.objects.values_list("name", flat=True))
        self.assertEqual(profiles, ["Alpha", "Zebra"])

    def test_is_active_can_be_set_false(self):
        profile = self._build_profile(is_active=False)
        profile.full_clean()
        profile.save()
        self.assertFalse(profile.is_active)

    def test_custom_delimiter(self):
        profile = self._build_profile(delimiter=";")
        profile.full_clean()
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.delimiter, ";")

    def test_custom_date_format(self):
        profile = self._build_profile(date_format="%d/%m/%Y")
        profile.full_clean()
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.date_format, "%d/%m/%Y")

    def test_clean_rejects_non_integer_keys(self):
        mappings = {"header_name": "date", "1": "item_name"}
        profile = self._build_profile(field_mappings=mappings)
        with self.assertRaises(ValidationError) as ctx:
            profile.full_clean()
        self.assertIn("field_mappings", ctx.exception.message_dict)
        self.assertIn("header_name", str(ctx.exception.message_dict["field_mappings"]))
