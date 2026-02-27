import hashlib
import io
import json
import uuid as uuid_lib

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

from apps.records.models import CSVFormatProfile, CSVUpload, SalesRecord, PurchaseRecord


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
            "6": "shipping_cost",
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
        initial_count = CSVFormatProfile.objects.count()
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
        self.assertEqual(CSVFormatProfile.objects.count(), initial_count + 2)
        copy = CSVFormatProfile.objects.filter(name="Original Profile (copy)").first()
        self.assertIsNotNone(copy)
        self.assertEqual(copy.record_type, profile.record_type)
        self.assertEqual(copy.delimiter, profile.delimiter)
        self.assertEqual(copy.date_format, profile.date_format)
        self.assertEqual(copy.field_mappings, profile.field_mappings)

    def test_duplicate_multiple_profiles(self):
        initial_count = CSVFormatProfile.objects.count()
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
        self.assertEqual(CSVFormatProfile.objects.count(), initial_count + 4)
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
            ["date", "item_name", "quantity", "unit_price", "total_price", "post_code", "shipping_cost"],
            ["2024-01-15", "Widget A", "10", "5.00", "50.00", "SW1A 1AA", "3.50"],
            ["2024-02-20", "Widget B", "5", "12.00", "60.00", "EC1A 1BB", "2.00"],
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
            ["date", "item_name", "quantity", "unit_price", "total_price", "post_code", "shipping_cost"],
            ["not-a-date", "Widget A", "10", "5.00", "50.00", "SW1A 1AA", "3.50"],
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
        self.assertIn("invalid date format", data["errors"][0])

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
        rows = [["date", "item_name", "quantity", "unit_price", "total_price", "post_code", "shipping_cost"]]
        for i in range(15):
            rows.append([f"2024-01-{i+1:02d}", f"Item {i}", "1", "10.00", "10.00", "SW1A", "1.00"])
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
        csv_content = "date;item_name;quantity;unit_price;total_price;post_code;shipping_cost\n2024-01-15;Widget A;10;5.00;50.00;SW1A 1AA;3.50\n"
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


class CSVUploadAdminTestBase(TestCase):
    """Base class for CSV upload admin tests."""

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
            "6": "shipping_cost",
        }

    def _create_profile(self, record_type="sales", **overrides):
        defaults = {
            "name": "Test Profile",
            "record_type": record_type,
            "delimiter": ",",
            "date_format": "%Y-%m-%d",
            "field_mappings": self._valid_mappings(),
            "is_active": True,
        }
        defaults.update(overrides)
        return CSVFormatProfile.objects.create(**defaults)

    def _make_valid_csv(self):
        return b"date,item_name,quantity,unit_price,total_price,post_code,shipping_cost\n2024-01-15,Widget A,10,5.00,50.00,SW1A 1AA,3.50\n2024-02-20,Widget B,5,12.00,60.00,EC1A 1BB,2.00"

    def _make_all_invalid_csv(self):
        return b"date,item_name,quantity,unit_price,total_price,post_code,shipping_cost\nnot-a-date,Widget,abc,bad,bad,XYZ,bad"

    def _upload_csv(self, csv_content, record_type="sales", profile=None, confirm_duplicate=False):
        if profile is None:
            profile = self._create_profile(record_type=record_type)
        upload_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")
        data = {
            "file": upload_file,
            "record_type": record_type,
            "format_profile": profile.pk,
        }
        if confirm_duplicate:
            data["confirm_duplicate"] = "on"
        response = self.client.post(
            "/admin/records/csvupload/add/",
            data,
            follow=True,
        )
        return response

    def _get_messages(self, response):
        return [m.message for m in response.context["messages"]]

    def _get_messages_with_levels(self, response):
        return [(m.level, m.message) for m in response.context["messages"]]


