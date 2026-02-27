import csv
import io
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from apps.records.models import PurchaseRecord, SalesRecord
from apps.records.services.csv_parser import DefaultCSVParser
from apps.records.services.export_service import (
    CSV_COLUMNS,
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
        """CSV headers must match canonical order with uuid first."""
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        expected = [
            "uuid", "date", "item_name", "quantity", "unit_price",
            "total_price", "shipping_cost", "post_code", "currency", "source",
        ]
        self.assertEqual(headers, expected)

    def test_csv_sales_only(self):
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        next(reader)  # skip headers
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        # uuid is column 0, item_name is column 2
        self.assertEqual(rows[0][2], "Widget A")

    def test_csv_purchase_only(self):
        result = export_records_as_csv("purchase")
        reader = csv.reader(io.StringIO(result))
        next(reader)  # skip headers
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        # uuid is column 0, item_name is column 2
        self.assertEqual(rows[0][2], "Raw Material X")

    def test_csv_sales_and_purchase_separate(self):
        """Sales and purchase exports are separate — no 'all' option."""
        sales_result = export_records_as_csv("sales")
        purchase_result = export_records_as_csv("purchase")
        sales_reader = csv.reader(io.StringIO(sales_result))
        purchase_reader = csv.reader(io.StringIO(purchase_result))
        next(sales_reader)  # skip headers
        next(purchase_reader)  # skip headers
        self.assertEqual(len(list(sales_reader)), 1)
        self.assertEqual(len(list(purchase_reader)), 1)

    def test_csv_date_format(self):
        """Dates must be formatted as %Y-%m-%d for round-trip compatibility."""
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        next(reader)
        row = next(reader)
        # uuid is column 0, date is column 1
        self.assertEqual(row[1], "2024-03-15")

    def test_csv_empty_result(self):
        """When no records exist for a type, CSV should have only headers."""
        SalesRecord.objects.all().delete()
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        self.assertEqual(headers, CSV_COLUMNS)
        rows = list(reader)
        self.assertEqual(len(rows), 0)

    def test_csv_uuid_is_first_column(self):
        """The first column in the exported CSV header row is uuid."""
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        headers = next(reader)
        self.assertEqual(headers[0], "uuid")

    def test_csv_uuid_values_are_valid(self):
        """Each exported row has a valid UUID in the first column."""
        import uuid as uuid_lib
        result = export_records_as_csv("sales")
        reader = csv.reader(io.StringIO(result))
        next(reader)  # skip headers
        for row in reader:
            uuid_lib.UUID(row[0])  # will raise ValueError if invalid


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

    def test_round_trip_export_reimport_zero_new_records(self):
        """Exporting records and re-importing the CSV creates 0 new records
        (all skipped due to UUID match)."""
        csv_content = export_records_as_csv("sales")

        # Parse with legacy parser (has uuid column)
        parser = DefaultCSVParser()
        records, errors = parser._parse_legacy(csv_content)
        self.assertEqual(errors, [])
        self.assertEqual(len(records), 1)

        # Try to create records - should be skipped since UUID already exists
        original_count = SalesRecord.objects.count()
        created = 0
        skipped = 0
        for record_data in records:
            if "uuid" in record_data:
                if SalesRecord.objects.filter(uuid=record_data["uuid"]).exists():
                    skipped += 1
                    continue
            SalesRecord.objects.create(**record_data)
            created += 1

        self.assertEqual(created, 0)
        self.assertEqual(skipped, 1)
        self.assertEqual(SalesRecord.objects.count(), original_count)


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

class TestDashboardExportUI(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:dashboard")

    def test_dashboard_has_export_section(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Export Data")
        self.assertContains(response, "Export CSV")

    def test_dashboard_has_table_select(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<option value="sales">Sales</option>')
        self.assertContains(response, '<option value="purchases">Purchases</option>')
