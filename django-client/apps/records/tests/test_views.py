from datetime import date
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from apps.records.models import SalesRecord, PurchaseRecord


class TestDashboardView(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("records:dashboard")

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

    def test_dashboard_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "records/dashboard.html")

    def test_dashboard_with_date_filter(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-01-31"}
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("50.00"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("50.00"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("0.00"))
        self.assertEqual(context["summary"]["sales_count"], 1)
        self.assertEqual(context["summary"]["purchases_count"], 1)

    def test_dashboard_full_range(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("110.00"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("100.00"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("10.00"))
        self.assertEqual(context["summary"]["sales_count"], 2)
        self.assertEqual(context["summary"]["purchases_count"], 2)

    def test_dashboard_no_results(self):
        response = self.client.get(
            self.url, {"start_date": "2025-01-01", "end_date": "2025-12-31"}
        )
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertEqual(context["summary"]["total_sales"], Decimal("0"))
        self.assertEqual(context["summary"]["total_purchases"], Decimal("0"))
        self.assertEqual(context["summary"]["net_profit"], Decimal("0"))

    def test_dashboard_invalid_dates_use_defaults(self):
        response = self.client.get(
            self.url, {"start_date": "not-a-date", "end_date": "also-bad"}
        )
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_records_in_template(self):
        response = self.client.get(
            self.url, {"start_date": "2024-01-01", "end_date": "2024-12-31"}
        )
        self.assertContains(response, "Widget A")
        self.assertContains(response, "Widget B")
        self.assertContains(response, "Raw Material X")
        self.assertContains(response, "Raw Material Y")
