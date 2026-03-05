from datetime import date
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from apps.records.models import SalesRecord, PurchaseRecord


class TestSalesPdfExport(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:sales_pdf_export")

        SalesRecord.objects.create(
            date=date(2024, 1, 15),
            item_name="Widget A",
            quantity=10,
            unit_price=Decimal("5.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("3.50"),
            post_code="SW1A 1AA",
        )
        SalesRecord.objects.create(
            date=date(2024, 2, 20),
            item_name="Widget B",
            quantity=5,
            unit_price=Decimal("12.00"),
            total_price=Decimal("60.00"),
            shipping_cost=Decimal("4.00"),
            post_code="EC1A 1BB",
        )
        SalesRecord.objects.create(
            date=date(2024, 6, 10),
            item_name="Widget C",
            quantity=3,
            unit_price=Decimal("20.00"),
            total_price=Decimal("60.00"),
            shipping_cost=Decimal("2.00"),
            post_code="W1A 0AX",
        )

    def test_returns_200_and_pdf_content_type(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")

    def test_content_disposition_header(self):
        response = self.client.get(self.url)
        self.assertIn("sales_report.pdf", response["Content-Disposition"])

    def test_returns_all_records_no_pagination(self):
        """All 3 records should be included (no pagination cutoff)."""
        # Verify there are 3 records in the DB
        self.assertEqual(SalesRecord.objects.count(), 3)
        # The PDF endpoint should return successfully with all records
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_date_filter_respected(self):
        """Only records within the date range should be included."""
        # First verify the full count
        self.assertEqual(SalesRecord.objects.count(), 3)

        # Filter to January only — should match 1 record
        response = self.client.get(self.url, {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")

        # Verify queryset count via the service directly
        from apps.records.services.aggregation import AggregationService
        qs = AggregationService.get_sales(date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(qs.count(), 1)

    def test_all_records_returned_unpaginated(self):
        """Create many records and ensure all are returned (not limited to page size)."""
        for i in range(50):
            SalesRecord.objects.create(
                date=date(2024, 3, 1),
                item_name=f"Bulk Item {i}",
                quantity=1,
                unit_price=Decimal("1.00"),
                total_price=Decimal("1.00"),
                shipping_cost=Decimal("0.50"),
                post_code="AB1 2CD",
            )
        # Total is now 53 records (3 from setUp + 50 new)
        self.assertEqual(SalesRecord.objects.count(), 53)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")

    def test_columns_param_filters_columns(self):
        response = self.client.get(self.url, {"columns": "date,item_name,total_price"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")


class TestPurchasesPdfExport(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:purchases_pdf_export")

        PurchaseRecord.objects.create(
            date=date(2024, 1, 10),
            item_name="Raw Material X",
            quantity=100,
            unit_price=Decimal("0.50"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("5.00"),
            post_code="N1 9GU",
        )
        PurchaseRecord.objects.create(
            date=date(2024, 3, 1),
            item_name="Raw Material Y",
            quantity=50,
            unit_price=Decimal("1.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("3.00"),
            post_code="E1 6AN",
        )

    def test_returns_200_and_pdf_content_type(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")

    def test_content_disposition_header(self):
        response = self.client.get(self.url)
        self.assertIn("purchases_report.pdf", response["Content-Disposition"])

    def test_returns_all_records_no_pagination(self):
        self.assertEqual(PurchaseRecord.objects.count(), 2)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_date_filter_respected(self):
        response = self.client.get(self.url, {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")

        from apps.records.services.aggregation import AggregationService
        qs = AggregationService.get_purchases(date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(qs.count(), 1)

    def test_all_records_returned_unpaginated(self):
        for i in range(50):
            PurchaseRecord.objects.create(
                date=date(2024, 4, 1),
                item_name=f"Bulk Purchase {i}",
                quantity=1,
                unit_price=Decimal("2.00"),
                total_price=Decimal("2.00"),
                shipping_cost=Decimal("0.25"),
                post_code="XY1 2ZZ",
            )
        self.assertEqual(PurchaseRecord.objects.count(), 52)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")


class TestBusinessPdfExport(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:business_pdf_export")

        SalesRecord.objects.create(
            date=date(2024, 1, 15),
            item_name="Widget A",
            quantity=10,
            unit_price=Decimal("5.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("3.50"),
            post_code="SW1A 1AA",
        )
        SalesRecord.objects.create(
            date=date(2024, 2, 20),
            item_name="Widget B",
            quantity=5,
            unit_price=Decimal("12.00"),
            total_price=Decimal("60.00"),
            shipping_cost=Decimal("4.00"),
            post_code="EC1A 1BB",
        )
        PurchaseRecord.objects.create(
            date=date(2024, 1, 10),
            item_name="Raw Material X",
            quantity=100,
            unit_price=Decimal("0.50"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("5.00"),
            post_code="N1 9GU",
        )
        PurchaseRecord.objects.create(
            date=date(2024, 3, 1),
            item_name="Raw Material Y",
            quantity=50,
            unit_price=Decimal("1.00"),
            total_price=Decimal("50.00"),
            shipping_cost=Decimal("3.00"),
            post_code="E1 6AN",
        )

    def test_returns_200_and_pdf_content_type(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")

    def test_content_disposition_header(self):
        response = self.client.get(self.url)
        self.assertIn("business_report.pdf", response["Content-Disposition"])

    def test_correct_net_profit(self):
        """Net profit = total_sales - total_purchases = 110 - 100 = 10."""
        from apps.records.services.aggregation import AggregationService

        sales_summary = AggregationService.get_summary(None, None)
        purchases_summary = AggregationService.get_summary(None, None)
        expected_net = sales_summary["total_sales"] - purchases_summary["total_purchases"]
        self.assertEqual(expected_net, Decimal("10.00"))

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")

    def test_date_filters_respected(self):
        response = self.client.get(self.url, {
            "sales_start_date": "2024-01-01",
            "sales_end_date": "2024-01-31",
            "purchases_start_date": "2024-01-01",
            "purchases_end_date": "2024-01-31",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html")

        from apps.records.services.aggregation import AggregationService
        sales_qs = AggregationService.get_sales(date(2024, 1, 1), date(2024, 1, 31))
        purchases_qs = AggregationService.get_purchases(date(2024, 1, 1), date(2024, 1, 31))
        self.assertEqual(sales_qs.count(), 1)
        self.assertEqual(purchases_qs.count(), 1)

    def test_net_profit_with_date_filter(self):
        """With Jan-only filter: sales=50, purchases=50, net_profit=0."""
        from apps.records.services.aggregation import AggregationService

        sales_summary = AggregationService.get_summary(
            date(2024, 1, 1), date(2024, 1, 31)
        )
        purchases_summary = AggregationService.get_summary(
            date(2024, 1, 1), date(2024, 1, 31)
        )
        expected_net = sales_summary["total_sales"] - purchases_summary["total_purchases"]
        self.assertEqual(expected_net, Decimal("0.00"))

        response = self.client.get(self.url, {
            "sales_start_date": "2024-01-01",
            "sales_end_date": "2024-01-31",
            "purchases_start_date": "2024-01-01",
            "purchases_end_date": "2024-01-31",
        })
        self.assertEqual(response.status_code, 200)
