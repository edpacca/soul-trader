import csv
import io
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from apps.records.models import PurchaseRecord, SalesRecord
from apps.records.services.csv_parser import DefaultCSVParser
from apps.records.services.export_service import (
    CSV_COLUMNS,
    export_db_dump,
    export_records_as_csv,
)


class TestExportRecordsAsCSV(TestCase):
    def setUp(self):
        SalesRecord.objects.create(
            date=date(2024, 3, 15),
            item_name="Widget A",
            quantity=10,
            unit_price=Decimal("5.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("3.50"),
            post_code="SW1A 1AA",
            currency="GBP",
        )
        PurchaseRecord.objects.create(
            date=date(2024, 4, 1),
            item_name="Raw Material X",
            quantity=100,
            unit_price=Decimal("0.50"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("5.00"),
            post_code="N1 9GU",
            currency="USD",
        )

    def test_csv_headers_match_canonical_order(self):
        """CSV headers must match REQUIRED_FIELDS + currency in the correct order."""
        result = export_records_as_csv("all")
        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        expected = [
            "date", "item_name", "quantity", "unit_price",
            "total_price", "shipping_cost", "post_code", "currency",
        ]
        self.assertEqual(headers, expected)

    def test_csv_sales_only(self):
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        next(reader)  # skip headers
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Widget A")

    def test_csv_purchase_only(self):
        result = export_records_as_csv("purchase")
        reader = csv.reader(io.StringIO(result))
        next(reader)  # skip headers
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Raw Material X")

    def test_csv_all_records(self):
        result = export_records_as_csv("all")
        reader = csv.reader(io.StringIO(result))
        next(reader)  # skip headers
        rows = list(reader)
        self.assertEqual(len(rows), 2)

    def test_csv_date_format(self):
        """Dates must be formatted as %Y-%m-%d for round-trip compatibility."""
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        self.assertEqual(row[0], "2024-03-15")

    def test_csv_empty_result(self):
        """When no records exist for a type, CSV should have only headers."""
        SalesRecord.objects.all().delete()
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        self.assertEqual(headers, CSV_COLUMNS)
        rows = list(reader)
        self.assertEqual(len(rows), 0)


class TestCSVRoundTrip(TestCase):
    """Export records via export_records_as_csv then re-import via DefaultCSVParser."""

    def setUp(self):
        SalesRecord.objects.create(
            date=date(2024, 6, 10),
            item_name="Round-trip Item",
            quantity=7,
            unit_price=Decimal("12.50"),
            total_price=Decimal("87.50"),
            shipping_cost=Decimal("4.25"),
            post_code="EC2A 1NT",
            currency="EUR",
        )

    def test_round_trip_export_import(self):
        csv_content = export_records_as_csv("sales")

        parser = DefaultCSVParser()
        records, errors = parser._parse_legacy(csv_content)

        self.assertEqual(errors, [])
        self.assertEqual(len(records), 1)

        record = records[0]
        self.assertEqual(record["date"], date(2024, 6, 10))
        self.assertEqual(record["item_name"], "Round-trip Item")
        self.assertEqual(record["quantity"], 7)
        self.assertEqual(record["unit_price"], Decimal("12.50"))
        self.assertEqual(record["total_price"], Decimal("87.50"))
        self.assertEqual(record["shipping_cost"], Decimal("4.25"))
        self.assertEqual(record["post_code"], "EC2A 1NT")
        self.assertEqual(record["currency"], "EUR")


class TestExportDbDump(TestCase):

    @patch("apps.records.services.export_service.subprocess.run")
    def test_pg_dump_error_raises_runtime_error(self, mock_run):
        """When pg_dump exits non-zero, export_db_dump must raise RuntimeError."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr=b"pg_dump: error: connection refused",
            stdout=b"",
        )
        with self.assertRaises(RuntimeError) as ctx:
            export_db_dump()
        self.assertIn("pg_dump failed", str(ctx.exception))
        self.assertIn("connection refused", str(ctx.exception))

    @override_settings(DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    })
    def test_sqlite_guard_raises_error(self):
        """export_db_dump must raise RuntimeError when engine is not PostgreSQL."""
        with self.assertRaises(RuntimeError) as ctx:
            export_db_dump()
        self.assertIn("only supported for PostgreSQL", str(ctx.exception))
        self.assertIn("sqlite3", str(ctx.exception))


class TestExportViews(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = Client()

        SalesRecord.objects.create(
            date=date(2024, 1, 15),
            item_name="View Widget",
            quantity=5,
            unit_price=Decimal("10.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("2.00"),
            post_code="SW1A 1AA",
        )

    def test_export_csv_requires_login(self):
        url = reverse("records:export_csv")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_export_dump_requires_login(self):
        url = reverse("records:export_dump")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_export_csv_returns_csv_response(self):
        self.client.login(username="testuser", password="testpass123")
        url = reverse("records:export_csv")
        response = self.client.get(url, {"table": "sales"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("export_sales_", response["Content-Disposition"])
        self.assertIn(".csv", response["Content-Disposition"])

    def test_export_csv_default_table_is_all(self):
        self.client.login(username="testuser", password="testpass123")
        url = reverse("records:export_csv")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("export_all_", response["Content-Disposition"])

    @patch("apps.records.views.export_records_as_csv", side_effect=Exception("boom"))
    def test_export_csv_error_redirects_with_message(self, mock_export):
        self.client.login(username="testuser", password="testpass123")
        url = reverse("records:export_csv")
        response = self.client.get(url, {"table": "sales"})
        self.assertEqual(response.status_code, 302)

    @patch("apps.records.views.export_db_dump", side_effect=Exception("db error"))
    def test_export_dump_error_redirects_with_message(self, mock_export):
        self.client.login(username="testuser", password="testpass123")
        url = reverse("records:export_dump")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class TestDashboardExportUI(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:dashboard")

    def test_dashboard_has_export_section(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Export Data")
        self.assertContains(response, "Export CSV")
        self.assertContains(response, "Download DB Dump")

    def test_dashboard_has_table_select(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<option value="sales">Sales</option>')
        self.assertContains(response, '<option value="purchases">Purchases</option>')
        self.assertContains(response, '<option value="all">All</option>')
