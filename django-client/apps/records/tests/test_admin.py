import io
import json

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from apps.records.models import CSVFormatProfile


class CSVFormatProfileAdminTestBase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin", password="adminpass", email="admin@test.com"
        )
        self.client.login(username="admin", password="adminpass")

    def _valid_mappings(self):
        return {
            "0": "date",
            "1": "item_name",
            "2": "quantity",
            "3": "unit_price",
            "4": "total_price",
            "5": "post_code",
        }

    def _create_profile(self, **overrides):
        defaults = {
            "name": "Test Profile",
            "record_type": "sales",
            "delimiter": ",",
            "date_format": "%Y-%m-%d",
            "field_mappings": self._valid_mappings(),
            "is_active": True,
        }
        defaults.update(overrides)
        return CSVFormatProfile.objects.create(**defaults)


class TestCSVFormatProfileAdminActions(CSVFormatProfileAdminTestBase):
    def _changelist_url(self):
        return reverse("admin:records_csvformatprofile_changelist")

    def test_duplicate_profile_action(self):
        profile = self._create_profile(name="Original Profile")
        response = self.client.post(
            self._changelist_url(),
            {
                "action": "duplicate_profile",
                "_selected_action": [profile.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CSVFormatProfile.objects.count(), 2)
        copy = CSVFormatProfile.objects.exclude(pk=profile.pk).first()
        self.assertEqual(copy.name, "Original Profile (copy)")
        self.assertEqual(copy.record_type, profile.record_type)
        self.assertEqual(copy.delimiter, profile.delimiter)
        self.assertEqual(copy.date_format, profile.date_format)
        self.assertEqual(copy.field_mappings, profile.field_mappings)

    def test_duplicate_multiple_profiles(self):
        p1 = self._create_profile(name="Profile A")
        p2 = self._create_profile(name="Profile B")
        response = self.client.post(
            self._changelist_url(),
            {
                "action": "duplicate_profile",
                "_selected_action": [p1.pk, p2.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CSVFormatProfile.objects.count(), 4)
        self.assertTrue(CSVFormatProfile.objects.filter(name="Profile A (copy)").exists())
        self.assertTrue(CSVFormatProfile.objects.filter(name="Profile B (copy)").exists())

    def test_deactivate_profiles_action(self):
        p1 = self._create_profile(name="Active 1", is_active=True)
        p2 = self._create_profile(name="Active 2", is_active=True)
        response = self.client.post(
            self._changelist_url(),
            {
                "action": "deactivate_profiles",
                "_selected_action": [p1.pk, p2.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertFalse(p1.is_active)
        self.assertFalse(p2.is_active)

    def test_activate_profiles_action(self):
        p1 = self._create_profile(name="Inactive 1", is_active=False)
        p2 = self._create_profile(name="Inactive 2", is_active=False)
        response = self.client.post(
            self._changelist_url(),
            {
                "action": "activate_profiles",
                "_selected_action": [p1.pk, p2.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertTrue(p1.is_active)
        self.assertTrue(p2.is_active)

    def test_deactivate_then_activate(self):
        profile = self._create_profile(is_active=True)
        self.client.post(
            self._changelist_url(),
            {
                "action": "deactivate_profiles",
                "_selected_action": [profile.pk],
            },
            follow=True,
        )
        profile.refresh_from_db()
        self.assertFalse(profile.is_active)
        self.client.post(
            self._changelist_url(),
            {
                "action": "activate_profiles",
                "_selected_action": [profile.pk],
            },
            follow=True,
        )
        profile.refresh_from_db()
        self.assertTrue(profile.is_active)


class TestCSVFormatProfileAdminForm(CSVFormatProfileAdminTestBase):
    def _add_url(self):
        return reverse("admin:records_csvformatprofile_add")

    def _change_url(self, pk):
        return reverse("admin:records_csvformatprofile_change", args=[pk])

    def test_add_form_loads(self):
        response = self.client.get(self._add_url())
        self.assertEqual(response.status_code, 200)

    def test_change_form_loads(self):
        profile = self._create_profile()
        response = self.client.get(self._change_url(profile.pk))
        self.assertEqual(response.status_code, 200)

    def test_change_form_contains_help_text(self):
        profile = self._create_profile()
        response = self.client.get(self._change_url(profile.pk))
        content = response.content.decode()
        self.assertIn("strftime", content)
        self.assertIn("%Y-%m-%d", content)
        self.assertIn("delimiter", content.lower())

    def test_change_form_contains_test_csv_section(self):
        profile = self._create_profile()
        response = self.client.get(self._change_url(profile.pk))
        content = response.content.decode()
        self.assertIn("Test with Sample CSV", content)

    def test_add_form_does_not_contain_test_csv_section(self):
        response = self.client.get(self._add_url())
        content = response.content.decode()
        self.assertNotIn("Test with Sample CSV", content)

    def test_form_contains_field_mappings_editor(self):
        profile = self._create_profile()
        response = self.client.get(self._change_url(profile.pk))
        content = response.content.decode()
        self.assertIn("field-mappings-editor", content)

    def test_form_contains_model_fields_reference(self):
        profile = self._create_profile()
        response = self.client.get(self._change_url(profile.pk))
        content = response.content.decode()
        self.assertIn("fields-reference", content)

    def test_fieldsets_present(self):
        profile = self._create_profile()
        response = self.client.get(self._change_url(profile.pk))
        content = response.content.decode()
        self.assertIn("CSV Format Settings", content)
        self.assertIn("Field Mappings", content)


class TestCSVFormatProfileTestCSVView(CSVFormatProfileAdminTestBase):
    def _test_csv_url(self, profile_id):
        return reverse("admin:records_csvformatprofile_test_csv", args=[profile_id])

    def _make_csv_content(self, rows):
        output = io.StringIO()
        for row in rows:
            output.write(",".join(row) + "\n")
        return output.getvalue().encode("utf-8")

    def test_test_csv_requires_post(self):
        profile = self._create_profile()
        response = self.client.get(self._test_csv_url(profile.pk))
        self.assertEqual(response.status_code, 405)

    def test_test_csv_requires_file(self):
        profile = self._create_profile()
        response = self.client.post(self._test_csv_url(profile.pk))
        self.assertEqual(response.status_code, 400)

    def test_test_csv_profile_not_found(self):
        response = self.client.post(self._test_csv_url(99999))
        self.assertEqual(response.status_code, 404)

    def test_test_csv_valid_file(self):
        profile = self._create_profile()
        csv_content = self._make_csv_content([
            ["date", "item_name", "quantity", "unit_price", "total_price", "post_code"],
            ["2024-01-15", "Widget A", "10", "5.00", "50.00", "SW1A 1AA"],
            ["2024-02-20", "Widget B", "5", "12.00", "60.00", "EC1A 1BB"],
        ])
        csv_file = io.BytesIO(csv_content)
        csv_file.name = "test.csv"
        response = self.client.post(
            self._test_csv_url(profile.pk),
            {"csv_file": csv_file},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["total_parsed"], 2)
        self.assertEqual(len(data["preview"]), 2)
        self.assertEqual(len(data["errors"]), 0)

    def test_test_csv_with_parsing_errors(self):
        profile = self._create_profile()
        csv_content = self._make_csv_content([
            ["date", "item_name", "quantity", "unit_price", "total_price", "post_code"],
            ["not-a-date", "Widget A", "10", "5.00", "50.00", "SW1A 1AA"],
        ])
        csv_file = io.BytesIO(csv_content)
        csv_file.name = "test.csv"
        response = self.client.post(
            self._test_csv_url(profile.pk),
            {"csv_file": csv_file},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(len(data["errors"]) > 0)
        self.assertIn("Invalid date", data["errors"][0])

    def test_test_csv_empty_file(self):
        profile = self._create_profile()
        csv_file = io.BytesIO(b"")
        csv_file.name = "empty.csv"
        response = self.client.post(
            self._test_csv_url(profile.pk),
            {"csv_file": csv_file},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("error", data)

    def test_test_csv_preview_limited_to_10_rows(self):
        profile = self._create_profile()
        rows = [["date", "item_name", "quantity", "unit_price", "total_price", "post_code"]]
        for i in range(15):
            rows.append([f"2024-01-{i+1:02d}", f"Item {i}", "1", "10.00", "10.00", "SW1A"])
        csv_content = self._make_csv_content(rows)
        csv_file = io.BytesIO(csv_content)
        csv_file.name = "test.csv"
        response = self.client.post(
            self._test_csv_url(profile.pk),
            {"csv_file": csv_file},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["total_parsed"], 15)
        self.assertEqual(len(data["preview"]), 10)

    def test_test_csv_with_semicolon_delimiter(self):
        profile = self._create_profile(delimiter=";")
        csv_content = "date;item_name;quantity;unit_price;total_price;post_code\n2024-01-15;Widget A;10;5.00;50.00;SW1A 1AA\n"
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "test.csv"
        response = self.client.post(
            self._test_csv_url(profile.pk),
            {"csv_file": csv_file},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["total_parsed"], 1)
        self.assertEqual(len(data["errors"]), 0)

    def test_test_csv_requires_login(self):
        self.client.logout()
        profile = self._create_profile()
        response = self.client.post(self._test_csv_url(profile.pk))
        self.assertEqual(response.status_code, 302)