class TestDeleteFailedUploads(CSVUploadAdminTestBase):
    """Feature 1: Delete failed CSV uploads automatically."""

    def test_zero_imports_deletes_upload_object(self):
        """A CSV that results in zero imported records causes the CSVUpload to be deleted."""
        csv_content = self._make_all_invalid_csv()
        self._upload_csv(csv_content)
        self.assertEqual(CSVUpload.objects.count(), 0)
        self.assertEqual(SalesRecord.objects.count(), 0)

    def test_zero_imports_shows_error_message(self):
        """When zero records are imported, an error message is shown."""
        csv_content = self._make_all_invalid_csv()
        response = self._upload_csv(csv_content)
        msgs = self._get_messages(response)
        self.assertTrue(any("Upload failed" in m for m in msgs))

    def test_unicode_error_deletes_upload_object(self):
        """A file with a UnicodeDecodeError causes the CSVUpload to be deleted."""
        profile = self._create_profile()
        # Create invalid UTF-8 bytes
        bad_bytes = b"\x80\x81\x82\x83\x84"
        upload_file = SimpleUploadedFile("bad.csv", bad_bytes, content_type="text/csv")
        self.client.post(
            "/admin/records/csvupload/add/",
            {
                "file": upload_file,
                "record_type": "sales",
                "format_profile": profile.pk,
            },
            follow=True,
        )
        self.assertEqual(CSVUpload.objects.count(), 0)

    def test_unicode_error_shows_error_message(self):
        """A UnicodeDecodeError shows an error message to the user."""
        profile = self._create_profile()
        bad_bytes = b"\x80\x81\x82\x83\x84"
        upload_file = SimpleUploadedFile("bad.csv", bad_bytes, content_type="text/csv")
        response = self.client.post(
            "/admin/records/csvupload/add/",
            {
                "file": upload_file,
                "record_type": "sales",
                "format_profile": profile.pk,
            },
            follow=True,
        )
        msgs = self._get_messages(response)
        self.assertTrue(any("File encoding error" in m for m in msgs))

    def test_successful_import_does_not_delete(self):
        """A successful import keeps the CSVUpload object."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content)
        self.assertEqual(CSVUpload.objects.count(), 1)
        self.assertEqual(SalesRecord.objects.count(), 2)


class TestImportedRecordIds(CSVUploadAdminTestBase):
    """Feature 2: Store imported record IDs and bulk-delete admin action."""

    def test_successful_import_stores_record_ids(self):
        """After a successful import, imported_record_ids contains the IDs of created records."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content)
        upload = CSVUpload.objects.first()
        self.assertEqual(len(upload.imported_record_ids), 2)
        # Verify the IDs actually correspond to existing SalesRecords
        for record_id in upload.imported_record_ids:
            self.assertTrue(SalesRecord.objects.filter(id=record_id).exists())

    def test_successful_import_stores_purchase_record_ids(self):
        """imported_record_ids works for purchase records too."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content, record_type="purchase")
        upload = CSVUpload.objects.first()
        self.assertEqual(len(upload.imported_record_ids), 2)
        for record_id in upload.imported_record_ids:
            self.assertTrue(PurchaseRecord.objects.filter(id=record_id).exists())

    def test_delete_imported_records_action_deletes_sales(self):
        """The delete_imported_records action deletes the correct SalesRecord rows."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content)
        upload = CSVUpload.objects.first()
        self.assertEqual(SalesRecord.objects.count(), 2)

        response = self.client.post(
            reverse("admin:records_csvupload_changelist"),
            {
                "action": "delete_imported_records",
                "_selected_action": [upload.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SalesRecord.objects.count(), 0)

    def test_delete_imported_records_action_deletes_purchases(self):
        """The delete_imported_records action deletes the correct PurchaseRecord rows."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content, record_type="purchase")
        upload = CSVUpload.objects.first()
        self.assertEqual(PurchaseRecord.objects.count(), 2)

        response = self.client.post(
            reverse("admin:records_csvupload_changelist"),
            {
                "action": "delete_imported_records",
                "_selected_action": [upload.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PurchaseRecord.objects.count(), 0)

    def test_delete_action_removes_upload_and_records(self):
        """After the action runs, the CSVUpload object and its associated records are deleted."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content)
        upload = CSVUpload.objects.first()
        self.assertEqual(CSVUpload.objects.count(), 1)

        self.client.post(
            reverse("admin:records_csvupload_changelist"),
            {
                "action": "delete_imported_records",
                "_selected_action": [upload.pk],
            },
            follow=True,
        )
        self.assertEqual(CSVUpload.objects.count(), 0)

    def test_delete_action_shows_success_message(self):
        """The action shows a success message with the count of deleted records and uploads."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content)
        upload = CSVUpload.objects.first()

        response = self.client.post(
            reverse("admin:records_csvupload_changelist"),
            {
                "action": "delete_imported_records",
                "_selected_action": [upload.pk],
            },
            follow=True,
        )
        msgs = self._get_messages(response)
        self.assertTrue(any("Deleted 2 records and 1 upload(s)" in m for m in msgs))

    def test_delete_action_with_empty_ids(self):
        """The action handles uploads with no imported_record_ids gracefully (still deletes upload)."""
        upload = CSVUpload.objects.create(
            file_name="test.csv",
            record_type="sales",
            imported_record_ids=[],
        )
        response = self.client.post(
            reverse("admin:records_csvupload_changelist"),
            {
                "action": "delete_imported_records",
                "_selected_action": [upload.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CSVUpload.objects.count(), 0)
        msgs = self._get_messages(response)
        self.assertTrue(any("Deleted 0 records and 1 upload(s)" in m for m in msgs))


class TestFileHashDuplicateDetection(CSVUploadAdminTestBase):
    """Feature 3: SHA-256 hash and duplicate upload blocking."""

    def test_successful_import_populates_file_hash(self):
        """After a successful import, file_hash is populated with the correct SHA-256 hash."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content)
        upload = CSVUpload.objects.first()
        # Compute expected hash
        decoded = csv_content.decode("utf-8-sig")
        expected_hash = hashlib.sha256(decoded.encode()).hexdigest()
        self.assertEqual(upload.file_hash, expected_hash)
        self.assertEqual(len(upload.file_hash), 64)

    def test_duplicate_upload_blocked_by_default(self):
        """Uploading the same file a second time blocks import and shows ERROR."""
        csv_content = self._make_valid_csv()
        profile = self._create_profile()
        self._upload_csv(csv_content, profile=profile)
        self.assertEqual(CSVUpload.objects.count(), 1)

        # Upload the same content again without confirming
        response = self._upload_csv(csv_content, profile=profile)
        # The duplicate upload should have been deleted
        self.assertEqual(CSVUpload.objects.count(), 1)
        self.assertEqual(SalesRecord.objects.count(), 2)  # No new records
        msgs = self._get_messages_with_levels(response)
        error_msgs = [m for level, m in msgs if level == messages.ERROR]
        self.assertTrue(any("duplicate" in m.lower() for m in error_msgs))

    def test_duplicate_upload_proceeds_with_confirmation(self):
        """Uploading a duplicate with confirm_duplicate checked proceeds normally."""
        csv_content = self._make_valid_csv()
        profile = self._create_profile()
        self._upload_csv(csv_content, profile=profile)
        self.assertEqual(CSVUpload.objects.count(), 1)

        # Upload same content with confirmation
        response = self._upload_csv(csv_content, profile=profile, confirm_duplicate=True)
        self.assertEqual(CSVUpload.objects.count(), 2)
        self.assertEqual(SalesRecord.objects.count(), 4)
        msgs = self._get_messages_with_levels(response)
        error_msgs = [m for level, m in msgs if level == messages.ERROR]
        self.assertFalse(any("duplicate" in m.lower() for m in error_msgs))

    def test_same_content_different_record_type_no_block(self):
        """Uploading a file with same content but different record_type does NOT trigger duplicate block."""
        csv_content = self._make_valid_csv()
        sales_profile = self._create_profile(record_type="sales", name="Sales Profile")
        purchase_profile = self._create_profile(record_type="purchase", name="Purchase Profile")

        self._upload_csv(csv_content, record_type="sales", profile=sales_profile)

        response = self._upload_csv(csv_content, record_type="purchase", profile=purchase_profile)
        # Should succeed without needing confirmation
        self.assertEqual(CSVUpload.objects.count(), 2)
        msgs = self._get_messages_with_levels(response)
        error_msgs = [m for level, m in msgs if level == messages.ERROR]
        self.assertFalse(any("duplicate" in m.lower() for m in error_msgs))

    def test_different_content_same_record_type_no_block(self):
        """Uploading a different file with the same record_type does NOT trigger duplicate block."""
        csv_content_1 = self._make_valid_csv()
        csv_content_2 = b"date,item_name,quantity,unit_price,total_price,post_code,shipping_cost\n2024-03-01,Different Item,1,1.00,1.00,SW1A 1AA,0.50"
        profile = self._create_profile()

        self._upload_csv(csv_content_1, profile=profile)
        response = self._upload_csv(csv_content_2, profile=profile)
        self.assertEqual(CSVUpload.objects.count(), 2)
        msgs = self._get_messages_with_levels(response)
        error_msgs = [m for level, m in msgs if level == messages.ERROR]
        self.assertFalse(any("duplicate" in m.lower() for m in error_msgs))


class TestDuplicateUUIDSkipping(CSVUploadAdminTestBase):
    """Tests for duplicate UUID skipping on CSV import."""

    def _make_csv_with_uuid(self, uuid_val):
        """Create a CSV with a uuid column mapped via a restore-from-backup profile."""
        return (
            f"uuid,date,item_name,quantity,unit_price,total_price,shipping_cost,post_code,currency\n"
            f"{uuid_val},2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA,GBP\n"
        ).encode("utf-8")

    def _create_restore_profile(self, record_type="sales"):
        return CSVFormatProfile.objects.create(
            name=f"Restore ({record_type})",
            record_type=record_type,
            delimiter=",",
            date_format="%Y-%m-%d",
            has_headers=True,
            is_active=True,
            field_mappings={
                "0": "uuid",
                "1": "date",
                "2": "item_name",
                "3": "quantity",
                "4": "unit_price",
                "5": "total_price",
                "6": "shipping_cost",
                "7": "post_code",
                "8": "currency",
            },
        )

    def test_duplicate_uuid_skipped_on_import(self):
        """Uploading the same CSV twice results in 0 new records on the second upload,
        and the skipped count appears in the admin message."""
        test_uuid = str(uuid_lib.uuid4())
        csv_content = self._make_csv_with_uuid(test_uuid)
        profile = self._create_restore_profile()

        # First upload
        response1 = self._upload_csv(csv_content, profile=profile)
        self.assertEqual(SalesRecord.objects.count(), 1)
        self.assertEqual(CSVUpload.objects.count(), 1)

        # Second upload (same UUID) - need to confirm duplicate since file hash matches
        response2 = self._upload_csv(csv_content, profile=profile, confirm_duplicate=True)
        # Still only 1 record because UUID was duplicate
        self.assertEqual(SalesRecord.objects.count(), 1)
        # The second upload should have been deleted (0 records created)
        self.assertEqual(CSVUpload.objects.count(), 1)

    def test_duplicate_uuid_shows_skipped_message(self):
        """The skipped count appears in the admin message."""
        test_uuid = str(uuid_lib.uuid4())
        csv_content = self._make_csv_with_uuid(test_uuid)
        profile = self._create_restore_profile()

        # First upload
        self._upload_csv(csv_content, profile=profile)

        # Create a CSV with mix of new and duplicate UUIDs
        new_uuid = str(uuid_lib.uuid4())
        csv_content_mixed = (
            f"uuid,date,item_name,quantity,unit_price,total_price,shipping_cost,post_code,currency\n"
            f"{test_uuid},2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA,GBP\n"
            f"{new_uuid},2024-02-20,Widget B,5,12.00,60.00,4.00,EC1A 1BB,USD\n"
        ).encode("utf-8")

        response = self._upload_csv(csv_content_mixed, profile=profile, confirm_duplicate=True)
        self.assertEqual(SalesRecord.objects.count(), 2)
        msgs = self._get_messages(response)
        self.assertTrue(any("skipped" in m.lower() for m in msgs))
        self.assertTrue(any("duplicate uuid" in m.lower() for m in msgs))

    def test_csv_without_uuid_column_works_normally(self):
        """CSV without uuid column still creates records normally."""
        csv_content = self._make_valid_csv()
        self._upload_csv(csv_content)
        self.assertEqual(SalesRecord.objects.count(), 2)


class TestBackupRestoreImport(CSVUploadAdminTestBase):
    """Tests for restore-from-backup CSV import with source column and UUID dedup."""

    def _create_restore_profile(self, record_type="sales"):
        return CSVFormatProfile.objects.create(
            name=f"Restore from Backup ({record_type.title()})",
            record_type=record_type,
            delimiter=",",
            date_format="%Y-%m-%d",
            has_headers=True,
            is_active=True,
            field_mappings={
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
            },
        )

    def _make_backup_csv(self, uuid_val, source_name="Test Source"):
        return (
            f"uuid,date,item_name,quantity,unit_price,total_price,shipping_cost,post_code,currency,source\n"
            f"{uuid_val},2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA,GBP,{source_name}\n"
        ).encode("utf-8")

    def _upload_backup_csv(self, csv_content, record_type="sales", profile=None, confirm_duplicate=False):
        if profile is None:
            profile = self._create_restore_profile(record_type=record_type)
        upload_file = SimpleUploadedFile("backup.csv", csv_content, content_type="text/csv")
        data = {
            "file": upload_file,
            "record_type": record_type,
            "format_profile": profile.pk,
            "restore_from_backup": "on",
        }
        if confirm_duplicate:
            data["confirm_duplicate"] = "on"
        response = self.client.post(
            "/admin/records/csvupload/add/",
            data,
            follow=True,
        )
        return response

    def test_backup_import_creates_source_from_csv(self):
        """Restore from backup creates Source objects from the CSV source column."""
        from apps.records.models import Source
        test_uuid = str(uuid_lib.uuid4())
        csv_content = self._make_backup_csv(test_uuid, source_name="My Backup Source")
        profile = self._create_restore_profile()

        self._upload_backup_csv(csv_content, profile=profile)

        self.assertEqual(SalesRecord.objects.count(), 1)
        record = SalesRecord.objects.first()
        self.assertIsNotNone(record.source)
        self.assertEqual(record.source.name, "My Backup Source")
        self.assertTrue(Source.objects.filter(name="My Backup Source").exists())

    def test_backup_import_ignores_source_dropdown(self):
        """When restore_from_backup is checked, source from CSV is used, not the dropdown."""
        from apps.records.models import Source
        dropdown_source = Source.objects.create(name="Dropdown Source")
        test_uuid = str(uuid_lib.uuid4())
        csv_content = self._make_backup_csv(test_uuid, source_name="CSV Source")
        profile = self._create_restore_profile()

        upload_file = SimpleUploadedFile("backup.csv", csv_content, content_type="text/csv")
        self.client.post(
            "/admin/records/csvupload/add/",
            {
                "file": upload_file,
                "record_type": "sales",
                "format_profile": profile.pk,
                "source": dropdown_source.pk,
                "restore_from_backup": "on",
            },
            follow=True,
        )

        record = SalesRecord.objects.first()
        self.assertIsNotNone(record.source)
        self.assertEqual(record.source.name, "CSV Source")

    def test_backup_import_skips_duplicate_uuids(self):
        """Restore from backup skips records with duplicate UUIDs."""
        test_uuid = str(uuid_lib.uuid4())
        csv_content = self._make_backup_csv(test_uuid)
        profile = self._create_restore_profile()

        # First upload
        self._upload_backup_csv(csv_content, profile=profile)
        self.assertEqual(SalesRecord.objects.count(), 1)

        # Second upload (same UUID)
        self._upload_backup_csv(csv_content, profile=profile, confirm_duplicate=True)
        # Still only 1 record
        self.assertEqual(SalesRecord.objects.count(), 1)

    def test_backup_import_success_message(self):
        """Restore from backup shows 'restored' in success message."""
        test_uuid = str(uuid_lib.uuid4())
        csv_content = self._make_backup_csv(test_uuid)
        profile = self._create_restore_profile()

        response = self._upload_backup_csv(csv_content, profile=profile)
        msgs = self._get_messages(response)
        self.assertTrue(any("restored" in m.lower() for m in msgs))

    def test_backup_import_without_source_column(self):
        """Backup import with CSV that has no source column still works."""
        test_uuid = str(uuid_lib.uuid4())
        # CSV without source column (use profile without source mapping)
        profile = CSVFormatProfile.objects.create(
            name="Restore no source",
            record_type="sales",
            delimiter=",",
            date_format="%Y-%m-%d",
            has_headers=True,
            is_active=True,
            field_mappings={
                "0": "uuid",
                "1": "date",
                "2": "item_name",
                "3": "quantity",
                "4": "unit_price",
                "5": "total_price",
                "6": "shipping_cost",
                "7": "post_code",
                "8": "currency",
            },
        )
        csv_content = (
            f"uuid,date,item_name,quantity,unit_price,total_price,shipping_cost,post_code,currency\n"
            f"{test_uuid},2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA,GBP\n"
        ).encode("utf-8")

        self._upload_backup_csv(csv_content, profile=profile)
        self.assertEqual(SalesRecord.objects.count(), 1)
        record = SalesRecord.objects.first()
        self.assertIsNone(record.source)

    def test_backup_import_reuses_existing_source(self):
        """If a Source with the same name already exists, it reuses it."""
        from apps.records.models import Source
        existing_source = Source.objects.create(name="Existing Source")
        test_uuid = str(uuid_lib.uuid4())
        csv_content = self._make_backup_csv(test_uuid, source_name="Existing Source")
        profile = self._create_restore_profile()

        self._upload_backup_csv(csv_content, profile=profile)

        record = SalesRecord.objects.first()
        self.assertEqual(record.source.pk, existing_source.pk)
        # Should not have created a duplicate Source
        self.assertEqual(Source.objects.filter(name="Existing Source").count(), 1)
